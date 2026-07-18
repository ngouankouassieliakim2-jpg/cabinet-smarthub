from django.db import migrations

# Mapping du BILAN (régime NO) : (cellule, ref DGI, libellé, préfixes comptes, sens, signe)
# signe : +1 côté actif (débit-positif), -1 côté passif / amort. (crédit-positif).
# Le résultat (CJ) est calculé : classes 6/7/8 -> CJ avec signe -1  =>  produits - charges.
BILAN_NO = [
    # --- ACTIF : valeurs brutes (colonne F) ---
    ("BILAN!F12", "AE", "Frais de développement et de prospection", "211", "debiteur", 1),
    ("BILAN!F13", "AF", "Brevets, licences, logiciels et droits similaires", "212,213", "debiteur", 1),
    ("BILAN!F14", "AG", "Fonds commercial et droit au bail", "215,216", "debiteur", 1),
    ("BILAN!F15", "AH", "Autres immobilisations incorporelles", "214,217,218,219", "debiteur", 1),
    ("BILAN!F17", "AJ", "Terrains", "22", "debiteur", 1),
    ("BILAN!F18", "AK", "Bâtiments", "231,232,237,239", "debiteur", 1),
    ("BILAN!F19", "AL", "Aménagements, agencements et installations", "233,234,235,238", "debiteur", 1),
    ("BILAN!F20", "AM", "Matériel, mobilier et actifs biologiques", "241,242,243,244,246,247,248", "debiteur", 1),
    ("BILAN!F21", "AN", "Matériel de transport", "245", "debiteur", 1),
    ("BILAN!F22", "AP", "Avances et acomptes versés sur immobilisations", "251,252", "debiteur", 1),
    ("BILAN!F24", "AR", "Titres de participation", "26", "debiteur", 1),
    ("BILAN!F25", "AS", "Autres immobilisations financières", "271,272,273,274,275,276,277,278", "debiteur", 1),
    ("BILAN!F27", "BA", "Actif circulant HAO", "485,488,318", "debiteur", 1),
    ("BILAN!F28", "BB", "Stocks et en-cours", "31,32,33,34,35,36,37", "debiteur", 1),
    ("BILAN!F30", "BH", "Fournisseurs, avances versées", "409", "debiteur", 1),
    ("BILAN!F31", "BI", "Clients", "411,412,414,416,418", "debiteur", 1),
    ("BILAN!F32", "BJ", "Autres créances", "421,4287,4449,449,4586,462,465,47", "debiteur", 1),
    ("BILAN!F34", "BQ", "Titres de placement", "50", "debiteur", 1),
    ("BILAN!F35", "BR", "Valeurs à encaisser", "51", "debiteur", 1),
    ("BILAN!F36", "BS", "Banques, chèques postaux, caisse", "52,53,57", "debiteur", 1),
    ("BILAN!F38", "BU", "Écart de conversion-Actif", "478", "debiteur", 1),
    # --- ACTIF : amortissements et dépréciations (colonne G) — crédit rendu positif ---
    ("BILAN!G12", "AE", "Amort./dépréc. frais de développement", "2811,2912", "crediteur", -1),
    ("BILAN!G13", "AF", "Amort./dépréc. brevets, licences, logiciels", "2812,2813,2913", "crediteur", -1),
    ("BILAN!G14", "AG", "Amort./dépréc. fonds commercial et droit au bail", "2815,2816,2915,2916", "crediteur", -1),
    ("BILAN!G15", "AH", "Amort./dépréc. autres immo incorporelles", "2814,2817,2818,2914,2917,2918", "crediteur", -1),
    ("BILAN!G17", "AJ", "Dépréciation terrains", "282,292", "crediteur", -1),
    ("BILAN!G18", "AK", "Amort./dépréc. bâtiments", "2831,2832,2837,2931,2932,2937", "crediteur", -1),
    ("BILAN!G19", "AL", "Amort./dépréc. aménagements et installations", "2833,2834,2835,2838,2933,2934,2935,2938", "crediteur", -1),
    ("BILAN!G20", "AM", "Amort./dépréc. matériel, mobilier, actifs bio", "2841,2842,2843,2844,2846,2847,2848,2941,2942,2943,2944,2946,2947,2948", "crediteur", -1),
    ("BILAN!G21", "AN", "Amort./dépréc. matériel de transport", "2845,2945", "crediteur", -1),
    ("BILAN!G24", "AR", "Dépréciation titres de participation", "296", "crediteur", -1),
    ("BILAN!G25", "AS", "Dépréciation autres immo financières", "297", "crediteur", -1),
    ("BILAN!G28", "BB", "Dépréciation stocks", "39", "crediteur", -1),
    ("BILAN!G31", "BI", "Dépréciation clients", "491", "crediteur", -1),
    ("BILAN!G32", "BJ", "Dépréciation autres créances", "492,493,494,495,496,497", "crediteur", -1),
    # --- PASSIF (colonne M) — crédit rendu positif ---
    ("BILAN!M11", "CA", "Capital", "10", "les_deux", -1),
    ("BILAN!M12", "CB", "Apporteurs, capital non appelé (-)", "109", "les_deux", -1),
    ("BILAN!M13", "CD", "Primes liées au capital social", "105", "les_deux", -1),
    ("BILAN!M14", "CE", "Écarts de réévaluation", "106", "les_deux", -1),
    ("BILAN!M15", "CF", "Réserves indisponibles", "111,112,113", "les_deux", -1),
    ("BILAN!M16", "CG", "Réserves libres", "118", "les_deux", -1),
    ("BILAN!M17", "CH", "Report à nouveau (+ ou -)", "12", "les_deux", -1),
    ("BILAN!M18", "CJ", "Résultat net de l'exercice", "6,7,8", "les_deux", -1),
    ("BILAN!M19", "CL", "Subventions d'investissement", "14", "les_deux", -1),
    ("BILAN!M20", "CM", "Provisions réglementées", "15", "les_deux", -1),
    ("BILAN!M22", "DA", "Emprunts et dettes financières diverses", "16", "les_deux", -1),
    ("BILAN!M23", "DB", "Dettes de location-acquisition", "17", "les_deux", -1),
    ("BILAN!M24", "DC", "Provisions pour risques et charges", "19", "les_deux", -1),
    ("BILAN!M27", "DH", "Dettes circulantes HAO", "481,482,484", "crediteur", -1),
    ("BILAN!M28", "DI", "Clients, avances reçues", "419", "crediteur", -1),
    ("BILAN!M29", "DJ", "Fournisseurs d'exploitation", "401,402,408", "crediteur", -1),
    ("BILAN!M30", "DK", "Dettes fiscales et sociales", "42,43,44", "crediteur", -1),
    ("BILAN!M31", "DM", "Autres dettes", "46,47", "crediteur", -1),
    ("BILAN!M32", "DN", "Provisions pour risques à court terme", "499,599", "crediteur", -1),
    ("BILAN!M35", "DQ", "Banques, crédits d'escompte", "565", "crediteur", -1),
    ("BILAN!M36", "DR", "Banques, établissements financiers et crédits de trésorerie", "52,53,561,564,566", "crediteur", -1),
    ("BILAN!M38", "DV", "Écart de conversion-Passif", "479", "les_deux", -1),
]


def charger(apps, schema_editor):
    LigneNote = apps.get_model("comptabilite", "LigneNote")
    LigneNote.objects.filter(regime_liasse="NO", code_note="BILAN").delete()
    LigneNote.objects.bulk_create([
        LigneNote(
            regime_liasse="NO", code_note="BILAN", libelle_ligne=libelle,
            ref_dgi=ref, cellule_dgi=cellule, prefixe_comptes=prefs,
            source="solde_final", sens=sens, signe=signe, ordre=ordre,
        )
        for ordre, (cellule, ref, libelle, prefs, sens, signe) in enumerate(BILAN_NO, start=1)
    ])


def vider(apps, schema_editor):
    LigneNote = apps.get_model("comptabilite", "LigneNote")
    LigneNote.objects.filter(regime_liasse="NO", code_note="BILAN").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("comptabilite", "0011_corriger_signe_amort_deprec"),
    ]
    operations = [
        migrations.RunPython(charger, vider),
    ]