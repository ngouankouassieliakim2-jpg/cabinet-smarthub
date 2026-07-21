from datetime import date
from decimal import Decimal

from django.db.models import Sum
from django.db.models.functions import TruncYear

from .models import Depense, Budget

STATUTS_EXCLUS = ["ANNULEE"]


def depenses_par_categorie(depuis=None):
    qs = Depense.objects.exclude(statut__in=STATUTS_EXCLUS)
    if depuis:
        qs = qs.filter(date_facture__gte=depuis)
    return list(qs.values("categorie__nom").annotate(total=Sum("montant_ht")).order_by("-total"))


def depenses_par_fournisseur(depuis=None, limite=10):
    qs = Depense.objects.exclude(statut__in=STATUTS_EXCLUS)
    if depuis:
        qs = qs.filter(date_facture__gte=depuis)
    return list(qs.values("fournisseur__raison_sociale").annotate(total=Sum("montant_ht")).order_by("-total")[:limite])


def depenses_par_service(depuis=None):
    """Service mappé sur le pôle du collaborateur créateur."""
    qs = Depense.objects.exclude(statut__in=STATUTS_EXCLUS)
    if depuis:
        qs = qs.filter(date_facture__gte=depuis)
    resultats = list(
        qs.values("cree_par__profil__pole__nom").annotate(total=Sum("montant_ht")).order_by("-total")
    )
    for resultat in resultats:
        if not resultat["cree_par__profil__pole__nom"]:
            resultat["cree_par__profil__pole__nom"] = "Non renseigné"
    return resultats


def depenses_par_collaborateur(depuis=None, limite=10):
    qs = Depense.objects.exclude(statut__in=STATUTS_EXCLUS).exclude(cree_par__isnull=True)
    if depuis:
        qs = qs.filter(date_facture__gte=depuis)
    return list(qs.values("cree_par__username").annotate(total=Sum("montant_ht")).order_by("-total")[:limite])


def evolution_annuelle(nb_annees=3):
    depuis = date(date.today().year - nb_annees + 1, 1, 1)
    return list(
        Depense.objects.exclude(statut__in=STATUTS_EXCLUS)
        .filter(date_facture__gte=depuis)
        .annotate(annee=TruncYear("date_facture"))
        .values("annee")
        .annotate(total=Sum("montant_ht"))
        .order_by("annee")
    )


def depassements_budgetaires(exercice=None):
    exercice = exercice or date.today().year
    budgets = Budget.objects.filter(exercice=exercice, actif=True).select_related("categorie")
    return [budget for budget in budgets if budget.taux_consommation >= 100]


def fournisseurs_les_plus_couteux(depuis=None, limite=10):
    qs = Depense.objects.exclude(statut__in=STATUTS_EXCLUS)
    if depuis:
        qs = qs.filter(date_facture__gte=depuis)
    return list(
        qs.values("fournisseur_id", "fournisseur__raison_sociale")
        .annotate(total=Sum("montant_ht"))
        .order_by("-total")[:limite]
    )
