from django.core.management.base import BaseCommand
from core.execution import tracer_execution
from devis.models import CategorieDepense

CATEGORIES = {
    "Loyer & Charges locatives": [],
    "Informatique": ["Matériel informatique", "Logiciels & abonnements", "Maintenance & support"],
    "Marketing & Communication": ["Publicité", "Impression & supports", "Événementiel"],
    "Salaires & Charges sociales": [],  # dépenses hors paie déjà gérée dans le module Paie — usage limité (ex : primes exceptionnelles)
    "Fournitures de bureau": [],
    "Transport & Déplacements": ["Carburant", "Entretien véhicule", "Mission & déplacement"],
    "Télécommunications": ["Internet", "Téléphonie"],
    "Eau & Électricité": [],
    "Assurances": [],
    "Honoraires externes": ["Notaire", "Avocat", "Consultant"],
    "Formation du personnel": [],
    "Entretien & Réparations": [],
    "Impôts & Taxes (cabinet)": [],
    "Divers": [],
}


class Command(BaseCommand):
    help = "Crée les catégories/sous-catégories de dépenses par défaut si elles n'existent pas déjà."

    def handle(self, *args, **options):
        with tracer_execution("seed_categories_depense") as trace:
            crees = 0
            for nom_parent, sous_categories in CATEGORIES.items():
                parent, cree = CategorieDepense.objects.get_or_create(nom=nom_parent, parent=None)
                if cree:
                    crees += 1
                for nom_enfant in sous_categories:
                    _, cree_enfant = CategorieDepense.objects.get_or_create(nom=nom_enfant, parent=parent)
                    if cree_enfant:
                        crees += 1
            trace.resume = f"{crees} catégorie(s)/sous-catégorie(s) créée(s)."
            self.stdout.write(self.style.SUCCESS(trace.resume))
