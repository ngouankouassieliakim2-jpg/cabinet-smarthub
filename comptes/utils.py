from django.core.exceptions import PermissionDenied


def user_can_access_client(user, client):
    """Raise PermissionDenied unless the user is allowed to access this client."""
    if client is None:
        return

    if client.compte is None:
        return

    if client.compte != user:
        raise PermissionDenied("Vous n'êtes pas autorisé à accéder à ce dossier client.")
