"""Utilitaires communs à tous les documents PDF générés : référence unique
et QR code, pour la traçabilité de chaque document émis par le cabinet."""
import uuid
import base64
from io import BytesIO


def generer_reference_document(prefixe):
    """Génère une référence unique et lisible, ex : CTR-A1B2C3D4."""
    return f"{prefixe}-{uuid.uuid4().hex[:8].upper()}"


def generer_qr_code_data_uri(contenu):
    """Génère un QR code PNG à partir d'un texte, en data URI prêt à être
    intégré dans un template PDF (même technique que les signatures)."""
    import qrcode

    img = qrcode.make(contenu)
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")
