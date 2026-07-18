from django.db import migrations

# NOTE 17 (Fournisseurs -> DJ) et NOTE 18 (Dettes fiscales et sociales -> DK), régime NO.
NOTE_17 = [
    ("NOTE 17!F9", "Fournisseurs dettes en compte", "4011,4012", "crediteur", -1),
    ("NOTE 17!F10", "Fournisseurs, sous-traitants", "4013", "crediteur", -1),
    ("NOTE 17!F12", "Fournisseurs, retenue de garantie", "4017", "crediteur", -1),
    ("NOTE 17!F13", "Fournisseurs, effets à payer", "402", "crediteur", -1),
    ("NOTE 17!F16", "Fournisseurs, factures non parvenues", "408", "crediteur", -1),
    ("NOTE 17!F19", "Fournisseurs, avances et acomptes versés", "4091,4092", "debiteur", 1),
    ("NOTE 17!F21", "Autres fournisseurs débiteurs", "4093,4094,4098", "debiteur", 1),
]
NOTE_18 = [
    ("NOTE 18!E9", "Personnel, rémunérations dues", "422", "crediteur", -1),
    ("NOTE 18!E10", "Personnel, congés à payer", "4281", "crediteur", -1),
    ("NOTE 18!E11", "Charges sociales sur congés à payer", "4382", "crediteur", -1),
    ("NOTE 18!E12", "Autres personnel", "423,425,426,427", "crediteur", -1),
    ("NOTE 18!E13", "Caisse de sécurité sociale", "431", "crediteur", -1),
    ("NOTE 18!E14", "Caisse de retraite", "432", "crediteur", -1),
    ("NOTE 18!E15", "Mutuelle de santé", "4331", "crediteur", -1),
    ("NOTE 18!E17", "Autres charges sociales à payer", "4386", "crediteur", -1),
    ("NOTE 18!E18", "Autres cotisations et organismes sociaux", "4333,4338,4318", "crediteur", -1),
    ("NOTE 18!E20", "État, impôts sur les bénéfices", "441", "crediteur", -1),
    ("NOTE 18!E21", "État, impôts et taxes", "442,446", "crediteur", -1),
    ("NOTE 18!E22", "État, TVA", "444", "crediteur", -1),
    ("NOTE 18!E23", "État, impôts retenus à la source", "447", "crediteur", -1),
    ("NOTE 18!E24", "Autres dettes État", "448", "crediteur", -1),
]


def charger(apps, schema_editor):
    LigneNote = apps.get_model("comptabilite", "LigneNote")
    for code_note, lignes in [("NOTE 17", NOTE_17), ("NOTE 18", NOTE_18)]:
        LigneNote.objects.filter(regime_liasse="NO", code_note=code_note).delete()
        LigneNote.objects.bulk_create([
            LigneNote(
                regime_liasse="NO", code_note=code_note, libelle_ligne=libelle,
                ref_dgi="", cellule_dgi=cellule, prefixe_comptes=prefs,
                source="solde_final", sens=sens, signe=signe, ordre=ordre,
            )
            for ordre, (cellule, libelle, prefs, sens, signe) in enumerate(lignes, start=1)
        ])


def vider(apps, schema_editor):
    LigneNote = apps.get_model("comptabilite", "LigneNote")
    LigneNote.objects.filter(regime_liasse="NO", code_note__in=["NOTE 17", "NOTE 18"]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("comptabilite", "0014_populate_notes_6_7"),
    ]
    operations = [
        migrations.RunPython(charger, vider),
    ]