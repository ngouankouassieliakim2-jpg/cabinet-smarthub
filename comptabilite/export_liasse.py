"""
Export de la liasse calculee vers une copie du fichier officiel DGI.

Ce module prend le resultat de comptabilite.moteur.generer_liasse() et
l'ecrit dans une copie du template Excel officiel (macro-enabled), en ne
touchant JAMAIS aux cellules qui sont des formules dans le fichier DGI
(NOTE 22 a 29 par exemple, qui pullent depuis COMP-CHARGES) -- seules les
cellules d'entree reelles (celles listees dans LigneNote.cellule_dgi) sont
ecrites.

Le fichier de sortie est un .xlsm (macro-enabled workbook), pas un .xltm
(template) : le cabinet doit pouvoir l'ouvrir directement comme un document
normal, pas comme base d'un "nouveau document".
"""

import os
from datetime import datetime

import openpyxl

from django.conf import settings

from .moteur import generer_liasse
from .export_suppl4 import ecrire_suppl4


# Chemin du template officiel par regime de liasse. A configurer dans
# settings.py : TEMPLATES_LIASSE_DGI = {"NO": "/chemin/vers/DGI-liasse-NO.xlsm", ...}
def _chemin_template(regime_liasse):
    templates = getattr(settings, "TEMPLATES_LIASSE_DGI", {})
    chemin = templates.get(regime_liasse)
    if not chemin:
        raise ValueError(
            f"Aucun template configure pour le regime '{regime_liasse}'. "
            f"Ajoute-le dans settings.TEMPLATES_LIASSE_DGI."
        )
    if not os.path.exists(chemin):
        raise FileNotFoundError(f"Template introuvable : {chemin}")
    return chemin


def _dossier_sortie():
    dossier = getattr(settings, "DOSSIER_LIASSES_GENEREES", None)
    if not dossier:
        dossier = os.path.join(settings.BASE_DIR, "liasses_generees")
    os.makedirs(dossier, exist_ok=True)
    return dossier


def _nom_fichier_sortie(balance):
    nom_client = getattr(balance.client, "nom", None) or getattr(balance.client, "denomination", None) or str(balance.client)
    nom_client_propre = "".join(c if c.isalnum() else "_" for c in str(nom_client))[:50]
    horodatage = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"Liasse_{balance.regime_liasse}_{nom_client_propre}_{balance.exercice}_{horodatage}.xlsm"


def _ecrire_valeurs(classeur, valeurs, anomalies_ecriture):
    """Ecrit chaque valeur calculee dans sa cellule. cellule_dgi est de la
    forme 'NOM ONGLET!ADRESSE' (ex. 'NOTE 3A!D17')."""
    for cellule_dgi, montant in valeurs.items():
        try:
            nom_onglet, adresse = cellule_dgi.split("!", 1)
        except ValueError:
            anomalies_ecriture.append(f"Cellule mal formee, ignoree : '{cellule_dgi}'")
            continue

        if nom_onglet not in classeur.sheetnames:
            anomalies_ecriture.append(f"Onglet '{nom_onglet}' absent du fichier officiel, ignore ({cellule_dgi})")
            continue

        feuille = classeur[nom_onglet]
        try:
            cellule = feuille[adresse]
        except (KeyError, ValueError):
            anomalies_ecriture.append(f"Adresse de cellule invalide, ignoree : '{cellule_dgi}'")
            continue

        # Securite : on n'ecrase jamais une cellule qui contient deja une
        # formule dans le fichier officiel -- ca ne devrait jamais arriver
        # si LigneNote est bien configure, mais on se protege quand meme.
        if isinstance(cellule.value, str) and cellule.value.startswith("="):
            anomalies_ecriture.append(
                f"ATTENTION : {cellule_dgi} contient deja une formule "
                f"({cellule.value[:40]}...), ecriture annulee pour cette cellule."
            )
            continue

        # Le franc CFA n'a pas de decimales -- on ecrit un entier.
        cellule.value = int(montant)


def generer_fichier_liasse(balance, chemin_template=None, chemin_sortie=None):
    """Point d'entree principal. Genere le fichier Excel rempli pour une
    Balance donnee, en s'appuyant sur le template officiel DGI.

    Retourne un dict :
      {
        "chemin_fichier": str,              # chemin du .xlsm genere
        "resultat_calcul": {...},            # ce que generer_liasse() a retourne
        "anomalies_ecriture": [...],         # problemes rencontres a l'ecriture
      }
    """
    resultat_calcul = generer_liasse(balance)

    chemin_template = chemin_template or _chemin_template(balance.regime_liasse)
    classeur = openpyxl.load_workbook(chemin_template, keep_vba=True)

    # On genere un .xlsm normal, pas un .xltm (template) -- le cabinet doit
    # pouvoir l'ouvrir comme un document deja rempli, pas comme base d'un
    # nouveau document vierge.
    classeur.template = False

    anomalies_ecriture = []
    _ecrire_valeurs(classeur, resultat_calcul["valeurs"], anomalies_ecriture)

    # Ecriture de SUPPL4 (tableau des immobilisations, nombre de lignes
    # variable) -- mecanisme distinct de _ecrire_valeurs car il insere des
    # lignes plutot que d'ecrire dans des cellules fixes. Ne fait rien si
    # aucune fiche d'immobilisation n'a ete saisie pour cette balance.
    lignes_immo = list(balance.immobilisations.all())
    ecrire_suppl4(classeur, lignes_immo)

    if chemin_sortie is None:
        chemin_sortie = os.path.join(_dossier_sortie(), _nom_fichier_sortie(balance))

    classeur.save(chemin_sortie)

    return {
        "chemin_fichier": chemin_sortie,
        "resultat_calcul": resultat_calcul,
        "anomalies_ecriture": anomalies_ecriture,
    }