from django.core.management.base import BaseCommand
from core.execution import tracer_execution
from devis.models import SeuilApprobation

SEUILS = [
    {"borne_min": 0, "borne_max": 99999, "niveau_requis": "CADRE"},
    {"borne_min": 100000, "borne_max": 500000, "niveau_requis": "DIRECTION"},
    {"borne_min": 500001, "borne_max": None, "niveau_requis": "DIRECTION"},
]


class Command(BaseCommand):
    help = "Crée les seuils d'approbation par défaut si aucun n'existe."

    def handle(self, *args, **options):
        with tracer_execution("seed_seuils_approbation") as trace:
            if SeuilApprobation.objects.exists():
                trace.resume = "Seuils déjà existants, rien créé."
                self.stdout.write(trace.resume)
                return
            for seuil in SEUILS:
                SeuilApprobation.objects.create(**seuil)
            trace.resume = f"{len(SEUILS)} seuil(s) créé(s)."
            self.stdout.write(self.style.SUCCESS(trace.resume))
