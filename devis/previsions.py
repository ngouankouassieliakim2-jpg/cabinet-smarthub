from datetime import date, timedelta
from decimal import Decimal
from django.db.models import Sum, F, DecimalField, Value
from django.db.models.functions import Coalesce

from .models import Facture

STATUTS_ATTENDUS = ["EN_ATTENTE_PAIEMENT", "PARTIELLEMENT_PAYEE", "EN_RETARD", "EN_CONTENTIEUX"]

PONDERATION_PAR_RETARD = [
    (0, 1.00),
    (30, 0.70),
    (60, 0.40),
    (90, 0.15),
]


def _ponderation(jours_retard):
    if jours_retard <= 0:
        return PONDERATION_PAR_RETARD[0][1]
    poids = PONDERATION_PAR_RETARD[-1][1]
    for seuil, valeur in PONDERATION_PAR_RETARD:
        if jours_retard < seuil:
            break
        poids = valeur
    return poids


def _factures_attendues():
    return Facture.objects.filter(
        statut__in=STATUTS_ATTENDUS,
        date_echeance__isnull=False,
    ).annotate(
        montant_paye_calc=Coalesce(Sum("paiements__montant"), Value(0), output_field=DecimalField())
    ).annotate(
        solde_calc=F("montant_ttc") - F("montant_paye_calc")
    )


def previsions_encaissements(aujourdhui=None):
    """Retourne un dict avec les montants bruts et pondérés attendus
    cette semaine / ce mois / ce trimestre."""
    aujourdhui = aujourdhui or date.today()
    fin_semaine = aujourdhui + timedelta(days=(7 - aujourdhui.weekday()))
    fin_mois = (aujourdhui.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    fin_trimestre = aujourdhui + timedelta(days=90)

    factures = list(_factures_attendues())

    def _agreger(date_limite):
        brut = Decimal("0")
        pondere = Decimal("0")
        for f in factures:
            if f.date_echeance <= date_limite:
                jours_retard = max((aujourdhui - f.date_echeance).days, 0)
                solde = f.solde_calc
                brut += solde
                pondere += solde * Decimal(str(_ponderation(jours_retard)))
        return {"brut": brut, "pondere": pondere.quantize(Decimal("1"))}

    return {
        "semaine": _agreger(fin_semaine),
        "mois": _agreger(fin_mois),
        "trimestre": _agreger(fin_trimestre),
        "aujourdhui": aujourdhui,
    }


def repartition_par_anciennete():
    """Vieillissement des créances : 0-30 / 31-60 / 61-90 / 90+ jours."""
    aujourdhui = date.today()
    tranches = {
        "j0_30": Decimal("0"),
        "j31_60": Decimal("0"),
        "j61_90": Decimal("0"),
        "j90_plus": Decimal("0"),
    }
    for f in _factures_attendues():
        jours_retard = max((aujourdhui - f.date_echeance).days, 0)
        solde = f.solde_calc
        if jours_retard <= 30:
            tranches["j0_30"] += solde
        elif jours_retard <= 60:
            tranches["j31_60"] += solde
        elif jours_retard <= 90:
            tranches["j61_90"] += solde
        else:
            tranches["j90_plus"] += solde
    return tranches
