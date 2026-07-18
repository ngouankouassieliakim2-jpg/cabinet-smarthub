"""
Table maître des 36 notes annexes officielles du Système Normal SYSCOHADA.
Source : Guide d'application du SYSCOHADA, Partie 3, sommaire de l'Application 127
(modèle type d'un jeu complet d'états financiers).

Cette table est indépendante du référentiel de mapping LigneNote : elle sert
uniquement à savoir quelles notes DOIVENT exister dans la liasse. Le moteur de
calcul boucle dessus systématiquement -- une note sans LigneNote configurée
sort simplement à zéro, elle n'est jamais absente de la liasse.
"""
from django.db import migrations

# (code_note, libelle, type_note, ordre)
NOTES_SYSTEME_NORMAL = [
    ("NOTE 1", "Dettes garanties par des sûretés réelles", "texte", 1),
    ("NOTE 2", "Informations obligatoires", "texte", 2),
    ("NOTE 3A", "Immobilisation brute", "mouvements", 3),
    ("NOTE 3B", "Biens pris en location acquisition", "situation", 4),
    ("NOTE 3C", "Immobilisations : amortissements", "mouvements", 5),
    ("NOTE 3D", "Immobilisations : plus-values et moins-values de cession", "situation", 6),
    ("NOTE 3E", "Informations sur les réévaluations effectuées par l'entité", "texte", 7),
    ("NOTE 3F", "Tableau d'étalement des charges immobilisées", "situation", 8),
    ("NOTE 4", "Immobilisations financières", "comparatif", 9),
    ("NOTE 5", "Actif circulant et dettes circulantes HAO", "comparatif", 10),
    ("NOTE 6", "Stocks et en-cours", "comparatif", 11),
    ("NOTE 7", "Clients", "comparatif", 12),
    ("NOTE 8", "Autres créances", "comparatif", 13),
    ("NOTE 9", "Titres de placement", "situation", 14),
    ("NOTE 10", "Valeurs à encaisser", "situation", 15),
    ("NOTE 11", "Disponibilités", "comparatif", 16),
    ("NOTE 12", "Écarts de conversion et transferts de charges", "comparatif", 17),
    ("NOTE 13", "Capital : valeur nominale des actions ou parts", "situation", 18),
    ("NOTE 14", "Primes et réserves", "situation", 19),
    ("NOTE 15A", "Subventions et provisions réglementées", "mouvements", 20),
    ("NOTE 15B", "Autres fonds propres", "situation", 21),
    ("NOTE 16A", "Dettes financières et ressources assimilées", "comparatif", 22),
    ("NOTE 16B", "Engagements de retraite et avantages assimilés (méthode actuarielle)", "texte", 23),
    ("NOTE 16C", "Actifs et passifs éventuels", "texte", 24),
    ("NOTE 17", "Fournisseurs d'exploitation", "comparatif", 25),
    ("NOTE 18", "Dettes fiscales et sociales", "comparatif", 26),
    ("NOTE 19", "Autres dettes et provisions pour risques à court terme", "comparatif", 27),
    ("NOTE 20", "Banques, crédits d'escompte et de trésorerie", "situation", 28),
    ("NOTE 21", "Chiffre d'affaires et autres produits", "comparatif", 29),
    ("NOTE 22", "Achats", "comparatif", 30),
    ("NOTE 23", "Transports", "comparatif", 31),
    ("NOTE 24", "Services extérieurs", "comparatif", 32),
    ("NOTE 25", "Impôts et taxes", "comparatif", 33),
    ("NOTE 26", "Autres charges", "comparatif", 34),
    ("NOTE 27A", "Charges de personnel", "comparatif", 35),
    ("NOTE 27B", "Effectifs, masse salariale et personnel extérieur", "comparatif", 36),
    ("NOTE 28", "Provisions et dépréciations inscrites au bilan", "mouvements", 37),
    ("NOTE 29", "Charges et revenus financiers", "comparatif", 38),
    ("NOTE 30", "Autres charges et produits HAO", "comparatif", 39),
    ("NOTE 31", "Répartition du résultat et autres éléments caractéristiques des 5 derniers exercices", "texte", 40),
    ("NOTE 32", "Production de l'exercice", "situation", 41),
    ("NOTE 33", "Achats destinés à la production", "situation", 42),
    ("NOTE 34", "Fiche de synthèse des principaux indicateurs financiers", "comparatif", 43),
    ("NOTE 35", "Liste des informations sociales, environnementales et sociétales à fournir", "texte", 44),
    ("NOTE 36", "Table des codes", "texte", 45),
]


def populate_notes_master(apps, schema_editor):
    NoteAnnexeDefinition = apps.get_model("comptabilite", "NoteAnnexeDefinition")
    objs = [
        NoteAnnexeDefinition(
            regime_liasse="NO", code_note=code, libelle=libelle,
            type_note=type_note, ordre=ordre,
        )
        for code, libelle, type_note, ordre in NOTES_SYSTEME_NORMAL
    ]
    NoteAnnexeDefinition.objects.bulk_create(objs, ignore_conflicts=True)


def depopulate_notes_master(apps, schema_editor):
    NoteAnnexeDefinition = apps.get_model("comptabilite", "NoteAnnexeDefinition")
    codes = [c for c, _, _, _ in NOTES_SYSTEME_NORMAL]
    NoteAnnexeDefinition.objects.filter(regime_liasse="NO", code_note__in=codes).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("comptabilite", "0002_populate_syscohada_complet"),
    ]

    operations = [
        migrations.RunPython(populate_notes_master, depopulate_notes_master),
    ]
