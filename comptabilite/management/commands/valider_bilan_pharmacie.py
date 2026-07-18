import re
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from clients.models import Client
from comptabilite.models import Balance, LigneBalance
from comptabilite.moteur import generer_liasse

# Balance réelle de la Pharmacie de Tiémélékro (exercice 2024).
# Solde final SIGNÉ : débit positif, crédit négatif.
BALANCE = {
    "10130000": -5000000, "19100000": -5000000, "24420000": 2462000, "27500000": 100000,
    "28440000": -615500, "31100000": 14973380, "40100000": -10760829, "41100000": 4803486,
    "42200000": -440875, "43100000": -358323, "43310000": -21000, "44210000": -880798,
    "44410000": -117409, "44700000": -10500, "44860000": -114768, "52100000": -20242, "57100000": 536310,
    "48100000": 0,
    "60100000": 77938562, "60310000": -14973380, "60510000": 60898, "60520000": 515800,
    "60550000": 680100, "60560000": 470750, "60810000": 3017250, "61400000": 200000,
    "61810000": 8500, "61830000": 514000, "62220000": 550000, "62420000": 40000,
    "62720000": 5328000, "62810000": 11500, "62880000": 117500, "63180000": 143667,
    "63240000": 720000, "63270000": 4000000, "63300000": 550000, "63810000": 583000,
    "63830000": 350000, "63840000": 1050000, "63880000": 1452198, "64130000": 18900,
    "64140000": 6300, "64150000": 18900, "64500000": 795311, "64710000": 114768,
    "64800000": 97657, "65820000": 150000, "65880000": 3791500, "66110000": 1575000,
    "66120000": 1920000, "66340000": 420000, "66410000": 269598, "68130000": 615500,
    "69110000": 5000000, "70100000": -97656711,
}


class Command(BaseCommand):
    help = "Rejoue la balance réelle de la Pharmacie de Tiémélékro : vérifie l'équilibre du bilan ET le compte de résultat."

    def handle(self, *args, **options):
        client = Client.objects.first()
        if client is None:
            self.stdout.write(self.style.ERROR("Aucun client en base — crée un client puis relance."))
            return

        with transaction.atomic():
            bal = Balance.objects.create(client=client, exercice=2024, regime_liasse="NO")
            LigneBalance.objects.bulk_create([
                LigneBalance(balance=bal, compte=c, solde_final=Decimal(str(s)))
                for c, s in BALANCE.items()
            ])
            res = generer_liasse(bal)
            v = res["valeurs"]

            def col_bilan(cellule):
                m = re.match(r"BILAN!([A-Z])\d+", cellule)
                return m.group(1) if m else None

            actif_brut = sum(val for cell, val in v.items() if col_bilan(cell) == "F")
            amort = sum(val for cell, val in v.items() if col_bilan(cell) == "G")
            actif_net = actif_brut - amort
            passif = sum(val for cell, val in v.items() if col_bilan(cell) == "M")

            # Résultat du CR = somme des lignes-feuilles du compte de résultat (colonne I).
            resultat_cr = sum(val for cell, val in v.items() if cell.startswith("RESULTAT!I"))
            resultat_bilan = v.get("BILAN!M18", Decimal(0))

            fmt = lambda n: f"{n:>15,.0f}".replace(",", " ")
            self.stdout.write("")
            self.stdout.write("  ── BILAN ──")
            self.stdout.write(f"  ACTIF NET             {fmt(actif_net)}")
            self.stdout.write(f"  PASSIF                {fmt(passif)}")
            self.stdout.write("  ── COMPTE DE RÉSULTAT ──")
            self.stdout.write(f"  Résultat net (CR)     {fmt(resultat_cr)}")
            self.stdout.write(f"  Résultat net (bilan)  {fmt(resultat_bilan)}")
            self.stdout.write("")

            if actif_net == passif == 22259676:
                self.stdout.write(self.style.SUCCESS("  ✓ Bilan : Actif net = Passif = 22 259 676"))
            else:
                self.stdout.write(self.style.ERROR(f"  ✗ Bilan déséquilibré : écart = {fmt(actif_net - passif).strip()}"))

            if resultat_cr == resultat_bilan == -465068:
                self.stdout.write(self.style.SUCCESS("  ✓ Résultat : CR = bilan = -465 068 (articulation vérifiée)"))
            elif resultat_cr == resultat_bilan:
                self.stdout.write(self.style.WARNING(f"  CR = bilan = {fmt(resultat_cr).strip()} mais ≠ -465 068"))
            else:
                self.stdout.write(self.style.ERROR(f"  ✗ Résultat CR ({fmt(resultat_cr).strip()}) ≠ bilan ({fmt(resultat_bilan).strip()})"))
            
            # ── ARTICULATION : chaque poste du bilan (net) = total net de sa note ──
            def somme(cells):
                return sum(v.get(c, Decimal(0)) for c in cells)

            articulations = [
                ("BB Stocks ↔ NOTE 6",
                 v.get("BILAN!F28", Decimal(0)) - v.get("BILAN!G28", Decimal(0)),
                 somme([f"NOTE 6!E{r}" for r in range(9, 17)]) - v.get("NOTE 6!E18", Decimal(0))),
                ("BI Clients ↔ NOTE 7",
                 v.get("BILAN!F31", Decimal(0)) - v.get("BILAN!G31", Decimal(0)),
                 somme(["NOTE 7!E9", "NOTE 7!E10", "NOTE 7!E13", "NOTE 7!E15", "NOTE 7!E16"])
                 - v.get("NOTE 7!E18", Decimal(0))),
                ("DJ Fournisseurs ↔ NOTE 17",
                 v.get("BILAN!M29", Decimal(0)),
                 somme(["NOTE 17!F9", "NOTE 17!F10", "NOTE 17!F12", "NOTE 17!F13", "NOTE 17!F16"])),
                ("DK Dettes fisc.&soc. ↔ NOTE 18",
                 v.get("BILAN!M30", Decimal(0)),
                 sum(val for cell, val in v.items() if cell.startswith("NOTE 18!E"))),
            ]
            self.stdout.write("  ── ARTICULATION NOTES ↔ BILAN ──")
            for libelle, cote_bilan, cote_note in articulations:
                if cote_bilan == cote_note:
                    marque = self.style.SUCCESS("  ✓")
                else:
                    marque = self.style.ERROR("  ✗")
                self.stdout.write(f"{marque} {libelle:22s}  bilan = {fmt(cote_bilan).strip()}   note = {fmt(cote_note).strip()}")
            self.stdout.write("")

            

            if res["anomalies"]:
                comptes = ", ".join(a["compte"] for a in res["anomalies"])
                self.stdout.write(f"  Comptes inconnus : {comptes}")

            transaction.set_rollback(True)  # validation seulement : on ne persiste rien