from datetime import date
from django.core.management.base import BaseCommand
from devis.models import Facture

SEUIL_CREATION_TACHE_JOURS = 30
STATUTS_CONCERNES = ["EN_ATTENTE_PAIEMENT", "PARTIELLEMENT_PAYEE", "EN_RETARD"]


class Command(BaseCommand):
    help = (
        "Règles d'automatisation du recouvrement non couvertes par les autres "
        "commandes (marquer_factures_en_retard, executer_relances). "
        "Actuellement : signalement des factures >30j sans tâche créée "
        "(création réelle bloquée, module Tâches absent — voir COMMENTAIRES.md)."
    )

    def handle(self, *args, **options):
        aujourdhui = date.today()
        candidates = Facture.objects.filter(
            statut__in=STATUTS_CONCERNES,
            date_echeance__isnull=False,
            date_echeance__lt=aujourdhui,
        )

        a_signaler = []
        for f in candidates:
            jours_retard = (aujourdhui - f.date_echeance).days
            if jours_retard >= SEUIL_CREATION_TACHE_JOURS:
                a_signaler.append(f)

        if not a_signaler:
            self.stdout.write("Aucune facture ne nécessite de tâche de suivi.")
            return

        self.stdout.write(self.style.WARNING(
            f"{len(a_signaler)} facture(s) dépassent {SEUIL_CREATION_TACHE_JOURS} jours de retard "
            f"— création de tâche non exécutée (module Tâches absent) :"
        ))
        for f in a_signaler:
            self.stdout.write(f"  - {f.numero_facture} ({f.client_nom})")

        # TODO : dès que le module Tâches existe, remplacer ce bloc par :
        # from taches.models import Tache
        # for f in a_signaler:
        #     Tache.objects.get_or_create(
        #         cle_unique=f"recouvrement_facture_{f.id}",
        #         defaults={"titre": f"Relancer {f.numero_facture}", "lien": ...})
