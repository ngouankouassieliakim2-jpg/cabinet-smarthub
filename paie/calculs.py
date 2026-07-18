"""
Moteur de calcul de paie ivoirienne.
Reproduit fidèlement la logique du fichier Excel LOGIPAIE.
"""
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP


def _d(valeur):
    """Convertit en Decimal proprement."""
    return Decimal(str(valeur or 0))


class _RubriqueVirtuelle:
    """Une rubrique récurrente du salarié, présentée au moteur avec ses règles."""
    def __init__(self, rr):
        self.montant = rr.montant
        self.traitement_fiscal = rr.rubrique.traitement_fiscal
        self.soumis_cnps = rr.rubrique.soumis_cnps
        self.type_rubrique = getattr(rr.rubrique, "type_rubrique", "GAIN")
        self.plafond_exoneration = getattr(rr.rubrique, "plafond_exoneration", 0)


def calculer_bulletin(bulletin):
    """
    Prend un BulletinPaie et renvoie un dictionnaire avec TOUS les montants calculés.
    """
    employe = bulletin.employe
    employeur = employe.employeur

    # Si le bulletin est une reprise historique (montants figés), renvoyer tels quels.
    if getattr(bulletin, "est_historique", False):
        net = bulletin.net_historique or Decimal("0")
        return {
            "salaire_categoriel": Decimal("0"), "prime_anciennete": Decimal("0"),
            "total_gains": net + (bulletin.its_historique or Decimal("0")) + (bulletin.cnps_salarie_historique or Decimal("0")) + (bulletin.cmu_salarie_historique or Decimal("0")),
            "brut_fiscal": Decimal("0"), "brut_social": Decimal("0"), "brut_fiscal_employeur": Decimal("0"),
            "parts_igr": _d(employe.parts_igr), "its_brut": Decimal("0"), "ricf": Decimal("0"),
            "its_final": bulletin.its_historique or Decimal("0"),
            "cnps_retraite_salarie": bulletin.cnps_salarie_historique or Decimal("0"),
            "cmu_salarie": bulletin.cmu_salarie_historique or Decimal("0"),
            "cmu_employeur": Decimal("0"), "cnps_retraite_employeur": Decimal("0"),
            "cnps_accident_travail": Decimal("0"), "cnps_prestations_familiales": Decimal("0"),
            "cnps_maternite": Decimal("0"), "fdfp_ta": Decimal("0"), "fdfp_fpc": Decimal("0"),
            "contribution_employeur": Decimal("0"), "contribution_nationale": Decimal("0"),
            "total_charges_patronales": Decimal("0"),
            "total_retenues": (bulletin.its_historique or Decimal("0")) + (bulletin.cnps_salarie_historique or Decimal("0")) + (bulletin.cmu_salarie_historique or Decimal("0")),
            "net": net, "net_arrondi": net,
        }

    # Récupérer les paramètres de l'entreprise (ou valeurs par défaut)
    params = getattr(employeur, "parametres", None)
    taux_retraite_sal = _d(params.taux_cnps_retraite_salarie) if params else Decimal("6.3")
    taux_retraite_emp = _d(params.taux_cnps_retraite_employeur) if params else Decimal("7.7")
    taux_pf = _d(params.taux_cnps_pf) if params else Decimal("5.0")
    taux_maternite = _d(params.taux_cnps_maternite) if params else Decimal("0.75")
    plafond_cnps = _d(params.plafond_cnps) if params else Decimal("3375000")
    taux_ta = _d(params.taux_fdfp_ta) if params else Decimal("0.4")
    taux_fpc = _d(params.taux_fdfp_fpc) if params else Decimal("0.6")
    montant_cmu = _d(params.montant_cmu) if params else Decimal("1000")
    taux_ce_local = _d(params.taux_ce_local) if params else Decimal("0")
    taux_ce_expatrie = _d(params.taux_ce_expatrie) if params else Decimal("9.2")
    taux_cn = _d(params.taux_cn) if params else Decimal("1.2")

    # Taux AT vient du secteur
    taux_at = _d(employeur.secteur.taux_at) if (employeur.secteur) else Decimal("3")

    # Plafond d'exonération de la prime de transport
    plafond_transport = _d(employeur.plafond_transport_exonere) if employeur.plafond_transport_exonere else Decimal("30000")

    jours = _d(bulletin.jours_travailles)

    # ========== 1. PRIME D'ANCIENNETÉ (barème sur salaire catégoriel) ==========
    salaire_categoriel = Decimal("0")
    if employeur.secteur:
        cat = employeur.secteur.grille.filter(code=employe.categorie).first()
        if cat:
            salaire_categoriel = _d(cat.salaire_minimum)
    taux_anc = _d(employe.taux_anciennete)
    prime_anciennete = salaire_categoriel * taux_anc / Decimal("100")

    # ========== 2. RASSEMBLER LES GAINS ==========
    salaire_base = _d(bulletin.salaire_base)
    sursalaire = _d(bulletin.sursalaire)
    heures_sup = _d(bulletin.heures_sup)
    prime_transport = _d(bulletin.prime_transport)
    conge_paye = _d(bulletin.conge_paye)
    gratification = _d(bulletin.gratification)
    preavis = _d(bulletin.preavis)
    indemnite_licenciement = _d(bulletin.indemnite_licenciement)
    indemnite_transactionnelle = _d(bulletin.indemnite_transactionnelle)
    frais_funeraires = _d(bulletin.frais_funeraires)
    prime_precarite = _d(getattr(bulletin, "prime_precarite", 0))

    # Les rubriques récurrentes du salarié (primes fixes + retenues), depuis sa fiche
    primes = [_RubriqueVirtuelle(rr) for rr in employe.rubriques_recurrentes.select_related("rubrique").all()]
    primes_gains = [p for p in primes if p.type_rubrique != "RETENUE"]
    primes_retenues = [p for p in primes if p.type_rubrique == "RETENUE"]

    total_primes_additionnelles = sum((_d(p.montant) for p in primes_gains), Decimal("0"))
    decaissement_pret = _d(getattr(bulletin, "decaissement_pret", 0))
    total_gains = (salaire_base + sursalaire + heures_sup + prime_anciennete + prime_transport
                   + conge_paye + gratification + preavis + indemnite_licenciement
                   + indemnite_transactionnelle + frais_funeraires
                   + decaissement_pret
                   + total_primes_additionnelles)

    # ========== 3. BRUT FISCAL (base de l'ITS et des impôts employeur) ==========
    transport_imposable = max(prime_transport - plafond_transport, Decimal("0"))

    if indemnite_licenciement > Decimal("50000"):
        licenciement_imposable = (indemnite_licenciement - Decimal("50000")) * Decimal("0.5")
    else:
        licenciement_imposable = Decimal("0")

    # Côté employeur, l'indemnité de licenciement est comptée en entier (pas d'abattement)
    licenciement_imposable_employeur = indemnite_licenciement

    primes_fiscal = Decimal("0")
    for p in primes_gains:
        montant = _d(p.montant)
        if p.traitement_fiscal == "exonere":
            continue
        elif p.traitement_fiscal == "plafonne":
            plafond = _d(getattr(p, "plafond_exoneration", 0))
            primes_fiscal += max(montant - plafond, Decimal("0"))
        elif p.traitement_fiscal == "abattement":
            primes_fiscal += montant * Decimal("0.9")
        else:
            primes_fiscal += montant

    brut_fiscal = (salaire_base + sursalaire + heures_sup + prime_anciennete + transport_imposable
                   + conge_paye + gratification + preavis + licenciement_imposable
                   + prime_precarite + primes_fiscal)

    # Base employeur : indemnité de licenciement sans abattement + indemnité transactionnelle incluse
    brut_fiscal_employeur = (salaire_base + sursalaire + heures_sup + prime_anciennete + transport_imposable
                             + conge_paye + gratification + preavis + licenciement_imposable_employeur
                             + indemnite_transactionnelle + prime_precarite + primes_fiscal)

    # ========== 4. BRUT SOCIAL (base CNPS) ==========
    primes_social = Decimal("0")
    for p in primes_gains:
        if not p.soumis_cnps:
            continue
        montant = _d(p.montant)
        if p.traitement_fiscal == "plafonne":
            plafond = _d(getattr(p, "plafond_exoneration", 0))
            primes_social += max(montant - plafond, Decimal("0"))
        else:
            primes_social += montant

    brut_social = (salaire_base + sursalaire + heures_sup + prime_anciennete + transport_imposable
                   + conge_paye + gratification + preavis + prime_precarite + primes_social)

    # ========== 5. CALCUL DE L'ITS (6 tranches + RICF) ==========
    its_brut = _calcul_its_tranches(brut_fiscal)

    parts = _d(employe.parts_igr)
    if brut_fiscal > Decimal("75000"):
        ricf = (parts - Decimal("1")) * Decimal("2") * Decimal("5500")
    else:
        ricf = Decimal("0")

    its_apres_ricf = max(its_brut - ricf, Decimal("0"))
    its_final = its_apres_ricf * jours / Decimal("30")

    # ========== 6. COTISATIONS SALARIÉ ==========
    base_cnps = min(brut_social, plafond_cnps)
    cnps_retraite_salarie = base_cnps * taux_retraite_sal / Decimal("100")

    # CMU : 1000 F/personne, réparti 50/50. Employeur cofinance salarié + conjoint + 6 enfants max.
    demi_cmu = _d(montant_cmu) / Decimal("2")
    nb_conjoint = 1 if getattr(employe, "cmu_conjoint_a_charge", False) else 0
    nb_enfants_cmu = int(employe.nombre_enfants or 0) if getattr(employe, "cmu_enfants_a_charge", True) else 0
    enfants_cofinances = min(nb_enfants_cmu, 6)
    enfants_hors_plafond = max(nb_enfants_cmu - 6, 0)
    personnes_cofinancees = 1 + nb_conjoint + enfants_cofinances
    cmu_employeur = demi_cmu * personnes_cofinancees
    cmu_salarie = demi_cmu * personnes_cofinancees + _d(montant_cmu) * enfants_hors_plafond

    # ========== 7. CHARGES PATRONALES ==========
    cnps_retraite_employeur = base_cnps * taux_retraite_emp / Decimal("100")
    cnps_accident_travail = base_cnps * taux_at / Decimal("100")
    cnps_prestations_familiales = base_cnps * taux_pf / Decimal("100")
    cnps_maternite = base_cnps * taux_maternite / Decimal("100")
    fdfp_ta = brut_social * taux_ta / Decimal("100")
    fdfp_fpc = brut_social * taux_fpc / Decimal("100")

    # Impôts sur salaires à la charge de l'employeur (sur le brut fiscal)
    # CE : exonérée pour le local, 9,2% pour l'expatrié
    if getattr(employe, "regime", "general") == "expatrie":
        contribution_employeur = brut_fiscal_employeur * taux_ce_expatrie / Decimal("100")
    else:
        contribution_employeur = brut_fiscal_employeur * taux_ce_local / Decimal("100")
    # CN : 1,2% (local et expatrié)
    contribution_nationale = brut_fiscal_employeur * taux_cn / Decimal("100")

    total_charges_patronales = (cnps_retraite_employeur + cnps_accident_travail
                                + cnps_prestations_familiales + cnps_maternite
                                + fdfp_ta + fdfp_fpc + cmu_employeur
                                + contribution_employeur + contribution_nationale)

    # ========== 8. RETENUES & NET ==========
    avance = _d(bulletin.avance_acompte)
    pret = _d(bulletin.montant_pret)
    autres = _d(bulletin.autres_retenues)

    total_retenues_rubriques = sum((_d(p.montant) for p in primes_retenues), Decimal("0"))
    total_retenues = (its_final + cnps_retraite_salarie + cmu_salarie
                      + avance + pret + autres + total_retenues_rubriques)

    net = total_gains - total_retenues

    arrondi = employeur.arrondi_net or 5
    net_arrondi = (net / Decimal(arrondi)).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * Decimal(arrondi)

    return {
        "salaire_categoriel": salaire_categoriel,
        "prime_anciennete": prime_anciennete,
        "total_gains": total_gains,
        "brut_fiscal": brut_fiscal,
        "brut_fiscal_employeur": brut_fiscal_employeur,
        "brut_social": brut_social,
        "parts_igr": parts,
        "its_brut": its_brut,
        "ricf": ricf,
        "its_final": its_final,
        "cnps_retraite_salarie": cnps_retraite_salarie,
        "cmu_salarie": cmu_salarie,
        "cmu_employeur": cmu_employeur,
        "cnps_retraite_employeur": cnps_retraite_employeur,
        "cnps_accident_travail": cnps_accident_travail,
        "cnps_prestations_familiales": cnps_prestations_familiales,
        "cnps_maternite": cnps_maternite,
        "fdfp_ta": fdfp_ta,
        "fdfp_fpc": fdfp_fpc,
        "contribution_employeur": contribution_employeur,
        "contribution_nationale": contribution_nationale,
        "total_charges_patronales": total_charges_patronales,
        "total_retenues": total_retenues,
        "net": net,
        "net_arrondi": net_arrondi,
    }


def _calcul_its_tranches(base):
    """Calcule l'ITS selon le barème ivoirien à 6 tranches cumulatives."""
    base = _d(base)
    tranches = [
        (Decimal("0"), Decimal("75000"), Decimal("0")),
        (Decimal("75000"), Decimal("240000"), Decimal("16")),
        (Decimal("240000"), Decimal("800000"), Decimal("21")),
        (Decimal("800000"), Decimal("2400000"), Decimal("24")),
        (Decimal("2400000"), Decimal("8000000"), Decimal("28")),
        (Decimal("8000000"), None, Decimal("32")),
    ]
    its = Decimal("0")
    for bas, haut, taux in tranches:
        if base <= bas:
            break
        if haut is None:
            portion = base - bas
        else:
            portion = min(base, haut) - bas
        its += portion * taux / Decimal("100")
    return its
def taux_horaire(salaire_base):
    """Taux horaire = salaire mensuel / 173,33 h (40h × 52 / 12)."""
    return _d(salaire_base) / Decimal("173.33")