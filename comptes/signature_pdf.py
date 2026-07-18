"""Prépare la signature à intégrer dans un document PDF généré."""
import base64
from django.utils import timezone

from .models import DelegationSignature, SignatureElectronique


def resoudre_signataire(utilisateur):
    """Retourne le régime réel d'apposition de signature pour l'utilisateur."""
    if not utilisateur:
        return {"mode": "AUCUNE"}

    aujourd_hui = timezone.now().date()
    delegations = DelegationSignature.objects.filter(
        delegataire=utilisateur,
        est_active=True,
        date_debut__lte=aujourd_hui,
        date_fin__gte=aujourd_hui,
    ).select_related("delegant").order_by("date_debut")

    if delegations.exists():
        delegation = delegations.first()
        return {
            "mode": delegation.mode,
            "image_de": delegation.delegant,
            "pour_compte_de": delegation.delegant,
        }

    return {"mode": "PROPRE", "image_de": utilisateur}


def preparer_signature_pdf(utilisateur):
    """Retourne (signature_data_uri, mention) à injecter dans un contexte de template."""
    if not utilisateur:
        return None, None

    resolution = resoudre_signataire(utilisateur)
    if resolution["mode"] == "AUCUNE":
        return None, None

    sig = SignatureElectronique.objects.filter(
        utilisateur=resolution["image_de"],
        est_active=True,
    ).first()
    if not sig or not sig.image:
        return None, None

    sig.image.open("rb")
    contenu = sig.image.read()
    sig.image.close()
    data_uri = "data:image/png;base64," + base64.b64encode(contenu).decode("ascii")

    mention = None
    if resolution["mode"] == "ORDRE":
        nom = resolution["pour_compte_de"].get_full_name() or resolution["pour_compte_de"].username
        mention = f"Par ordre de {nom}"
    elif resolution["mode"] == "DELEGATION_POUVOIR":
        nom = resolution["pour_compte_de"].get_full_name() or resolution["pour_compte_de"].username
        mention = f"Par délégation de pouvoir de {nom}"

    return data_uri, mention
