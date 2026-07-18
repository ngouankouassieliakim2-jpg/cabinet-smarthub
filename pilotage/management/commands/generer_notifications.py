"""Commande planifiée (cron quotidien) : scanne les salariés et crée les notifications manquantes."""
from django.core.management.base import BaseCommand
from pilotage.models import Notification

class Command(BaseCommand):
    help = "Génère les notifications RH (échéances de contrat, fins de période d'essai)."

    def handle(self, *args, **options):
        from paie.models import Employe

        nb_crees = 0
        salaries_actifs = Employe.objects.filter(statut="ACTIF")

        for e in salaries_actifs:
            # --- Échéance de contrat (CDD/Stage) ---
            if e.echeance_proche:
                cle = f"cdd_echeance-{e.id}-{e.date_sortie}"
                _, cree = Notification.objects.get_or_create(
                    cle=cle,
                    defaults={
                        "type_notification": "cdd_echeance",
                        "titre": f"{e.nom_prenoms} — contrat à échéance",
                        "message": f"{e.get_contrat_display()} arrive à échéance dans {e.jours_avant_echeance} jour(s) (le {e.date_sortie:%d/%m/%Y}).",
                        "url": f"/paie/actions-rh/{e.employeur_id}/salarie/{e.id}/",
                    })
                if cree:
                    nb_crees += 1

            # --- Fin de période d'essai ---
            if e.fin_essai_proche:
                cle = f"fin_essai-{e.id}"
                _, cree = Notification.objects.get_or_create(
                    cle=cle,
                    defaults={
                        "type_notification": "fin_essai",
                        "titre": f"{e.nom_prenoms} — fin de période d'essai",
                        "message": f"La période d'essai se termine dans les 7 prochains jours.",
                        "url": f"/paie/actions-rh/{e.employeur_id}/salarie/{e.id}/",
                    })
                if cree:
                    nb_crees += 1

        self.stdout.write(self.style.SUCCESS(f"{nb_crees} nouvelle(s) notification(s) créée(s)."))
