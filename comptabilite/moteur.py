"""
Moteur de calcul du module comptabilite.

Ce fichier contient toute la logique qui transforme une Balance importee
(LigneBalance, comptes clients) en valeurs pretes a etre ecrites dans une
copie du fichier officiel DGI (BILAN, NOTE 3A, NOTE 3C, NOTE 4, NOTE 5,
COMP-CHARGES...).

Principes directeurs (voir conversation de conception) :
  1. La balance est TOUJOURS la source de verite pour ce qu'elle peut donner.
  2. Les ajustements manuels (AjustementNote) sont RESIDUELS : ils se
     soustraient ou remplacent une valeur deja calculee, jamais ajoutes
     en parallele -- impossible de desynchroniser le total.
  3. La liasse est TOUJOURS generee en entier (toutes les NoteAnnexeDefinition
     du regime) : une note sans LigneNote configure sort a zero/vide plutot
     que d'etre absente.
  4. Un compte de balance qui ne correspond a AUCUN compte SYSCOHADA officiel
     est signale en anomalie, jamais ignore silencieusement.
  5. On n'ecrit JAMAIS dans une cellule qui est une formule dans le fichier
     officiel (ex. NOTE 22 a 29 pullent depuis COMP-CHARGES via formule --
     on ecrit dans COMP-CHARGES, jamais directement dans NOTE 22-29).
  6. Le moteur decouvre dynamiquement quelles notes sont configurees (via
     les code_note distincts presents dans LigneNote), plutot qu'une liste
     figee dans le code -- ajouter une note ne demande qu'une migration de
     donnees, jamais une modification de moteur.py.
"""

from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

from .models import (
    AjustementNote,
    CompteSyscohada,
    LigneBalance,
    LigneNote,
    NoteAnnexeDefinition,
)


# ======================================================================
# 0. ARRONDI AU FRANC CFA ENTIER (aucune décimale dans la liasse)
# ======================================================================
# Le franc CFA n'a pas de centimes. On garde la précision décimale pendant
# les calculs intermediaires (division du prorata notamment), et on arrondit
# UNIQUEMENT au moment de finaliser les valeurs a ecrire dans la liasse --
# arrondir plus tot accumulerait des erreurs d'arrondi ligne par ligne.

def arrondir_fcfa(valeur):
    """Arrondit un montant Decimal au franc CFA entier le plus proche
    (arrondi commercial standard : 0,5 arrondit vers le haut)."""
    return Decimal(valeur).quantize(Decimal("1"), rounding=ROUND_HALF_UP)


# ======================================================================
# 1. RATTACHEMENT D'UN COMPTE DE BALANCE A SA RACINE SYSCOHADA OFFICIELLE
# ======================================================================

def charger_codes_syscohada_connus():
    """Retourne l'ensemble de tous les codes SYSCOHADA officiels connus.
    A appeler une seule fois par generation de liasse (pas par compte)."""
    return set(CompteSyscohada.objects.values_list("code", flat=True))


def racine_syscohada(compte_balance, codes_connus):
    """Trouve le code SYSCOHADA officiel le plus specifique (le plus long)
    dont le code est un prefixe du compte de balance donne.

    Exemple : 60110001 -> teste 60110001, 6011000, 601100, ... jusqu'a
    trouver "6011" dans codes_connus.

    Retourne None si aucun prefixe ne correspond (compte inconnu du plan).
    """
    s = str(compte_balance).strip()
    for k in range(len(s), 0, -1):
        prefixe = s[:k]
        if prefixe in codes_connus:
            return prefixe
    return None


# ======================================================================
# 2. RATTACHEMENT D'UNE RACINE SYSCOHADA A UNE LIGNE DE NOTE (LigneNote)
# ======================================================================

def construire_index_lignenote(regime_liasse, code_note, source):
    """Pour un couple (note, colonne source) donne, construit la liste des
    (prefixe, LigneNote) triee par longueur de prefixe decroissante, pour
    que le matching le plus specifique gagne toujours (ex. 2315 avant 231)."""
    lignes = LigneNote.objects.filter(
        regime_liasse=regime_liasse, code_note=code_note, source=source
    )
    index = []
    for ligne in lignes:
        for prefixe in ligne.prefixe_comptes.split(","):
            prefixe = prefixe.strip()
            if prefixe:
                index.append((prefixe, ligne))
    index.sort(key=lambda t: -len(t[0]))
    return index


def trouver_ligne_note(racine, index, sens_compte):
    """Retourne la LigneNote correspondant au plus long prefixe de l'index qui
    matche la racine SYSCOHADA donnee ET dont le sens est compatible avec le
    sens du compte (debiteur / crediteur), ou None si aucune ne correspond.

    Le filtre par sens est applique ICI, pendant la selection -- pas apres.
    Sinon un compte a double sens (ex. 52 crediteur = decouvert) matcherait la
    regle de l'autre cote (tresorerie-actif), serait ensuite rejete, et
    tomberait dans le vide au lieu d'aller cote passif.
    """
    for prefixe, ligne in index:
        if racine.startswith(prefixe) and (ligne.sens == "les_deux" or ligne.sens == sens_compte):
            return ligne
    return None


# ======================================================================
# 3. CALCUL D'UNE NOTE (OU D'UN TABLEAU COMME COMP-CHARGES) DEPUIS LA BALANCE
# ======================================================================

def calculer_note(balance, code_note, codes_connus):
    """Calcule toutes les valeurs d'une note/tableau (a partir des LigneNote
    configurees pour ce code_note) pour la Balance donnee.

    Retourne (valeurs, anomalies) :
      - valeurs : dict {cellule_dgi: Decimal}
      - anomalies : liste de dicts {compte, libelle, message}
    """
    regime = balance.regime_liasse
    sources_utilisees = (
        LigneNote.objects.filter(regime_liasse=regime, code_note=code_note)
        .order_by()  # annule le tri par defaut du modele avant .distinct()
        .values_list("source", flat=True)
        .distinct()
    )

    index_par_source = {
        source: construire_index_lignenote(regime, code_note, source)
        for source in sources_utilisees
    }

    valeurs = defaultdict(Decimal)
    anomalies = []

    for ligne_balance in LigneBalance.objects.filter(balance=balance):
        racine = racine_syscohada(ligne_balance.compte, codes_connus)
        if racine is None:
            anomalies.append({
                "compte": ligne_balance.compte,
                "libelle": ligne_balance.libelle,
                "message": "Compte inconnu du plan SYSCOHADA officiel — à vérifier avec le cabinet.",
            })
            continue

        # Sens du compte, deduit du signe du solde final (convention interne :
        # debit positif, credit negatif). Sert de filtre pour router les comptes
        # a double sens (ex. 52 crediteur = decouvert -> tresorerie-passif).
        solde = ligne_balance.solde_final or Decimal(0)
        if solde > 0:
            sens_compte = "debiteur"
        elif solde < 0:
            sens_compte = "crediteur"
        else:
            sens_compte = "nul"

        for source in sources_utilisees:
            montant = getattr(ligne_balance, source)
            if not montant:
                continue
            ligne_note = trouver_ligne_note(racine, index_par_source[source], sens_compte)
            if ligne_note is not None:
                # signe : +1 cote actif (debit-positif), -1 cote passif (credit-positif).
                # Sur un solde signe, ceci place la valeur du bon cote avec le bon signe --
                # le +/- du report a nouveau et du resultat en decoule automatiquement.
                # Sur un mouvement (montant positif), signe=+1 par defaut => inchange.
                valeurs[ligne_note.cellule_dgi] += ligne_note.signe * montant

    # Ajustements manuels residuels / remplacement pour cette note
    for ajustement in AjustementNote.objects.filter(balance=balance, code_note=code_note):
        if ajustement.mode == "remplacement":
            valeurs[ajustement.cellule_dgi] = ajustement.montant
        else:  # complement_residuel : soustrait de la valeur calculee automatiquement
            valeurs[ajustement.cellule_dgi] -= ajustement.montant

    return dict(valeurs), anomalies


# ======================================================================
# 4. CAS PARTICULIER : PRORATA IMMEUBLE DE PLACEMENT (NOTE 3C)
# ======================================================================
# Rappel : aucun compte SYSCOHADA officiel ne distingue l'amortissement d'un
# immeuble de placement. On applique donc le meme ratio (valeur brute
# placement / valeur brute totale des batiments) trouve en NOTE 3A a
# l'amortissement total des batiments calcule en NOTE 3C, et on repartit.
# (Ce cas sera affine plus tard si les fiches LigneImmobilisation/SUPPL4
# sont renseignees -- elles permettront un calcul exact bien par bien.)

def appliquer_prorata_placement_3c(valeurs_3a, valeurs_3c):
    """Modifie valeurs_3c EN PLACE : repartit l'amortissement 'batiments'
    (actuellement entierement affecte a la ligne hors-placement, faute de
    compte distinct) entre hors-placement et placement, au prorata des
    valeurs brutes trouvees en NOTE 3A.

    IMPORTANT : deux ratios distincts, pas un seul --
      - ratio_ouverture (valeurs brutes D19/D20 SEULES) pour la colonne
        D (amortissement cumule a l'ouverture). Un bien acquis pendant
        l'exercice a une valeur brute d'ouverture nulle, donc il ne peut
        structurellement PAS avoir d'amortissement cumule a l'ouverture --
        utiliser le ratio de cloture ici attribuerait a tort de
        l'amortissement d'ouverture a un bien qui n'existait pas encore
        au 1er janvier.
      - ratio_cloture (valeurs brutes en fin d'exercice, D+E-H) pour la
        colonne F (dotations de l'exercice), simplification assumee en
        l'absence de fiches d'immobilisation bien par bien (SUPPL4).
    """
    ouverture_hors_placement = valeurs_3a.get("NOTE 3A!D19", 0)
    ouverture_placement = valeurs_3a.get("NOTE 3A!D20", 0)
    ouverture_totale = ouverture_hors_placement + ouverture_placement

    cloture_hors_placement = (
        valeurs_3a.get("NOTE 3A!D19", 0) + valeurs_3a.get("NOTE 3A!E19", 0) - valeurs_3a.get("NOTE 3A!H19", 0)
    )
    cloture_placement = (
        valeurs_3a.get("NOTE 3A!D20", 0) + valeurs_3a.get("NOTE 3A!E20", 0) - valeurs_3a.get("NOTE 3A!H20", 0)
    )
    cloture_totale = cloture_hors_placement + cloture_placement

    amort_ouverture_total = valeurs_3c.get("NOTE 3C!D18", 0)
    amort_dotation_total = valeurs_3c.get("NOTE 3C!F18", 0)
    amort_sortie_total = valeurs_3c.get("NOTE 3C!H18", 0)

    # --- Colonne D (ouverture) : ratio base sur les valeurs brutes D'OUVERTURE ---
    if ouverture_totale:
        ratio_ouverture = Decimal(ouverture_placement) / Decimal(ouverture_totale)
    else:
        ratio_ouverture = Decimal(0)  # rien n'existait a l'ouverture -> aucun amort. d'ouverture possible

    if amort_ouverture_total:
        if not ouverture_totale:
            # Incoherence reelle : de l'amortissement d'ouverture existe en
            # balance (compte 28xx) mais aucune valeur brute d'ouverture en
            # NOTE 3A -- on ne devine pas, on laisse tout en "hors placement"
            # par defaut et ce cas devrait remonter en anomalie a verifier
            # par le cabinet (donnee de balance suspecte).
            pass
        part_ouverture_placement = Decimal(amort_ouverture_total) * ratio_ouverture
        valeurs_3c["NOTE 3C!D19"] = part_ouverture_placement
        valeurs_3c["NOTE 3C!D18"] = Decimal(amort_ouverture_total) - part_ouverture_placement

    # --- Colonne F (dotations de l'exercice) : ratio base sur les valeurs de CLOTURE ---
    if cloture_totale:
        ratio_cloture = Decimal(cloture_placement) / Decimal(cloture_totale)
        if amort_dotation_total:
            part_dotation_placement = Decimal(amort_dotation_total) * ratio_cloture
            valeurs_3c["NOTE 3C!F19"] = part_dotation_placement
            valeurs_3c["NOTE 3C!F18"] = Decimal(amort_dotation_total) - part_dotation_placement

        # --- Colonne H (amortissements sur elements sortis) : meme ratio de cloture ---
        if amort_sortie_total:
            part_sortie_placement = Decimal(amort_sortie_total) * ratio_cloture
            valeurs_3c["NOTE 3C!H19"] = part_sortie_placement
            valeurs_3c["NOTE 3C!H18"] = Decimal(amort_sortie_total) - part_sortie_placement


# ======================================================================
# 5. GENERATION DE LA LIASSE COMPLETE (toutes les notes, meme a zero)
# ======================================================================

def notes_configurees(regime_liasse):
    """Decouvre dynamiquement tous les code_note pour lesquels au moins une
    LigneNote existe -- pas de liste figee a maintenir dans le code."""
    return list(
        LigneNote.objects.filter(regime_liasse=regime_liasse)
        .order_by()  # meme piege : sans ca, .distinct() porte sur
        # (code_note, ordre) a cause du Meta.ordering du modele, et on
        # recupere des centaines de "faux doublons" au lieu de 5 notes.
        .values_list("code_note", flat=True)
        .distinct()
    )


def generer_liasse(balance):
    """Point d'entree principal. Pour une Balance donnee, retourne :
      {
        "valeurs": {cellule_dgi: Decimal, ...},   # toutes notes/tableaux confondus
        "anomalies": [...],                        # comptes non reconnus
        "notes_calculees": [...],                   # codes avec au moins une LigneNote
        "notes_a_zero": [...],                       # onglets calculables de la liasse
                                                       # (etat_financier / note_syscohada /
                                                       # supplementaire_dgi) pas encore configures
      }
    """
    codes_connus = charger_codes_syscohada_connus()
    regime = balance.regime_liasse

    codes_configures = notes_configurees(regime)

    valeurs_globales = {}
    anomalies_globales = []
    resultats_par_note = {}

    for code_note in codes_configures:
        valeurs, anomalies = calculer_note(balance, code_note, codes_connus)
        resultats_par_note[code_note] = valeurs
        valeurs_globales.update(valeurs)
        anomalies_globales.extend(anomalies)

    # Cas particulier : repartition placement pour NOTE 3C, si les deux
    # notes sources sont bien disponibles
    if "NOTE 3A" in resultats_par_note and "NOTE 3C" in resultats_par_note:
        appliquer_prorata_placement_3c(resultats_par_note["NOTE 3A"], resultats_par_note["NOTE 3C"])
        valeurs_globales.update(resultats_par_note["NOTE 3C"])

    # Dedoublonnage des anomalies (un meme compte inconnu peut remonter
    # plusieurs fois s'il est croise par plusieurs notes/tableaux)
    vus = set()
    anomalies_dedupliquees = []
    for a in anomalies_globales:
        cle = a["compte"]
        if cle not in vus:
            vus.add(cle)
            anomalies_dedupliquees.append(a)

    # Tous les onglets calculables de la liasse (on exclut "identification" :
    # ce sont des pages de garde/fiches saisies une fois, jamais calculees)
    onglets_calculables = list(
        NoteAnnexeDefinition.objects.filter(regime_liasse=regime)
        .exclude(categorie="identification")
        .values_list("code_note", flat=True)
    )
    notes_a_zero = [c for c in onglets_calculables if c not in codes_configures]

    # Arrondi final au franc CFA entier -- aucune decimale dans la liasse.
    # Fait en tout dernier, apres tous les calculs (dont le prorata), pour
    # ne pas accumuler d'erreurs d'arrondi ligne par ligne.
    valeurs_arrondies = {
        cellule: arrondir_fcfa(montant) for cellule, montant in valeurs_globales.items()
    }

    return {
        "valeurs": valeurs_arrondies,
        "anomalies": anomalies_dedupliquees,
        "notes_calculees": codes_configures,
        "notes_a_zero": notes_a_zero,
    }