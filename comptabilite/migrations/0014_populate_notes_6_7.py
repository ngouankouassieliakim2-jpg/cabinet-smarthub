from django.db import migrations

# NOTE 6 (Stocks) et NOTE 7 (Clients), régime NO : (cellule, libellé, préfixes, sens, signe).
# source solde_final. Le TOTAL NET de la note = le poste correspondant du bilan (BB, BI).
NOTE_6 = [
    ("NOTE 6!E9", "Marchandises", "31", "les_deux", 1),
    ("NOTE 6!E10", "Matières premières et fournitures liées", "32", "les_deux", 1),
    ("NOTE 6!E11", "Autres approvisionnements", "33", "les_deux", 1),
    ("NOTE 6!E12", "Produits en cours", "34", "les_deux", 1),
    ("NOTE 6!E13", "Services en cours", "35", "les_deux", 1),
    ("NOTE 6!E14", "Produits finis", "36", "les_deux", 1),
    ("NOTE 6!E15", "Produits intermédiaires", "37", "les_deux", 1),
    ("NOTE 6!E16", "Stocks en cours de route, en consignation ou en dépôt", "38", "les_deux", 1),
    ("NOTE 6!E18", "Dépréciations des stocks", "39", "crediteur", -1),
]
NOTE_7 = [
    ("NOTE 7!E9", "Clients (hors réserves de propriété)", "411", "debiteur", 1),
    ("NOTE 7!E10", "Clients, effets à recevoir", "412", "debiteur", 1),
    ("NOTE 7!E13", "Créances sur cession d'immobilisations", "414", "debiteur", 1),
    ("NOTE 7!E15", "Créances litigieuses ou douteuses", "416", "debiteur", 1),
    ("NOTE 7!E16", "Clients, produits à recevoir", "418", "debiteur", 1),
    ("NOTE 7!E18", "Dépréciations des comptes clients", "491", "crediteur", -1),
    ("NOTE 7!E20", "Clients, avances reçues hors groupe", "4191", "crediteur", -1),
    ("NOTE 7!E21", "Clients, avances reçues groupe", "4192", "crediteur", -1),
    ("NOTE 7!E22", "Autres clients créditeurs", "4194,4198", "crediteur", -1),
]


def charger(apps, schema_editor):
    LigneNote = apps.get_model("comptabilite", "LigneNote")
    for code_note, lignes in [("NOTE 6", NOTE_6), ("NOTE 7", NOTE_7)]:
        LigneNote.objects.filter(regime_liasse="NO", code_note=code_note).delete()
        LigneNote.objects.bulk_create([
            LigneNote(
                regime_liasse="NO", code_note=code_note, libelle_ligne=libelle,
                ref_dgi="", cellule_dgi=cellule, prefixe_comptes=prefs,
                source="solde_final", sens=sens, signe=signe, ordre=ordre,
            )
            for ordre, (cellule, libelle, prefs, sens, signe) in enumerate(lignes, start=1)
        ])
    # Alignement : le poste BB du bilan doit inclure les stocks en cours de route (38),
    # comme la NOTE 6, pour que l'articulation « BB = total NOTE 6 » tienne toujours.
    LigneNote.objects.filter(
        regime_liasse="NO", code_note="BILAN", cellule_dgi="BILAN!F28"
    ).update(prefixe_comptes="31,32,33,34,35,36,37,38")


def vider(apps, schema_editor):
    LigneNote = apps.get_model("comptabilite", "LigneNote")
    LigneNote.objects.filter(regime_liasse="NO", code_note__in=["NOTE 6", "NOTE 7"]).delete()
    LigneNote.objects.filter(
        regime_liasse="NO", code_note="BILAN", cellule_dgi="BILAN!F28"
    ).update(prefixe_comptes="31,32,33,34,35,36,37")


class Migration(migrations.Migration):
    dependencies = [
        ("comptabilite", "0013_populate_lignenote_resultat"),
    ]
    operations = [
        migrations.RunPython(charger, vider),
    ]