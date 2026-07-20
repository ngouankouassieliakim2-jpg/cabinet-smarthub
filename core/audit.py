from .models import JournalAudit


def _get_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def journaliser(request, action, objet=None, description=""):
    """À appeler explicitement dans les vues sur les actions notables."""
    JournalAudit.objects.create(
        utilisateur=request.user if request.user.is_authenticated else None,
        action=action,
        description=description[:255],
        objet=objet,
        adresse_ip=_get_ip(request),
    )
