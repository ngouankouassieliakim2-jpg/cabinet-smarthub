from django.utils import timezone


class PresenceMiddleware:
    """Met à jour la dernière activité de l'utilisateur connecté à chaque
    requête -- sert à calculer 'En ligne' / 'Vu il y a...' dans la Messagerie."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.user.is_authenticated:
            profil = getattr(request.user, "profil", None)
            if profil:
                type(profil).objects.filter(pk=profil.pk).update(
                    derniere_activite=timezone.now()
                )
        return response
