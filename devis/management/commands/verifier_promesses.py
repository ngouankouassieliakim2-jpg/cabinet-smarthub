from datetime import date
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from devis.models import PromessePaiement
from core.execution import tracer_execution


class Command(BaseCommand):
    help = (
        "Vérifie les promesses de paiement en cours et marque TENUE ou ROMPUE "
        "selon le paiement effectif à la date promise."
    )

    def handle(self, *args, **options):
        with tracer_execution(
            commande="verifier_promesses",
            description="Vérification des promesses de paiement en cours",
            utilisateur=User.objects.filter(is_superuser=True).first(),
            contexte={"date_execution": date.today().isoformat()},
        ) as trace:
            promesses = PromessePaiement.objects.filter(
                statut="EN_COURS",
                date_promise__lte=date.today(),
            ).select_related("facture")

            if not promesses.exists():
                trace.resume = "Aucune promesse de paiement en cours à vérifier."
                self.stdout.write(trace.resume)
                return

            compteur = 0
            for promesse in promesses:
                avant = promesse.statut
                promesse.verifier()
                apres = promesse.statut
                if avant != apres:
                    compteur += 1

            trace.resume = f"{compteur} promesse(s) mises à jour."
            self.stdout.write(trace.resume)
