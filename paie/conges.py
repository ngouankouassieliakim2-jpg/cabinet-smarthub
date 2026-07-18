"""Calcul des congés : jours ouvrables par mois et indemnité répartie.
Règle : jours ouvrables = tous les jours sauf le dimanche.
Indemnité = salaire moyen des 12 derniers mois ÷ 30 × jours ouvrables (droit ivoirien).
Répartition (b) : l'indemnité est ventilée mois par mois selon les jours de chaque mois."""
from datetime import timedelta
from decimal import Decimal


def _salaire_moyen_12_mois(employe):
    """Moyenne des total_gains des 12 derniers bulletins (même logique que la fin de contrat).
    Repli sur le salaire de base si aucun bulletin."""
    from .models import BulletinPaie
    from .calculs import calculer_bulletin
    bulletins = list(BulletinPaie.objects.filter(employe=employe).order_by("-annee", "-mois")[:12])
    if bulletins:
        total = sum((calculer_bulletin(b)["brut_social"] for b in bulletins), Decimal("0"))
        return total / len(bulletins)
    return Decimal(str(employe.salaire_base or 0))


def jours_ouvrables(date_debut, date_fin):
    """Nombre de jours ouvrables (hors dimanche ET hors jours fériés) entre deux dates, bornes incluses."""
    if not date_debut or not date_fin or date_fin < date_debut:
        return 0
    from .models import JourFerie
    feries = set(JourFerie.objects.filter(date__range=(date_debut, date_fin)).values_list("date", flat=True))
    n = 0
    jour = date_debut
    while jour <= date_fin:
        if jour.weekday() != 6 and jour not in feries:  # 6 = dimanche, et pas un férié
            n += 1
        jour += timedelta(days=1)
    return n


def calculer_conge(employe, date_depart, date_retour):
    """Calcule le congé entre le départ et le RETOUR (le retour = reprise, donc dernier jour = veille du retour).
    Renvoie un dict :
      - jours_total : jours ouvrables de tout le congé
      - montant_total : indemnité totale (Decimal)
      - salaire_journalier : salaire moyen /30 (Decimal)
      - repartition : liste de dicts {annee, mois, jours, montant} par mois touché
    """
    from datetime import date

    # Le retour est le jour de reprise : le congé va donc jusqu'à la veille.
    dernier_jour = date_retour - timedelta(days=1)

    salaire_moyen = _salaire_moyen_12_mois(employe)
    salaire_journalier = (salaire_moyen / Decimal("30")).quantize(Decimal("1"))

    jours_total = jours_ouvrables(date_depart, dernier_jour)
    montant_total = (salaire_journalier * Decimal(str(jours_total))).quantize(Decimal("1"))

    # Répartition mois par mois
    repartition = []
    if jours_total > 0:
        # On balaie chaque mois touché entre départ et dernier jour
        curseur = date(date_depart.year, date_depart.month, 1)
        fin = date(dernier_jour.year, dernier_jour.month, 1)
        while curseur <= fin:
            # Bornes du mois courant, intersectées avec la période de congé
            if curseur.month == 12:
                fin_mois = date(curseur.year, 12, 31)
            else:
                fin_mois = date(curseur.year, curseur.month + 1, 1) - timedelta(days=1)
            debut_portion = max(date_depart, curseur)
            fin_portion = min(dernier_jour, fin_mois)
            jours_mois = jours_ouvrables(debut_portion, fin_portion)
            if jours_mois > 0:
                montant_mois = (salaire_journalier * Decimal(str(jours_mois))).quantize(Decimal("1"))
                repartition.append({
                    "annee": curseur.year, "mois": curseur.month,
                    "jours": jours_mois, "montant": montant_mois,
                })
            # Mois suivant
            if curseur.month == 12:
                curseur = date(curseur.year + 1, 1, 1)
            else:
                curseur = date(curseur.year, curseur.month + 1, 1)

    return {
        "jours_total": jours_total,
        "montant_total": montant_total,
        "salaire_journalier": salaire_journalier,
        "repartition": repartition,
    }


def compteur_conges(employe):
    """Calcule le solde de congé annuel du salarié : acquis, pris, restant."""
    from datetime import date
    from .models import BulletinPaie, Conge
    import calendar

    if not employe.date_entree:
        return {"debut_cycle": None, "acquis": 0, "pris": 0, "restant": 0}

    taux_mensuel = employe.employeur.jours_conges_par_mois or Decimal("2.2")
    aujourd_hui = date.today()

    dernier_conge = (Conge.objects.filter(employe=employe, type_conge="annuel")
                     .order_by("-date_depart").first())
    reference = dernier_conge.date_retour if dernier_conge else employe.date_entree

    debut_cycle = reference
    while True:
        mois_total = debut_cycle.month - 1 + 12
        annee_suivante = debut_cycle.year + mois_total // 12
        mois_suivant = mois_total % 12 + 1
        jour_suivant = min(debut_cycle.day, calendar.monthrange(annee_suivante, mois_suivant)[1])
        fin_cycle = debut_cycle.replace(year=annee_suivante, month=mois_suivant, day=jour_suivant)
        if fin_cycle > aujourd_hui:
            break
        debut_cycle = fin_cycle

    acquis = Decimal("0")
    curseur = date(debut_cycle.year, debut_cycle.month, 1)
    while curseur <= aujourd_hui:
        bulletin = BulletinPaie.objects.filter(employe=employe, mois=curseur.month, annee=curseur.year).first()
        jours_travailles = bulletin.jours_travailles if bulletin else Decimal("30")
        acquis += taux_mensuel * (Decimal(str(jours_travailles)) / Decimal("30"))
        if curseur.month == 12:
            curseur = date(curseur.year + 1, 1, 1)
        else:
            curseur = date(curseur.year, curseur.month + 1, 1)

    conges_cycle = Conge.objects.filter(employe=employe, type_conge="annuel", date_depart__gte=debut_cycle)
    pris = sum((c.jours_ouvrables for c in conges_cycle), 0)

    acquis = round(float(acquis), 1)
    restant = round(acquis - pris, 1)

    return {"debut_cycle": debut_cycle, "acquis": acquis, "pris": pris, "restant": restant}
