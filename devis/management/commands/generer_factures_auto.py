from datetime import date
from django.core.management.base import BaseCommand
from django.utils import timezone

from devis.models import Facture


class Command(BaseCommand):
    help = "Génère automatiquement les factures récurrentes du mois selon les paramètres de facturation."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true",
                            help="Génère les factures même si la date n'est pas atteinte.")

    def handle(self, *args, **options):
        aujourd_hui = timezone.now().date()
        force = options["force"]

        factures = Facture.objects.filter(type_facturation="RECURRENTE")
        if not factures.exists():
            self.stdout.write("Aucune facture récurrente trouvée.")
            return

        crees = 0
        for facture in factures:
            if not force and facture.date_signature:
                if facture.date_signature.month != aujourd_hui.month or facture.date_signature.year != aujourd_hui.year:
                    continue

            if facture.statut == "BROUILLON":
                facture.date_emission = aujourd_hui
                facture.statut = "ENVOYEE"
                facture.save(update_fields=["date_emission", "statut"])
                crees += 1

        self.stdout.write(self.style.SUCCESS(f"Factures générées ou mises à jour : {crees}"))
