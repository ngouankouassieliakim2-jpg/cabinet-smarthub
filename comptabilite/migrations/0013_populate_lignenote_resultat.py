from django.db import migrations

# Mapping du COMPTE DE RÉSULTAT (régime NO) : (cellule, ref DGI, libellé, préfixes comptes).
# Convention (cf. note de la liasse) : produits en +, charges en −, cascade par simple somme.
# => chaque ligne = −solde_final : source solde_final, sens les_deux, signe -1 pour TOUTES.
RESULTAT_NO = [
    ("RESULTAT!I11", "TA", "Ventes de marchandises", "701"),
    ("RESULTAT!I12", "RA", "Achats de marchandises", "601"),
    ("RESULTAT!I13", "RB", "Variation de stocks de marchandises", "6031"),
    ("RESULTAT!I15", "TB", "Ventes de produits fabriqués", "702,703,704"),
    ("RESULTAT!I16", "TC", "Travaux, services vendus", "705,706"),
    ("RESULTAT!I17", "TD", "Produits accessoires", "707"),
    ("RESULTAT!I19", "TE", "Production stockée (ou déstockage)", "73"),
    ("RESULTAT!I20", "TF", "Production immobilisée", "72"),
    ("RESULTAT!I21", "TG", "Subventions d'exploitation", "71"),
    ("RESULTAT!I22", "TH", "Autres produits", "75"),
    ("RESULTAT!I23", "TI", "Transferts de charges d'exploitation", "781"),
    ("RESULTAT!I24", "RC", "Achats de matières premières et fournitures liées", "602"),
    ("RESULTAT!I25", "RD", "Variation de stocks de matières premières et fournitures liées", "6032"),
    ("RESULTAT!I26", "RE", "Autres achats", "604,605,608"),
    ("RESULTAT!I27", "RF", "Variation de stocks d'autres approvisionnements", "6033"),
    ("RESULTAT!I28", "RG", "Transports", "61"),
    ("RESULTAT!I29", "RH", "Services extérieurs", "62,63"),
    ("RESULTAT!I30", "RI", "Impôts et taxes", "64"),
    ("RESULTAT!I31", "RJ", "Autres charges", "65"),
    ("RESULTAT!I33", "RK", "Charges de personnel", "66"),
    ("RESULTAT!I35", "TJ", "Reprises d'amortissements, provisions et dépréciations", "791,798"),
    ("RESULTAT!I36", "RL", "Dotations aux amortissements, aux provisions et dépréciations", "681,691"),
    ("RESULTAT!I38", "TK", "Revenus financiers et assimilés", "77"),
    ("RESULTAT!I39", "TL", "Reprises de provisions et dépréciations financières", "797,779"),
    ("RESULTAT!I40", "TM", "Transferts de charges financières", "787"),
    ("RESULTAT!I41", "RM", "Frais financiers et charges assimilées", "67"),
    ("RESULTAT!I42", "RN", "Dotations aux provisions et dépréciations financières", "687,697"),
    ("RESULTAT!I45", "TN", "Produits des cessions d'immobilisations", "82"),
    ("RESULTAT!I46", "TO", "Autres produits HAO", "84,86,88"),
    ("RESULTAT!I47", "RO", "Valeurs comptables des cessions d'immobilisations", "81"),
    ("RESULTAT!I48", "RP", "Autres charges HAO", "83,85"),
    ("RESULTAT!I50", "RQ", "Participation des travailleurs", "87"),
    ("RESULTAT!I51", "RS", "Impôts sur le résultat", "89"),
]


def charger(apps, schema_editor):
    LigneNote = apps.get_model("comptabilite", "LigneNote")
    LigneNote.objects.filter(regime_liasse="NO", code_note="RESULTAT").delete()
    LigneNote.objects.bulk_create([
        LigneNote(
            regime_liasse="NO", code_note="RESULTAT", libelle_ligne=libelle,
            ref_dgi=ref, cellule_dgi=cellule, prefixe_comptes=prefs,
            source="solde_final", sens="les_deux", signe=-1, ordre=ordre,
        )
        for ordre, (cellule, ref, libelle, prefs) in enumerate(RESULTAT_NO, start=1)
    ])


def vider(apps, schema_editor):
    LigneNote = apps.get_model("comptabilite", "LigneNote")
    LigneNote.objects.filter(regime_liasse="NO", code_note="RESULTAT").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("comptabilite", "0012_populate_lignenote_bilan"),
    ]
    operations = [
        migrations.RunPython(charger, vider),
    ]