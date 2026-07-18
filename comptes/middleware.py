from django.contrib.auth import logout
from django.shortcuts import redirect
from django.utils import timezone


# Durée d'inactivité autorisée avant déconnexion automatique.
# 30 minutes = 30 * 60 secondes = 1800 secondes.
DUREE_INACTIVITE = 30 * 60


class DelaiInactiviteMiddleware:
    """Déconnecte automatiquement un utilisateur resté inactif trop longtemps.
    « Inactif » = aucune page chargée pendant la durée définie."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            maintenant = int(timezone.now().timestamp())
            derniere_activite = request.session.get("derniere_activite")

            if derniere_activite is not None and (maintenant - derniere_activite) > DUREE_INACTIVITE:
                logout(request)
                return redirect("login")

            request.session["derniere_activite"] = maintenant
            request.session.modified = True

        return self.get_response(request)