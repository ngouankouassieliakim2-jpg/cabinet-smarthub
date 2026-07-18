import json
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from comptes.decorators import role_requis
from comptes.models import Profil
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.utils.text import slugify
from decimal import Decimal
from django.urls import reverse

from .models import Absence, Employeur, Employe, BulletinPaie, PrimeConfiguree, SecteurActivite, CategorieSalaire, RubriqueRecurrente, Emploi, PeriodeEmploi, ReglageGenerationAuto, DeclarationDASC, ReglementCNPS, Pret, RemboursementPret, JourFerie, Conge, MouvementPersonnel
from .forms import AbsenceForm, RubriqueForm, SecteurForm, CategorieForm, EmployeForm, EmployeurForm, EmployeurDepuisClientForm, FinContratForm, ImportDocumentForm, AvenantForm, EmploiForm, PretForm, JourFerieForm, CongePoserForm, CongeExceptionnelForm, ContratGenerationForm
from .calculs import calculer_bulletin, taux_horaire
from .conges import calculer_conge
from .pdf import generer_pdf_bulletin, generer_pdf_bulletins_groupes, generer_pdf_livre_mensuel, generer_pdf_livre_annuel, generer_pdf_recap_annuel, generer_pdf_justificatif_pret, generer_pdf_ordre_virement
from pilotage.modules_data import MODULES, charger_sous_modules
from .calculs_rupture import calculer_fin_contrat
from .edi import generer_edi_its
from .declarations import generer_cnps_nominative, generer_disa, cotisations_cnps_mois
from .attestations import generer_attestation
from .archivage import archiver_document, archiver_et_renvoyer
from .contrats import generer_contrat_cdi




def _contexte_paie():
    """Barre du haut + sidebar de l'interface Direction pour le module Social & RH."""
    modules_nav = [{"cle": "dashboard", "nom": "Tableau de bord", "icone": "🏠", "url": "/pilotage/"}]
    for cle, data in MODULES.items():
        modules_nav.append({
            "cle": cle, "nom": data["nom"], "icone": data["icone"],
            "url": f"/pilotage/module/{cle}/",
        })
    data = MODULES.get("social-rh", {})
    return {
        "modules_nav": modules_nav,
        "module_actif": {
            "cle": "social-rh",
            "nom": data.get("nom", "Social & RH"),
            "icone": data.get("icone", "👥"),
            "description": data.get("description", "Social & RH"),
        },
        "sous_modules": charger_sous_modules("paie"),
        "module_nom": data.get("nom", "Social & RH"),
        "module_icone": data.get("icone", "👥"),
    }


def _salaire_categoriel(employeur, code):
    """Salaire catégoriel lu dans la grille du secteur de l'employeur, selon le code catégorie."""
    if employeur.secteur and code:
        cat = employeur.secteur.grille.filter(code=code).first()
        if cat:
            return Decimal(str(cat.salaire_minimum))
    return Decimal("0")


def _grille_json(employeur):
    """Dictionnaire code -> salaire, pour l'affichage en direct dans le formulaire."""
    d = {}
    if employeur.secteur:
        for c in employeur.secteur.grille.all():
            d[c.code] = float(c.salaire_minimum)
    return json.dumps(d)


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def liste_employeurs(request):
    employeurs = Employeur.objects.all()
    maintenant = timezone.now()
    stats = {
        'nb_employeurs': employeurs.count(),
        'total_employes': Employe.objects.count(),
        'nb_conventions': SecteurActivite.objects.count(),
        'paies_ce_mois': BulletinPaie.objects.filter(
            mois=maintenant.month,
            annee=maintenant.year
        ).count(),
    }
    ctx = _contexte_paie()
    ctx.update({
        "employeurs": employeurs,
        "stats": stats,
        "paie_employeur_nouveau_url": reverse('paie_employeur_nouveau'),
    })
    return render(request, "paie/liste_employeurs.html", ctx)


# ========== GRILLE DES SALAIRES ==========

@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def grille_salaires(request):
    categories = CategorieSalaire.objects.select_related("secteur").all()
    secteurs = SecteurActivite.objects.all()
    ctx = _contexte_paie()
    ctx.update({
        "categories": categories, "secteurs": secteurs,
        "form_cat": CategorieForm(), "form_sect": SecteurForm(),
    })
    return render(request, "paie/grille_salaires.html", ctx)


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def categorie_ajouter(request):
    if request.method == "POST":
        form = CategorieForm(request.POST)
        if form.is_valid():
            form.save()
    return redirect("paie_grille")


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def categorie_modifier(request, categorie_id):
    cat = get_object_or_404(CategorieSalaire, pk=categorie_id)
    if request.method == "POST":
        form = CategorieForm(request.POST, instance=cat)
        if form.is_valid():
            form.save()
            return redirect("paie_grille")
    else:
        form = CategorieForm(instance=cat)
    ctx = _contexte_paie()
    ctx.update({"form": form, "categorie": cat})
    return render(request, "paie/form_categorie.html", ctx)


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def categorie_supprimer(request, categorie_id):
    cat = get_object_or_404(CategorieSalaire, pk=categorie_id)
    if request.method == "POST":
        cat.delete()
    return redirect("paie_grille")


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def secteur_ajouter(request):
    if request.method == "POST":
        form = SecteurForm(request.POST)
        if form.is_valid():
            form.save()
    return redirect("paie_grille")


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def secteur_modifier(request, secteur_id):
    secteur = get_object_or_404(SecteurActivite, pk=secteur_id)
    if request.method == "POST":
        form = SecteurForm(request.POST, instance=secteur)
        if form.is_valid():
            form.save()
            return redirect("paie_grille")
    else:
        form = SecteurForm(instance=secteur)
    ctx = _contexte_paie()
    ctx.update({"form": form, "secteur": secteur})
    return render(request, "paie/form_secteur.html", ctx)


# ========== PERSONNEL (fiche salarié) ==========

def _enregistrer_rubriques_recurrentes(request, employe, employeur):
    """Supprime et recrée les rubriques récurrentes du salarié à partir du formulaire."""
    employe.rubriques_recurrentes.all().delete()
    ids = request.POST.getlist("rub_rubrique")
    montants = request.POST.getlist("rub_montant")
    catalogue = {str(r.id): r for r in employeur.primes_configurees.all()}
    for rid, montant in zip(ids, montants):
        if not rid or rid not in catalogue:
            continue
        try:
            m = Decimal(montant) if montant not in (None, "") else Decimal("0")
        except Exception:
            m = Decimal("0")
        RubriqueRecurrente.objects.create(employe=employe, rubrique=catalogue[rid], montant=m)


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def employes_liste(request, employeur_id):
    employeur = get_object_or_404(Employeur, pk=employeur_id)
    employes = employeur.employes.all()
    nb_alertes_cdd = sum(1 for e in employes if e.alerte_requalification_cdd)
    ctx = _contexte_paie()
    ctx.update({"employeur": employeur, "employes": employes, "nb_alertes_cdd": nb_alertes_cdd})
    return render(request, "paie/employes_liste.html", ctx)


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def journal_personnel(request, employeur_id):
    """Journal chronologique des mouvements du personnel d'une entreprise."""
    employeur = get_object_or_404(Employeur, pk=employeur_id)
    mouvements = employeur.mouvements_personnel.select_related("employe").all()
    ctx = _contexte_paie()
    ctx.update({"employeur": employeur, "mouvements": mouvements})
    return render(request, "paie/journal_personnel.html", ctx)


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def indicateurs_rh(request, employeur_id):
    """Tableau de bord RH : effectifs, masse salariale, turnover, alertes."""
    from datetime import date
    employeur = get_object_or_404(Employeur, pk=employeur_id)
    annee = int(request.GET.get("annee", timezone.now().year))
    mois = int(request.GET.get("mois", timezone.now().month))

    actifs = employeur.employes.filter(statut="ACTIF")
    effectif_total = actifs.count()
    par_contrat = {
        "CDI": actifs.filter(contrat="CDI").count(),
        "CDD": actifs.filter(contrat="CDD").count(),
        "STAGE": actifs.filter(contrat="STAGE").count(),
    }

    # Masse salariale du mois choisi
    bulletins_mois = BulletinPaie.objects.filter(employe__employeur=employeur, mois=mois, annee=annee)
    masse_brute = Decimal("0")
    masse_nette = Decimal("0")
    for b in bulletins_mois:
        c = calculer_bulletin(b)
        masse_brute += c["total_gains"]
        masse_nette += c["net_arrondi"]

    # Turnover de l'année (depuis le journal)
    mouvements_annee = employeur.mouvements_personnel.filter(date_mouvement__year=annee)
    nb_embauches = mouvements_annee.filter(type_mouvement="embauche").count()
    nb_sorties = mouvements_annee.filter(type_mouvement="sortie").count()

    # Répartition par catégorie
    par_categorie = {}
    for e in actifs:
        cle = e.categorie or "—"
        par_categorie[cle] = par_categorie.get(cle, 0) + 1

    # Alertes
    alertes_requalification = [e for e in actifs if e.alerte_requalification_cdd]
    alertes_echeance = [e for e in actifs if e.echeance_proche]

    mois_liste = [(i, nom) for i, nom in BulletinPaie.MOIS_CHOICES]
    annees_liste = list(range(annee - 2, annee + 2))
    mois_nom = dict(BulletinPaie.MOIS_CHOICES).get(mois, "")

    ctx = _contexte_paie()
    ctx.update({
        "employeur": employeur, "effectif_total": effectif_total, "par_contrat": par_contrat,
        "masse_brute": masse_brute, "masse_nette": masse_nette,
        "nb_embauches": nb_embauches, "nb_sorties": nb_sorties,
        "par_categorie": par_categorie,
        "alertes_requalification": alertes_requalification, "alertes_echeance": alertes_echeance,
        "annee": annee, "mois": mois, "mois_nom": mois_nom,
        "mois_liste": mois_liste, "annees_liste": annees_liste,
    })
    return render(request, "paie/indicateurs_rh.html", ctx)


def _matricule_auto(employeur):
    """Suggère un matricule : préfixe (sigle) + compteur, sans réutiliser un existant."""
    prefixe = (employeur.sigle or employeur.raison_sociale[:3] or "EMP").upper().replace(" ", "")[:4]
    n = employeur.employes.count() + 1
    while employeur.employes.filter(matricule=f"{prefixe}-{n:05d}").exists():
        n += 1
    return f"{prefixe}-{n:05d}"


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def employe_creer(request, employeur_id):
    employeur = get_object_or_404(Employeur, pk=employeur_id)
    if request.method == "POST":
        form = EmployeForm(request.POST, employeur=employeur)
        if form.is_valid():
            emp = form.save(commit=False)
            emp.employeur = employeur
            emp.salaire_base = _salaire_categoriel(employeur, emp.categorie) + (emp.sursalaire or Decimal("0"))
            emp.save()
            _enregistrer_rubriques_recurrentes(request, emp, employeur)
            MouvementPersonnel.objects.create(
                employe=emp, employeur=employeur, type_mouvement="embauche",
                date_mouvement=emp.date_entree, detail=f"{emp.get_contrat_display()} — {emp.poste or emp.categorie}")
            return redirect("paie_employes_liste", employeur_id=employeur.id)
    else:
        form = EmployeForm(employeur=employeur, initial={"matricule": _matricule_auto(employeur)})
    ctx = _contexte_paie()
    ctx.update({
        "form": form, "employeur": employeur, "titre": "Nouveau salarié",
        "grille_json": _grille_json(employeur),
        "rubriques_catalogue": employeur.primes_configurees.all(),
        "rubriques_recurrentes": [],
    })
    return render(request, "paie/form_employe.html", ctx)


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def employe_modifier(request, employeur_id, employe_id):
    employeur = get_object_or_404(Employeur, pk=employeur_id)
    emp = get_object_or_404(Employe, pk=employe_id, employeur=employeur)
    if request.method == "POST":
        ancien_salaire = emp.salaire_base
        ancien_poste = emp.poste
        form = EmployeForm(request.POST, instance=emp, employeur=employeur)
        if form.is_valid():
            emp = form.save(commit=False)
            emp.salaire_base = _salaire_categoriel(employeur, emp.categorie) + (emp.sursalaire or Decimal("0"))
            emp.save()
            if emp.salaire_base != ancien_salaire:
                MouvementPersonnel.objects.create(
                    employe=emp, employeur=employeur, type_mouvement="changement_salaire",
                    date_mouvement=timezone.now().date(),
                    detail=f"{ancien_salaire:.0f} F → {emp.salaire_base:.0f} F")
            if emp.poste != ancien_poste and emp.poste:
                MouvementPersonnel.objects.create(
                    employe=emp, employeur=employeur, type_mouvement="changement_poste",
                    date_mouvement=timezone.now().date(),
                    detail=f"{ancien_poste or '—'} → {emp.poste}")
            _enregistrer_rubriques_recurrentes(request, emp, employeur)
            return redirect("paie_employes_liste", employeur_id=employeur.id)
    else:
        form = EmployeForm(instance=emp, employeur=employeur)
    ctx = _contexte_paie()
    ctx.update({
        "form": form, "employeur": employeur, "titre": "Modifier le salarié", "employe": emp,
        "grille_json": _grille_json(employeur),
        "rubriques_catalogue": employeur.primes_configurees.all(),
        "rubriques_recurrentes": emp.rubriques_recurrentes.select_related("rubrique").all(),
        "periodes_anterieures": emp.periodes_anterieures.all(),
    })
    return render(request, "paie/form_employe.html", ctx)
@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def employe_transformer_cdi(request, employeur_id, employe_id):
    """CDD → CDI : même matricule, pas de rupture, on efface juste les infos de fin de CDD."""
    employeur = get_object_or_404(Employeur, pk=employeur_id)
    emp = get_object_or_404(Employe, pk=employe_id, employeur=employeur)
    if request.method == "POST":
        emp.contrat = "CDI"
        emp.duree_cdd_mois = None
        emp.date_sortie = None
        emp.save()
        MouvementPersonnel.objects.create(
            employe=emp, employeur=employeur, type_mouvement="transformation_cdi",
            date_mouvement=timezone.now().date(), detail="CDD requalifié en CDI")
        return redirect("paie_employes_liste", employeur_id=employeur.id)
    ctx = _contexte_paie()
    ctx.update({"employeur": employeur, "employe": emp})
    return render(request, "paie/confirmer_transformation_cdi.html", ctx)


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def employe_reembaucher(request, employeur_id, employe_id):
    """Réembauche : archive la période close dans PeriodeEmploi, nouveau matricule, nouvelle période active."""
    employeur = get_object_or_404(Employeur, pk=employeur_id)
    emp = get_object_or_404(Employe, pk=employe_id, employeur=employeur)
    if emp.statut != "SORTI":
        return redirect("paie_employes_liste", employeur_id=employeur.id)

    if request.method == "POST":
        # 1) Archiver la période qui se termine
        PeriodeEmploi.objects.create(
            employe=emp,
            matricule=emp.matricule,
            contrat=emp.contrat,
            date_entree=emp.date_entree,
            date_sortie=emp.date_sortie or timezone.now().date(),
            motif_sortie=emp.motif_sortie,
        )
        # 2) Ouvrir la nouvelle période
        emp.matricule = _matricule_auto(employeur)
        emp.date_entree = request.POST.get("date_entree") or timezone.now().date()
        emp.date_sortie = None
        emp.motif_sortie = ""
        emp.contrat = request.POST.get("contrat", emp.contrat)
        emp.statut = "ACTIF"
        emp.save()
        MouvementPersonnel.objects.create(
            employe=emp, employeur=employeur, type_mouvement="reembauche",
            date_mouvement=emp.date_entree, detail=f"Nouveau matricule {emp.matricule}")
        return redirect("paie_employes_liste", employeur_id=employeur.id)

    ctx = _contexte_paie()
    ctx.update({"employeur": employeur, "employe": emp, "today": timezone.now().date()})
    return render(request, "paie/form_reembauche.html", ctx)


# ========== CATALOGUE DE RUBRIQUES (par employeur) ==========

@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def rubriques_liste(request, employeur_id):
    employeur = get_object_or_404(Employeur, pk=employeur_id)
    rubriques = employeur.primes_configurees.all()
    ctx = _contexte_paie()
    ctx.update({"employeur": employeur, "rubriques": rubriques})
    return render(request, "paie/rubriques_liste.html", ctx)


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def rubrique_creer(request, employeur_id):
    employeur = get_object_or_404(Employeur, pk=employeur_id)
    if request.method == "POST":
        form = RubriqueForm(request.POST)
        if form.is_valid():
            rubrique = form.save(commit=False)
            rubrique.employeur = employeur
            rubrique.save()
            return redirect("paie_rubriques_liste", employeur_id=employeur.id)
    else:
        form = RubriqueForm()
    ctx = _contexte_paie()
    ctx.update({"form": form, "employeur": employeur, "titre": "Nouvelle rubrique"})
    return render(request, "paie/form_rubrique.html", ctx)


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def rubrique_modifier(request, employeur_id, rubrique_id):
    employeur = get_object_or_404(Employeur, pk=employeur_id)
    rubrique = get_object_or_404(PrimeConfiguree, pk=rubrique_id, employeur=employeur)
    if request.method == "POST":
        form = RubriqueForm(request.POST, instance=rubrique)
        if form.is_valid():
            form.save()
            return redirect("paie_rubriques_liste", employeur_id=employeur.id)
    else:
        form = RubriqueForm(instance=rubrique)
    ctx = _contexte_paie()
    ctx.update({"form": form, "employeur": employeur, "titre": "Modifier la rubrique", "rubrique": rubrique})
    return render(request, "paie/form_rubrique.html", ctx)


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def rubrique_supprimer(request, employeur_id, rubrique_id):
    employeur = get_object_or_404(Employeur, pk=employeur_id)
    rubrique = get_object_or_404(PrimeConfiguree, pk=rubrique_id, employeur=employeur)
    if request.method == "POST":
        rubrique.delete()
    return redirect("paie_rubriques_liste", employeur_id=employeur.id)


# ========== TRAITEMENT DE LA PAIE (table vivante) ==========

# Le salaire de base n'est PAS ici : il vient de la catégorie du salarié.
TABLE_FIELDS = ["jours_travailles", "prime_transport", "heures_sup", "avance_acompte"]


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def traitement_paie(request, employeur_id):
    employeur = get_object_or_404(Employeur, pk=employeur_id)

    if request.method == "POST":
        mois = int(request.POST.get("mois"))
        annee = int(request.POST.get("annee"))
        action = request.POST.get("action", "enregistrer")
    else:
        mois = int(request.GET.get("mois", timezone.now().month))
        annee = int(request.GET.get("annee", timezone.now().year))

    # Seuls les salariés EN ACTIVITÉ sur ce mois (pas avant l'entrée, pas après la sortie)
    employes = [e for e in employeur.employes.filter(statut="ACTIF") if e.est_actif_sur(mois, annee)]

    if request.method == "POST":
        if action == "generer":
            # Crée les bulletins MANQUANTS, pré-remplis, sans toucher aux existants
            from .calculs import jours_travailles_depuis_absences
            for e in employes:
                jt = jours_travailles_depuis_absences(e, mois, annee)
                BulletinPaie.objects.get_or_create(
                    employe=e, mois=mois, annee=annee,
                    defaults={"salaire_base": e.salaire_base, "jours_travailles": jt})
        else:
            # Enregistre les ajustements de la table
            for e in employes:
                prefixe = f"emp_{e.id}_"
                bulletin, _ = BulletinPaie.objects.get_or_create(
                    employe=e, mois=mois, annee=annee,
                    defaults={"salaire_base": e.salaire_base})
                # Un solde de tout compte est finalisé : on ne l'écrase pas
                if not getattr(bulletin, "est_solde_tout_compte", False):
                    bulletin.salaire_base = e.salaire_base
                    bulletin.sursalaire = Decimal("0")
                    for champ in TABLE_FIELDS:
                        valeur = request.POST.get(prefixe + champ)
                        if valeur is not None and valeur != "":
                            setattr(bulletin, champ, Decimal(valeur))
                    bulletin.save()
        return redirect(f"{request.path}?mois={mois}&annee={annee}")

    # === Affichage ===
    ids_enregistres = set(BulletinPaie.objects.filter(
        employe__in=[e.id for e in employes], mois=mois, annee=annee).values_list("employe_id", flat=True))

    lignes = []
    for e in employes:
        bulletin = BulletinPaie.objects.filter(employe=e, mois=mois, annee=annee).first()
        if not bulletin:
            bulletin = BulletinPaie(employe=e, mois=mois, annee=annee,
                                    jours_travailles=30, salaire_base=e.salaire_base, sursalaire=0)
        calcul = calculer_bulletin(bulletin)
        lignes.append({"employe": e, "bulletin": bulletin, "calcul": calcul,
                       "enregistre": e.id in ids_enregistres})

    mois_liste = [(i, nom) for i, nom in BulletinPaie.MOIS_CHOICES]
    annees_liste = list(range(annee - 2, annee + 2))
    # Report automatique du prêt (décaissement en gain / mensualité en retenue)
    for e in employes:
        b = BulletinPaie.objects.filter(employe=e, mois=mois, annee=annee).first()
        if b and not getattr(b, "est_solde_tout_compte", False):
            _reporter_pret_sur_bulletin(b)
            b.save()

    ctx = _contexte_paie()
    ctx.update({
        "employeur": employeur, "lignes": lignes, "mois": mois, "annee": annee,
        "mois_liste": mois_liste, "annees_liste": annees_liste,
        "nb_enregistres": len(ids_enregistres), "nb_employes": len(employes),
    })
    return render(request, "paie/traitement_paie.html", ctx)

    # === Affichage ===
    ids_enregistres = set(BulletinPaie.objects.filter(
        employe__in=[e.id for e in employes], mois=mois, annee=annee).values_list("employe_id", flat=True))

    lignes = []
    for e in employes:
        bulletin = BulletinPaie.objects.filter(employe=e, mois=mois, annee=annee).first()
        if not bulletin:
            bulletin = BulletinPaie(employe=e, mois=mois, annee=annee,
                                    jours_travailles=30, salaire_base=e.salaire_base, sursalaire=0)
        calcul = calculer_bulletin(bulletin)
        lignes.append({"employe": e, "bulletin": bulletin, "calcul": calcul,
                       "enregistre": e.id in ids_enregistres})

    mois_liste = [(i, nom) for i, nom in BulletinPaie.MOIS_CHOICES]
    annees_liste = list(range(annee - 2, annee + 2))

    ctx = _contexte_paie()
    ctx.update({
        "employeur": employeur, "lignes": lignes, "mois": mois, "annee": annee,
        "mois_liste": mois_liste, "annees_liste": annees_liste,
        "nb_enregistres": len(ids_enregistres), "nb_employes": employes.count(),
    })
    return render(request, "paie/traitement_paie.html", ctx)


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def traitement_calcul(request, employeur_id):
    """Recalcule UNE ligne à la volée (AJAX), sans rien enregistrer."""
    employeur = get_object_or_404(Employeur, pk=employeur_id)
    employe = get_object_or_404(Employe, pk=request.POST.get("employe_id"), employeur=employeur)
    mois = int(request.POST.get("mois"))
    annee = int(request.POST.get("annee"))

    bulletin = BulletinPaie.objects.filter(employe=employe, mois=mois, annee=annee).first()
    if not bulletin:
        bulletin = BulletinPaie(employe=employe, mois=mois, annee=annee)
    # Le salaire de base vient toujours de la catégorie du salarié
    bulletin.salaire_base = employe.salaire_base
    bulletin.sursalaire = Decimal("0")

    for champ in TABLE_FIELDS:
        valeur = request.POST.get(champ)
        if valeur is not None and valeur != "":
            setattr(bulletin, champ, Decimal(valeur))

    c = calculer_bulletin(bulletin)
    return JsonResponse({
        "total_gains": float(c["total_gains"]),
        "its_final": float(c["its_final"]),
        "cnps_retraite_salarie": float(c["cnps_retraite_salarie"]),
        "net_arrondi": float(c["net_arrondi"]),
    })

@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def bulletin_pdf(request, employeur_id, employe_id):
    """Génère et affiche le bulletin de paie PDF d'un salarié pour un mois donné."""
    employeur = get_object_or_404(Employeur, pk=employeur_id)
    employe = get_object_or_404(Employe, pk=employe_id, employeur=employeur)
    mois = int(request.GET.get("mois", timezone.now().month))
    annee = int(request.GET.get("annee", timezone.now().year))

    bulletin = BulletinPaie.objects.filter(employe=employe, mois=mois, annee=annee).first()
    if not bulletin:
        if not employe.est_actif_sur(mois, annee):
            return HttpResponse(
                "<p style='font-family:sans-serif;padding:2rem;color:#b91c1c'>"
                "Ce salarié n'était pas en activité sur cette période — aucun bulletin ne peut être établi.</p>",
                status=400)
        bulletin = BulletinPaie(employe=employe, mois=mois, annee=annee,
                                jours_travailles=30, salaire_base=employe.salaire_base)

    pdf_bytes = generer_pdf_bulletin(bulletin, mois, annee, request)
    nom_fichier = f"bulletin-{employe.matricule or employe.id}-{mois}-{annee}.pdf"
    libelle = f"Bulletin de paie — {employe.nom_prenoms} — {mois}/{annee}"
    cle = f"bulletin-emp{employe.id}-{mois}-{annee}"
    return archiver_et_renvoyer(
        employeur, pdf_bytes, nom_fichier, "application/pdf",
        type_doc="bulletin", libelle=libelle, cle=cle,
        employe=employe, mois=mois, annee=annee)

@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def recap_annuel_pdf(request, employeur_id, employe_id):
    employeur = get_object_or_404(Employeur, pk=employeur_id)
    employe = get_object_or_404(Employe, pk=employe_id, employeur=employeur)
    annee = int(request.GET.get("annee", timezone.now().year))
    from .pdf import generer_pdf_recap_annuel
    pdf_bytes = generer_pdf_recap_annuel(employe, annee, request)
    nom_fichier = f"recap-annuel-{employe.matricule}-{annee}.pdf"
    libelle = f"Récapitulatif annuel {annee} — {employe.nom_prenoms}"
    cle = f"recap_annuel-emp{employe.id}-{annee}"
    return archiver_et_renvoyer(
        employeur, pdf_bytes, nom_fichier, "application/pdf",
        type_doc="recap_annuel", libelle=libelle, cle=cle,
        employe=employe, annee=annee)

# ========== NAVIGATION : choisir une entreprise ==========

@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def choisir_entreprise(request, section):
    """Liste les entreprises pour accéder à une section (personnel, rubriques, traitement, documents)."""
    employeurs = Employeur.objects.all()
    titres = {"personnel": "Personnel", "rubriques": "Rubriques",
              "traitement": "Traitement de la paie", "documents": "Documents",
              "actions-rh": "Actions RH"}
    ctx = _contexte_paie()
    ctx.update({"employeurs": employeurs, "section": section, "titre_section": titres.get(section, "")})
    return render(request, "paie/choisir_entreprise.html", ctx)


# ========== DOCUMENTS : entreprise -> période -> documents du mois ==========

@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def documents_periodes(request, employeur_id):
    employeur = get_object_or_404(Employeur, pk=employeur_id)
    periodes = (BulletinPaie.objects.filter(employe__employeur=employeur)
                .values("mois", "annee").distinct().order_by("-annee", "-mois"))
    mois_noms = dict(BulletinPaie.MOIS_CHOICES)
    periodes_list = []
    for p in periodes:
        nb = BulletinPaie.objects.filter(employe__employeur=employeur, mois=p["mois"], annee=p["annee"]).count()
        periodes_list.append({"mois": p["mois"], "annee": p["annee"], "nom": mois_noms.get(p["mois"], ""), "nb": nb})
    ctx = _contexte_paie()
    ctx.update({"employeur": employeur, "periodes": periodes_list})
    return render(request, "paie/documents_periodes.html", ctx)


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def documents_mois(request, employeur_id, annee, mois):
    employeur = get_object_or_404(Employeur, pk=employeur_id)
    bulletins = (BulletinPaie.objects.filter(employe__employeur=employeur, mois=mois, annee=annee)
                 .select_related("employe").order_by("employe__nom_prenoms"))
    mois_nom = dict(BulletinPaie.MOIS_CHOICES).get(mois, "")
    ctx = _contexte_paie()
    ctx.update({"employeur": employeur, "bulletins": bulletins, "mois": mois, "annee": annee, "mois_nom": mois_nom})
    return render(request, "paie/documents_mois.html", ctx)
@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def employeur_nouveau(request):
    """Crée un employeur à partir d'un client existant + une convention collective."""
    if request.method == "POST":
        form = EmployeurDepuisClientForm(request.POST)
        if form.is_valid():
            client = form.cleaned_data["client"]
            secteur = form.cleaned_data["secteur"]
            employeur = Employeur.objects.create(
                client=client,
                raison_sociale=client.nom or "Entreprise",
                ncc=client.ncc or "",
                commune=client.commune or "",
                secteur=secteur,
                banque_nom=form.cleaned_data.get("banque_nom", ""),
                banque_code=form.cleaned_data.get("banque_code", ""),
                banque_guichet=form.cleaned_data.get("banque_guichet", ""),
                banque_numero_compte=form.cleaned_data.get("banque_numero_compte", ""),
                banque_cle_rib=form.cleaned_data.get("banque_cle_rib", ""),
                banque_iban=form.cleaned_data.get("banque_iban", ""),
                banque_intitule=form.cleaned_data.get("banque_intitule", ""),
            )
            # On reprend le logo du client s'il existe
            if client.logo_entreprise:
                employeur.logo = client.logo_entreprise
                employeur.save()
            return redirect("paie_employes_liste", employeur_id=employeur.id)
    else:
        form = EmployeurDepuisClientForm()
    ctx = _contexte_paie()
    ctx.update({"form": form})
    return render(request, "paie/form_employeur_nouveau.html", ctx)

@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def bulletins_groupes_pdf(request, employeur_id):
    """Tous les bulletins d'un mois pour une entreprise, dans un seul PDF."""
    employeur = get_object_or_404(Employeur, pk=employeur_id)
    mois = int(request.GET.get("mois", timezone.now().month))
    annee = int(request.GET.get("annee", timezone.now().year))
    pdf_bytes = generer_pdf_bulletins_groupes(employeur, mois, annee, request)
    nom_fichier = f"bulletins-{employeur.id}-{mois}-{annee}.pdf"
    libelle = f"Bulletins groupés — {employeur.raison_sociale} — {mois}/{annee}"
    cle = f"bulletins_groupes-{employeur.id}-{mois}-{annee}"
    return archiver_et_renvoyer(
        employeur, pdf_bytes, nom_fichier, "application/pdf",
        type_doc="bulletins_groupes", libelle=libelle, cle=cle,
        mois=mois, annee=annee)


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def ordre_virement_pdf(request, employeur_id):
    employeur = get_object_or_404(Employeur, pk=employeur_id)
    mois = int(request.GET.get("mois", timezone.now().month))
    annee = int(request.GET.get("annee", timezone.now().year))
    pdf_bytes = generer_pdf_ordre_virement(employeur, mois, annee, request)
    nom_fichier = f"ordre-virement-{employeur.id}-{mois}-{annee}.pdf"
    mois_nom = dict(BulletinPaie.MOIS_CHOICES).get(mois, "")
    libelle = f"Ordre de virement — {employeur.raison_sociale} — {mois_nom} {annee}"
    cle = f"ordre_virement-{employeur.id}-{mois}-{annee}"
    return archiver_et_renvoyer(
        employeur, pdf_bytes, nom_fichier, "application/pdf",
        type_doc="ordre_virement", libelle=libelle, cle=cle, mois=mois, annee=annee)


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def livre_mensuel_pdf(request, employeur_id):
    """Livre de paie mensuel (récapitulatif) en PDF."""
    employeur = get_object_or_404(Employeur, pk=employeur_id)
    mois = int(request.GET.get("mois", timezone.now().month))
    annee = int(request.GET.get("annee", timezone.now().year))
    pdf_bytes = generer_pdf_livre_mensuel(employeur, mois, annee, request)
    nom_fichier = f"livre-paie-{employeur.id}-{mois}-{annee}.pdf"
    libelle = f"Livre de paie mensuel — {employeur.raison_sociale} — {mois}/{annee}"
    cle = f"livre_mensuel-{employeur.id}-{mois}-{annee}"
    return archiver_et_renvoyer(
        employeur, pdf_bytes, nom_fichier, "application/pdf",
        type_doc="livre_mensuel", libelle=libelle, cle=cle, mois=mois, annee=annee)

@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def jours_feries_liste(request):
    """Gestion des jours fériés (nationaux) : liste + ajout."""
    if request.method == "POST":
        form = JourFerieForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("paie_jours_feries")
    else:
        form = JourFerieForm()
    feries = JourFerie.objects.all()
    ctx = _contexte_paie()
    ctx.update({"feries": feries, "form": form})
    return render(request, "paie/jours_feries.html", ctx)


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def jour_ferie_supprimer(request, ferie_id):
    ferie = get_object_or_404(JourFerie, pk=ferie_id)
    if request.method == "POST":
        ferie.delete()
    return redirect("paie_jours_feries")


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def livre_calcul(request):
    """Documentation interne : comment le système calcule chaque élément de paie, avec sources légales."""
    ctx = _contexte_paie()
    return render(request, "paie/livre_calcul.html", ctx)


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def guide_utilisation(request):
    """Guide d'utilisation du module Paie/RH, pour les collaborateurs du cabinet."""
    ctx = _contexte_paie()
    return render(request, "paie/guide_utilisation.html", ctx)


def _donnees_auto_fin_contrat(employe, date_sortie):
    """Déduit tout de l'historique des bulletins : salaire moyen, ancienneté,
    gratification, et congés comptés DEPUIS LE DERNIER CONGÉ pris."""
    from datetime import date
    from .calculs_rupture import bonus_conges_anciennete

    bulletins = list(BulletinPaie.objects.filter(employe=employe).order_by("-annee", "-mois")[:12])
    if bulletins:
        total = sum((calculer_bulletin(b)["total_gains"] for b in bulletins), Decimal("0"))
        salaire_moyen = total / len(bulletins)
    else:
        salaire_moyen = Decimal(str(employe.salaire_base or 0))

    anciennete = 0.0
    if employe.date_entree:
        anciennete = max((date_sortie - employe.date_entree).days, 0) / 365.25

    # Congés : on repart du DERNIER congé pris (bulletin avec congé), sinon de l'embauche.
    dernier_conge = (BulletinPaie.objects.filter(employe=employe, conge_paye__gt=0)
                     .order_by("-annee", "-mois").first())
    if dernier_conge:
        debut_ref = date(dernier_conge.annee, dernier_conge.mois, 1)
    else:
        debut_ref = employe.date_entree or date(date_sortie.year, 1, 1)
    mois_conges = (date_sortie.year - debut_ref.year) * 12 + (date_sortie.month - debut_ref.month)
    mois_conges = max(0, min(mois_conges, 12))  # non cumulatif au-delà d'un cycle de 12 mois
    jours_conges = Decimal("2.2") * Decimal(str(mois_conges)) + Decimal(str(bonus_conges_anciennete(anciennete)))

    # Gratification : mois travaillés dans l'année civile
    debut_annee = date(date_sortie.year, 1, 1)
    debut_g = employe.date_entree if (employe.date_entree and employe.date_entree > debut_annee) else debut_annee
    mois_annee = max(1, min((date_sortie.year - debut_g.year) * 12 + (date_sortie.month - debut_g.month) + 1, 12))

    # Total des salaires du contrat (précarité CDD)
    tous = BulletinPaie.objects.filter(employe=employe)
    total_cdd = sum((calculer_bulletin(b)["total_gains"] for b in tous), Decimal("0"))
    if total_cdd == 0:
        total_cdd = Decimal(str(employe.salaire_base or 0)) * Decimal(str(mois_annee))

    return {"salaire_moyen": salaire_moyen, "anciennete": anciennete, "mois_annee": mois_annee,
            "mois_conges": mois_conges, "jours_conges": jours_conges,
            "total_cdd": total_cdd, "jours_presence": date_sortie.day, "dernier_conge": dernier_conge}


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def fin_contrat(request, employeur_id, employe_id):
    from django.urls import reverse
    employeur = get_object_or_404(Employeur, pk=employeur_id)
    employe = get_object_or_404(Employe, pk=employe_id, employeur=employeur)
    resultat = None
    form = FinContratForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        date_fin = d["date_fin"]
        auto = _donnees_auto_fin_contrat(employe, date_fin)
        resultat = calculer_fin_contrat(
            motif=d["motif"], salaire_moyen=auto["salaire_moyen"], salaire_base=employe.salaire_base,
            anciennete_annees=auto["anciennete"], jours_presence=auto["jours_presence"],
            jours_conges=auto["jours_conges"], mois_travailles_annee=auto["mois_annee"],
            total_salaires_cdd=auto["total_cdd"],
        )
        resultat["auto"] = auto

        if "reporter" in request.POST:
            comp = resultat["composantes"]
            mois, annee = date_fin.month, date_fin.year
            jp = Decimal(str(auto["jours_presence"]))
            bulletin, _ = BulletinPaie.objects.get_or_create(
                employe=employe, mois=mois, annee=annee,
                defaults={"salaire_base": employe.salaire_base})
            bulletin.salaire_base = Decimal(str(employe.salaire_base or 0)) * jp / Decimal("30")  # présence
            bulletin.sursalaire = Decimal("0")
            bulletin.jours_travailles = 30
            bulletin.conge_paye = comp.get("conges", 0)
            bulletin.gratification = comp.get("gratification", 0)
            bulletin.preavis = comp.get("preavis", 0)
            bulletin.indemnite_licenciement = comp.get("licenciement", 0)
            bulletin.prime_precarite = comp.get("precarite", 0)
            bulletin.est_solde_tout_compte = True
            bulletin.motif_sortie = resultat["motif_label"]
            bulletin.save()
            employe.date_sortie = date_fin
            employe.motif_sortie = resultat["motif_label"]
            employe.statut = "SORTI"
            employe.save()
            MouvementPersonnel.objects.create(
                employe=employe, employeur=employeur, type_mouvement="sortie",
                date_mouvement=date_fin, detail=resultat["motif_label"])
            return redirect(f"{reverse('paie_bulletin_pdf', args=[employeur.id, employe.id])}?mois={mois}&annee={annee}")

    ctx = _contexte_paie()
    ctx.update({"employeur": employeur, "employe": employe, "form": form, "resultat": resultat})
    return render(request, "paie/fin_contrat.html", ctx)

@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def emplois_liste(request):
    emplois = Emploi.objects.all()
    ctx = _contexte_paie()
    ctx.update({"emplois": emplois, "form": EmploiForm()})
    return render(request, "paie/emplois_liste.html", ctx)


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def emploi_ajouter(request):
    if request.method == "POST":
        form = EmploiForm(request.POST)
        if form.is_valid():
            form.save()
    return redirect("paie_emplois")


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def emploi_modifier(request, emploi_id):
    emploi = get_object_or_404(Emploi, pk=emploi_id)
    if request.method == "POST":
        form = EmploiForm(request.POST, instance=emploi)
        if form.is_valid():
            form.save()
            return redirect("paie_emplois")
    else:
        form = EmploiForm(instance=emploi)
    ctx = _contexte_paie()
    ctx.update({"form": form, "emploi": emploi})
    return render(request, "paie/form_emploi.html", ctx)


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def emploi_supprimer(request, emploi_id):
    emploi = get_object_or_404(Emploi, pk=emploi_id)
    if request.method == "POST":
        emploi.delete()
    return redirect("paie_emplois")
@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def reglage_generation(request, employeur_id):
    employeur = get_object_or_404(Employeur, pk=employeur_id)
    reglage, _ = ReglageGenerationAuto.objects.get_or_create(employeur=employeur)
    if request.method == "POST":
        reglage.active = bool(request.POST.get("active"))
        try:
            jour = int(request.POST.get("jour_du_mois") or 28)
        except ValueError:
            jour = 28
        reglage.jour_du_mois = min(max(jour, 1), 31)
        reglage.save()
        return redirect(f"{reverse('traitement_paie', args=[employeur.id])}")
    ctx = _contexte_paie()
    ctx.update({"employeur": employeur, "reglage": reglage})
    return render(request, "paie/reglage_generation.html", ctx)
# Les 4 taux légaux d'heures supplémentaires (Côte d'Ivoire)
HSUP_TAUX = [("hsup_15", "15%", Decimal("0.15")),
             ("hsup_50", "50%", Decimal("0.50")),
             ("hsup_75", "75%", Decimal("0.75")),
             ("hsup_100", "100%", Decimal("1.00"))]


def _montant_hsup(bulletin):
    """Calcule le montant total des heures sup d'un bulletin à partir des 4 taux."""
    th = taux_horaire(bulletin.salaire_base)
    total = Decimal("0")
    for champ, _lib, taux in HSUP_TAUX:
        heures = Decimal(str(getattr(bulletin, champ, 0) or 0))
        total += th * heures * (Decimal("1") + taux)
    return total


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def heures_sup(request, employeur_id):
    employeur = get_object_or_404(Employeur, pk=employeur_id)
    mois = int(request.GET.get("mois", timezone.now().month))
    annee = int(request.GET.get("annee", timezone.now().year))
    employes = [e for e in employeur.employes.filter(statut="ACTIF") if e.est_actif_sur(mois, annee)]

    if request.method == "POST":
        for e in employes:
            bulletin, _ = BulletinPaie.objects.get_or_create(
                employe=e, mois=mois, annee=annee,
                defaults={"salaire_base": e.salaire_base, "jours_travailles": 30})
            if getattr(bulletin, "est_solde_tout_compte", False):
                continue
            for champ, _lib, _taux in HSUP_TAUX:
                valeur = request.POST.get(f"emp_{e.id}_{champ}")
                setattr(bulletin, champ, Decimal(valeur) if valeur not in (None, "") else Decimal("0"))
            bulletin.heures_sup = _montant_hsup(bulletin)  # le montant total → dans le brut
            bulletin.save()
        return redirect(f"{reverse('paie_heures_sup', args=[employeur.id])}?mois={mois}&annee={annee}")

    lignes = []
    for e in employes:
        bulletin = BulletinPaie.objects.filter(employe=e, mois=mois, annee=annee).first()
        lignes.append({
            "employe": e,
            "th": round(taux_horaire(e.salaire_base), 2),
            "vals": {champ: (getattr(bulletin, champ, 0) if bulletin else 0) for champ, _l, _t in HSUP_TAUX},
            "montant": (bulletin.heures_sup if bulletin else 0),
        })

    mois_liste = [(i, nom) for i, nom in BulletinPaie.MOIS_CHOICES]
    annees_liste = list(range(annee - 2, annee + 2))
    ctx = _contexte_paie()
    ctx.update({"employeur": employeur, "lignes": lignes, "mois": mois, "annee": annee,
                "mois_liste": mois_liste, "annees_liste": annees_liste, "taux": HSUP_TAUX})
    return render(request, "paie/heures_sup.html", ctx)

@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def livre_annuel_pdf(request, employeur_id):
    employeur = get_object_or_404(Employeur, pk=employeur_id)
    annee = int(request.GET.get("annee", timezone.now().year))
    pdf_bytes = generer_pdf_livre_annuel(employeur, annee, request)
    nom_fichier = f"livre-paie-annuel-{employeur.id}-{annee}.pdf"
    libelle = f"Livre de paie annuel — {employeur.raison_sociale} — {annee}"
    cle = f"livre_annuel-{employeur.id}-{annee}"
    return archiver_et_renvoyer(
        employeur, pdf_bytes, nom_fichier, "application/pdf",
        type_doc="livre_annuel", libelle=libelle, cle=cle, annee=annee)

@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def declaration_edi_its(request, employeur_id):
    employeur = get_object_or_404(Employeur, pk=employeur_id)
    mois = int(request.GET.get("mois", timezone.now().month))
    annee = int(request.GET.get("annee", timezone.now().year))
    xml = generer_edi_its(employeur, mois, annee)
    ncc = employeur.ncc or "SANS-NCC"
    nom_fichier = f"{ncc}-EDI-etat_301_mensuel-{annee}-{mois:02d}.xml"
    libelle = f"EDI ITS mensuel — {employeur.raison_sociale} — {mois}/{annee}"
    cle = f"edi_its_mensuel-{employeur.id}-{mois}-{annee}"
    return archiver_et_renvoyer(
        employeur, xml.encode("utf-8"), nom_fichier, "application/xml; charset=utf-8",
        type_doc="edi_its_mensuel", libelle=libelle, cle=cle,
        mois=mois, annee=annee, disposition="attachment")



@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def employeur_modifier(request, employeur_id):
    """Modifier les infos d'une entreprise (adresse, RIB émetteur via banques, couleur, exercice…)."""
    employeur = get_object_or_404(Employeur, pk=employeur_id)
    if request.method == "POST":
        form = EmployeurForm(request.POST, request.FILES, instance=employeur)
        if form.is_valid():
            form.save()
            return redirect("paie_employes_liste", employeur_id=employeur.id)
    else:
        form = EmployeurForm(instance=employeur)
    ctx = _contexte_paie()
    ctx.update({"form": form, "employeur": employeur, "titre": "Infos de l'entreprise"})
    return render(request, "paie/form_employeur.html", ctx)
@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def declaration_edi_annuel(request, employeur_id):
    employeur = get_object_or_404(Employeur, pk=employeur_id)
    annee = int(request.GET.get("annee", timezone.now().year))
    xml = generer_edi_its(employeur, 1, annee, type_edi="etat_301")
    ncc = employeur.ncc or "SANS-NCC"
    nom_fichier = f"{ncc}-EDI-etat_301-{annee}.xml"
    libelle = f"EDI État 301 annuel — {employeur.raison_sociale} — {annee}"
    cle = f"edi_its_annuel-{employeur.id}-{annee}"
    return archiver_et_renvoyer(
        employeur, xml.encode("utf-8"), nom_fichier, "application/xml; charset=utf-8",
        type_doc="edi_its_annuel", libelle=libelle, cle=cle,
        annee=annee, disposition="attachment")
@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def declarations_annuelles(request, employeur_id):
    employeur = get_object_or_404(Employeur, pk=employeur_id)
    # Les années où l'entreprise a des bulletins (pour le sélecteur)
    annees = sorted(set(BulletinPaie.objects.filter(employe__employeur=employeur)
                        .values_list("annee", flat=True)), reverse=True)
    annee_choisie = int(request.GET.get("annee", annees[0] if annees else timezone.now().year))
    ctx = _contexte_paie()
    ctx.update({"employeur": employeur, "annees": annees, "annee_choisie": annee_choisie})
    return render(request, "paie/declarations_annuelles.html", ctx)
@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def declaration_cnps(request, employeur_id):
    employeur = get_object_or_404(Employeur, pk=employeur_id)
    mois = int(request.GET.get("mois", timezone.now().month))
    annee = int(request.GET.get("annee", timezone.now().year))
    contenu = generer_cnps_nominative(employeur, mois, annee)
    ncc = employeur.ncc or "SANS-NCC"
    nom_fichier = f"CNPS-nominative-{ncc}-{annee}-{mois:02d}.xlsx"
    libelle = f"CNPS nominative — {employeur.raison_sociale} — {mois}/{annee}"
    cle = f"cnps_nominative-{employeur.id}-{mois}-{annee}"
    return archiver_et_renvoyer(
        employeur, contenu, nom_fichier,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type_doc="cnps_nominative", libelle=libelle, cle=cle,
        mois=mois, annee=annee, disposition="attachment")
@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def declaration_disa(request, employeur_id):
    employeur = get_object_or_404(Employeur, pk=employeur_id)
    annee = int(request.GET.get("annee", timezone.now().year))
    contenu = generer_disa(employeur, annee)
    ncc = employeur.ncc or "SANS-NCC"
    nom_fichier = f"DISA-{ncc}-{annee}.xlsm"
    libelle = f"DISA/DASC — {employeur.raison_sociale} — {annee}"
    cle = f"disa-{employeur.id}-{annee}"
    return archiver_et_renvoyer(
        employeur, contenu, nom_fichier,
        "application/vnd.ms-excel.sheet.macroEnabled.12",
        type_doc="disa", libelle=libelle, cle=cle,
        annee=annee, disposition="attachment")
@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def saisie_dasc(request, employeur_id):
    employeur = get_object_or_404(Employeur, pk=employeur_id)
    annee = int(request.GET.get("annee", timezone.now().year))
    dasc, _ = DeclarationDASC.objects.get_or_create(employeur=employeur, annee=annee)

    if request.method == "POST":
        def val(nom):
            v = request.POST.get(nom)
            try:
                return Decimal(v) if v not in (None, "") else Decimal("0")
            except Exception:
                return Decimal("0")
        dasc.cotisations_t1 = val("cot_t1"); dasc.cotisations_t2 = val("cot_t2")
        dasc.cotisations_t3 = val("cot_t3"); dasc.cotisations_t4 = val("cot_t4")
        dasc.paiements_t1 = val("pai_t1"); dasc.paiements_t2 = val("pai_t2")
        dasc.paiements_t3 = val("pai_t3"); dasc.paiements_t4 = val("pai_t4")
        dasc.save()
        return redirect(f"{reverse('paie_saisie_dasc', args=[employeur.id])}?annee={annee}&ok=1")

    annees = sorted(set(BulletinPaie.objects.filter(employe__employeur=employeur)
                        .values_list("annee", flat=True)), reverse=True) or [annee]
    ctx = _contexte_paie()
    ctx.update({"employeur": employeur, "dasc": dasc, "annee": annee, "annees": annees,
                "ok": request.GET.get("ok")})
    return render(request, "paie/saisie_dasc.html", ctx)
@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def reglements_cnps(request, employeur_id):
    employeur = get_object_or_404(Employeur, pk=employeur_id)
    annee = int(request.GET.get("annee", timezone.now().year))

    if request.method == "POST":
        for m in range(1, 13):
            reg, _ = ReglementCNPS.objects.get_or_create(employeur=employeur, annee=annee, mois=m)
            montant = request.POST.get(f"paye_{m}")
            date_p = request.POST.get(f"date_{m}")
            ref = request.POST.get(f"ref_{m}", "")
            try:
                reg.montant_paye = Decimal(montant) if montant not in (None, "") else Decimal("0")
            except Exception:
                reg.montant_paye = Decimal("0")
            reg.date_paiement = date_p or None
            reg.reference = ref
            reg.save()
        return redirect(f"{reverse('paie_reglements_cnps', args=[employeur.id])}?annee={annee}&ok=1")

    noms_mois = dict(BulletinPaie.MOIS_CHOICES)
    lignes = []
    for m in range(1, 13):
        reg = ReglementCNPS.objects.filter(employeur=employeur, annee=annee, mois=m).first()
        lignes.append({
            "mois": m,
            "periode": f"{noms_mois.get(m, m)} {annee}",
            "declare": cotisations_cnps_mois(employeur, annee, m),
            "paye": (reg.montant_paye if reg else 0),
            "date": (reg.date_paiement.strftime("%Y-%m-%d") if (reg and reg.date_paiement) else ""),
            "reference": (reg.reference if reg else ""),
        })

    annees = sorted(set(BulletinPaie.objects.filter(employe__employeur=employeur)
                        .values_list("annee", flat=True)), reverse=True) or [annee]
    ctx = _contexte_paie()
    ctx.update({"employeur": employeur, "lignes": lignes, "annee": annee, "annees": annees,
                "ok": request.GET.get("ok")})
    return render(request, "paie/reglements_cnps.html", ctx)
def _reporter_pret_sur_bulletin(bulletin):
    """Reporte le prêt sur le bulletin : décaissement (gain) le 1er mois, puis mensualités (retenue)."""
    from .models import RemboursementPret
    employe = bulletin.employe
    pret = employe.prets.filter(solde=False).first()
    if not pret:
        return

    # 1) Décaissement : le mois du 1er remboursement (date_debut), on verse le montant en GAIN, une seule fois.
    if not pret.decaisse and pret.date_debut and \
       pret.date_debut.month == bulletin.mois and pret.date_debut.year == bulletin.annee:
        bulletin.decaissement_pret = pret.montant
        pret.decaisse = True
        pret.save()

    # 2) Remboursement : mensualité en RETENUE, si le prêt est actif et pas déjà remboursé ce mois.
    if pret.est_actif():
        deja = RemboursementPret.objects.filter(pret=pret, mois=bulletin.mois, annee=bulletin.annee).exists()
        if not deja:
            reste = Decimal(str(pret.capital_restant()))
            mensualite = min(Decimal(str(pret.mensualite)), reste)
            if mensualite > 0:
                RemboursementPret.objects.create(pret=pret, mois=bulletin.mois, annee=bulletin.annee, montant=mensualite)
                bulletin.montant_pret = mensualite
                if pret.capital_restant() <= 0:
                    pret.solde = True
                    pret.save()


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def prets_employe(request, employeur_id, employe_id):
    employeur = get_object_or_404(Employeur, pk=employeur_id)
    employe = get_object_or_404(Employe, pk=employe_id, employeur=employeur)
    pret_actif = employe.prets.filter(solde=False).first()

    if request.method == "POST" and "creer" in request.POST:
        if not (pret_actif and pret_actif.est_actif()):
            form = PretForm(request.POST)
            if form.is_valid():
                d = form.cleaned_data
                montant = d["montant"]
                if d["mode"] == "nombre":
                    mensualite = (montant / d["nombre_mensualites"]).quantize(Decimal("1"))
                else:
                    mensualite = d["mensualite"]
                Pret.objects.create(employe=employe, montant=montant, mensualite=mensualite,
                                    date_debut=d["date_debut"], motif=d.get("motif", ""))
                return redirect("paie_prets_employe", employeur_id=employeur.id, employe_id=employe.id)
        else:
            form = PretForm()
    elif request.method == "POST" and "solder" in request.POST:
        p = employe.prets.filter(id=request.POST.get("pret_id")).first()
        if p:
            p.solde = True; p.save()
        return redirect("paie_prets_employe", employeur_id=employeur.id, employe_id=employe.id)
    else:
        form = PretForm()

    prets = employe.prets.all().prefetch_related("remboursements")
    ctx = _contexte_paie()
    ctx.update({"employeur": employeur, "employe": employe, "form": form,
                "prets": prets, "pret_actif": pret_actif})
    return render(request, "paie/prets_employe.html", ctx)


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def justificatif_pret_pdf(request, employeur_id, employe_id, pret_id):
    employeur = get_object_or_404(Employeur, pk=employeur_id)
    employe = get_object_or_404(Employe, pk=employe_id, employeur=employeur)
    pret = get_object_or_404(Pret, pk=pret_id, employe=employe)
    pdf_bytes = generer_pdf_justificatif_pret(pret, request)
    nom_fichier = f"justificatif-pret-{employe.matricule}-{pret.id}.pdf"
    libelle = f"Justificatif de prêt — {employe.nom_prenoms} ({pret.montant:.0f} F)"
    cle = f"justificatif_pret-{pret.id}"
    return archiver_et_renvoyer(
        employeur, pdf_bytes, nom_fichier, "application/pdf",
        type_doc="justificatif_pret", libelle=libelle, cle=cle,
        employe=employe, annee=timezone.now().year)


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def attestation_pdf(request, employeur_id, employe_id, type_doc):
    employeur = get_object_or_404(Employeur, pk=employeur_id)
    employe = get_object_or_404(Employe, pk=employe_id, employeur=employeur)
    conge = None
    cle_suffixe = ""
    if type_doc == "conge":
        debut = request.GET.get("debut")
        fin = request.GET.get("fin")
        from datetime import datetime
        try:
            conge = {"debut": datetime.strptime(debut, "%Y-%m-%d").date() if debut else None,
                     "fin": datetime.strptime(fin, "%Y-%m-%d").date() if fin else None}
            cle_suffixe = f"-{debut}-{fin}"  # une attestation de congé par période
        except Exception:
            conge = None

    pdf_bytes = generer_attestation(employe, type_doc, request, conge=conge, utilisateur_signataire=request.user)

    noms = {"travail": "attestation-travail", "certificat": "certificat-travail", "conge": "attestation-conge", "stage": "attestation-fin-stage"}
    libelles = {"travail": "Attestation de travail", "certificat": "Certificat de travail", "conge": "Attestation de congé", "stage": "Attestation de fin de stage"}
    nom_fichier = f"{noms.get(type_doc, 'document')}-{employe.matricule}.pdf"
    libelle = f"{libelles.get(type_doc, 'Document')} — {employe.nom_prenoms}"
    cle = f"attestation_{type_doc}-emp{employe.id}{cle_suffixe}"

    from django.utils import timezone
    return archiver_et_renvoyer(
        employeur, pdf_bytes, nom_fichier, "application/pdf",
        type_doc=f"attestation_{type_doc}", libelle=libelle, cle=cle,
        employe=employe, annee=timezone.now().year)


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def attestations_employe(request, employeur_id, employe_id):
    employeur = get_object_or_404(Employeur, pk=employeur_id)
    employe = get_object_or_404(Employe, pk=employe_id, employeur=employeur)

    # Congés réels du salarié (bulletins avec du congé) -> pour l'attestation de congé
    conges = []
    bulletins_conge = (BulletinPaie.objects.filter(employe=employe, conge_paye__gt=0)
                       .order_by("-annee", "-mois"))
    noms_mois = dict(BulletinPaie.MOIS_CHOICES)
    for b in bulletins_conge:
        conges.append({
            "mois": b.mois, "annee": b.annee,
            "libelle": f"{noms_mois.get(b.mois, b.mois)} {b.annee}",
            "debut": b.conge_date_debut.strftime("%Y-%m-%d") if b.conge_date_debut else "",
            "fin": b.conge_date_fin.strftime("%Y-%m-%d") if b.conge_date_fin else "",
        })

    ctx = _contexte_paie()
    ctx.update({
        "employeur": employeur, "employe": employe,
        "est_actif": employe.statut == "ACTIF",
        "est_sorti": bool(employe.date_sortie) or employe.statut == "SORTI",
        "conges": conges,
    })
    return render(request, "paie/attestations_employe.html", ctx)

@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def archives_entreprises(request):
    """Liste des entreprises ayant des documents archivés (+ compte)."""
    from django.db.models import Count
    employeurs = (Employeur.objects.annotate(nb_docs=Count("documents_archives"))
                  .order_by("raison_sociale"))
    ctx = _contexte_paie()
    ctx.update({"employeurs": employeurs})
    return render(request, "paie/archives_entreprises.html", ctx)


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def archives_entreprise(request, employeur_id):
    """Documents archivés d'une entreprise, triés par date de production (récent en haut)."""
    employeur = get_object_or_404(Employeur, pk=employeur_id)
    documents = employeur.documents_archives.all().order_by("-cree_le")
    ctx = _contexte_paie()
    ctx.update({"employeur": employeur, "documents": documents})
    return render(request, "paie/archives_entreprise.html", ctx)


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def archive_telecharger(request, document_id):
    """Renvoie le fichier stocké en base."""
    from .models import DocumentArchive
    doc = get_object_or_404(DocumentArchive, pk=document_id)
    response = HttpResponse(bytes(doc.contenu), content_type=doc.content_type)
    response["Content-Disposition"] = f'inline; filename="{doc.nom_fichier}"'
    return response


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def contrat_generer(request, employeur_id, employe_id):
    """Génère le contrat de travail du salarié (CDI pour l'instant) et l'archive."""
    employeur = get_object_or_404(Employeur, pk=employeur_id)
    employe = get_object_or_404(Employe, pk=employe_id, employeur=employeur)

    if request.method == "POST":
        form = ContratGenerationForm(request.POST)
        if form.is_valid():
            options = form.cleaned_data
            from .contrats import generer_contrat_cdd, generer_contrat_stage
            DUREE_ESSAI_MOIS = {"horaire": 0, "mensuel": 1, "maitrise": 2, "cadre": 3}
            if employe.contrat != "STAGE":
                employe.duree_essai_mois = DUREE_ESSAI_MOIS.get(options.get("niveau_essai", "mensuel"), 1)
                employe.save()

            if employe.contrat == "CDD":
                pdf_bytes = generer_contrat_cdd(employe, options, request, utilisateur_signataire=request.user)
            elif employe.contrat == "STAGE":
                pdf_bytes = generer_contrat_stage(employe, options, request, utilisateur_signataire=request.user)
            else:
                pdf_bytes = generer_contrat_cdi(employe, options, request, utilisateur_signataire=request.user)
            nom_fichier = f"contrat-{employe.matricule}-{employe.contrat}.pdf"
            libelle = f"Contrat de travail ({employe.get_contrat_display}) — {employe.nom_prenoms}"
            cle = f"contrat-emp{employe.id}"
            return archiver_et_renvoyer(
                employeur, pdf_bytes, nom_fichier, "application/pdf",
                type_doc="contrat", libelle=libelle, cle=cle,
                employe=employe, annee=timezone.now().year)
    else:
        form = ContratGenerationForm()

    ctx = _contexte_paie()
    ctx.update({"employeur": employeur, "employe": employe, "form": form})
    return render(request, "paie/contrat_generer.html", ctx)


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def avenant_generer(request, employeur_id, employe_id):
    """Génère un avenant de reconduction (CDD) ou de prolongation (Stage)."""
    employeur = get_object_or_404(Employeur, pk=employeur_id)
    employe = get_object_or_404(Employe, pk=employe_id, employeur=employeur)

    if request.method == "POST":
        form = AvenantForm(request.POST)
        if form.is_valid():
            from .contrats import generer_avenant_reconduction
            nouvelle_date_fin = form.cleaned_data["nouvelle_date_fin"]
            motif = form.cleaned_data.get("motif_reconduction", "")
            pdf_bytes, depassement = generer_avenant_reconduction(
                employe, nouvelle_date_fin, motif, request,
                utilisateur_signataire=request.user
            )

            if employe.date_entree:
                mois_cumules = round((nouvelle_date_fin - employe.date_entree).days / 30.44)
                employe.duree_cdd_mois = mois_cumules
            employe.date_sortie = nouvelle_date_fin
            employe.save()

            nom_fichier = f"avenant-{employe.matricule}-{nouvelle_date_fin}.pdf"
            libelle = f"Avenant de reconduction — {employe.nom_prenoms} (jusqu'au {nouvelle_date_fin})"
            cle = f"avenant-emp{employe.id}-{nouvelle_date_fin}"
            return archiver_et_renvoyer(
                employeur, pdf_bytes, nom_fichier, "application/pdf",
                type_doc="avenant", libelle=libelle, cle=cle,
                employe=employe, annee=timezone.now().year)
    else:
        form = AvenantForm()

    ctx = _contexte_paie()
    ctx.update({"employeur": employeur, "employe": employe, "form": form})
    return render(request, "paie/avenant_generer.html", ctx)


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def import_document(request):
    """Importe un document signé dans l'archive de l'entreprise."""
    if request.method == "POST":
        form = ImportDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            d = form.cleaned_data
            employeur = d["employeur"]
            employe = d.get("employe")
            fichier = d["fichier"]
            contenu = fichier.read()
            cle = f"import-{d['nature']}-{fichier.name}-{timezone.now().timestamp()}"
            archiver_document(
                employeur, d["nature"], d["libelle"], cle, contenu, fichier.name,
                content_type=fichier.content_type or "application/octet-stream",
                employe=employe, annee=timezone.now().year)
            messages.success(request, "Le document a bien été importé dans les archives.")
            return redirect("paie_archives")
    else:
        form = ImportDocumentForm()

    ctx = _contexte_paie()
    ctx.update({"form": form})
    return render(request, "paie/import_document.html", ctx)


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def import_salaries_employeur(request, employeur_id):
    """Renvoie en JSON la liste des salariés d'une entreprise (pour le formulaire d'import)."""
    employeur = get_object_or_404(Employeur, pk=employeur_id)
    salaries = [{"id": e.id, "nom": e.nom_prenoms} for e in employeur.employes.all().order_by("nom_prenoms")]
    return JsonResponse({"salaries": salaries})


def actions_rh_salarie(request, employeur_id, employe_id):
    """Page d'opérations d'un salarié : congés, prêts, documents, absences, historique."""
    from .conges import compteur_conges

    employeur = get_object_or_404(Employeur, pk=employeur_id)
    employe = get_object_or_404(Employe, pk=employe_id, employeur=employeur)
    pret_actif = employe.prets.filter(solde=False).first()
    conges = employe.conges.all()[:10]
    solde = compteur_conges(employe)
    annee_courante = timezone.now().year
    annees_recap = sorted(set(
        BulletinPaie.objects.filter(employe=employe).values_list("annee", flat=True)
    ), reverse=True) or [annee_courante]
    absences_recentes = employe.absences.order_by("-date_debut")[:5]
    bulletins_historiques = BulletinPaie.objects.filter(
        employe=employe, est_historique=True).order_by("-annee", "-mois")[:6]
    ctx = _contexte_paie()
    ctx.update({
        "employeur": employeur, "employe": employe,
        "pret_actif": pret_actif, "conges": conges,
        "annees_recap": annees_recap, "annee_courante": annee_courante,
        "solde": solde,
        "absences_recentes": absences_recentes,
        "nb_absences": employe.absences.count(),
        "bulletins_historiques": bulletins_historiques,
        "nb_bulletins_historiques": BulletinPaie.objects.filter(employe=employe, est_historique=True).count(),
    })
    return render(request, "paie/actions_rh_salarie.html", ctx)


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def actions_rh_salarie(request, employeur_id, employe_id):
    """Page d'opérations d'un salarié : congés, prêts, documents, absences, historique."""
    from .conges import compteur_conges

    employeur = get_object_or_404(Employeur, pk=employeur_id)
    employe = get_object_or_404(Employe, pk=employe_id, employeur=employeur)
    pret_actif = employe.prets.filter(solde=False).first()
    conges = employe.conges.all()[:10]
    solde = compteur_conges(employe)
    annee_courante = timezone.now().year
    annees_recap = sorted(set(
        BulletinPaie.objects.filter(employe=employe).values_list("annee", flat=True)
    ), reverse=True) or [annee_courante]
    absences_recentes = employe.absences.order_by("-date_debut")[:5]
    bulletins_historiques = BulletinPaie.objects.filter(
        employe=employe, est_historique=True).order_by("-annee", "-mois")[:6]
    ctx = _contexte_paie()
    ctx.update({
        "employeur": employeur, "employe": employe,
        "pret_actif": pret_actif, "conges": conges,
        "annees_recap": annees_recap, "annee_courante": annee_courante,
        "solde": solde,
        "absences_recentes": absences_recentes,
        "nb_absences": employe.absences.count(),
        "bulletins_historiques": bulletins_historiques,
        "nb_bulletins_historiques": BulletinPaie.objects.filter(employe=employe, est_historique=True).count(),
    })
    return render(request, "paie/actions_rh_salarie.html", ctx)


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def absences_employe(request, employeur_id, employe_id):
    employeur = get_object_or_404(Employeur, pk=employeur_id)
    employe = get_object_or_404(Employe, pk=employe_id, employeur=employeur)
    absences = employe.absences.order_by("-date_debut").all()
    form = AbsenceForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        absence = form.save(commit=False)
        absence.employe = employe
        absence.save()
        messages.success(request, "Absence enregistrée avec succès.")
        return redirect("paie_absences_employe", employeur_id=employeur.id, employe_id=employe.id)

    ctx = _contexte_paie()
    ctx.update({
        "employeur": employeur,
        "employe": employe,
        "absences": absences,
        "form": form,
    })
    return render(request, "paie/absences_employe.html", ctx)


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def bulletin_historique_creer(request, employeur_id, employe_id):
    employeur = get_object_or_404(Employeur, pk=employeur_id)
    employe = get_object_or_404(Employe, pk=employe_id, employeur=employeur)
    from .forms import BulletinHistoriqueForm
    if request.method == "POST":
        form = BulletinHistoriqueForm(request.POST)
        if form.is_valid():
            d = form.cleaned_data
            BulletinPaie.objects.update_or_create(
                employe=employe, mois=int(d["mois"]), annee=d["annee"],
                defaults={
                    "salaire_base": employe.salaire_base, "est_historique": True,
                    "net_historique": d["net_historique"],
                    "its_historique": d.get("its_historique") or 0,
                    "cnps_salarie_historique": d.get("cnps_salarie_historique") or 0,
                    "cmu_salarie_historique": d.get("cmu_salarie_historique") or 0,
                })
            return redirect("paie_bulletin_historique_creer", employeur_id=employeur.id, employe_id=employe.id)
    else:
        form = BulletinHistoriqueForm()
    bulletins_historiques = BulletinPaie.objects.filter(employe=employe, est_historique=True).order_by("-annee", "-mois")
    ctx = _contexte_paie()
    ctx.update({"employeur": employeur, "employe": employe, "form": form, "bulletins_historiques": bulletins_historiques})
    return render(request, "paie/bulletin_historique.html", ctx)


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def actions_rh_liste(request, employeur_id):
    """Liste des salariés ACTIFS d'une entreprise, pour accéder à leurs opérations RH."""
    employeur = get_object_or_404(Employeur, pk=employeur_id)
    employes = employeur.employes.filter(statut="ACTIF")
    ctx = _contexte_paie()
    ctx.update({"employeur": employeur, "employes": employes})
    return render(request, "paie/actions_rh_liste.html", ctx)


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def conge_poser(request, employeur_id, employe_id):
    """Poser un congé : calcule l'indemnité répartie et reporte sur les bulletins (Option 1)."""
    employeur = get_object_or_404(Employeur, pk=employeur_id)
    employe = get_object_or_404(Employe, pk=employe_id, employeur=employeur)
    resultat = None
    form = CongePoserForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        resultat = calculer_conge(employe, d["date_depart"], d["date_retour"])

        if "confirmer" in request.POST:
            # 1) Créer le congé maître
            conge = Conge.objects.create(
                employe=employe, type_conge=d["type_conge"],
                date_depart=d["date_depart"], date_retour=d["date_retour"],
                jours_ouvrables=resultat["jours_total"],
                montant_total=resultat["montant_total"],
                motif=d.get("motif", ""),
            )
            # 2) Reporter chaque portion sur le bulletin du mois concerné
            from datetime import date, timedelta
            dernier_jour = d["date_retour"] - timedelta(days=1)
            for portion in resultat["repartition"]:
                mois, annee = portion["mois"], portion["annee"]
                bulletin, _ = BulletinPaie.objects.get_or_create(
                    employe=employe, mois=mois, annee=annee,
                    defaults={"salaire_base": employe.salaire_base, "jours_travailles": 30})
                if getattr(bulletin, "est_solde_tout_compte", False):
                    continue
                # Dates de la portion (bornes du mois intersectées avec le congé)
                debut_portion = max(d["date_depart"], date(annee, mois, 1))
                if mois == 12:
                    fin_mois = date(annee, 12, 31)
                else:
                    fin_mois = date(annee, mois + 1, 1) - timedelta(days=1)
                fin_portion = min(dernier_jour, fin_mois)
                bulletin.conge_paye = Decimal(str(portion["montant"]))
                bulletin.conge_date_debut = debut_portion
                bulletin.conge_date_fin = fin_portion
                bulletin.save()
            # Génère et archive automatiquement l'attestation de congé pour cette période
            conge_info = {"debut": conge.date_depart, "fin": conge.date_retour}
            pdf_attestation = generer_attestation(
                employe, "conge", request, conge=conge_info,
                utilisateur_signataire=request.user
            )
            nom_fichier_att = f"attestation-conge-{employe.matricule}-{conge.date_depart}.pdf"
            libelle_att = f"Attestation de congé — {employe.nom_prenoms} ({conge.date_depart} au {conge.date_retour})"
            cle_att = f"attestation_conge-emp{employe.id}-{conge.date_depart}-{conge.date_retour}"
            archiver_et_renvoyer(
                employeur, pdf_attestation, nom_fichier_att, "application/pdf",
                type_doc="attestation_conge", libelle=libelle_att, cle=cle_att,
                employe=employe, annee=conge.date_depart.year)
            return redirect("paie_actions_rh_salarie", employeur_id=employeur.id, employe_id=employe.id)

    ctx = _contexte_paie()
    ctx.update({"employeur": employeur, "employe": employe, "form": form, "resultat": resultat})
    return render(request, "paie/conge_poser.html", ctx)


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def conge_exceptionnel_poser(request, employeur_id, employe_id):
    employeur = get_object_or_404(Employeur, pk=employeur_id)
    employe = get_object_or_404(Employe, pk=employe_id, employeur=employeur)
    if request.method == "POST":
        form = CongeExceptionnelForm(request.POST)
        if form.is_valid():
            d = form.cleaned_data
            libelles = dict(CongeExceptionnelForm.MOTIF_CHOICES)
            motif_texte = libelles.get(d["motif"], "")
            if d.get("precision"):
                motif_texte += f" — {d['precision']}"
            Conge.objects.create(
                employe=employe, type_conge="exceptionnel",
                date_depart=d["date_depart"], date_retour=d["date_retour"],
                jours_ouvrables=(d["date_retour"] - d["date_depart"]).days,
                montant_total=0, motif=motif_texte)
            return redirect("paie_actions_rh_salarie", employeur_id=employeur.id, employe_id=employe.id)
    else:
        form = CongeExceptionnelForm()
    ctx = _contexte_paie()
    ctx.update({"employeur": employeur, "employe": employe, "form": form})
    return render(request, "paie/conge_exceptionnel.html", ctx)

