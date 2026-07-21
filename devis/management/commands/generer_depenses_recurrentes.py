from datetime import date
from django.core.management.base import BaseCommand
from core.execution import tracer_execution
from devis.models import DepenseRecurrente


class Command(BaseCommand):
    help = "Génère les dépenses dues pour toutes les dépenses récurrentes actives."

    def handle(self, *args, **options):
        with tracer_execution("generer_depenses_recurrentes") as trace:
            aujourd_hui = date.today()
            compteur = 0
            for recurrente in DepenseRecurrente.objects.filter(actif=True):
                for echeance in recurrente.echeances_dues(aujourd_hui):
                    depense = recurrente.generer_depense(echeance)
                    if depense:
                        compteur += 1
            trace.resume = f"{compteur} dépense(s) générée(s) automatiquement."
            self.stdout.write(self.style.SUCCESS(trace.resume))
