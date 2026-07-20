import json
from datetime import date
from itertools import chain
from operator import attrgetter
from django.shortcuts import render, get_object_or_404, redirect
from django.forms import modelform_factory, modelformset_factory
from django import forms
from django.db.models import Sum, F, DecimalField, Value, Case, When, BooleanField, Q
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from .models import Devis, LignePrestation, Associe, Facture, LigneFacture, EtapeRelance, Litige, ActionRecouvrement, Paiement, Avoir, Remboursement, Compensation, Fournisseur, ContratFournisseur, CategorieDepense, Depense, PaiementDepense, DocumentDepense, Relance
from .forms import (
    PaiementForm, TransitionStatutForm, AvoirForm,
    RemboursementForm, CompensationForm, EtapeRelanceForm,
    LitigeForm, CommentaireLitigeForm, PieceJointeLitigeForm,
    AffectationRecouvreurForm, ActionRecouvrementForm,
    ResolutionLitigeForm, FournisseurForm, ContratFournisseurForm,
    DepenseForm, DocumentDepenseForm, PaiementDepenseForm, NoteInterneForm,
)
from .ia import generer_note_explicative, analyser_dossier
from parametres.models import CategoriePrestation, PrestationCatalogue
from django.http import HttpResponse
from django.contrib import messages
from .pdf import generer_pdf_devis
from django.contrib.auth.decorators import login_required
from comptes.decorators import role_requis
from comptes.models import Profil
from pilotage.modules_data import charger_sous_modules, get_module_info
from core.audit import journaliser
from core.exports import exporter_csv, exporter_excel
from core.models import NoteInterne
from parametres.emails import envoyer_email as notifier_email
from .kpi import (
    delai_moyen_paiement, taux_impayes, taux_recouvrement,
    clients_a_risque, encaissements_mensuels, creances_par_anciennete,
)
from .previsions import previsions_encaissements, repartition_par_anciennete


@login_required
def tableau_kpi(request):
    debut_annee = date(date.today().year, 1, 1)
    context = {
        "module_actif": get_module_info("recouvrement"),
        "delai_moyen": delai_moyen_paiement(),
        "taux_impayes": taux_impayes(depuis=debut_annee),
        "taux_recouvrement": taux_recouvrement(depuis=debut_annee),
        "clients_risque": clients_a_risque(),
        "encaissements": encaissements_mensuels(),
        "anciennete": creances_par_anciennete(),
    }
    return render(request, "devis/creances/tableau_kpi.html", context)


@login_required
def liste_fournisseurs(request):
    recherche = request.GET.get("q", "").strip()
    fournisseurs = Fournisseur.objects.all()
    if recherche:
        fournisseurs = fournisseurs.filter(raison_sociale__icontains=recherche)

    context = {
        "module_actif": get_module_info("recouvrement"),
        "fournisseurs": fournisseurs,
        "recherche": recherche,
    }
    return render(request, "devis/depenses/liste_fournisseurs.html", context)


@login_required
def creer_fournisseur(request):
    if request.method == "POST":
        form = FournisseurForm(request.POST)
        if form.is_valid():
            fournisseur = form.save()
            messages.success(request, "Fournisseur créé.")
            return redirect("devis:detail_fournisseur", fournisseur_id=fournisseur.id)
    else:
        form = FournisseurForm()
    return render(request, "devis/depenses/form_fournisseur.html", {
        "module_actif": get_module_info("recouvrement"), "form": form, "creation": True})


@login_required
def modifier_fournisseur(request, fournisseur_id):
    fournisseur = get_object_or_404(Fournisseur, pk=fournisseur_id)
    if request.method == "POST":
        form = FournisseurForm(request.POST, instance=fournisseur)
        if form.is_valid():
            form.save()
            messages.success(request, "Fournisseur mis à jour.")
            return redirect("devis:detail_fournisseur", fournisseur_id=fournisseur.id)
    else:
        form = FournisseurForm(instance=fournisseur)
    return render(request, "devis/depenses/form_fournisseur.html", {
        "module_actif": get_module_info("recouvrement"), "form": form, "creation": False, "fournisseur": fournisseur})


@login_required
def detail_fournisseur(request, fournisseur_id):
    fournisseur = get_object_or_404(Fournisseur, pk=fournisseur_id)
    contrat_form = ContratFournisseurForm()

    if request.method == "POST" and "ajouter_contrat" in request.POST:
        contrat_form = ContratFournisseurForm(request.POST, request.FILES)
        if contrat_form.is_valid():
            ContratFournisseur.objects.create(fournisseur=fournisseur, **contrat_form.cleaned_data)
            messages.success(request, "Contrat ajouté.")
            return redirect("devis:detail_fournisseur", fournisseur_id=fournisseur.id)

    context = {
        "module_actif": get_module_info("recouvrement"),
        "fournisseur": fournisseur,
        "contrats": fournisseur.contrats.all(),
        "contrat_form": contrat_form,
    }
    return render(request, "devis/depenses/detail_fournisseur.html", context)


@login_required
def liste_depenses(request):
    depenses = Depense.objects.select_related("fournisseur", "categorie").order_by("-date_facture")

    statut = request.GET.get("statut", "")
    if statut:
        depenses = depenses.filter(statut=statut)

    fournisseur_id = request.GET.get("fournisseur", "")
    if fournisseur_id:
        depenses = depenses.filter(fournisseur_id=fournisseur_id)

    context = {
        "module_actif": get_module_info("recouvrement"),
        "depenses": depenses,
        "statuts": Depense.STATUT_CHOICES,
        "fournisseurs": Fournisseur.objects.filter(actif=True),
        "filtre_statut": statut,
        "filtre_fournisseur": fournisseur_id,
    }
    return render(request, "devis/depenses/liste_depenses.html", context)


@login_required
def creer_depense(request):
    if request.method == "POST":
        form = DepenseForm(request.POST)
        if form.is_valid():
            depense = form.save(commit=False)
            depense.cree_par = request.user
            depense.save()
            messages.success(request, "Dépense enregistrée.")
            return redirect("devis:detail_depense", depense_id=depense.id)
    else:
        form = DepenseForm()
    return render(request, "devis/depenses/form_depense.html", {
        "module_actif": get_module_info("recouvrement"), "form": form})


@login_required
def detail_depense(request, depense_id):
    depense = get_object_or_404(Depense, pk=depense_id)
    document_form = DocumentDepenseForm()
    paiement_form = PaiementDepenseForm(depense=depense)

    if request.method == "POST":
        if "ajouter_document" in request.POST:
            document_form = DocumentDepenseForm(request.POST, request.FILES)
            if document_form.is_valid():
                DocumentDepense.objects.create(depense=depense, **document_form.cleaned_data)
                messages.success(request, "Document ajouté.")
                return redirect("devis:detail_depense", depense_id=depense.id)

        elif "enregistrer_paiement" in request.POST:
            paiement_form = PaiementDepenseForm(request.POST, request.FILES, depense=depense)
            if paiement_form.is_valid():
                depense.enregistrer_paiement(
                    montant=paiement_form.cleaned_data["montant"],
                    utilisateur=request.user,
                    date_paiement=paiement_form.cleaned_data["date_paiement"],
                    mode_paiement=paiement_form.cleaned_data["mode_paiement"],
                    reference_bancaire=paiement_form.cleaned_data["reference_bancaire"],
                    justificatif=paiement_form.cleaned_data["justificatif"],
                    commentaire=paiement_form.cleaned_data["commentaire"],
                )
                messages.success(request, "Paiement enregistré.")
                return redirect("devis:detail_depense", depense_id=depense.id)

    context = {
        "module_actif": get_module_info("recouvrement"),
        "depense": depense,
        "document_form": document_form,
        "paiement_form": paiement_form,
        "documents": depense.documents.all(),
        "paiements": depense.paiements.select_related("utilisateur").order_by("-date_paiement"),
        "historique": depense.historique_statuts.select_related("utilisateur").order_by("-date_changement"),
    }
    return render(request, "devis/depenses/detail_depense.html", context)


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def journal_paiements(request):
    avoirs = Avoir.objects.select_related("facture", "cree_par").all()
    remboursements = Remboursement.objects.select_related("facture", "utilisateur").all()
    compensations = Compensation.objects.select_related("facture_source", "facture_cible", "utilisateur").all()

    recherche = request.GET.get("q", "").strip()
    if recherche:
        avoirs = avoirs.filter(facture__numero_facture__icontains=recherche)
        remboursements = remboursements.filter(facture__numero_facture__icontains=recherche)
        compensations = compensations.filter(
            Q(facture_source__numero_facture__icontains=recherche) |
            Q(facture_cible__numero_facture__icontains=recherche))

    type_filtre = request.GET.get("type", "")

    mouvements = list(chain(
        ({
            "type": "Avoir",
            "date": a.date_creation,
            "facture": a.facture,
            "montant": -a.montant,
            "detail": a.get_type_avoir_display(),
            "par": a.cree_par,
        } for a in avoirs) if type_filtre in ("", "AVOIR") else [] ,
        ({
            "type": "Remboursement",
            "date": r.date_enregistrement,
            "facture": r.facture,
            "montant": -r.montant,
            "detail": r.get_mode_remboursement_display(),
            "par": r.utilisateur,
        } for r in remboursements) if type_filtre in ("", "REMBOURSEMENT") else [],
        ({
            "type": "Compensation",
            "date": c.date_creation,
            "facture": c.facture_cible,
            "montant": c.montant,
            "detail": f"depuis {c.facture_source.numero_facture}",
            "par": c.utilisateur,
        } for c in compensations) if type_filtre in ("", "COMPENSATION") else [],
    ))

    mouvements.sort(key=attrgetter("date"), reverse=True)

    if "export" in request.GET:
        colonnes = [
            ("Type", lambda m: m["type"]),
            ("Date", lambda m: m["date"].strftime("%d/%m/%Y")),
            ("Facture", lambda m: m["facture"].numero_facture),
            ("Montant", lambda m: m["montant"]),
            ("Détail", lambda m: m["detail"]),
            ("Enregistré par", lambda m: str(m["par"]) if m["par"] else "—"),
        ]
        journaliser(request, "EXPORT", description="Export journal des paiements")
        if request.GET["export"] == "excel":
            return exporter_excel(mouvements, colonnes, "journal_paiements")
        return exporter_csv(mouvements, colonnes, "journal_paiements")

    context = {
        "module_actif": get_module_info("recouvrement"),
        "mouvements": mouvements,
        "filtre_recherche": recherche,
        "filtre_type": type_filtre,
        "total_avoirs": avoirs.aggregate(t=Sum("montant"))["t"] or 0,
        "total_remboursements": remboursements.aggregate(t=Sum("montant"))["t"] or 0,
        "total_compensations": compensations.aggregate(t=Sum("montant"))["t"] or 0,
    }
    return render(request, "devis/creances/journal_paiements.html", context)


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


@login_required
def previsions_tresorerie(request):
    debut_annee = date(date.today().year, 1, 1)
    previsions = previsions_encaissements()
    anciennete = creances_par_anciennete()

    if "export" in request.GET:
        lignes = [
            {"categorie": "Cette semaine (brut)", "montant": previsions["semaine"]["brut"]},
            {"categorie": "Cette semaine (pondéré)", "montant": previsions["semaine"]["pondere"]},
            {"categorie": "Ce mois (brut)", "montant": previsions["mois"]["brut"]},
            {"categorie": "Ce mois (pondéré)", "montant": previsions["mois"]["pondere"]},
            {"categorie": "Ce trimestre (brut)", "montant": previsions["trimestre"]["brut"]},
            {"categorie": "Ce trimestre (pondéré)", "montant": previsions["trimestre"]["pondere"]},
            {"categorie": "Ancienneté 0-30j", "montant": anciennete["j0_30"]},
            {"categorie": "Ancienneté 31-60j", "montant": anciennete["j31_60"]},
            {"categorie": "Ancienneté 61-90j", "montant": anciennete["j61_90"]},
            {"categorie": "Ancienneté 90+j", "montant": anciennete["j90_plus"]},
        ]
        colonnes = [("Catégorie", lambda l: l["categorie"]), ("Montant (FCFA)", lambda l: l["montant"])]
        journaliser(request, "EXPORT", description="Export prévisions de trésorerie")
        if request.GET["export"] == "excel":
            return exporter_excel(lignes, colonnes, "previsions_tresorerie")
        return exporter_csv(lignes, colonnes, "previsions_tresorerie")

    journaliser(request, "CONSULTATION", description="Consultation prévisions de trésorerie")

    context = {
        "module_actif": get_module_info("recouvrement"),
        "previsions": previsions,
        "anciennete": anciennete,
    }
    return render(request, "devis/creances/previsions_tresorerie.html", context)


def _direction_ou_cadre(user):
    profil = getattr(user, "profil", None)
    return profil and profil.role in (Profil.Role.DIRECTION, Profil.Role.CADRE)


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


STATUTS_EN_RETARD_POSSIBLES = ["EN_ATTENTE_PAIEMENT", "PARTIELLEMENT_PAYEE"]


def _factures_avec_soldes():
    """Annotate montant_paye/solde_restant en une seule requête (évite le
    N+1 de la property Python sur une liste)."""
    return Facture.objects.annotate(
        montant_paye_calc=Coalesce(
            Sum("paiements__montant"), Value(0), output_field=DecimalField()
        )
    ).annotate(
        solde_restant_calc=F("montant_ttc") - F("montant_paye_calc"),
        en_retard=Case(
            When(
                statut__in=STATUTS_EN_RETARD_POSSIBLES,
                date_echeance__lt=timezone.now().date(),
                then=Value(True),
            ),
            default=Value(False),
            output_field=BooleanField(),
        ),
    )


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def liste_creances(request):
    aujourdhui = timezone.now().date()

    factures = _factures_avec_soldes().select_related("devis_source").order_by("-date_emission")

    voir_archivees = request.GET.get("archivees") == "1"
    factures = factures.filter(archive=voir_archivees)

    statut = request.GET.get("statut", "")
    if statut:
        factures = factures.filter(statut=statut)

    recherche = request.GET.get("q", "").strip()
    if recherche:
        factures = factures.filter(
            Q(numero_facture__icontains=recherche) | Q(client_nom__icontains=recherche)
        )

    client = request.GET.get("client", "").strip()
    if client:
        factures = factures.filter(client_nom__icontains=client)

    en_retard_seulement = request.GET.get("en_retard") == "1"
    if en_retard_seulement:
        factures = factures.filter(
            statut__in=STATUTS_EN_RETARD_POSSIBLES,
            date_echeance__lt=aujourdhui,
        )

    if "export" in request.GET:
        colonnes = [
            ("N° facture", lambda f: f.numero_facture),
            ("Client", lambda f: f.client_nom),
            ("Échéance", lambda f: f.date_echeance),
            ("Montant TTC", lambda f: f.montant_ttc),
            ("Solde restant", lambda f: f.solde_restant_calc),
            ("Statut", lambda f: f.get_statut_display()),
        ]
        journaliser(request, "EXPORT", description="Export liste des créances")
        if request.GET["export"] == "excel":
            return exporter_excel(factures, colonnes, "creances")
        return exporter_csv(factures, colonnes, "creances")

    factures = list(factures)
    for f in factures:
        f.est_en_retard_affichage = (
            f.statut in STATUTS_EN_RETARD_POSSIBLES
            and f.date_echeance is not None
            and f.date_echeance < aujourdhui
        )

    total_creances = sum((f.montant_ttc for f in factures), 0)
    total_solde = sum((f.solde_restant_calc for f in factures), 0)

    context = {
        "module_actif": get_module_info("recouvrement"),
        "factures": factures,
        "statuts": Facture.STATUT_CHOICES,
        "filtre_statut": statut,
        "filtre_recherche": recherche,
        "filtre_client": client,
        "filtre_en_retard": en_retard_seulement,
        "voir_archivees": voir_archivees,
        "total_creances": total_creances,
        "total_solde": total_solde,
        "aujourdhui": aujourdhui,
    }
    return render(request, "devis/creances/liste.html", context)


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def kanban_creances(request):
    STATUTS_KANBAN = ["EN_ATTENTE_PAIEMENT", "PARTIELLEMENT_PAYEE", "CONTESTEE", "EN_LITIGE", "EN_RETARD", "PAYEE"]
    colonnes = []
    for code in STATUTS_KANBAN:
        factures = Facture.objects.filter(statut=code, archive=False).select_related("devis_source")[:50]
        colonnes.append({
            "code": code,
            "libelle": dict(Facture.STATUT_CHOICES)[code],
            "factures": factures,
        })
    return render(request, "devis/creances/kanban.html", {
        "module_actif": get_module_info("recouvrement"),
        "colonnes": colonnes,
    })


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def detail_creance(request, facture_id):
    facture = get_object_or_404(Facture, pk=facture_id)
    facture_ct = ContentType.objects.get_for_model(Facture)

    paiement_form = PaiementForm(facture=facture)
    transition_form = TransitionStatutForm(facture=facture, user=request.user)
    avoir_form = AvoirForm(facture=facture)
    remboursement_form = RemboursementForm(facture=facture)
    compensation_form = CompensationForm(facture=facture)
    litige_form = LitigeForm()
    affectation_form = AffectationRecouvreurForm(initial={"recouvreur": facture.recouvreur})
    action_form = ActionRecouvrementForm()
    commentaire_form = CommentaireLitigeForm()
    piece_form = PieceJointeLitigeForm()
    resolution_form = ResolutionLitigeForm()
    note_form = NoteInterneForm()

    if request.method == "POST":
        if "enregistrer_paiement" in request.POST:
            paiement_form = PaiementForm(request.POST, request.FILES, facture=facture)
            if paiement_form.is_valid():
                facture.enregistrer_paiement(
                    montant=paiement_form.cleaned_data["montant"],
                    utilisateur=request.user,
                    date_paiement=paiement_form.cleaned_data["date_paiement"],
                    mode_paiement=paiement_form.cleaned_data["mode_paiement"],
                    banque=paiement_form.cleaned_data["banque"],
                    reference_bancaire=paiement_form.cleaned_data["reference_bancaire"],
                    justificatif=paiement_form.cleaned_data["justificatif"],
                    commentaire=paiement_form.cleaned_data["commentaire"],
                )
                journaliser(request, "ACTION_METIER", objet=facture, description="Paiement enregistré")
                if facture.solde_restant <= 0 and facture.client_email:
                    succes_email, erreur_email = notifier_email(
                        facture.client_email,
                        f"Facture {facture.numero_facture} soldée",
                        f"Votre facture {facture.numero_facture} a été intégralement réglée. Merci."
                    )
                    if not succes_email:
                        messages.warning(request, f"Notification email non envoyée : {erreur_email}")
                    else:
                        messages.success(request, "Email de clôture envoyé au client.")
                messages.success(request, "Paiement enregistré.")
                return redirect("devis:detail_creance", facture_id=facture.id)

        elif "changer_statut" in request.POST:
            transition_form = TransitionStatutForm(request.POST, facture=facture, user=request.user)
            if transition_form.is_valid():
                facture.changer_statut(
                    transition_form.cleaned_data["nouveau_statut"],
                    utilisateur=request.user,
                    commentaire=transition_form.cleaned_data["commentaire"],
                )
                journaliser(request, "ACTION_METIER", objet=facture, description="Statut de facture modifié")
                messages.success(request, "Statut mis à jour.")
                return redirect("devis:detail_creance", facture_id=facture.id)

        elif "enregistrer_avoir" in request.POST:
            avoir_form = AvoirForm(request.POST, facture=facture)
            if avoir_form.is_valid():
                try:
                    avoir = facture.enregistrer_avoir(
                        montant=avoir_form.cleaned_data["montant"],
                        type_avoir=avoir_form.cleaned_data["type_avoir"],
                        motif=avoir_form.cleaned_data["motif"],
                        utilisateur=request.user,
                    )
                    journaliser(request, "ACTION_METIER", objet=avoir, description=f"Avoir émis : {avoir.montant} FCFA")
                    messages.success(request, "Avoir enregistré (non certifié FNE — voir COMMENTAIRES.md).")
                    return redirect("devis:detail_creance", facture_id=facture.id)
                except ValueError as e:
                    avoir_form.add_error(None, str(e))

        elif "enregistrer_remboursement" in request.POST:
            remboursement_form = RemboursementForm(request.POST, request.FILES, facture=facture)
            if remboursement_form.is_valid():
                try:
                    remboursement = facture.enregistrer_remboursement(
                        montant=remboursement_form.cleaned_data["montant"],
                        utilisateur=request.user,
                        date_remboursement=remboursement_form.cleaned_data["date_remboursement"],
                        mode_remboursement=remboursement_form.cleaned_data["mode_remboursement"],
                        reference=remboursement_form.cleaned_data["reference"],
                        justificatif=remboursement_form.cleaned_data["justificatif"],
                        commentaire=remboursement_form.cleaned_data["commentaire"],
                    )
                    journaliser(request, "ACTION_METIER", objet=remboursement, description=f"Remboursement émis : {remboursement.montant} FCFA")
                    messages.success(request, "Remboursement enregistré.")
                    return redirect("devis:detail_creance", facture_id=facture.id)
                except ValueError as e:
                    remboursement_form.add_error(None, str(e))

        elif "enregistrer_compensation" in request.POST:
            compensation_form = CompensationForm(request.POST, facture=facture)
            if compensation_form.is_valid():
                try:
                    compensation = facture.enregistrer_compensation(
                        facture_cible=compensation_form.cleaned_data["facture_cible"],
                        montant=compensation_form.cleaned_data["montant"],
                        utilisateur=request.user,
                        commentaire=compensation_form.cleaned_data["commentaire"],
                    )
                    journaliser(request, "ACTION_METIER", objet=compensation, description=f"Compensation émise : {compensation.montant} FCFA")
                    messages.success(request, "Compensation appliquée.")
                    return redirect("devis:detail_creance", facture_id=facture.id)
                except ValueError as e:
                    compensation_form.add_error(None, str(e))

        elif "affecter_recouvreur" in request.POST:
            if not _direction_ou_cadre(request.user):
                raise PermissionDenied
            affectation_form = AffectationRecouvreurForm(request.POST)
            if affectation_form.is_valid():
                facture.recouvreur = affectation_form.cleaned_data["recouvreur"]
                facture.save(update_fields=["recouvreur"])
                description = f"Recouvreur affecté : {facture.recouvreur or 'aucun'}"
                journaliser(request, "MODIFICATION", objet=facture, description=description)
                messages.success(request, "Recouvreur affecté.")
                return redirect("devis:detail_creance", facture_id=facture.id)

        elif "ajouter_action" in request.POST:
            action_form = ActionRecouvrementForm(request.POST)
            if action_form.is_valid():
                action = ActionRecouvrement.objects.create(
                    facture=facture, recouvreur=request.user,
                    type_action=action_form.cleaned_data["type_action"],
                    commentaire=action_form.cleaned_data["commentaire"],
                )
                journaliser(request, "ACTION_METIER", objet=action, description=f"Action recouvrement : {action.get_type_action_display()}")
                messages.success(request, "Action enregistrée.")
                return redirect("devis:detail_creance", facture_id=facture.id)

        elif "ouvrir_litige" in request.POST:
            litige_form = LitigeForm(request.POST)
            if litige_form.is_valid():
                try:
                    litige = facture.ouvrir_litige(
                        motif_type=litige_form.cleaned_data["motif_type"],
                        description=litige_form.cleaned_data["description"],
                        utilisateur=request.user,
                    )
                    journaliser(request, "ACTION_METIER", objet=litige, description="Litige ouvert")
                    messages.success(request, "Litige ouvert.")
                    return redirect("devis:detail_litige", litige_id=litige.id)
                except ValueError as e:
                    litige_form.add_error(None, str(e))

        elif "passer_en_cours" in request.POST:
            litige_id = request.POST.get("litige_id")
            litige = get_object_or_404(Litige, pk=litige_id, facture=facture)
            try:
                litige.passer_en_cours(utilisateur=request.user)
                journaliser(request, "ACTION_METIER", objet=facture, description="Litige passé en cours")
                messages.success(request, "Litige passé en cours.")
                return redirect("devis:detail_creance", facture_id=facture.id)
            except ValueError as e:
                messages.error(request, str(e))

        elif "resoudre_litige" in request.POST:
            resolution_form = ResolutionLitigeForm(request.POST)
            litige_id = request.POST.get("litige_id")
            litige = get_object_or_404(Litige, pk=litige_id, facture=facture)
            if resolution_form.is_valid():
                try:
                    litige.resoudre(
                        commentaire=resolution_form.cleaned_data["commentaire"],
                        utilisateur=request.user,
                    )
                    journaliser(request, "ACTION_METIER", objet=facture, description="Litige résolu")
                    messages.success(request, "Litige résolu.")
                    return redirect("devis:detail_creance", facture_id=facture.id)
                except ValueError as e:
                    resolution_form.add_error(None, str(e))

        elif "abandonner_litige" in request.POST:
            litige_id = request.POST.get("litige_id")
            litige = get_object_or_404(Litige, pk=litige_id, facture=facture)
            try:
                litige.abandonner(utilisateur=request.user)
                journaliser(request, "ACTION_METIER", objet=facture, description="Litige abandonné")
                messages.success(request, "Litige abandonné.")
                return redirect("devis:detail_creance", facture_id=facture.id)
            except ValueError as e:
                messages.error(request, str(e))

        elif "ajouter_note" in request.POST:
            note_form = NoteInterneForm(request.POST)
            if note_form.is_valid():
                NoteInterne.objects.create(
                    content_type=facture_ct,
                    object_id=facture.id,
                    auteur=request.user,
                    message=note_form.cleaned_data["message"],
                )
                journaliser(request, "ACTION_METIER", objet=facture, description="Note interne ajoutée")
                return redirect("devis:detail_creance", facture_id=facture.id)

        elif "ajouter_commentaire" in request.POST:
            commentaire_form = CommentaireLitigeForm(request.POST)
            litige_id = request.POST.get("litige_id")
            litige = get_object_or_404(Litige, pk=litige_id, facture=facture)
            if commentaire_form.is_valid():
                commentaire = commentaire_form.save(commit=False)
                commentaire.litige = litige
                commentaire.auteur = request.user
                commentaire.save()
                messages.success(request, "Commentaire ajouté au litige.")
                return redirect("devis:detail_creance", facture_id=facture.id)

        elif "ajouter_piece" in request.POST:
            piece_form = PieceJointeLitigeForm(request.POST, request.FILES)
            litige_id = request.POST.get("litige_id")
            litige = get_object_or_404(Litige, pk=litige_id, facture=facture)
            if piece_form.is_valid():
                piece = piece_form.save(commit=False)
                piece.litige = litige
                piece.ajoute_par = request.user
                piece.save()
                messages.success(request, "Pièce jointe ajoutée au litige.")
                return redirect("devis:detail_creance", facture_id=facture.id)

        elif "archiver" in request.POST:
            if not _direction_ou_cadre(request.user):
                raise PermissionDenied
            try:
                facture.archiver(utilisateur=request.user)
                journaliser(request, "ACTION_METIER", objet=facture, description="Facture archivée")
                messages.success(request, "Facture archivée.")
            except ValueError as e:
                messages.error(request, str(e))
            return redirect("devis:liste_creances")

    journaliser(request, "CONSULTATION", objet=facture, description="Consultation de la fiche facture")

    context = {
        "module_actif": get_module_info("recouvrement"),
        "facture": facture,
        "form": paiement_form,
        "transition_form": transition_form,
        "avoir_form": avoir_form,
        "remboursement_form": remboursement_form,
        "compensation_form": compensation_form,
        "paiements": facture.paiements.select_related("utilisateur").order_by("-date_paiement"),
        "avoirs": facture.avoirs.select_related("cree_par").order_by("-date_creation"),
        "remboursements": facture.remboursements.select_related("utilisateur").order_by("-date_remboursement"),
        "compensations_emises": facture.compensations_emises.order_by("-date_creation"),
        "compensations_recues": facture.compensations_recues.order_by("-date_creation"),
        "historique": facture.historique_statuts.select_related("utilisateur").order_by("-date_changement"),
        "litiges": facture.litiges.select_related("ouvert_par").order_by("-date_ouverture"),
        "litige_form": litige_form,
        "affectation_form": affectation_form,
        "action_form": action_form,
        "actions_recouvrement": facture.actions_recouvrement.select_related("recouvreur").order_by("-date_action"),
        "commentaire_form": commentaire_form,
        "piece_form": piece_form,
        "resolution_form": resolution_form,
        "note_form": note_form,
        "notes": NoteInterne.objects.filter(content_type=facture_ct, object_id=facture.id).select_related("auteur"),
        "peut_ouvrir_litige": not facture.litiges.filter(statut__in=["OUVERT", "EN_COURS"]).exists()
            and facture.statut in Litige.STATUTS_SOURCE_AUTORISES,
        "peut_affecter": _direction_ou_cadre(request.user),
        "peut_archiver": _direction_ou_cadre(request.user) and facture.statut in ("PAYEE", "ANNULEE", "IRRECOUVRABLE"),
    }
    return render(request, "devis/creances/detail.html", context)


@login_required
def detail_litige(request, litige_id):
    litige = get_object_or_404(Litige, pk=litige_id)
    commentaire_form = CommentaireLitigeForm()
    piece_form = PieceJointeLitigeForm()
    resolution_form = ResolutionLitigeForm()

    if request.method == "POST":
        if "ajouter_commentaire" in request.POST:
            commentaire_form = CommentaireLitigeForm(request.POST)
            if commentaire_form.is_valid():
                commentaire = commentaire_form.save(commit=False)
                commentaire.litige = litige
                commentaire.auteur = request.user
                commentaire.save()
                journaliser(request, "ACTION_METIER", objet=litige, description="Commentaire ajouté au litige")
                messages.success(request, "Commentaire ajouté au litige.")
                return redirect("devis:detail_litige", litige_id=litige.id)

        elif "ajouter_piece" in request.POST:
            piece_form = PieceJointeLitigeForm(request.POST, request.FILES)
            if piece_form.is_valid():
                piece = piece_form.save(commit=False)
                piece.litige = litige
                piece.ajoute_par = request.user
                piece.save()
                journaliser(request, "ACTION_METIER", objet=litige, description=f"Pièce jointe ajoutée : {piece.libelle}")
                messages.success(request, "Pièce jointe ajoutée au litige.")
                return redirect("devis:detail_litige", litige_id=litige.id)

        elif "passer_en_cours" in request.POST:
            try:
                litige.passer_en_cours(utilisateur=request.user)
                journaliser(request, "ACTION_METIER", objet=litige, description="Litige passé en instruction")
                messages.success(request, "Litige passé en instruction.")
            except ValueError as e:
                messages.error(request, str(e))
            return redirect("devis:detail_litige", litige_id=litige.id)

        elif "resoudre_litige" in request.POST:
            resolution_form = ResolutionLitigeForm(request.POST)
            if resolution_form.is_valid():
                try:
                    litige.resoudre(
                        commentaire=resolution_form.cleaned_data["commentaire"],
                        utilisateur=request.user,
                    )
                    journaliser(request, "ACTION_METIER", objet=litige, description="Litige résolu")
                    messages.success(request, "Litige résolu.")
                    return redirect("devis:detail_creance", facture_id=litige.facture.id)
                except ValueError as e:
                    resolution_form.add_error(None, str(e))

        elif "abandonner_litige" in request.POST:
            resolution_form = ResolutionLitigeForm(request.POST)
            if resolution_form.is_valid():
                try:
                    litige.abandonner(
                        utilisateur=request.user,
                        commentaire=resolution_form.cleaned_data["commentaire"],
                    )
                    journaliser(request, "ACTION_METIER", objet=litige, description="Litige abandonné")
                    messages.success(request, "Litige abandonné.")
                    return redirect("devis:detail_creance", facture_id=litige.facture.id)
                except ValueError as e:
                    resolution_form.add_error(None, str(e))

    journaliser(request, "CONSULTATION", objet=litige)
    return render(request, "devis/creances/detail_litige.html", {
        "module_actif": get_module_info("recouvrement"),
        "litige": litige,
        "facture": litige.facture,
        "commentaire_form": commentaire_form,
        "piece_form": piece_form,
        "resolution_form": resolution_form,
    })


@login_required
def liste_litiges(request):
    litiges = Litige.objects.select_related("facture", "ouvert_par").order_by("-date_ouverture")

    statut = request.GET.get("statut", "")
    if statut:
        litiges = litiges.filter(statut=statut)

    recherche = request.GET.get("q", "").strip()
    if recherche:
        litiges = litiges.filter(
            Q(facture__numero_facture__icontains=recherche) | Q(facture__client_nom__icontains=recherche)
        )

    if "export" in request.GET:
        colonnes = [
            ("Facture", lambda l: l.facture.numero_facture),
            ("Client", lambda l: l.facture.client_nom),
            ("Motif", lambda l: l.get_motif_type_display()),
            ("Statut", lambda l: l.get_statut_display()),
            ("Ouvert le", lambda l: l.date_ouverture.strftime("%d/%m/%Y")),
            ("Ouvert par", lambda l: str(l.ouvert_par) if l.ouvert_par else "—"),
        ]
        journaliser(request, "EXPORT", description="Export liste des litiges")
        if request.GET["export"] == "excel":
            return exporter_excel(litiges, colonnes, "litiges")
        return exporter_csv(litiges, colonnes, "litiges")

    context = {
        "module_actif": get_module_info("recouvrement"),
        "litiges": litiges,
        "statuts": Litige.STATUT_CHOICES,
        "filtre_statut": statut,
        "filtre_recherche": recherche,
        "nb_ouverts": Litige.objects.filter(statut__in=["OUVERT", "EN_COURS"]).count(),
    }
    return render(request, "devis/creances/liste_litiges.html", context)


@login_required
def kanban_litiges(request):
    colonnes = []
    for code, libelle in Litige.STATUT_CHOICES:
        litiges = Litige.objects.filter(statut=code).select_related("facture")[:50]
        colonnes.append({"code": code, "libelle": libelle, "litiges": litiges})
    context = {"module_actif": get_module_info("recouvrement"), "colonnes": colonnes}
    return render(request, "devis/creances/kanban_litiges.html", context)


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def mon_portefeuille(request):
    factures = _factures_avec_soldes().filter(
        recouvreur=request.user
    ).exclude(statut__in=["PAYEE", "ANNULEE", "IRRECOUVRABLE"]).order_by("date_echeance")

    return render(request, "devis/creances/mon_portefeuille.html", {
        "module_actif": get_module_info("recouvrement"),
        "factures": factures,
    })


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def kpi_recouvreurs(request):
    if not _direction_ou_cadre(request.user):
        raise PermissionDenied

    recouvreurs = User.objects.filter(portefeuille_creances__isnull=False).distinct()
    donnees = []
    for r in recouvreurs:
        factures_qs = Facture.objects.filter(recouvreur=r)
        montant_recupere = Paiement.objects.filter(
            facture__recouvreur=r
        ).aggregate(total=Sum("montant"))["total"] or 0
        donnees.append({
            "recouvreur": r,
            "nb_factures": factures_qs.count(),
            "nb_appels": ActionRecouvrement.objects.filter(facture__recouvreur=r, type_action="APPEL").count(),
            "nb_emails": ActionRecouvrement.objects.filter(facture__recouvreur=r, type_action="EMAIL").count(),
            "montant_recupere": montant_recupere,
        })

    return render(request, "devis/creances/kpi_recouvreurs.html", {
        "module_actif": get_module_info("recouvrement"),
        "donnees": donnees,
    })


EtapeRelanceFormSet = modelformset_factory(EtapeRelance, form=EtapeRelanceForm, extra=0)


@login_required
def config_relances(request):
    profil = getattr(request.user, "profil", None)
    est_direction_cadre = profil and profil.role in (Profil.Role.DIRECTION, Profil.Role.CADRE)
    if not est_direction_cadre:
        raise PermissionDenied

    queryset = EtapeRelance.objects.all().order_by("delai_jours")

    if request.method == "POST":
        formset = EtapeRelanceFormSet(request.POST, queryset=queryset)
        if formset.is_valid():
            formset.save()
            journaliser(request, "MODIFICATION", description="Configuration des étapes de relance modifiée")
            messages.success(request, "Étapes de relance mises à jour.")
            return redirect("devis:config_relances")
    else:
        formset = EtapeRelanceFormSet(queryset=queryset)

    return render(request, "devis/creances/config_relances.html", {
        "module_actif": get_module_info("recouvrement"),
        "formset": formset,
    })


@login_required
def journal_relances(request):
    relances = Relance.objects.select_related("facture", "etape").order_by("-date_declenchement")

    etape_filtre = request.GET.get("etape", "")
    if etape_filtre:
        relances = relances.filter(etape_id=etape_filtre)

    recherche = request.GET.get("q", "").strip()
    if recherche:
        relances = relances.filter(facture__numero_facture__icontains=recherche)

    if "export" in request.GET:
        colonnes = [
            ("Date", lambda r: r.date_declenchement.strftime("%d/%m/%Y %H:%M")),
            ("Facture", lambda r: r.facture.numero_facture),
            ("Étape", lambda r: r.etape.nom),
            ("Résultat", lambda r: "OK" if r.reussie else f"Échec : {r.erreur}"),
        ]
        journaliser(request, "EXPORT", description="Export journal des relances")
        if request.GET["export"] == "excel":
            return exporter_excel(relances, colonnes, "journal_relances")
        return exporter_csv(relances, colonnes, "journal_relances")

    total = relances.count()
    echecs = relances.filter(reussie=False).count()
    taux_succes = round((total - echecs) / total * 100, 1) if total else None

    context = {
        "module_actif": get_module_info("recouvrement"),
        "relances": relances[:200],
        "etapes": EtapeRelance.objects.all().order_by("delai_jours"),
        "filtre_etape": etape_filtre,
        "filtre_recherche": recherche,
        "total": total,
        "echecs": echecs,
        "taux_succes": taux_succes,
    }
    return render(request, "devis/creances/journal_relances.html", context)


@login_required
def journal_actions_recouvrement(request):
    actions = ActionRecouvrement.objects.select_related("facture", "recouvreur").order_by("-date_action")

    recouvreur_id = request.GET.get("recouvreur", "")
    if recouvreur_id:
        actions = actions.filter(recouvreur_id=recouvreur_id)

    recherche = request.GET.get("q", "").strip()
    if recherche:
        actions = actions.filter(facture__numero_facture__icontains=recherche)

    if "export" in request.GET:
        colonnes = [
            ("Date", lambda a: a.date_action.strftime("%d/%m/%Y %H:%M")),
            ("Facture", lambda a: a.facture.numero_facture),
            ("Type", lambda a: a.get_type_action_display()),
            ("Recouvreur", lambda a: str(a.recouvreur) if a.recouvreur else "—"),
            ("Commentaire", lambda a: a.commentaire),
        ]
        journaliser(request, "EXPORT", description="Export journal des actions de recouvrement")
        if request.GET["export"] == "excel":
            return exporter_excel(actions, colonnes, "actions_recouvrement")
        return exporter_csv(actions, colonnes, "actions_recouvrement")

    context = {
        "module_actif": get_module_info("recouvrement"),
        "actions": actions[:200],
        "recouvreurs": User.objects.filter(portefeuille_creances__isnull=False).distinct(),
        "filtre_recouvreur": recouvreur_id,
        "filtre_recherche": recherche,
    }
    return render(request, "devis/creances/journal_actions.html", context)


@login_required
def affectation_masse(request):
    if not _direction_ou_cadre(request.user):
        raise PermissionDenied

    factures_ouvertes = Facture.objects.exclude(
        statut__in=["PAYEE", "ANNULEE", "IRRECOUVRABLE"]
    ).select_related("recouvreur")

    client_filtre = request.GET.get("client", "").strip()
    if client_filtre:
        factures_ouvertes = factures_ouvertes.filter(client_nom__icontains=client_filtre)

    if request.method == "POST":
        recouvreur_id = request.POST.get("recouvreur") or None
        facture_ids = request.POST.getlist("factures")
        if facture_ids:
            nb = Facture.objects.filter(id__in=facture_ids).update(recouvreur_id=recouvreur_id)
            recouvreur = User.objects.filter(id=recouvreur_id).first() if recouvreur_id else None
            journaliser(request, "MODIFICATION", description=f"Affectation en masse : {nb} facture(s) → recouvreur {recouvreur or 'aucun'}")
            messages.success(request, f"{nb} facture(s) affectée(s).")
            return redirect("devis:affectation_masse")

    context = {
        "module_actif": get_module_info("recouvrement"),
        "factures": factures_ouvertes,
        "recouvreurs": User.objects.filter(portefeuille_creances__isnull=False).distinct(),
        "filtre_client": client_filtre,
    }
    return render(request, "devis/creances/affectation_masse.html", context)


@login_required
def calendrier_relances(request):
    from collections import defaultdict
    from datetime import timedelta

    aujourdhui = timezone.now().date()
    horizon = aujourdhui + timedelta(days=60)

    etapes = list(EtapeRelance.objects.filter(actif=True))
    factures = Facture.objects.filter(
        statut__in=["EN_ATTENTE_PAIEMENT", "PARTIELLEMENT_PAYEE", "EN_RETARD"],
        date_echeance__isnull=False,
    )

    par_jour = defaultdict(list)
    for f in factures:
        deja_declenchees = set(Relance.objects.filter(facture=f).values_list("etape_id", flat=True))
        for etape in etapes:
            if etape.id in deja_declenchees:
                continue
            date_prevue = f.date_echeance + timedelta(days=etape.delai_jours)
            if aujourdhui <= date_prevue <= horizon:
                par_jour[date_prevue].append({"facture": f, "etape": etape})

    jours_tries = sorted(par_jour.items())

    context = {
        "module_actif": get_module_info("recouvrement"),
        "jours": jours_tries,
        "aujourdhui": aujourdhui,
    }
    return render(request, "devis/creances/calendrier_relances.html", context)


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