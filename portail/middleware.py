from django.shortcuts import redirect
from django.urls import reverse
from clients.models import Client


class ParcoursAccueilMiddleware:
    """Force les clients « en attente » à suivre le parcours de première connexion.
    Tant que le client n'est pas « actif », il est redirigé vers le parcours d'accueil."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            client = Client.objects.filter(compte=request.user).first()

            # Si c'est un client « en attente », on le force sur le parcours d'accueil
            if client and client.statut == "EN_ATTENTE":
                url_logout = reverse("logout")

                # On laisse passer : toutes les étapes du parcours + la déconnexion
                chemins_autorises = [
                    reverse("portail_premiere_connexion_mdp"),
                    reverse("portail_premiere_connexion_lettre"),
                    reverse("portail_premiere_connexion_cgv"),
                    url_logout,
                ]
                est_autorise = any(request.path.startswith(c) for c in chemins_autorises)
                est_statique = request.path.startswith("/static/") or request.path.startswith("/media/")

                if not est_autorise and not est_statique:
                    return redirect("portail_premiere_connexion_mdp")

        return self.get_response(request)