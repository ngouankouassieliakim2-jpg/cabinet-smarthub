"""
Calculs de fin de contrat (solde de tout compte) — droit du travail ivoirien.
Chaque motif déclenche les composantes applicables.
"""
from decimal import Decimal


def _d(v):
    return Decimal(str(v or 0))


# Motifs de rupture et composantes applicables
MOTIFS = {
    "demission":               {"label": "Démission",                       "presence": True, "conges": True, "gratification": True, "licenciement": False, "preavis": False, "precarite": False},
    "licenciement_personnel":  {"label": "Licenciement (motif personnel)",   "presence": True, "conges": True, "gratification": True, "licenciement": True,  "preavis": True,  "precarite": False},
    "licenciement_economique": {"label": "Licenciement économique",          "presence": True, "conges": True, "gratification": True, "licenciement": True,  "preavis": True,  "precarite": False},
    "faute_lourde":            {"label": "Licenciement pour faute lourde",   "presence": True, "conges": True, "gratification": True, "licenciement": False, "preavis": False, "precarite": False},
    "commun_accord":           {"label": "Rupture d'un commun accord",       "presence": True, "conges": True, "gratification": True, "licenciement": True,  "preavis": False, "precarite": False},
    "fin_cdd":                 {"label": "Fin de CDD (arrivée du terme)",    "presence": True, "conges": True, "gratification": True, "licenciement": False, "preavis": False, "precarite": True},
    "rupture_cdd":             {"label": "Rupture anticipée de CDD",         "presence": True, "conges": True, "gratification": True, "licenciement": False, "preavis": False, "precarite": False},
    "retraite":                {"label": "Départ à la retraite",            "presence": True, "conges": True, "gratification": True, "licenciement": True,  "preavis": True,  "precarite": False},
    "deces":                   {"label": "Décès",                           "presence": True, "conges": True, "gratification": True, "licenciement": True,  "preavis": False, "precarite": False},
    "fin_essai":               {"label": "Rupture en période d'essai",       "presence": True, "conges": True, "gratification": True, "licenciement": False, "preavis": False, "precarite": False},
    "force_majeure":           {"label": "Force majeure",                   "presence": True, "conges": True, "gratification": True, "licenciement": False, "preavis": False, "precarite": False},
}

MOTIF_CHOICES = [(k, v["label"]) for k, v in MOTIFS.items()]


def duree_preavis_mois(anciennete_annees):
    """Durée du préavis (mois) pour un salarié payé au mois, 5 premières catégories."""
    a = float(anciennete_annees or 0)
    if a < 6:
        return Decimal("1")
    elif a < 11:
        return Decimal("2")
    elif a < 16:
        return Decimal("3")
    return Decimal("4")


def indemnite_licenciement(salaire_moyen, anciennete_annees):
    """30% pour les 5 premières années, 35% de la 6e à la 10e, 40% au-delà — par année."""
    a = _d(anciennete_annees)
    sm = _d(salaire_moyen)
    t1 = min(a, Decimal("5"))
    t2 = min(max(a - Decimal("5"), Decimal("0")), Decimal("5"))
    t3 = max(a - Decimal("10"), Decimal("0"))
    taux = t1 * Decimal("0.30") + t2 * Decimal("0.35") + t3 * Decimal("0.40")
    return sm * taux


def calculer_fin_contrat(motif, salaire_moyen, salaire_base, anciennete_annees,
                         jours_presence=30, jours_conges=0, mois_travailles_annee=12,
                         total_salaires_cdd=0):
    """Détail des composantes du solde de tout compte selon le motif."""
    regles = MOTIFS.get(motif, MOTIFS["demission"])
    sm = _d(salaire_moyen)   # moyenne 12 mois : pour congés et indemnités
    sb = _d(salaire_base)    # salaire actuel : pour le salaire de présence
    lignes = []
    composantes = {}
    total = Decimal("0")

    def ajoute(cle, libelle, montant):
        nonlocal total
        montant = _d(montant)
        lignes.append({"libelle": libelle, "montant": montant})
        composantes[cle] = montant
        total += montant

    if regles["presence"]:
        ajoute("presence", "Salaire de présence", sb * _d(jours_presence) / Decimal("30"))
    if regles["conges"]:
        ajoute("conges", "Indemnité compensatrice de congés", sm * _d(jours_conges) / Decimal("30"))
    if regles["gratification"]:
        ajoute("gratification", "Gratification (13e mois, prorata)", sb * _d(mois_travailles_annee) / Decimal("12"))
    if regles["licenciement"]:
        libelle = "Indemnité de départ à la retraite" if motif == "retraite" else "Indemnité de licenciement"
        ajoute("licenciement", libelle, indemnite_licenciement(sm, anciennete_annees))
    if regles["preavis"]:
        mois_p = duree_preavis_mois(anciennete_annees)
        ajoute("preavis", f"Indemnité compensatrice de préavis ({mois_p} mois)", sm * mois_p)
    if regles["precarite"]:
        ajoute("precarite", "Prime de précarité CDD (3%)", _d(total_salaires_cdd) * Decimal("0.03"))

    return {"lignes": lignes, "total": total, "motif_label": regles["label"], "composantes": composantes}
def bonus_conges_anciennete(anciennete_annees):
    """Jours de congés supplémentaires selon l'ancienneté (Code du travail)."""
    a = float(anciennete_annees or 0)
    if a >= 30: return 8
    if a >= 25: return 7
    if a >= 20: return 5
    if a >= 15: return 3
    if a >= 10: return 2
    if a >= 5:  return 1
    return 0