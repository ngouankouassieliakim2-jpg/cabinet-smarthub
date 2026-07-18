from django.template.loader import render_to_string
from django.core.files.base import ContentFile
from .pdf import generer_pdf_lettre_mission


def generer_lettre_mission(devis, request=None):
    """Génère la lettre de mission en PDF à partir d'un devis et la rattache au devis."""
    pdf_bytes = generer_pdf_lettre_mission(devis, request=request)
    nom_fichier = f"lettre_mission_{devis.numero_devis}.pdf"
    devis.lettre_mission_pdf.save(nom_fichier, ContentFile(pdf_bytes), save=True)
    return devis.lettre_mission_pdf

def transformer_devis_en_client(devis):
    """Crée un client à partir d'un devis, en récupérant la lettre de mission."""
    from clients.models import Client

    # 1. Générer la lettre de mission si elle n'existe pas encore
    if not devis.lettre_mission_pdf:
        generer_lettre_mission(devis)

    # 2. Créer le client relié à ce devis
    client = Client(devis_origine=devis, statut="EN_ATTENTE")

    # 3. Récupérer la lettre de mission du devis
    if devis.lettre_mission_pdf:
        client.lettre_mission = devis.lettre_mission_pdf

    client.save()

    # 4. Mettre à jour le statut du devis
    devis.statut = "TRANSFORME"
    devis.save()

    return client