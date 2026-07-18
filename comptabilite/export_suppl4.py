"""
Ecriture de l'onglet SUPPL4 (Etat supplementaire n4 : tableau des
amortissements et inventaire des immobilisations) -- un onglet a NOMBRE DE
LIGNES VARIABLE, contrairement a NOTE 3A/3C/COMP-CHARGES qui ont des
cellules fixes.

Particularites geree ici, decouvertes en inspectant le fichier officiel :
  - La ligne 10 est le modele (premiere ligne de donnees).
  - La ligne 11 (a l'origine) est le TOTAL, avec des formules qui se
    recalculent toutes seules via ROW() -- donc AUCUN ajustement de formule
    n'est necessaire apres insertion de lignes.
  - En revanche, openpyxl NE DEPLACE PAS les cellules fusionnees lors d'un
    insert_rows() : il faut re-fusionner "TOTAL" (A:F) a la nouvelle
    position, et fusionner B:D (designation) sur chaque nouvelle ligne
    inseree, sous peine de fichier Excel visuellement casse.
  - K10 (valeur residuelle) n'a PAS de formule dans le fichier officiel tel
    que recu -- on lui ajoute nous-memes "=G-J" (valeur d'acquisition moins
    amortissement total), qui est le calcul correct, mais ce n'est pas une
    formule copiee du cabinet : a signaler si jamais un comportement
    different etait attendu.
"""

from copy import copy


LIGNE_MODELE = 10
LIGNE_TOTAL_ORIGINALE = 11
COLONNES_DONNEES = ["A", "B", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N"]


def _copier_formatage_cellule(source, cible):
    cible.font = copy(source.font)
    cible.border = copy(source.border)
    cible.fill = copy(source.fill)
    cible.number_format = source.number_format
    cible.alignment = copy(source.alignment)


def ecrire_suppl4(classeur, lignes_immobilisation):
    """Ecrit les fiches d'immobilisation dans SUPPL4. Ne fait rien si
    l'onglet n'existe pas dans ce template, ou si la liste est vide."""
    if "SUPPL4" not in classeur.sheetnames or not lignes_immobilisation:
        return

    feuille = classeur["SUPPL4"]
    n = len(lignes_immobilisation)

    if n > 1:
        # On retire la fusion du label TOTAL AVANT l'insertion, sinon
        # openpyxl la laisse figee a l'ancienne position (ligne 11) alors
        # que le vrai total se retrouve plus bas.
        feuille.unmerge_cells(
            start_row=LIGNE_TOTAL_ORIGINALE, start_column=1,
            end_row=LIGNE_TOTAL_ORIGINALE, end_column=6,
        )

        feuille.insert_rows(LIGNE_TOTAL_ORIGINALE, amount=n - 1)

        # Chaque nouvelle ligne reprend le format (pas les valeurs) de la
        # ligne modele, et sa propre fusion B:D pour la designation.
        for i in range(1, n):
            ligne_cible = LIGNE_MODELE + i
            for col in COLONNES_DONNEES:
                _copier_formatage_cellule(feuille[f"{col}{LIGNE_MODELE}"], feuille[f"{col}{ligne_cible}"])
            feuille.merge_cells(start_row=ligne_cible, start_column=2, end_row=ligne_cible, end_column=4)

        nouvelle_ligne_total = LIGNE_TOTAL_ORIGINALE + (n - 1)
        feuille.merge_cells(
            start_row=nouvelle_ligne_total, start_column=1,
            end_row=nouvelle_ligne_total, end_column=6,
        )
        feuille[f"A{nouvelle_ligne_total}"] = "TOTAL"

    for i, immo in enumerate(lignes_immobilisation):
        ligne = LIGNE_MODELE + i
        feuille[f"A{ligne}"] = immo.compte
        feuille[f"B{ligne}"] = immo.designation
        feuille[f"E{ligne}"] = float(immo.taux_amortissement)
        feuille[f"F{ligne}"] = immo.date_mise_en_service
        feuille[f"G{ligne}"] = int(immo.valeur_acquisition)
        feuille[f"H{ligne}"] = int(immo.amortissements_anterieurs)
        feuille[f"I{ligne}"] = int(immo.amortissements_exercice)
        feuille[f"J{ligne}"] = f"=H{ligne}+I{ligne}"
        feuille[f"K{ligne}"] = f"=G{ligne}-J{ligne}"  # ajoutee par nous, cf. docstring

        if immo.prix_cession is not None:
            feuille[f"L{ligne}"] = int(immo.prix_cession)
            plus_value = immo.plus_value
            moins_value = immo.moins_value
            if plus_value:
                feuille[f"M{ligne}"] = int(plus_value)
            if moins_value:
                feuille[f"N{ligne}"] = int(moins_value)
