SOUS_MODULES = [
    {"nom": "Documents à signer", "url": "/comptes/documents-a-signer/"},
    {"nom": "Ma signature", "url": "/comptes/signature/"},
    {"nom": "Signer un document", "url": "/comptes/signature/apposer/"},
]


def sous_modules_dynamiques(request):
    """Ajoute des entrées uniquement si l'utilisateur est concerné par une délégation active."""
    if not request.user.is_authenticated:
        return []

    from django.utils import timezone
    from .models import DelegationSignature

    aujourd_hui = timezone.now().date()
    entrees = []

    if DelegationSignature.objects.filter(
        delegataire=request.user, mode="ORDRE",
        date_debut__lte=aujourd_hui, date_fin__gte=aujourd_hui,
    ).exists():
        entrees.append({"nom": "Signature par ordre", "url": "/comptes/signature/ordre/"})

    if DelegationSignature.objects.filter(
        delegataire=request.user, mode="DELEGATION_POUVOIR",
        date_debut__lte=aujourd_hui, date_fin__gte=aujourd_hui,
    ).exists():
        entrees.append({"nom": "Signature par délégation de pouvoir", "url": "/comptes/signature/delegation/"})

    return entrees
