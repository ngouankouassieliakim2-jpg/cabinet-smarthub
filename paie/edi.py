"""Génération du fichier XML EDI ITS pour e-impot (format DGI)."""
from decimal import Decimal
from .models import BulletinPaie
from .calculs import calculer_bulletin


def _num(valeur, decimales=False):
    """Format DGI : entier brut, ou virgule décimale française (2 décimales)."""
    v = Decimal(str(valeur or 0))
    if decimales:
        return f"{v:.2f}".replace(".", ",")
    return str(int(v.quantize(Decimal("1"))))


def _situation(code):
    m = {"celibataire": "C", "marie": "M", "veuf": "V", "divorce": "D"}
    return m.get((code or "").lower(), "C")


def _indemnites_exonerees(e, bulletins):
    """Somme des parts exonérées (transport sous plafond + rubriques exonérées/plafonnées) + libellés."""
    employeur = e.employeur
    plafond_transport = Decimal(str(getattr(employeur, "plafond_transport_exonere", 0) or 30000))
    total = Decimal("0")
    designations = []
    seen = set()
    for b in bulletins:
        transport = Decimal(str(b.prime_transport or 0))
        if transport > 0:
            total += min(transport, plafond_transport)
            if "TRANSPORT" not in seen:
                designations.append("TRANSPORT"); seen.add("TRANSPORT")
    for rr in e.rubriques_recurrentes.select_related("rubrique").all():
        montant = Decimal(str(rr.montant or 0))
        t = rr.rubrique.traitement_fiscal
        if t == "exonere":
            part = montant
        elif t == "plafonne":
            part = min(montant, Decimal(str(getattr(rr.rubrique, "plafond_exoneration", 0) or 0)))
        else:
            part = Decimal("0")
        if part > 0:
            total += part * len(bulletins)
            lib = (rr.rubrique.libelle or "").upper()
            if lib not in seen:
                designations.append(lib); seen.add(lib)
    return total, " + ".join(designations)


def _champs_salarie(e, parts, jours, total_gains, brut_fiscal, ricf, its, indemnites_exo, designation):
    emploi_lib = ""; code_emploi = ""
    if getattr(e, "emploi_ref", None):
        emploi_lib = (e.emploi_ref.libelle or "").upper()
        code_emploi = e.emploi_ref.code or ""
    expatrie = getattr(e, "regime", "general") == "expatrie"
    sexe = "F" if (e.sexe or "").upper().startswith("F") else "M"
    return [
        ("numero_cnps", e.numero_cnps or "0"),
        ("identite", (e.nom_prenoms or "").upper()),
        ("emploi_qualite", emploi_lib),
        ("code_emploi", code_emploi),
        ("regime_general", "G"),
        ("sexe", sexe),
        ("nationalite", "E" if expatrie else "I"),
        ("loc_exp", "E" if expatrie else "L"),
        ("situation_famille", _situation(e.situation_matrimoniale)),
        ("nbre_enfants_charge_nat_cas", str(int(e.nombre_enfants or 0))),
        ("nbre_parts_igr", _num(parts, decimales=True)),
        ("nbre_jours_app_paiements", _num(jours)),
        ("mnt_sala_remune_acs", _num(Decimal(str(total_gains)) - Decimal(str(indemnites_exo)))),
        ("mnt_avtgs_nat_reglm", "0"),
        ("mnt_avtgs_nat_reele", "0"),
        ("sal_ttl_brut", _num(brut_fiscal)),
        ("rev_non_imposable", "0"),
        ("rev_brut_imposable", _num(brut_fiscal)),
        ("ricf", _num(ricf)),
        ("its_sal_brut", _num(its, decimales=True)),
        ("its_sal_net", "0"),
        ("ajustement", "0"),
        ("its_net_a_payer", _num(its, decimales=True)),
        ("mnt_indemnites", _num(indemnites_exo)),
        ("designation_indemnites", designation),
    ]


def _ligne(champs):
    blocs = "".join(f"<champ><code>{c}</code><valeur>{v}</valeur></champ>" for c, v in champs)
    return f"<ligne>{blocs}</ligne>"


def _ligne_salarie(bulletin):
    e = bulletin.employe
    c = calculer_bulletin(bulletin)
    indemnites_exo, designation = _indemnites_exonerees(e, [bulletin])
    champs = _champs_salarie(e, c["parts_igr"], bulletin.jours_travailles,
                             c["total_gains"], c["brut_fiscal"], c["ricf"], c["its_final"],
                             indemnites_exo, designation)
    return _ligne(champs)


def _ligne_salarie_cumul(bulletins):
    dernier = bulletins[-1]
    e = dernier.employe
    total_gains = Decimal("0"); brut_fiscal = Decimal("0"); ricf = Decimal("0")
    its = Decimal("0"); jours = Decimal("0")
    for b in bulletins:
        c = calculer_bulletin(b)
        total_gains += Decimal(str(c["total_gains"]))
        brut_fiscal += Decimal(str(c["brut_fiscal"]))
        ricf += Decimal(str(c["ricf"]))
        its += Decimal(str(c["its_final"]))
        jours += Decimal(str(b.jours_travailles or 0))
    indemnites_exo, designation = _indemnites_exonerees(e, bulletins)
    c_ref = calculer_bulletin(dernier)
    champs = _champs_salarie(e, c_ref["parts_igr"], jours, total_gains, brut_fiscal, ricf, its,
                             indemnites_exo, designation)
    return _ligne(champs)


def generer_edi_its(employeur, mois, annee, type_edi="etat_301_mensuel"):
    """type_edi='etat_301_mensuel' (mois) ou 'etat_301' (annuel)."""
    ncc = employeur.ncc or ""

    if type_edi == "etat_301":
        code_taxe = "ETATITSREG"
        employe_ids = (BulletinPaie.objects.filter(employe__employeur=employeur, annee=annee)
                       .values_list("employe_id", flat=True).distinct())
        lignes_list = []
        for eid in employe_ids:
            bulletins = list(BulletinPaie.objects.filter(employe_id=eid, annee=annee)
                             .select_related("employe").order_by("mois"))
            if bulletins:
                lignes_list.append(_ligne_salarie_cumul(bulletins))
        lignes = "\r\n".join(lignes_list)
    else:
        code_taxe = "ITS"
        bulletins = (BulletinPaie.objects.filter(employe__employeur=employeur, mois=mois, annee=annee)
                     .select_related("employe").order_by("employe__nom_prenoms"))
        lignes = "\r\n".join(_ligne_salarie(b) for b in bulletins)

    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<EDI><informations>'
        f'<type>{type_edi}</type>'
        f'<ncc>{ncc}</ncc>'
        f'<codeTaxe>{code_taxe}</codeTaxe>'
        f'<mois>{mois}</mois>'
        f'<exercice>{annee}</exercice>'
        '</informations><tableaux><tableau><donnees>\r\n'
        f'{lignes}'
        '\r\n</donnees></tableau></tableaux></EDI>\r\n'
    )