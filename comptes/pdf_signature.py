from datetime import datetime
from io import BytesIO

from PIL import Image
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from pypdf import PdfReader, PdfWriter

POSITIONS_DISPONIBLES = [
    ("bas_droite", "Bas à droite"),
    ("bas_gauche", "Bas à gauche"),
    ("bas_centre", "Bas au centre"),
    ("haut_droite", "Haut à droite"),
    ("haut_gauche", "Haut à gauche"),
]


def apposer_signature_sur_pdf(original_pdf_bytes, signature_png_bytes, nom_signataire,
                               numero_page=1, centre_x_pt=None, centre_y_pt=None,
                               position="bas_droite", largeur_mm=45):
    """Appose une signature PNG transparente sur une page choisie d'un PDF.

    Deux façons de choisir l'emplacement :
    - centre_x_pt / centre_y_pt : position précise (en points PDF, origine
      bas-gauche de la page), typiquement issue d'un glisser-déposer côté
      utilisateur -- a priorité si fournie ;
    - position : l'un des 5 préréglages, utilisé en repli si aucune
      coordonnée précise n'est fournie.
    `numero_page` en 1-indexé, -1 = dernière page."""
    reader = PdfReader(BytesIO(original_pdf_bytes))
    nb_pages = len(reader.pages)

    if numero_page < 0:
        index_page = nb_pages + numero_page
    else:
        index_page = numero_page - 1
    if index_page < 0 or index_page >= nb_pages:
        raise ValueError(f"Page {numero_page} invalide -- ce document a {nb_pages} page(s).")

    page_cible = reader.pages[index_page]
    page_width = float(page_cible.mediabox.width)
    page_height = float(page_cible.mediabox.height)

    signature_image = Image.open(BytesIO(signature_png_bytes)).convert("RGBA")
    rapport = signature_image.height / signature_image.width
    largeur_pt = largeur_mm * mm
    hauteur_pt = largeur_pt * rapport

    if centre_x_pt is not None and centre_y_pt is not None:
        x = float(centre_x_pt) - largeur_pt / 2
        y = float(centre_y_pt) - hauteur_pt / 2
        x = max(2 * mm, min(x, page_width - largeur_pt - 2 * mm))
        y = max(2 * mm, min(y, page_height - hauteur_pt - 2 * mm))
    else:
        marge = 15 * mm
        hauteur_legende = 24
        positions = {
            "bas_droite": (page_width - largeur_pt - marge, marge + hauteur_legende),
            "bas_gauche": (marge, marge + hauteur_legende),
            "bas_centre": ((page_width - largeur_pt) / 2, marge + hauteur_legende),
            "haut_droite": (page_width - largeur_pt - marge, page_height - hauteur_pt - marge),
            "haut_gauche": (marge, page_height - hauteur_pt - marge),
        }
        x, y = positions.get(position, positions["bas_droite"])

    overlay_buffer = BytesIO()
    canvas_pdf = canvas.Canvas(overlay_buffer, pagesize=(page_width, page_height))
    canvas_pdf.drawImage(ImageReader(signature_image), x, y, width=largeur_pt, height=hauteur_pt, mask="auto")
    date_signature = datetime.now().strftime("%d/%m/%Y à %H:%M")
    canvas_pdf.setFont("Helvetica", 8)
    canvas_pdf.drawString(x, max(2, y - 12), f"Signé électroniquement par {nom_signataire}")
    canvas_pdf.drawString(x, max(2, y - 22), f"le {date_signature}")
    canvas_pdf.save()
    overlay_buffer.seek(0)

    overlay_page = PdfReader(overlay_buffer).pages[0]
    page_cible.merge_page(overlay_page)

    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)

    output = BytesIO()
    writer.write(output)
    return output.getvalue()
