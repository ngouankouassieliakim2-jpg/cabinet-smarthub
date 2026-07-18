"""
Peuplement de LigneNote pour les 4 notes pilotes (3A, 3C, 4, 5), a partir de la
structure REELLE des onglets NOTE 3A / NOTE 3C / NOTE 4 / NOTE 5 du fichier
officiel DGI-liasse-NO.xlsm (et non plus de l'exemple simplifie du Guide).

Principe : on ne cree une ligne LigneNote QUE pour les cellules d'ENTREE reelles
du fichier DGI (les lignes de detail, colonnes brutes). Les cellules de TOTAUX
et la colonne de cloture/solde sont des FORMULES dans le fichier officiel
(ex. J = D+E+F+G-H-I en NOTE 3A) -- on ne les remplit donc jamais nous-memes,
le fichier DGI les calcule tout seul a l'ouverture.

Limites connues, assumees en accord avec le principe "zero quand pas d'info" :
  - NOTE 3A : les colonnes F (virements+), G (reevaluation) et I (virements-)
    ne sont pas deductibles d'une balance a 6 colonnes -> aucune LigneNote,
    laissees a zero / saisie manuelle du cabinet dans le fichier DGI.
  - NOTE 3C : aucun compte SYSCOHADA officiel ne distingue l'amortissement
    d'un immeuble de placement -> la ligne "Batiments - immeuble de placement"
    reste a zero (limite structurelle du plan comptable, pas un oubli).
    La colonne H (amort. relatifs aux elements sortis) recoit tout le mouvement
    crediteur ; la colonne J (reprises) et L (virements) restent a zero.
  - NOTE 4 et 5 : les colonnes d'echeancier (creances a un an / deux ans / plus)
    ne sont pas deductibles d'une balance -> non renseignees.
"""
from django.db import migrations

REGIME = "NO"


def _cellule(onglet, colonne, ligne):
    return f"{onglet}!{colonne}{ligne}"


# ============================================================
# NOTE 3A : IMMOBILISATION BRUTE (mouvements)
# Colonnes reelles : D=ouverture, E=acquisitions, H=cessions (F,G,I manuels)
# ============================================================
# (ligne_excel, libelle, prefixe_comptes)
RUBRIQUES_3A = [
    (12, "Frais de développement et de prospection", "211"),
    (13, "Brevets, licences, logiciels, et droits similaires", "212,213"),
    (14, "Fonds commercial et droit au bail", "215,216"),
    (15, "Autres immobilisations incorporelles", "214,217,218,219"),
    (17, "Terrains hors immeuble de placement", "221,222,223,224,225,226,227,2285,2288"),
    (18, "Terrains - immeuble de placement", "2281"),
    (19, "Bâtiments hors immeuble de placement", "231,232,237,239"),
    (20, "Bâtiments - immeuble de placement", "2315,2325"),
    (21, "Aménagements, agencements et installations", "233,234,235,238"),
    (22, "Matériel, mobilier et actifs biologiques", "241,242,243,244,246,247,248,249"),
    (23, "Matériel de transport", "245"),
    (25, "Avances et acomptes sur immobilisations incorporelles", "251"),
    (26, "Avances et acomptes sur immobilisations corporelles", "252"),
    (28, "Titres de participation", "26"),
    (29, "Autres immobilisations financières", "27"),
]

# ============================================================
# NOTE 3C : IMMOBILISATIONS - AMORTISSEMENTS (mouvements)
# Colonnes reelles : D=ouverture, F=dotations, H=amort. sur elements sortis
# (J=reprises et L=virements non deductibles de la balance -> manuels)
# ============================================================
RUBRIQUES_3C = [
    (11, "Frais de développement et de prospection", "2811"),
    (12, "Brevets, licences, logiciels et droits similaires", "2812,2813"),
    (13, "Fonds commercial et droit au bail", "2815,2816"),
    (14, "Autres immobilisations incorporelles", "2814,2817,2818"),
    (16, "Terrains hors immeuble de placement", "282"),
    (17, "Terrains - immeuble de placement", ""),  # aucun compte officiel distinct -> zéro
    (18, "Bâtiments hors immeuble de placement", "2831,2832,2837"),
    (19, "Bâtiments - immeuble de placement", ""),  # limite structurelle -> zéro (cf. docstring)
    (20, "Aménagements, agencements et installations", "2833,2834,2835,2838"),
    (21, "Matériel, mobilier et actifs biologiques", "2841,2842,2843,2844,2846,2847,2848"),
    (22, "Matériel de transport", "2845"),
]

# ============================================================
# NOTE 4 : IMMOBILISATIONS FINANCIERES (comparatif N / N-1)
# Colonnes reelles : F=Année N (solde_final), G=Année N-1 (solde_initial)
# ============================================================
RUBRIQUES_4 = [
    (9, "Titres de participation", "26"),
    (10, "Prêts et créances", "271"),
    (11, "Prêt au personnel", "272"),
    (12, "Créances sur l'État", "273"),
    (13, "Titres immobilisés", "274"),
    (14, "Dépôts et cautionnements", "275"),
    (15, "Intérêts courus", "276"),
    (16, "Créances rattachées à des avances et participations à des GIE", "277"),
    (17, "Immobilisations financières diverses", "278"),
    (19, "Dépréciations des titres de participation", "296"),
    (20, "Dépréciations des autres immobilisations financières", "297"),
]

# ============================================================
# NOTE 5 : ACTIF CIRCULANT ET DETTES CIRCULANTES HAO (comparatif N / N-1)
# Colonnes reelles : E=Année N (solde_final), G=Année N-1 (solde_initial)
# ============================================================
RUBRIQUES_5 = [
    (10, "Créances sur cessions d'immobilisations", "485"),
    (11, "Autres créances hors activités ordinaires", "488"),
    (13, "Dépréciations des créances HAO", "498"),
    (22, "Fournisseurs d'investissements", "481"),
    (23, "Fournisseurs d'investissements effets à payer", "482"),
    (24, "Versements restant à effectuer sur titres de participation et titres immobilisés non libérés", "472"),
    (25, "Autres dettes hors activités ordinaires", "484"),
]


def populate_lignenote(apps, schema_editor):
    LigneNote = apps.get_model("comptabilite", "LigneNote")
    objs = []

    # --- NOTE 3A : D(ouverture) / E(acquisitions) / H(cessions) ---
    for i, (ligne, libelle, prefixe) in enumerate(RUBRIQUES_3A):
        for colonne, source in [("D", "solde_initial"), ("E", "mouvement_debit"), ("H", "mouvement_credit")]:
            objs.append(LigneNote(
                regime_liasse=REGIME, code_note="NOTE 3A", libelle_ligne=libelle,
                prefixe_comptes=prefixe, source=source,
                cellule_dgi=_cellule("NOTE 3A", colonne, ligne), ordre=i,
            ))

    # --- NOTE 3C : D(ouverture) / F(dotations) / H(amort. sortis) ---
    for i, (ligne, libelle, prefixe) in enumerate(RUBRIQUES_3C):
        if not prefixe:
            continue  # pas de compte officiel -> pas de ligne, reste à zéro dans le fichier DGI
        for colonne, source in [("D", "solde_initial"), ("F", "mouvement_debit"), ("H", "mouvement_credit")]:
            objs.append(LigneNote(
                regime_liasse=REGIME, code_note="NOTE 3C", libelle_ligne=libelle,
                prefixe_comptes=prefixe, source=source,
                cellule_dgi=_cellule("NOTE 3C", colonne, ligne), ordre=i,
            ))

    # --- NOTE 4 : F(Année N = solde_final) / G(Année N-1 = solde_initial) ---
    for i, (ligne, libelle, prefixe) in enumerate(RUBRIQUES_4):
        for colonne, source in [("F", "solde_final"), ("G", "solde_initial")]:
            objs.append(LigneNote(
                regime_liasse=REGIME, code_note="NOTE 4", libelle_ligne=libelle,
                prefixe_comptes=prefixe, source=source,
                cellule_dgi=_cellule("NOTE 4", colonne, ligne), ordre=i,
            ))

    # --- NOTE 5 : E(Année N = solde_final) / G(Année N-1 = solde_initial) ---
    for i, (ligne, libelle, prefixe) in enumerate(RUBRIQUES_5):
        for colonne, source in [("E", "solde_final"), ("G", "solde_initial")]:
            objs.append(LigneNote(
                regime_liasse=REGIME, code_note="NOTE 5", libelle_ligne=libelle,
                prefixe_comptes=prefixe, source=source,
                cellule_dgi=_cellule("NOTE 5", colonne, ligne), ordre=i,
            ))

    LigneNote.objects.bulk_create(objs, ignore_conflicts=True)


def depopulate_lignenote(apps, schema_editor):
    LigneNote = apps.get_model("comptabilite", "LigneNote")
    LigneNote.objects.filter(
        regime_liasse=REGIME,
        code_note__in=["NOTE 3A", "NOTE 3C", "NOTE 4", "NOTE 5"],
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("comptabilite", "0005_repopulate_notes_master_complet"),
    ]

    operations = [
        migrations.RunPython(populate_lignenote, depopulate_lignenote),
    ]
