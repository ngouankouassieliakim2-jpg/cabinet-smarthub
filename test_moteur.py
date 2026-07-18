import django
import os


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from comptabilite.models import Balance
from comptabilite.moteur import generer_liasse
from decimal import Decimal

balance = Balance.objects.get(exercice=2025)
print("Balance trouvee, lancement du calcul...")

resultat = generer_liasse(balance)

print("--- VALEURS CALCULEES ---")
for cellule, montant in sorted(resultat["valeurs"].items()):
    if montant:
        print(cellule, "=", montant)

print()
print("--- ANOMALIES ---")
for a in resultat["anomalies"]:
    print(a)

print()
print("Notes calculees :", resultat["notes_calculees"])
print("Nb notes encore a zero :", len(resultat["notes_a_zero"]))
print("TERMINE")
from comptabilite.export_liasse import generer_fichier_liasse

resultat = generer_fichier_liasse(balance)
print("Fichier genere :", resultat["chemin_fichier"])
print("Anomalies ecriture :", resultat["anomalies_ecriture"])

from datetime import date
from comptabilite.models import LigneImmobilisation
from comptabilite.export_liasse import generer_fichier_liasse

# On reinitialise pour eviter les doublons si on relance le test plusieurs fois
balance.immobilisations.all().delete()

LigneImmobilisation.objects.bulk_create([
    LigneImmobilisation(
        balance=balance, compte="2311", designation="Batiment industriel principal",
        taux_amortissement=Decimal("5"), date_mise_en_service=date(2025, 3, 1),
        valeur_acquisition=Decimal("50000000"), amortissements_anterieurs=Decimal("0"),
        amortissements_exercice=Decimal("2500000"),
    ),
    LigneImmobilisation(
        balance=balance, compte="2315", designation="Immeuble loue a des tiers",
        taux_amortissement=Decimal("5"), date_mise_en_service=date(2018, 1, 1),
        valeur_acquisition=Decimal("30000000"), amortissements_anterieurs=Decimal("6000000"),
        amortissements_exercice=Decimal("1500000"),
    ),
    LigneImmobilisation(
        balance=balance, compte="2441", designation="Materiel informatique cede",
        taux_amortissement=Decimal("20"), date_mise_en_service=date(2020, 6, 1),
        valeur_acquisition=Decimal("2000000"), amortissements_anterieurs=Decimal("1600000"),
        amortissements_exercice=Decimal("200000"),
        date_cession=date(2025, 9, 15), prix_cession=Decimal("150000"),
    ),
])

print()
print("=== TEST EXPORT FICHIER AVEC SUPPL4 ===")
resultat_fichier = generer_fichier_liasse(balance)
print("Fichier genere :", resultat_fichier["chemin_fichier"])
print("Anomalies ecriture :", resultat_fichier["anomalies_ecriture"])