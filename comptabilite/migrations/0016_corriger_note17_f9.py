from django.db import migrations


def corriger(apps, schema_editor):
    # Le compte fournisseur générique (40100000) a pour racine SYSCOHADA "401",
    # pas "4011". On mappe donc F9 au niveau "401". Les sous-comptes 4013/4017
    # restent captés par F10/F12 grâce à leur préfixe plus long (règle du plus long).
    LigneNote = apps.get_model("comptabilite", "LigneNote")
    LigneNote.objects.filter(
        regime_liasse="NO", code_note="NOTE 17", cellule_dgi="NOTE 17!F9"
    ).update(prefixe_comptes="401")


def inverse(apps, schema_editor):
    LigneNote = apps.get_model("comptabilite", "LigneNote")
    LigneNote.objects.filter(
        regime_liasse="NO", code_note="NOTE 17", cellule_dgi="NOTE 17!F9"
    ).update(prefixe_comptes="4011,4012")


class Migration(migrations.Migration):
    dependencies = [
        ("comptabilite", "0015_populate_notes_17_18"),
    ]
    operations = [
        migrations.RunPython(corriger, inverse),
    ]