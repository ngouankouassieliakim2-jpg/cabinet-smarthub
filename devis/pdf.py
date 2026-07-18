from io import BytesIO
import base64
import os
from datetime import date
from django.template.loader import render_to_string
from weasyprint import HTML
from pypdf import PdfReader, PdfWriter

from parametres.models import PrestationCatalogue


def _construire_contexte_lettre_mission(devis):
    recurrentes, ponctuelles = [], []
    preavis_max = 0
    modalites_rec = ""
    modalites_ponc = ""

    for ligne in devis.lignes.all():
        presta = PrestationCatalogue.objects.filter(libelle=ligne.designation).first()
        cat = presta.categorie if presta else None
        info = {
            "libelle": ligne.designation,
            "periodicite": ligne.periodicite,
            "livrable": presta.livrable if presta else "",
            "delai": presta.delai_livraison if presta else "",
            "categorie": cat.nom if cat else "",
            "duree": cat.duree_engagement_mois if cat else None,
        }
        if cat and cat.regime == "PONCTUELLE":
            ponctuelles.append(info)
            if cat.modalites_paiement:
                modalites_ponc = cat.modalites_paiement
        elif cat and cat.regime == "RECURRENTE":
            recurrentes.append(info)
            if cat.preavis_mois and cat.preavis_mois > preavis_max:
                preavis_max = cat.preavis_mois
            if cat.modalites_paiement:
                modalites_rec = cat.modalites_paiement
        else:
            if (ligne.periodicite or "").lower().startswith("ponct"):
                ponctuelles.append(info)
            else:
                recurrentes.append(info)

    groupes_rec = {}
    for r in recurrentes:
        cle = r["categorie"] or "Suivi régulier"
        if cle not in groupes_rec:
            groupes_rec[cle] = {"nom": cle, "duree": r["duree"], "lignes": []}
        groupes_rec[cle]["lignes"].append(r)
    groupes_recurrents = list(groupes_rec.values())

    if devis.date_effet_mission:
        date_effet = devis.date_effet_mission
    else:
        today = date.today()
        if today.month == 12:
            date_effet = date(today.year + 1, 1, 1)
        else:
            date_effet = date(today.year, today.month + 1, 1)

    annexes = []
    for document in devis.documents.filter(statut="FOURNI").exclude(fichier__isnull=True).exclude(fichier__exact=""):
        annexes.append({
            "titre": document.get_type_document_display(),
            "description": document.libelle_libre or document.commentaire or os.path.basename(document.fichier.name),
        })

    return {
        "devis": devis,
        "groupes_recurrents": groupes_recurrents,
        "ponctuelles": ponctuelles,
        "a_recurrent": len(recurrentes) > 0,
        "a_ponctuel": len(ponctuelles) > 0,
        "date_effet": date_effet,
        "honoraires": devis.total_ttc,
        "preavis": preavis_max or 3,
        "modalites_rec": modalites_rec,
        "modalites_ponc": modalites_ponc,
        "annexes": annexes,
    }


def _collect_annex_pdf_paths(devis):
    chemins = []
    for document in devis.documents.filter(statut="FOURNI").exclude(fichier__isnull=True).exclude(fichier__exact=""):
        chemin = getattr(document.fichier, "path", None)
        if chemin and chemin.lower().endswith(".pdf") and os.path.exists(chemin):
            chemins.append(chemin)
    return chemins


def generer_pdf_devis(devis, request=None):
    """Génère le PDF du devis (devis + note) et retourne les bytes du PDF."""
    # On réutilise le template d'aperçu autonome du devis
    groupes = {}
    for ligne in devis.lignes.all():
        cle = ligne.periodicite or "Autres prestations"
        groupes.setdefault(cle, []).append(ligne)
    sections = []
    for periodicite, lignes in groupes.items():
        sous_total = sum(l.total_ht for l in lignes)
        sections.append({"titre": periodicite, "lignes": lignes, "sous_total": sous_total})

    html_string = render_to_string("devis/apercu_devis.html", {
        "devis": devis,
        "sections": sections,
    })

    # base_url permet à WeasyPrint de retrouver les images (logo) et le CSS
    if request is not None:
        base = request.build_absolute_uri("/")
    else:
        base = "http://127.0.0.1:8000/"

    pdf_bytes = HTML(string=html_string, base_url=base).write_pdf()
    return pdf_bytes


def generer_pdf_lettre_mission(devis, request=None):
    """Génère le PDF de la lettre de mission avec les annexes PDF fournies."""
    contexte = _construire_contexte_lettre_mission(devis)

    # Si la Direction a validé et possède une signature électronique enregistrée,
    # on l'intègre directement dans le HTML (en data URI, pour ne dépendre
    # d'aucune URL/serveur média au moment de la génération).
    if devis.lettre_validee_par_id:
        from comptes.models import SignatureElectronique
        sig = SignatureElectronique.objects.filter(
            utilisateur=devis.lettre_validee_par,
            est_active=True,
        ).first()
        if sig and sig.image:
            sig.image.open("rb")
            contenu_sig = sig.image.read()
            sig.image.close()
            contexte["signature_direction_data_uri"] = (
                "data:image/png;base64," + base64.b64encode(contenu_sig).decode("ascii"))

    base_url = request.build_absolute_uri("/") if request is not None else "http://127.0.0.1:8000/"
    html = render_to_string("devis/lettre_mission.html", contexte)
    pdf_bytes = HTML(string=html, base_url=base_url).write_pdf()

    annexes_pdf = _collect_annex_pdf_paths(devis)
    if not annexes_pdf:
        return pdf_bytes

    writer = PdfWriter()
    reader = PdfReader(BytesIO(pdf_bytes))
    for page in reader.pages:
        writer.add_page(page)

    for chemin in annexes_pdf:
        with open(chemin, "rb") as handle:
            annex_reader = PdfReader(handle)
            for page in annex_reader.pages:
                writer.add_page(page)

    sortie = BytesIO()
    writer.write(sortie)
    return sortie.getvalue()
