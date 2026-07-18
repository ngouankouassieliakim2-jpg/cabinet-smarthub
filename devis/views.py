import json
from datetime import date
from django.shortcuts import render, get_object_or_404, redirect
from django.forms import modelform_factory
from django import forms
from .models import Devis, LignePrestation, Associe, Facture, LigneFacture
from .ia import generer_note_explicative, analyser_dossier
from parametres.models import CategoriePrestation, PrestationCatalogue
from django.http import HttpResponse
from django.contrib import messages
from .pdf import generer_pdf_devis
from django.contrib.auth.decorators import login_required
from comptes.decorators import role_requis
from comptes.models import Profil
from pilotage.modules_data import charger_sous_modules


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def facture_certifier(request, facture_id):
    """Complète les champs FNE d'une facture (pré-remplis autant que possible)
    puis lance la certification auprès de la DGI. Affiche les champs manquants
    avant même de tenter l'appel réseau."""
    from .models import Facture
    from .fne import erreurs_champs_obligatoires
    from .fne_client import certifier_facture
    from parametres.models import ParametresFNE

    facture = get_object_or_404(Facture, id=facture_id)
    parametres_fne = ParametresFNE.get_solo()

    champs = ["payment_method", "template", "client_telephone", "client_email",
              "is_rne", "rne_numero", "point_de_vente", "etablissement",
              "vendeur_nom", "message_commercial", "pied_de_page"]
    FactureForm = modelform_factory(Facture, fields=champs)

    initial = {}
    if not facture.point_de_vente and parametres_fne.point_de_vente_defaut:
        initial["point_de_vente"] = parametres_fne.point_de_vente_defaut
    if not facture.etablissement and parametres_fne.etablissement_defaut:
        initial["etablissement"] = parametres_fne.etablissement_defaut

    if request.method == "POST":
        form = FactureForm(request.POST, instance=facture)
        if form.is_valid():
            form.save()

            if request.POST.get("action") == "certifier":
                if not parametres_fne.est_configure:
                    messages.error(request, "La clé API FNE n'est pas encore configurée (Paramètres → FNE).")
                else:
                    succes, message = certifier_facture(facture)
                    if succes:
                        messages.success(request, message)
                    else:
                        messages.error(request, message)
            else:
                messages.success(request, "Champs FNE enregistrés.")

            return redirect("facture_certifier", facture_id=facture.id)
    else:
        form = FactureForm(instance=facture, initial=initial)

    return render(request, "devis/facture_certifier.html", {
        "facture": facture,
        "form": form,
        "erreurs": erreurs_champs_obligatoires(facture),
        "fne_configure": parametres_fne.est_configure,
    })


def _contexte_devis(actif_sous="devis", extra=None):
    base = {
        "actif": "devis",
        "actif_sous": actif_sous,
        "module_actif": {
            "cle": "recouvrement",
            "nom": "Recouvrement & Dépenses",
            "icone": "📄",
            "description": "Devis, lettres de mission et facturation.",
        },
        "sous_modules": charger_sous_modules("devis"),
    }
    if extra:
        base.update(extra)
    return base


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def liste_devis(request):
    # Envoyer automatiquement les relances dues (à chaque ouverture de la liste)
    try:
        from .relances import envoyer_relances_dues
        nb = envoyer_relances_dues(request)
        if nb > 0:
            from django.contrib import messages
            messages.info(request, f"{nb} relance(s) automatique(s) envoyée(s) aujourd'hui.")
    except Exception:
        pass  # ne jamais bloquer l'affichage de la liste si la relance échoue

    devis = Devis.objects.all()
    return render(request, "devis/liste_devis.html", _contexte_devis("devis", {"devis_list": devis}))
@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def supprimer_devis_multiple(request):
    """Supprime un ou plusieurs devis sélectionnés via cases à cocher."""
    if request.method == "POST":
        ids = request.POST.getlist("devis_ids")
        if ids:
            Devis.objects.filter(id__in=ids).delete()
    return redirect("liste_devis")


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def detail_devis(request, devis_id):
    devis = get_object_or_404(Devis, pk=devis_id)
    return render(request, "devis/detail_devis.html", _contexte_devis("devis", {"devis": devis}))


# ===================== PARCOURS DE CRÉATION EN ÉTAPES =====================

@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def creer_devis(request):
    """ÉTAPE 1 — Choix nouveau/existant + type de client. Crée le brouillon."""
    if request.method == "POST":
        type_client = request.POST.get("type_client", "PM")
        devis = Devis.objects.create(type_client=type_client, statut="BROUILLON")
        return redirect("devis_etape2", devis_id=devis.id)
    return render(request, "devis/etape1.html", _contexte_devis("devis", {"etape": 1}))


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def devis_etape2(request, devis_id):
    """ÉTAPE 2 — Identification minimale (le strict nécessaire pour établir et
    envoyer le devis). L'identification complète (NCC, RCCM, régime, obligations
    fiscales, siège, dirigeant, documents, associés...) se fait désormais à
    Porte d'entrée (module Secrétariat), une fois le devis accepté par le prospect."""
    devis = get_object_or_404(Devis, pk=devis_id)

    if devis.type_client == "PM":
        champs = ["pm_raison_sociale", "telephone", "email", "activite_principale"]
    else:  # PP_CONSTITUEE et PP_INFORMEL partagent désormais le même minimum
        champs = ["pp_nom_prenoms", "telephone", "email", "activite_principale"]

    DevisForm = modelform_factory(Devis, fields=champs)

    if request.method == "POST":
        form = DevisForm(request.POST, instance=devis)
        _appliquer_obligatoires(form)

        if form.is_valid():
            form.save()
            return redirect("devis_etape3", devis_id=devis.id)
    else:
        form = DevisForm(instance=devis)
        _appliquer_obligatoires(form)

    return render(request, "devis/etape2.html", _contexte_devis("devis", {
        "form": form, "devis": devis, "etape": 2,
    }))


def _appliquer_obligatoires(form):
    """Marque les champs obligatoires du formulaire minimal (identiques
    quel que soit le type de client)."""
    obligatoires = ["telephone", "email", "activite_principale"]
    for candidat in ("pm_raison_sociale", "pp_nom_prenoms"):
        if candidat in form.fields:
            obligatoires.append(candidat)
    for nom in obligatoires:
        if nom in form.fields:
            form.fields[nom].required = True


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def devis_etape3(request, devis_id):
    """ÉTAPE 3 — Montage du devis : sections par catégorie, variantes, ligne libre."""
    devis = get_object_or_404(Devis, pk=devis_id)

    identite_ok = devis.pm_raison_sociale or devis.pp_nom_prenoms
    if not identite_ok:
        return redirect("devis_etape2", devis_id=devis.id)

    if request.method == "POST":
        devis.lignes.all().delete()

        lignes_json = request.POST.get("lignes_data", "[]")
        try:
            lignes = json.loads(lignes_json)
        except Exception:
            lignes = []

        for l in lignes:
            designation = (l.get("designation") or "").strip()
            if not designation:
                continue
            LignePrestation.objects.create(
                devis=devis,
                designation=designation,
                periodicite=l.get("periodicite", ""),
                quantite=l.get("quantite") or 1,
                prix_unitaire=l.get("prix") or 0,
                taux_tva=str(l.get("tva", "18")),
            )

        remise = request.POST.get("remise_pourcentage") or 0
        try:
            devis.remise_pourcentage = remise
        except Exception:
            devis.remise_pourcentage = 0
        devis.save()

        return redirect("devis_etape4", devis_id=devis.id)

    categories = CategoriePrestation.objects.all().prefetch_related("prestations__variantes")
    catalogue_data = []
    for cat in categories:
        prestations = []
        for p in cat.prestations.all():
            variantes = [{"libelle": v.libelle, "prix": float(v.prix)} for v in p.variantes.all()]
            prestations.append({
                "id": p.id,
                "libelle": p.libelle,
                "periodicite": p.periodicite or "Ponctuel",
                "tva": p.taux_tva,
                "prix_base": float(p.prix_par_defaut),
                "variantes": variantes,
            })
        catalogue_data.append({
            "id": cat.id,
            "nom": cat.nom,
            "regime": cat.regime,
            "prestations": prestations,
        })

    lignes_existantes = []
    for ligne in devis.lignes.all():
        lignes_existantes.append({
            "designation": ligne.designation,
            "periodicite": ligne.periodicite,
            "quantite": float(ligne.quantite),
            "prix": float(ligne.prix_unitaire),
            "tva": ligne.taux_tva,
        })

    return render(request, "devis/etape3.html", _contexte_devis("devis", {
        "devis": devis,
        "etape": 3,
        "catalogue_json": json.dumps(catalogue_data),
        "lignes_existantes_json": json.dumps(lignes_existantes),
    }))


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def devis_etape4(request, devis_id):
    """ÉTAPE 4 — Visualisation du brouillon (devis + note)."""
    devis = get_object_or_404(Devis, pk=devis_id)

    if not devis.lignes.exists():
        return redirect("devis_etape3", devis_id=devis.id)

    if not devis.note_explicative:
        try:
            devis.note_explicative = generer_note_explicative(devis)
            devis.save()
        except Exception:
            pass

    groupes = {}
    for ligne in devis.lignes.all():
        cle = ligne.periodicite or "Autres prestations"
        groupes.setdefault(cle, []).append(ligne)
    sections = []
    for periodicite, lignes in groupes.items():
        sous_total = sum(l.total_ht for l in lignes)
        sections.append({"titre": periodicite, "lignes": lignes, "sous_total": sous_total})

    return render(request, "devis/etape4.html", _contexte_devis("devis", {
        "devis": devis, "sections": sections, "etape": 4,
    }))


# ===================== MODIFICATION (ancienne page, conservée) =====================

@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def modifier_devis(request, devis_id):
    devis = get_object_or_404(Devis, pk=devis_id)

    if not devis.est_modifiable:
        return render(request, "devis/devis_verrouille.html", _contexte_devis("devis", {"devis": devis}))

    DevisForm = modelform_factory(Devis, fields=[
        "type_client", "statut", "client_rattache",
        "pp_nom_prenoms", "pp_date_naissance", "pp_lieu_naissance", "pp_nationalite",
        "pp_nom_pere", "pp_nom_mere", "pp_piece_type", "pp_piece_numero",
        "pp_piece_delivree_le", "pp_piece_delivree_a", "pp_adresse_perso",
        "pm_raison_sociale", "pm_nom_commercial", "pm_sigle", "pm_forme_juridique", "pm_capital_social",
        "ncc", "rccm_numero", "rccm_delivre_le", "rccm_delivre_par",
        "code_activite", "regime_imposition", "est_employeur",
        "obl_patente", "obl_bic_ba", "obl_bnc", "obl_tva", "obl_tob",
        "obl_taxe_bois", "obl_its", "obl_airsi", "obl_tse",
        "obl_impots_fonciers", "obl_impot_micro", "obl_igr", "obl_autres",
        "siege_ville", "siege_commune", "siege_quartier", "siege_rue",
        "siege_lot", "siege_ilot", "ref_section", "ref_parcelle", "ref_tf", "boite_postale",
        "telephone", "telephone2", "email", "fax",
        "activite_principale", "activite_date_debut", "autres_activites", "ca_previsionnel",
        "dirigeant_nom", "dirigeant_qualite", "dirigeant_bp", "dirigeant_tel", "dirigeant_email",
        "a_eu_comptable", "comptable_precedent_nom", "comptable_precedent_ncc",
        "comptable_precedent_adresse", "comptable_precedent_email", "comptable_precedent_tel",
        "doc_rccm", "doc_dfe", "doc_cnps", "doc_tribunal_travail",
        "doc_piece_identite", "doc_contrat_bail", "doc_statuts",
        "autres_etablissements", "remise_pourcentage",
        "type_mission", "honoraires_proposes", "etat_compta_reprise", "notes_internes",
    ])

    if request.method == "POST":
        form = DevisForm(request.POST, request.FILES, instance=devis)
        if form.is_valid():
            form.save()
            return redirect("detail_devis", devis_id=devis.id)
    else:
        form = DevisForm(instance=devis)

    return render(request, "devis/modifier_devis.html", _contexte_devis("devis", {"form": form, "devis": devis}))


# ===================== APERÇUS & NOTE =====================

@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def apercu_devis(request, devis_id):
    """Affiche le devis au format présentation (devis + note), imprimable en PDF."""
    devis = get_object_or_404(Devis, pk=devis_id)

    groupes = {}
    for ligne in devis.lignes.all():
        cle = ligne.periodicite or "Autres prestations"
        groupes.setdefault(cle, []).append(ligne)

    sections = []
    for periodicite, lignes in groupes.items():
        sous_total = sum(l.total_ht for l in lignes)
        sections.append({"titre": periodicite, "lignes": lignes, "sous_total": sous_total})

    return render(request, "devis/apercu_devis.html", _contexte_devis("devis", {"devis": devis, "sections": sections}))


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def generer_note(request, devis_id):
    """Génère la note explicative structurée via l'IA et l'enregistre."""
    devis = get_object_or_404(Devis, pk=devis_id)
    devis.note_explicative = generer_note_explicative(devis)
    devis.save()
    return redirect("detail_devis", devis_id=devis.id)


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def apercu_note(request, devis_id):
    """Affiche la note explicative au format présentation, imprimable."""
    devis = get_object_or_404(Devis, pk=devis_id)
    return render(request, "devis/apercu_note.html", _contexte_devis("devis", {"devis": devis}))


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def rapport_analyse(request, devis_id):
    """Page du rapport d'analyse du dossier par l'IA."""
    devis = get_object_or_404(Devis, pk=devis_id)
    rapport = analyser_dossier(devis)
    return render(request, "devis/rapport_analyse.html", _contexte_devis("devis", {
        "devis": devis, "rapport": rapport,
    }))

@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def devis_etape5(request, devis_id):
    """ÉTAPE 5 — Validation : vérification de complétude (adaptée aux 3 types) + accès à la lettre."""
    devis = get_object_or_404(Devis, pk=devis_id)

    if not devis.lignes.exists():
        return redirect("devis_etape3", devis_id=devis.id)

    # --- Vérification de complétude (identique aux 3 types, formulaire minimal) ---
    nom = devis.pm_raison_sociale if devis.type_client == "PM" else devis.pp_nom_prenoms
    controles = [
        {"label": "Nom / Raison sociale", "ok": bool(nom)},
        {"label": "Téléphone", "ok": bool(devis.telephone)},
        {"label": "Email", "ok": bool(devis.email)},
        {"label": "Activité / objet de la prestation", "ok": bool(devis.activite_principale)},
        {"label": "Au moins une prestation", "ok": devis.lignes.exists()},
    ]

    # Le dossier est complet si tous les contrôles sont OK
    manquants = [c for c in controles if not c["ok"]]
    dossier_complet = len(manquants) == 0

    return render(request, "devis/etape5.html", _contexte_devis("devis", {
        "devis": devis, "etape": 5,
        "controles": controles,
        "manquants": manquants,
        "dossier_complet": dossier_complet,
    }))

@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def valider_et_lettre(request, devis_id):
    """Valide le devis (statut ENVOYÉ), envoie le devis PDF par email, puis ouvre la lettre."""
    devis = get_object_or_404(Devis, pk=devis_id)

    # 1. Changer le statut (une seule fois)
    if devis.statut == "BROUILLON":
        from datetime import date
        devis.statut = "ENVOYE"
        devis.date_envoi = date.today()
        devis.save()

    # 2. Envoyer le devis par email au prospect (si une adresse est renseignée)
    from django.contrib import messages
    if devis.email:
        try:
            from .pdf import generer_pdf_devis
            from parametres.emails import envoyer_email

            pdf_bytes = generer_pdf_devis(devis, request)

            # Nom du client pour personnaliser
            if devis.type_client == "PM":
                nom_client = devis.pm_raison_sociale or "Madame, Monsieur"
            else:
                nom_client = devis.pp_nom_prenoms or "Madame, Monsieur"

            sujet = f"Votre devis {devis.numero_devis} — Cabinet K&L"
            corps = (
                f"Bonjour {nom_client},\n\n"
                f"Veuillez trouver ci-joint notre devis n° {devis.numero_devis} "
                f"pour les prestations comptables et fiscales évoquées.\n\n"
                f"Ce devis est accompagné d'une note explicative détaillant chaque prestation. "
                f"Nous restons à votre entière disposition pour tout complément d'information.\n\n"
                f"Cordialement,\n"
                f"Cabinet Comptable & Fiscal K&L\n"
                f"Tél : 27 32 70 44 04\n"
                f"cabinetkl120@gmail.com"
            )

            fichiers = [(f"Devis-{devis.numero_devis}.pdf", pdf_bytes, "application/pdf")]
            ok, erreur = envoyer_email([devis.email], sujet, corps, fichiers)

            if ok:
                messages.success(request, f"Devis envoyé par email à {devis.email}.")
            else:
                messages.error(request, f"Le devis n'a pas pu être envoyé : {erreur}")
        except Exception as e:
            messages.error(request, f"Erreur lors de l'envoi du devis : {str(e)}")
    else:
        messages.warning(request, "Aucune adresse email n'est renseignée pour ce client : le devis n'a pas été envoyé.")

    # 3. Ouvrir la lettre de mission
    return redirect("lettre_mission", devis_id=devis.id)

def construire_contexte_lettre_mission(devis):
    """Prépare le contexte partagé pour l'affichage et la génération PDF."""
    recurrentes, ponctuelles = [], []
    preavis_max = 0
    modalites_rec = ""
    modalites_ponc = ""

    for ligne in devis.lignes.all():
        presta = PrestationCatalogue.objects.filter(libelle=ligne.designation).first()
        cat = presta.categorie if presta else None
        info = {
            "libelle": ligne.designation,
            "periodicite": ligne.periodicite,
            "livrable": presta.livrable if presta else "",
            "delai": presta.delai_livraison if presta else "",
            "categorie": cat.nom if cat else "",
            "duree": cat.duree_engagement_mois if cat else None,
        }
        if cat and cat.regime == "PONCTUELLE":
            ponctuelles.append(info)
            if cat.modalites_paiement:
                modalites_ponc = cat.modalites_paiement
        elif cat and cat.regime == "RECURRENTE":
            recurrentes.append(info)
            if cat.preavis_mois and cat.preavis_mois > preavis_max:
                preavis_max = cat.preavis_mois
            if cat.modalites_paiement:
                modalites_rec = cat.modalites_paiement
        else:
            if (ligne.periodicite or "").lower().startswith("ponct"):
                ponctuelles.append(info)
            else:
                recurrentes.append(info)

    groupes_rec = {}
    for r in recurrentes:
        cle = r["categorie"] or "Suivi régulier"
        if cle not in groupes_rec:
            groupes_rec[cle] = {"nom": cle, "duree": r["duree"], "lignes": []}
        groupes_rec[cle]["lignes"].append(r)
    groupes_recurrents = list(groupes_rec.values())

    if devis.date_effet_mission:
        date_effet = devis.date_effet_mission
    else:
        today = date.today()
        if today.month == 12:
            date_effet = date(today.year + 1, 1, 1)
        else:
            date_effet = date(today.year, today.month + 1, 1)

    a_recurrent = len(recurrentes) > 0
    a_ponctuel = len(ponctuelles) > 0

    annexes = []
    for document in devis.documents.filter(statut="FOURNI").exclude(fichier__isnull=True).exclude(fichier__exact=""):
        annexes.append({
            "titre": document.get_type_document_display(),
            "description": document.libelle_libre or document.commentaire or document.fichier.name,
        })

    return _contexte_devis("devis", {
        "devis": devis,
        "groupes_recurrents": groupes_recurrents,
        "ponctuelles": ponctuelles,
        "a_recurrent": a_recurrent,
        "a_ponctuel": a_ponctuel,
        "date_effet": date_effet,
        "honoraires": devis.total_ttc,
        "preavis": preavis_max or 3,
        "modalites_rec": modalites_rec,
        "modalites_ponc": modalites_ponc,
        "annexes": annexes,
    })


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def lettre_mission(request, devis_id):
    """ÉTAPE 5 — Lettre de mission générée depuis le devis + le catalogue."""
    devis = get_object_or_404(Devis, pk=devis_id)
    return render(request, "devis/lettre_mission.html", construire_contexte_lettre_mission(devis))


def _enregistrer_associes(devis, request):
    """Enregistre les associés envoyés en JSON depuis le formulaire (rubrique F)."""
    associes_json = request.POST.get("associes_data", "[]")
    try:
        associes = json.loads(associes_json)
    except Exception:
        associes = []
    devis.associes.all().delete()
    for a in associes:
        nom = (a.get("nom") or "").strip()
        if not nom:
            continue
        Associe.objects.create(
            devis=devis,
            nom=nom,
            adresse=a.get("adresse", ""),
            nationalite=a.get("nationalite", ""),
            part_montant=a.get("montant") or 0,
            part_pourcentage=a.get("pourcentage") or 0,
        )
@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def telecharger_pdf_devis(request, devis_id):
    """Télécharge le devis en PDF (pour tester la génération)."""
    devis = get_object_or_404(Devis, pk=devis_id)
    pdf_bytes = generer_pdf_devis(devis, request)
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="devis-{devis.numero_devis}.pdf"'
    return response
@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def documents_bibliotheque(request):
    """Sous-module Documents : bibliothèque des documents générés (maquette)."""

    # --- Documents d'EXEMPLE (à remplacer par les vrais fichiers stockés) ---
    documents = [
        {"nom": "MEGA-CHALLENGE-DEV-2026-06-24-14h30", "type": "Devis", "client": "MEGA CHALLENGE", "date": "24/06/2026 14:30", "taille": "82 Ko"},
        {"nom": "MEGA-CHALLENGE-NOTE-2026-06-24-14h31", "type": "Note explicative", "client": "MEGA CHALLENGE", "date": "24/06/2026 14:31", "taille": "45 Ko"},
        {"nom": "ETS-SAMTEX-DEV-2026-06-20-09h15", "type": "Devis", "client": "ETS SAMTEX", "date": "20/06/2026 09:15", "taille": "78 Ko"},
        {"nom": "ETS-SAMTEX-LETTRE-2026-06-20-09h20", "type": "Lettre de mission", "client": "ETS SAMTEX", "date": "20/06/2026 09:20", "taille": "52 Ko"},
        {"nom": "KPMG-CI-DEV-2026-06-18-16h45", "type": "Devis", "client": "KPMG CÔTE D'IVOIRE", "date": "18/06/2026 16:45", "taille": "80 Ko"},
    ]

    # Recherche simple (sur le nom ou le client)
    q = request.GET.get("q", "").strip()
    if q:
        ql = q.lower()
        documents = [d for d in documents if ql in d["nom"].lower() or ql in d["client"].lower()]

    return render(request, "devis/documents.html", _contexte_devis("documents", {
        "documents": documents,
        "q": q,
    }))
@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def facturation_accueil(request):
    """Accueil + liste du sous-module Facturation."""
    from .models import Facture

    def fmt(n):
        return f"{int(n):,.0f}".replace(",", " ")

    classes_statut = {
        "PAYEE": "bg-emerald-100 text-emerald-700",
        "ENVOYEE": "bg-blue-100 text-blue-700",
        "A_CERTIFIER": "bg-amber-100 text-amber-700",
        "CERTIFIEE": "bg-purple-100 text-purple-700",
        "ANNULEE": "bg-red-100 text-red-700",
        "BROUILLON": "bg-gray-100 text-gray-600",
    }

    factures = list(Facture.objects.all())
    for f in factures:
        f.badge = classes_statut.get(f.statut, "bg-gray-100 text-gray-600")

    montant_facture = sum(f.montant_ttc for f in factures)
    montant_paye = sum(f.montant_ttc for f in factures if f.statut == "PAYEE")

    return render(request, "devis/facturation.html", _contexte_devis("facturation", {
        "factures": factures,
        "nb_total": len(factures),
        "nb_a_certifier": sum(1 for f in factures if f.statut == "A_CERTIFIER"),
        "montant_facture": fmt(montant_facture),
        "montant_paye": fmt(montant_paye),
    }))


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def apercu_proforma(request, devis_id):
    """Facture proforma : même document que l'aperçu du devis, mais en 'mode proforma'
    (badge, numéro PRO-..., mention non définitive). Réutilise _document_devis.html."""
    devis = get_object_or_404(Devis, pk=devis_id)

    # Regroupement par périodicité — identique à apercu_devis
    groupes = {}
    for ligne in devis.lignes.all():
        cle = ligne.periodicite or "Autres prestations"
        groupes.setdefault(cle, []).append(ligne)

    sections = []
    for periodicite, lignes in groupes.items():
        sous_total = sum(l.total_ht for l in lignes)
        sections.append({"titre": periodicite, "lignes": lignes, "sous_total": sous_total})

    numero_proforma = f"PRO-{date.today().year}-{devis.id:03d}"

    return render(request, "devis/apercu_proforma.html", _contexte_devis("devis", {
        "devis": devis,
        "sections": sections,
        "est_proforma": True,
        "numero_proforma": numero_proforma,
    }))


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def facture_creer(request):
    """Crée une facture à partir d'un devis existant."""
    devis_id = request.GET.get("devis_id")
    if request.method == "POST":
        selected_id = request.POST.get("devis_id")
        devis = get_object_or_404(Devis, pk=selected_id)
        facture = Facture.objects.create(
            devis_source=devis,
            client_nom=devis.pm_raison_sociale or devis.pp_nom_prenoms or "Client",
            client_ncc=devis.ncc or "",
            type_facturation="PONCTUELLE",
            date_signature=date.today(),
            montant_ht=devis.total_ht,
            montant_tva=devis.montant_tva,
            montant_ttc=devis.total_ttc,
            statut="BROUILLON",
        )
        for ligne in devis.lignes.all():
            LigneFacture.objects.create(
                facture=facture,
                designation=ligne.designation,
                quantite=ligne.quantite,
                prix_unitaire=ligne.prix_unitaire,
                taux_tva=ligne.taux_tva,
            )
        messages.success(request, f"Facture {facture.numero_facture} créée à partir du devis {devis.numero_devis}.")
        return redirect("apercu_facture", facture_id=facture.id)

    if devis_id:
        devis = get_object_or_404(Devis, pk=devis_id)
        return render(request, "devis/facture_confirmer.html", _contexte_devis("facturation", {
            "devis": devis,
        }))

    devis_list = Devis.objects.exclude(statut="BROUILLON").order_by("-date_creation")[:50]
    return render(request, "devis/facture_choisir_devis.html", _contexte_devis("facturation", {
        "devis_list": devis_list,
    }))


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def apercu_facture(request, facture_id):
    facture = get_object_or_404(Facture, pk=facture_id)
    lignes = facture.lignes.all()
    return render(request, "devis/apercu_facture.html", _contexte_devis("facturation", {
        "facture": facture,
        "lignes": lignes,
    }))