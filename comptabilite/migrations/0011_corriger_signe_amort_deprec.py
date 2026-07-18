from django.db import migrations


def corriger_signe(apps, schema_editor):
    """Convention 'solde signe' (debit +, credit -) : les lignes qui lisent un
    SOLDE (initial/final) sur des comptes d'amortissement ou de depreciation
    (28, 29, 39, 49, 59) recoivent un solde NEGATIF. Or ces notes presentent
    l'amortissement/depreciation en POSITIF -> on leur met signe = -1 pour
    retrouver la magnitude. Les lignes qui lisent des MOUVEMENTS ne sont pas
    concernees (mouvement_debit/credit sont des montants positifs directionnels).
    """
    LigneNote = apps.get_model("comptabilite", "LigneNote")
    amort = ("28", "29", "39", "49", "59")
    for ligne in LigneNote.objects.filter(source__in=["solde_initial", "solde_final"]):
        prefs = [p.strip() for p in ligne.prefixe_comptes.split(",") if p.strip()]
        if prefs and all(p.startswith(amort) for p in prefs):
            ligne.signe = -1
            ligne.save(update_fields=["signe"])


def inverse(apps, schema_editor):
    LigneNote = apps.get_model("comptabilite", "LigneNote")
    amort = ("28", "29", "39", "49", "59")
    for ligne in LigneNote.objects.filter(source__in=["solde_initial", "solde_final"]):
        prefs = [p.strip() for p in ligne.prefixe_comptes.split(",") if p.strip()]
        if prefs and all(p.startswith(amort) for p in prefs):
            ligne.signe = 1
            ligne.save(update_fields=["signe"])


class Migration(migrations.Migration):
    dependencies = [
        ("comptabilite", "0010_lignenote_sens_lignenote_signe"),
    ]
    operations = [
        migrations.RunPython(corriger_signe, inverse),
    ]