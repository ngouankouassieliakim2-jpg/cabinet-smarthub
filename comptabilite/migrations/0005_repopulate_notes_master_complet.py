"""
Repeuplement complet de NoteAnnexeDefinition à partir de la structure REELLE
des onglets du fichier officiel DGI-liasse-NO.xlsm (85 onglets), classee en
4 familles :

  - identification       : pages de garde / fiches signalétiques (saisie manuelle,
                            une fois par client, jamais calculées depuis la balance)
  - etat_financier        : Bilan, Actif, Passif, Résultat, TFT (agrégation directe
                             des comptes, PAS via le référentiel LigneNote)
  - note_syscohada        : les notes annexes normalisées OHADA (calculées via
                             LigneNote -- c'est le coeur du moteur de calcul)
  - supplementaire_dgi    : les 9 tableaux ajoutés par la DGI Côte d'Ivoire en
                             plus du référentiel OHADA (COMP-CHARGES, COMP-TVA,
                             SUPPL1 à SUPPL7)

Remplace entièrement le peuplement précédent (issu du seul sommaire du Guide,
qui ne couvrait que 45 lignes et ne distinguait pas les familles).
"""
from django.db import migrations

# (code_note, libelle, type_note, categorie, onglet_dgi, ordre)
NOTES_NO = [
    # --- Identification / pages de garde (saisie manuelle, une fois par client) ---
    ("COUVERTURE", "Page de couverture", "texte", "identification", "COUVERTURE", 1),
    ("GARDE", "Page de garde", "texte", "identification", "GARDE", 2),
    ("RECEVABILITE", "Conditions de recevabilité", "texte", "identification", "RECEVABILITE", 3),
    ("NOTE36", "Table des codes", "texte", "identification", "NOTE36 (TABLE DES CODES)", 4),
    ("NOTE36 SUITE", "Nomenclature", "texte", "identification", "NOTE36 Suite (Nomenclature)", 5),
    ("FICHE R1", "Fiche signalétique R1", "texte", "identification", "FICHE R1", 6),
    ("FICHE R2", "Fiche signalétique R2", "texte", "identification", "FICHE R2", 7),
    ("FICHE R3", "Fiche signalétique R3", "texte", "identification", "FICHE R3", 8),
    ("FICHE R4", "Fiche signalétique R4", "texte", "identification", "FICHE R4", 9),

    # --- États financiers principaux (agrégation directe des comptes) ---
    ("BILAN", "Bilan (saisie maîtresse)", "situation", "etat_financier", "BILAN", 20),
    ("ACTIF", "Bilan - Actif (vue formatée)", "situation", "etat_financier", "ACTIF", 21),
    ("PASSIF", "Bilan - Passif (vue formatée)", "situation", "etat_financier", "PASSIF", 22),
    ("RESULTAT", "Compte de résultat", "comparatif", "etat_financier", "RESULTAT", 23),
    ("TFT", "Tableau des flux de trésorerie", "comparatif", "etat_financier", "TFT", 24),

    # --- Notes annexes SYSCOHADA (calculées via LigneNote) ---
    ("NOTE 1", "Dettes garanties par des sûretés réelles", "texte", "note_syscohada", "NOTE 1", 30),
    ("NOTE 2", "Informations obligatoires", "texte", "note_syscohada", "NOTE 2", 31),
    ("NOTE 3A", "Immobilisation brute", "mouvements", "note_syscohada", "NOTE 3A", 32),
    ("NOTE 3B", "Biens pris en location acquisition", "situation", "note_syscohada", "NOTE 3B", 33),
    ("NOTE 3C", "Immobilisations : amortissements", "mouvements", "note_syscohada", "NOTE 3C", 34),
    ("NOTE 3C BIS", "Immobilisations : amortissements (suite)", "mouvements", "note_syscohada", "NOTE 3C BIS", 35),
    ("NOTE 3D", "Immobilisations : plus-values et moins-values de cession", "situation", "note_syscohada", "NOTE 3D", 36),
    ("NOTE 3E", "Informations sur les réévaluations effectuées par l'entité", "texte", "note_syscohada", "NOTE 3E", 37),
    ("NOTE 4", "Immobilisations financières", "comparatif", "note_syscohada", "NOTE 4", 38),
    ("NOTE 5", "Actif circulant et dettes circulantes HAO", "comparatif", "note_syscohada", "NOTE 5", 39),
    ("NOTE 6", "Stocks et en-cours", "comparatif", "note_syscohada", "NOTE 6", 40),
    ("NOTE 7", "Clients", "comparatif", "note_syscohada", "NOTE 7", 41),
    ("NOTE 8", "Autres créances", "comparatif", "note_syscohada", "NOTE 8", 42),
    ("NOTE 8A", "Autres créances (détail A)", "comparatif", "note_syscohada", "NOTE 8A", 43),
    ("NOTE 8B", "Autres créances (détail B)", "comparatif", "note_syscohada", "NOTE 8B", 44),
    ("NOTE 8C", "Autres créances (détail C)", "comparatif", "note_syscohada", "NOTE 8C", 45),
    ("NOTE 9", "Titres de placement", "situation", "note_syscohada", "NOTE 9", 46),
    ("NOTE 10", "Valeurs à encaisser", "situation", "note_syscohada", "NOTE 10", 47),
    ("NOTE 11", "Disponibilités", "comparatif", "note_syscohada", "NOTE 11", 48),
    ("NOTE 12", "Écarts de conversion et transferts de charges", "comparatif", "note_syscohada", "NOTE 12", 49),
    ("NOTE 13", "Capital : valeur nominale des actions ou parts", "situation", "note_syscohada", "NOTE 13", 50),
    ("NOTE 14", "Primes et réserves", "situation", "note_syscohada", "NOTE 14", 51),
    ("NOTE 15A", "Subventions et provisions réglementées", "mouvements", "note_syscohada", "NOTE 15A", 52),
    ("NOTE 15B", "Autres fonds propres", "situation", "note_syscohada", "NOTE 15B", 53),
    ("NOTE 16A", "Dettes financières et ressources assimilées", "comparatif", "note_syscohada", "NOTE 16A", 54),
    ("NOTE 16B", "Engagements de retraite et avantages assimilés (méthode actuarielle)", "texte", "note_syscohada", "NOTE 16B", 55),
    ("NOTE 16B BIS", "Engagements de retraite et avantages assimilés (suite)", "texte", "note_syscohada", "NOTE 16B BIS", 56),
    ("NOTE 16C", "Actifs et passifs éventuels", "texte", "note_syscohada", "NOTE 16C", 57),
    ("NOTE 17", "Fournisseurs d'exploitation", "comparatif", "note_syscohada", "NOTE 17", 58),
    ("NOTE 18", "Dettes fiscales et sociales", "comparatif", "note_syscohada", "NOTE 18", 59),
    ("NOTE 19", "Autres dettes et provisions pour risques à court terme", "comparatif", "note_syscohada", "NOTE 19", 60),
    ("NOTE 20", "Banques, crédits d'escompte et de trésorerie", "situation", "note_syscohada", "NOTE 20", 61),
    ("NOTE 21", "Chiffre d'affaires et autres produits", "comparatif", "note_syscohada", "NOTE 21", 62),
    ("NOTE 22", "Achats", "comparatif", "note_syscohada", "NOTE 22", 63),
    ("NOTE 23", "Transports", "comparatif", "note_syscohada", "NOTE 23", 64),
    ("NOTE 24", "Services extérieurs", "comparatif", "note_syscohada", "NOTE 24", 65),
    ("NOTE 25", "Impôts et taxes", "comparatif", "note_syscohada", "NOTE 25", 66),
    ("NOTE 26", "Autres charges", "comparatif", "note_syscohada", "NOTE 26", 67),
    ("NOTE 27A", "Charges de personnel", "comparatif", "note_syscohada", "NOTE 27A", 68),
    ("NOTE 27B", "Effectifs, masse salariale et personnel extérieur", "comparatif", "note_syscohada", "NOTE 27B", 69),
    ("NOTE 28", "Provisions et dépréciations inscrites au bilan", "mouvements", "note_syscohada", "NOTE 28", 70),
    ("NOTE 29", "Charges et revenus financiers", "comparatif", "note_syscohada", "NOTE 29", 71),
    ("NOTE 30", "Autres charges et produits HAO", "comparatif", "note_syscohada", "NOTE 30", 72),
    ("NOTE 31", "Répartition du résultat et autres éléments caractéristiques des 5 derniers exercices", "texte", "note_syscohada", "NOTE 31", 73),
    ("NOTE 32", "Production de l'exercice", "situation", "note_syscohada", "NOTE 32", 74),
    ("NOTE 33", "Achats destinés à la production", "situation", "note_syscohada", "NOTE 33", 75),
    ("NOTE 34", "Fiche de synthèse des principaux indicateurs financiers", "comparatif", "note_syscohada", "NOTE 34", 76),
    ("NOTE 35", "Liste des informations sociales, environnementales et sociétales à fournir", "texte", "note_syscohada", "NOTE 35", 77),
    ("NOTE 37", "Note complémentaire 37 (à confirmer/documenter)", "texte", "note_syscohada", "NOTE 37", 78),
    ("NOTE 38", "Note complémentaire 38 (à confirmer/documenter)", "texte", "note_syscohada", "NOTE 38", 79),
    ("NOTE 39", "Note complémentaire 39 (à confirmer/documenter)", "texte", "note_syscohada", "NOTE 39", 80),

    # --- Tableaux supplémentaires DGI / INS (hors norme OHADA stricte) ---
    ("GARDE DGI-INS", "Page de garde DGI-INS", "texte", "supplementaire_dgi", "GARDE (DGI-INS)", 90),
    ("NOTES DGI-INS", "Notes complémentaires DGI-INS", "texte", "supplementaire_dgi", "NOTES DGI - INS", 91),
    ("COMP-CHARGES", "Complément charges", "comparatif", "supplementaire_dgi", "COMP-CHARGES", 92),
    ("COMP-TVA", "Complément TVA", "comparatif", "supplementaire_dgi", "COMP-TVA", 93),
    ("COMP-TVA 2", "Complément TVA (suite)", "comparatif", "supplementaire_dgi", "COMP-TVA (2)", 94),
    ("SUPPL1", "Tableau supplémentaire DGI/INS 1", "texte", "supplementaire_dgi", "SUPPL1", 95),
    ("SUPPL2", "Tableau supplémentaire DGI/INS 2", "texte", "supplementaire_dgi", "SUPPL2", 96),
    ("SUPPL3", "Tableau supplémentaire DGI/INS 3", "texte", "supplementaire_dgi", "SUPPL3", 97),
    ("SUPPL4", "Tableau supplémentaire DGI/INS 4", "texte", "supplementaire_dgi", "SUPPL4", 98),
    ("SUPPL5", "Tableau supplémentaire DGI/INS 5", "texte", "supplementaire_dgi", "SUPPL5", 99),
    ("SUPPL6", "Tableau supplémentaire DGI/INS 6", "texte", "supplementaire_dgi", "SUPPL6", 100),
    ("SUPPL7", "Tableau supplémentaire DGI/INS 7", "texte", "supplementaire_dgi", "SUPPL7", 101),
]


def repopulate_notes_master(apps, schema_editor):
    NoteAnnexeDefinition = apps.get_model("comptabilite", "NoteAnnexeDefinition")
    # On repart propre : l'ancien peuplement (45 lignes, sommaire du Guide,
    # sans onglet_dgi ni categorie fiables) est supprimé puis remplacé.
    NoteAnnexeDefinition.objects.filter(regime_liasse="NO").delete()
    objs = [
        NoteAnnexeDefinition(
            regime_liasse="NO", code_note=code, libelle=libelle,
            type_note=type_note, categorie=categorie, onglet_dgi=onglet_dgi, ordre=ordre,
        )
        for code, libelle, type_note, categorie, onglet_dgi, ordre in NOTES_NO
    ]
    NoteAnnexeDefinition.objects.bulk_create(objs, ignore_conflicts=True)


def depopulate_notes_master(apps, schema_editor):
    # Remet l'ancien peuplement minimal (45 lignes) pour permettre le rollback.
    NoteAnnexeDefinition = apps.get_model("comptabilite", "NoteAnnexeDefinition")
    NoteAnnexeDefinition.objects.filter(regime_liasse="NO").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("comptabilite", "0004_noteannexedefinition_categorie_and_more"),
    ]

    operations = [
        migrations.RunPython(repopulate_notes_master, depopulate_notes_master),
    ]
