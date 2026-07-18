"""Génération des attestations et certificats (PDF) à partir de la fiche salarié."""
from datetime import date
from django.template.loader import render_to_string
from weasyprint import HTML


MOIS_FR = ["", "janvier", "février", "mars", "avril", "mai", "juin",
           "juillet", "août", "septembre", "octobre", "novembre", "décembre"]


def _date_longue(d):
    if not d:
        return "—"
    return f"{d.day} {MOIS_FR[d.month]} {d.year}"


def _contexte_commun(employe):
    employeur = employe.employeur
    civ = (employe.civilite or "").strip()
    return {
        "employeur": employeur,
        "employe": employe,
        "civilite": civ or "M./Mme",
        "nom": employe.nom_prenoms or "",
        "emploi": (employe.emploi_ref.libelle if getattr(employe, "emploi_ref", None) else "") or "—",
        "date_entree_longue": _date_longue(employe.date_entree),
        "date_sortie_longue": _date_longue(employe.date_sortie),
        "date_jour_longue": _date_longue(date.today()),
        "lieu": getattr(employeur, "commune", "") or "___",
    }


def generer_attestation(employe, type_doc, request=None, conge=None, utilisateur_signataire=None):
    """type_doc : 'travail', 'certificat', 'conge'. conge = dict {debut, fin} pour l'attestation de congé."""
    ctx = _contexte_commun(employe)
    ctx["type_doc"] = type_doc
    if type_doc == "travail":
        ctx["titre"] = "ATTESTATION DE TRAVAIL"
    elif type_doc == "certificat":
        ctx["titre"] = "CERTIFICAT DE TRAVAIL"
    elif type_doc == "conge":
        ctx["titre"] = "ATTESTATION DE CONGÉ"
        ctx["conge_debut"] = _date_longue(conge["debut"]) if conge else "—"
        ctx["conge_fin"] = _date_longue(conge["fin"]) if conge else "—"

    from comptes.signature_pdf import preparer_signature_pdf
    from .documents_utils import generer_reference_document, generer_qr_code_data_uri
    signature_data_uri, mention_signature = preparer_signature_pdf(utilisateur_signataire)
    reference = generer_reference_document("ATT")
    qr_data_uri = generer_qr_code_data_uri(f"Cabinet Smart-Hub — {ctx['titre']} {reference} — {employe.nom_prenoms}")
    ctx["signature_data_uri"] = signature_data_uri
    ctx["mention_signature"] = mention_signature
    ctx["reference"] = reference
    ctx["qr_data_uri"] = qr_data_uri
    html_string = render_to_string("paie/attestation_pdf.html", ctx)
    base = request.build_absolute_uri("/") if request is not None else "http://127.0.0.1:8000/"
    return HTML(string=html_string, base_url=base).write_pdf()