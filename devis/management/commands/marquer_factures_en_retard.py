from datetime import date
from django.core.management.base import BaseCommand
from devis.models import Facture


class Command(BaseCommand):
    help = "Bascule en EN_RETARD les factures dont l'échéance est dépassée."

    STATUTS_CONCERNES = ["EN_ATTENTE_PAIEMENT", "PARTIELLEMENT_PAYEE"]

    def handle(self, *args, **options):
        aujourdhui = date.today()
        candidates = Facture.objects.filter(
            statut__in=self.STATUTS_CONCERNES,
            date_echeance__lt=aujourdhui,
        )
        compteur = 0
        for facture in candidates:
            facture.changer_statut(
                "EN_RETARD",
                commentaire="Bascule automatique — échéance dépassée (commande marquer_factures_en_retard)",
            )
            compteur += 1
        self.stdout.write(self.style.SUCCESS(f"{compteur} facture(s) basculée(s) en retard."))
