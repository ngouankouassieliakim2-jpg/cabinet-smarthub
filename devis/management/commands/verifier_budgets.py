from django.core.management.base import BaseCommand
from django.urls import reverse
from core.execution import tracer_execution
from pilotage.models import Notification
from devis.models import Budget


class Command(BaseCommand):
    help = "Alerte quand un budget atteint 80/90/100% de consommation."

    def handle(self, *args, **options):
        with tracer_execution("verifier_budgets") as trace:
            compteur = 0
            for budget in Budget.objects.filter(actif=True):
                taux = budget.taux_consommation
                seuil_atteint = max((s for s in Budget.SEUILS_ALERTE if taux >= s), default=None)
                if seuil_atteint is None:
                    continue

                cle = f"budget_{budget.id}_seuil_{seuil_atteint}"
                _, cree = Notification.objects.get_or_create(
                    cle=cle,
                    defaults={
                        "type_notification": "budget_alerte",
                        "titre": f"Budget {budget.categorie} — {seuil_atteint}% atteint"[:200],
                        "message": f"{budget.consomme} FCFA consommés sur {budget.montant_alloue} FCFA alloués."[:300],
                        "url": reverse("devis:detail_budget", args=[budget.id]),
                    })
                if cree:
                    compteur += 1
            trace.resume = f"{compteur} alerte(s) de budget créée(s)."
            self.stdout.write(self.style.SUCCESS(trace.resume))
