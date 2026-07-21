from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.urls import reverse
from core.execution import tracer_execution
from pilotage.models import Notification
from devis.models import ContratFournisseur

SEUIL_ALERTE_JOURS = 30


class Command(BaseCommand):
    help = "Alerte sur les contrats fournisseurs arrivant à échéance sous 30 jours."

    def handle(self, *args, **options):
        with tracer_execution("verifier_contrats_fournisseurs") as trace:
            aujourdhui = date.today()
            seuil = aujourdhui + timedelta(days=SEUIL_ALERTE_JOURS)
            contrats = ContratFournisseur.objects.filter(
                date_fin__isnull=False,
                date_fin__gte=aujourdhui,
                date_fin__lte=seuil,
            )

            compteur = 0
            for contrat in contrats:
                cle = f"contrat_fournisseur_{contrat.id}_expiration"
                _, cree = Notification.objects.get_or_create(
                    cle=cle,
                    defaults={
                        "type_notification": "relance_notification_interne",
                        "titre": f"Contrat arrivant à échéance — {contrat.fournisseur}"[:200],
                        "message": f"Le contrat « {contrat.libelle} » expire le {contrat.date_fin}."[:300],
                        "url": reverse("devis:detail_fournisseur", args=[contrat.fournisseur_id]),
                    },
                )
                if cree:
                    compteur += 1
            trace.resume = f"{compteur} alerte(s) de contrat créée(s)."
            self.stdout.write(self.style.SUCCESS(trace.resume))
