from datetime import date
import calendar
from django.core.management.base import BaseCommand
from django.utils import timezone

from paie.models import Employeur, BulletinPaie, ReglageGenerationAuto


class Command(BaseCommand):
    help = "Génère automatiquement les bulletins manquants du mois pour les entreprises dont la génération auto est activée et dont c'est le jour."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true",
                            help="Ignore la date et génère tout de suite (pour tester).")

    def handle(self, *args, **options):
        aujourd_hui = timezone.now().date()
        force = options["force"]
        mois, annee = aujourd_hui.month, aujourd_hui.year
        dernier_jour = calendar.monthrange(annee, mois)[1]

        reglages = ReglageGenerationAuto.objects.filter(active=True).select_related("employeur")
        if not reglages:
            self.stdout.write("Aucune entreprise avec génération auto activée.")
            return

        total_crees = 0
        for reglage in reglages:
            # Jour cible : si réglé au-delà du dernier jour (ex. 31), on prend le dernier jour réel
            jour_cible = min(reglage.jour_du_mois, dernier_jour)

            if not force:
                if aujourd_hui.day != jour_cible:
                    continue
                # Évite de régénérer deux fois le même mois
                if reglage.derniere_execution and \
                   reglage.derniere_execution.month == mois and reglage.derniere_execution.year == annee:
                    continue

            employeur = reglage.employeur
            employes = [e for e in employeur.employes.filter(statut="ACTIF")
                        if e.est_actif_sur(mois, annee)]
            crees = 0
            for e in employes:
                _, cree = BulletinPaie.objects.get_or_create(
                    employe=e, mois=mois, annee=annee,
                    defaults={"salaire_base": e.salaire_base, "jours_travailles": 30})
                if cree:
                    crees += 1
            reglage.derniere_execution = aujourd_hui
            reglage.save()
            total_crees += crees
            self.stdout.write(self.style.SUCCESS(
                f"{employeur.raison_sociale} : {crees} bulletin(s) créé(s) pour {mois}/{annee}."))

        self.stdout.write(self.style.SUCCESS(f"Terminé. {total_crees} bulletin(s) créé(s) au total."))