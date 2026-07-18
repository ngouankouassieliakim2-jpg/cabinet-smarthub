from django.contrib.auth.decorators import login_required
from django.shortcuts import render


def get_collaborateur_module_actif():
    return {
        "cle": "collaborateur",
        "nom": "Espace Collaborateur",
        "icone": "👥",
        "description": "Accès aux dossiers, missions et échanges internes.",
    }


@login_required
def accueil(request):
    """Accueil de l'interface Collaborateur (coquille niveau 3)."""
    return render(request, "collaborateurs/accueil.html", {
        "module_actif": get_collaborateur_module_actif(),
    })