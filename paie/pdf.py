from django.template.loader import render_to_string
from weasyprint import HTML
from decimal import Decimal
from .calculs import calculer_bulletin
from .models import BulletinPaie


def _prep_bulletin(bulletin):
    employe = bulletin.employe
    calcul = calculer_bulletin(bulletin)
    rubriques = list(employe.rubriques_recurrentes.select_related("rubrique").all())
    gains_rub = [r for r in rubriques if getattr(r.rubrique, "type_rubrique", "GAIN") != "RETENUE"]
    retenues_rub = [r for r in rubriques if getattr(r.rubrique, "type_rubrique", "GAIN") == "RETENUE"]
    return calcul, gains_rub, retenues_rub


def generer_pdf_bulletin(bulletin, mois, annee, request=None):
    employe = bulletin.employe
    employeur = employe.employeur
    calcul, gains_rub, retenues_rub = _prep_bulletin(bulletin)
    mois_nom = dict(BulletinPaie.MOIS_CHOICES).get(mois, "")
    from .documents_utils import generer_reference_document, generer_qr_code_data_uri
    reference = generer_reference_document("BUL")
    qr_data_uri = generer_qr_code_data_uri(f"Cabinet Smart-Hub — Bulletin {reference} — {employe.nom_prenoms} — {mois_nom} {annee}")
    html_string = render_to_string("paie/bulletin_pdf.html", {
        "employeur": employeur, "employe": employe, "bulletin": bulletin, "c": calcul,
        "gains_rub": gains_rub, "retenues_rub": retenues_rub, "mois_nom": mois_nom, "annee": annee,
        "reference": reference,
        "qr_data_uri": qr_data_uri,
    })
    base = request.build_absolute_uri("/") if request is not None else "http://127.0.0.1:8000/"
    return HTML(string=html_string, base_url=base).write_pdf()


def generer_pdf_bulletins_groupes(employeur, mois, annee, request=None):
    items = []
    for e in employeur.employes.filter(statut="ACTIF"):
        bulletin = BulletinPaie.objects.filter(employe=e, mois=mois, annee=annee).first()
        if not bulletin:
            bulletin = BulletinPaie(employe=e, mois=mois, annee=annee,
                                    jours_travailles=30, salaire_base=e.salaire_base)
        calcul, gains_rub, retenues_rub = _prep_bulletin(bulletin)
        items.append({"employe": e, "bulletin": bulletin, "c": calcul,
                      "gains_rub": gains_rub, "retenues_rub": retenues_rub})
    mois_nom = dict(BulletinPaie.MOIS_CHOICES).get(mois, "")
    html_string = render_to_string("paie/bulletins_groupes_pdf.html", {
        "employeur": employeur, "bulletins": items, "mois_nom": mois_nom, "annee": annee,
    })
    base = request.build_absolute_uri("/") if request is not None else "http://127.0.0.1:8000/"
    return HTML(string=html_string, base_url=base).write_pdf()


def generer_pdf_ordre_virement(employeur, mois, annee, request=None):
    """Lettre d'ordre de virement + annexe des salariés payés par virement."""
    from .models import Employe

    bulletins = (BulletinPaie.objects.filter(employe__employeur=employeur, mois=mois, annee=annee,
                                              employe__mode_paiement="virement")
                 .select_related("employe").order_by("employe__nom_prenoms"))
    lignes = []
    total = Decimal("0")
    for b in bulletins:
        c = calculer_bulletin(b)
        lignes.append({"employe": b.employe, "net": c["net_arrondi"]})
        total += c["net_arrondi"]

    mois_nom = dict(BulletinPaie.MOIS_CHOICES).get(mois, "")
    html_string = render_to_string("paie/ordre_virement_pdf.html", {
        "employeur": employeur, "lignes": lignes, "total": total,
        "mois_nom": mois_nom, "annee": annee, "nb_salaries": len(lignes),
    })
    base = request.build_absolute_uri("/") if request is not None else "http://127.0.0.1:8000/"
    return HTML(string=html_string, base_url=base).write_pdf()


def generer_pdf_livre_mensuel(employeur, mois, annee, request=None):
    """Livre de paie mensuel DÉTAILLÉ : bases, part salariale, part patronale, totaux."""
    lignes = []
    cles = ["brut_social", "brut_fiscal", "cnps_sal", "its", "cmu_sal", "net",
            "cnps_emp", "pf", "at", "mat", "ta", "fpc", "ce", "cn", "cmu_emp", "total_pat"]
    T = {k: 0.0 for k in cles}
    for e in employeur.employes.filter(statut="ACTIF"):
        bulletin = BulletinPaie.objects.filter(employe=e, mois=mois, annee=annee).first()
        if not bulletin:
            bulletin = BulletinPaie(employe=e, mois=mois, annee=annee,
                                    jours_travailles=30, salaire_base=e.salaire_base)
        c = calculer_bulletin(bulletin)
        lignes.append({"employe": e, "c": c})
        T["brut_social"] += float(c["brut_social"]);   T["brut_fiscal"] += float(c["brut_fiscal"])
        T["cnps_sal"] += float(c["cnps_retraite_salarie"]); T["its"] += float(c["its_final"])
        T["cmu_sal"] += float(c["cmu_salarie"]);       T["net"] += float(c["net_arrondi"])
        T["cnps_emp"] += float(c["cnps_retraite_employeur"]); T["pf"] += float(c["cnps_prestations_familiales"])
        T["at"] += float(c["cnps_accident_travail"]);  T["mat"] += float(c["cnps_maternite"])
        T["ta"] += float(c["fdfp_ta"]);                T["fpc"] += float(c["fdfp_fpc"])
        T["ce"] += float(c["contribution_employeur"]); T["cn"] += float(c["contribution_nationale"])
        T["cmu_emp"] += float(c["cmu_employeur"]);     T["total_pat"] += float(c["total_charges_patronales"])

    mois_nom = dict(BulletinPaie.MOIS_CHOICES).get(mois, "")
    html_string = render_to_string("paie/livre_mensuel_pdf.html", {
        "employeur": employeur, "lignes": lignes, "totaux": T, "mois_nom": mois_nom, "annee": annee,
    })
    base = request.build_absolute_uri("/") if request is not None else "http://127.0.0.1:8000/"
    return HTML(string=html_string, base_url=base).write_pdf()
def generer_pdf_livre_annuel(employeur, annee, request=None):
    """Livre de paie annuel : cumul des 12 mois par salarié + totaux généraux."""
    lignes = []
    cles = ["brut_social", "brut_fiscal", "cnps_sal", "its", "cmu_sal", "net",
            "cnps_emp", "pf", "at", "mat", "ta", "fpc", "ce", "cn", "cmu_emp", "total_pat"]
    T = {k: 0.0 for k in cles}

    # Tous les salariés ayant au moins un bulletin dans l'année
    employe_ids = (BulletinPaie.objects.filter(employe__employeur=employeur, annee=annee)
                   .values_list("employe_id", flat=True).distinct())
    employes = employeur.employes.filter(id__in=list(employe_ids))

    for e in employes:
        bulletins = BulletinPaie.objects.filter(employe=e, annee=annee)
        cumul = {k: 0.0 for k in cles}
        nb_mois = 0
        for b in bulletins:
            c = calculer_bulletin(b)
            nb_mois += 1
            cumul["brut_social"] += float(c["brut_social"]);   cumul["brut_fiscal"] += float(c["brut_fiscal"])
            cumul["cnps_sal"] += float(c["cnps_retraite_salarie"]); cumul["its"] += float(c["its_final"])
            cumul["cmu_sal"] += float(c["cmu_salarie"]);       cumul["net"] += float(c["net_arrondi"])
            cumul["cnps_emp"] += float(c["cnps_retraite_employeur"]); cumul["pf"] += float(c["cnps_prestations_familiales"])
            cumul["at"] += float(c["cnps_accident_travail"]);  cumul["mat"] += float(c["cnps_maternite"])
            cumul["ta"] += float(c["fdfp_ta"]);                cumul["fpc"] += float(c["fdfp_fpc"])
            cumul["ce"] += float(c["contribution_employeur"]); cumul["cn"] += float(c["contribution_nationale"])
            cumul["cmu_emp"] += float(c["cmu_employeur"]);     cumul["total_pat"] += float(c["total_charges_patronales"])
        lignes.append({"employe": e, "cumul": cumul, "nb_mois": nb_mois})
        for k in cles:
            T[k] += cumul[k]

    html_string = render_to_string("paie/livre_annuel_pdf.html", {
        "employeur": employeur, "lignes": lignes, "totaux": T, "annee": annee,
    })
    base = request.build_absolute_uri("/") if request is not None else "http://127.0.0.1:8000/"
    return HTML(string=html_string, base_url=base).write_pdf()


def generer_pdf_recap_annuel(employe, annee, request=None):
    """Récapitulatif annuel complet d'un salarié : détail mensuel + congés + prêts."""
    from .models import BulletinPaie, Conge

    bulletins = list(BulletinPaie.objects.filter(employe=employe, annee=annee).order_by("mois"))
    lignes = []
    T = {"brut": 0.0, "its": 0.0, "cnps": 0.0, "cmu": 0.0, "net": 0.0}
    mois_noms = dict(BulletinPaie.MOIS_CHOICES)
    for b in bulletins:
        c = calculer_bulletin(b)
        ligne = {
            "mois_nom": mois_noms.get(b.mois, b.mois),
            "brut": c["total_gains"], "its": c["its_final"],
            "cnps": c["cnps_retraite_salarie"], "cmu": c["cmu_salarie"],
            "net": c["net_arrondi"],
        }
        lignes.append(ligne)
        T["brut"] += float(c["total_gains"]); T["its"] += float(c["its_final"])
        T["cnps"] += float(c["cnps_retraite_salarie"]); T["cmu"] += float(c["cmu_salarie"])
        T["net"] += float(c["net_arrondi"])

    conges = Conge.objects.filter(employe=employe, date_depart__year=annee).order_by("date_depart")
    prets = employe.prets.filter(date_debut__year=annee).prefetch_related("remboursements")

    html_string = render_to_string("paie/recap_annuel_pdf.html", {
        "employeur": employe.employeur, "employe": employe, "annee": annee,
        "lignes": lignes, "totaux": T, "conges": conges, "prets": prets,
    })
    base = request.build_absolute_uri("/") if request is not None else "http://127.0.0.1:8000/"
    return HTML(string=html_string, base_url=base).write_pdf()


def generer_pdf_justificatif_pret(pret, request=None):
    """Génère le PDF du justificatif / reconnaissance de dette pour un prêt."""
    employe = pret.employe
    employeur = employe.employeur
    html_string = render_to_string("paie/justificatif_pret_pdf.html", {
        "employeur": employeur,
        "employe": employe,
        "pret": pret,
    })
    base = request.build_absolute_uri("/") if request is not None else "http://127.0.0.1:8000/"
    return HTML(string=html_string, base_url=base).write_pdf()