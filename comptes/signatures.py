"""
Extraction d'une signature manuscrite depuis une photo/scan sur papier blanc.
Technique : détourage par luminance — les pixels sombres (encre) deviennent
opaques, les pixels clairs (papier) deviennent transparents, avec un léger
lissage pour absorber le bruit/grain d'une photo prise au téléphone.
"""
from io import BytesIO
from PIL import Image, ImageFilter


def extraire_signature(image_bytes, seuil=195, purete=False):
    """Prend les octets d'une photo de signature manuscrite sur fond clair,
    retire l'arrière-plan et retourne une image PIL RGBA (fond transparent),
    recadrée sur le tracé. `seuil` (0-255) : plus il est bas, plus seuls les
    traits très sombres sont conservés. `purete` : traits pleinement opaques
    et plus contrastés, au lieu d'un dégradé doux sur les bords."""
    img = Image.open(BytesIO(image_bytes)).convert("RGB")
    gris = img.convert("L")

    # Léger flou avant seuillage pour absorber le bruit/grain de la photo
    gris_lisse = gris.filter(ImageFilter.GaussianBlur(radius=0.6))
    masque = gris_lisse.point(lambda p: 255 if p < seuil else 0)

    flou_bords = 0.5 if purete else 1.2
    masque = masque.filter(ImageFilter.GaussianBlur(radius=flou_bords))

    if purete:
        # Repousse le masque vers du tout-ou-rien : un trait plein plutôt qu'un dégradé.
        masque = masque.point(lambda p: 255 if p > 110 else 0)

    img_rgba = img.convert("RGBA")
    img_rgba.putalpha(masque)

    if purete:
        # Fonce et sature l'encre elle-même (sans changer sa teinte).
        from PIL import ImageEnhance
        r, g, b, a = img_rgba.split()
        rgb_fonce = Image.merge("RGB", (r, g, b))
        rgb_fonce = ImageEnhance.Contrast(rgb_fonce).enhance(1.6)
        rgb_fonce = ImageEnhance.Color(rgb_fonce).enhance(1.3)
        r2, g2, b2 = rgb_fonce.split()
        img_rgba = Image.merge("RGBA", (r2, g2, b2, a))

    # Recadrage automatique sur le contenu visible (retire la marge blanche)
    bbox = img_rgba.getbbox()
    if bbox:
        img_rgba = img_rgba.crop(bbox)

    return img_rgba


def signature_vers_png_bytes(image_rgba):
    """Convertit une image PIL RGBA en octets PNG (prêts à sauvegarder ou encoder)."""
    buffer = BytesIO()
    image_rgba.save(buffer, format="PNG")
    return buffer.getvalue()
