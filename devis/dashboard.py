from datetime import date
from decimal import Decimal
from django.db.models import Sum

from .models import Facture, Paiement, Depense, Budget, PromessePaiement


def montants_echu_non_echu():
    aujourdhui = date.today()
    qs = Facture.objects.filter(
        statut__in=["EN_ATTENTE_PAIEMENT", "PARTIELLEMENT_PAYEE", "EN_RETARD", "EN_CONTENTIEUX"],
        date_echeance__isnull=False,
    )
    echu = Decimal("0")
    non_echu = Decimal("0")
    for f in qs:
        if f.date_echeance < aujourdhui:
            echu += f.solde_restant
        else:
            non_echu += f.solde_restant
    return {"echu": echu, "non_echu": non_echu}


def encaisse_aujourdhui():
    return Paiement.objects.filter(date_paiement=date.today()).aggregate(
        total=Sum("montant"))[
        "total"] or Decimal("0")


def factures_en_litige():
    return Facture.objects.filter(statut__in=["CONTESTEE", "EN_LITIGE"]).count()


def factures_promises():
    return PromessePaiement.objects.filter(statut="EN_COURS").count()


def total_creances():
    return Facture.objects.filter(
        statut__in=["EN_ATTENTE_PAIEMENT", "PARTIELLEMENT_PAYEE", "EN_RETARD", "EN_CONTENTIEUX"]
    ).aggregate(total=Sum("montant_ttc"))["total"] or Decimal("0")


def depenses_du_mois():
    debut_mois = date.today().replace(day=1)
    return Depense.objects.exclude(statut="ANNULEE").filter(
        date_facture__gte=debut_mois
    ).aggregate(total=Sum("montant_ht"))["total"] or Decimal("0")


def situation_budgets(exercice=None):
    exercice = exercice or date.today().year
    budgets = Budget.objects.filter(exercice=exercice, actif=True)
    alloue = sum((b.montant_alloue for b in budgets), Decimal("0"))
    consomme = sum((b.consomme for b in budgets), Decimal("0"))
    return {"alloue": alloue, "consomme": consomme, "disponible": alloue - consomme}


def situation_validation_depenses():
    return {
        "en_attente": Depense.objects.filter(statut_validation="SOUMISE").count(),
        "refusees": Depense.objects.filter(statut_validation="REJETEE").count(),
        "validees_non_payees": Depense.objects.filter(
            statut_validation="VALIDEE"
        ).exclude(statut="PAYEE").count(),
    }
