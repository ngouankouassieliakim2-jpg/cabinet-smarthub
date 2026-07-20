from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Sum, Max
from django.db.models.functions import TruncMonth

from .models import Facture, Paiement
from .previsions import repartition_par_anciennete

STATUTS_IMPAYES = ["EN_ATTENTE_PAIEMENT", "PARTIELLEMENT_PAYEE", "EN_RETARD", "EN_CONTENTIEUX"]


def delai_moyen_paiement(mois_glissants=12):
    """DSO simplifié : moyenne (date du dernier paiement soldant la facture -
    date d'émission), sur les factures PAYEE dont le solde a été atteint
    dans les N derniers mois. Ignore les factures soldées par avoir/compensation
    seule (pas de ligne Paiement) : le délai n'a pas de sens dans ce cas."""
    depuis = date.today() - timedelta(days=30 * mois_glissants)
    factures_payees = Facture.objects.filter(
        statut="PAYEE", date_emission__isnull=False,
    ).annotate(dernier_paiement=Max("paiements__date_paiement"))

    delais = []
    for f in factures_payees:
        if f.dernier_paiement and f.dernier_paiement >= depuis:
            delais.append((f.dernier_paiement - f.date_emission).days)

    if not delais:
        return None
    return round(sum(delais) / len(delais), 1)


def taux_impayes(depuis=None):
    """Montant total impayé / montant total facturé (hors brouillons/annulées),
    sur la période. depuis=None -> tout l'historique."""
    qs = Facture.objects.exclude(statut__in=["BROUILLON", "ANNULEE"])
    if depuis:
        qs = qs.filter(date_emission__gte=depuis)

    total_facture = qs.aggregate(total=Sum("montant_ttc"))["total"] or Decimal("0")
    if total_facture == 0:
        return Decimal("0")

    total_impaye = sum((f.solde_restant for f in qs if f.statut in STATUTS_IMPAYES), Decimal("0"))
    return round((total_impaye / total_facture) * 100, 1)


def taux_recouvrement(depuis=None):
    """Montant encaissé / montant facturable (TTC - avoirs), sur la période."""
    qs = Facture.objects.exclude(statut__in=["BROUILLON", "ANNULEE"])
    if depuis:
        qs = qs.filter(date_emission__gte=depuis)

    total_du = sum((f.montant_du for f in qs), Decimal("0"))
    if total_du == 0:
        return Decimal("0")

    total_encaisse = sum((f.montant_paye for f in qs), Decimal("0"))
    return round((total_encaisse / total_du) * 100, 1)


def clients_a_risque(seuil_jours_retard=60, limite=10):
    """Clients dont au moins une facture dépasse le seuil de retard,
    classés par montant total impayé décroissant."""
    aujourdhui = date.today()
    qs = Facture.objects.filter(statut__in=STATUTS_IMPAYES, date_echeance__isnull=False)

    par_client = {}
    for f in qs:
        jours_retard = (aujourdhui - f.date_echeance).days
        if jours_retard < seuil_jours_retard:
            continue
        par_client.setdefault(f.client_nom, Decimal("0"))
        par_client[f.client_nom] += f.solde_restant

    classement = sorted(par_client.items(), key=lambda x: x[1], reverse=True)
    return classement[:limite]


def encaissements_mensuels(mois_glissants=12):
    """Total des paiements reçus, groupés par mois, sur les N derniers mois."""
    depuis = date.today() - timedelta(days=30 * mois_glissants)
    resultats = (
        Paiement.objects.filter(date_paiement__gte=depuis)
        .annotate(mois=TruncMonth("date_paiement"))
        .values("mois")
        .annotate(total=Sum("montant"))
        .order_by("mois")
    )
    return list(resultats)


def creances_par_anciennete():
    """Réutilise le calcul déjà écrit pour les prévisions de trésorerie —
    pas de duplication."""
    return repartition_par_anciennete()
