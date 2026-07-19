from .modules_data import MODULES, charger_sous_modules


def navigation(request):
    """Injecte la barre du haut (modules) sur toutes les pages, filtrée
    selon le pôle de l'utilisateur connecté."""
    if not request.user.is_authenticated:
        return {"modules_nav_auto": []}

    from comptes.models import Profil
    from .modules_data import modules_visibles_pour

    profil = getattr(request.user, "profil", None)
    role = profil.role if profil else None
    cles_visibles = modules_visibles_pour(request.user)

    modules_nav = []
    for cle, data in MODULES.items():
        if cle == "outils":
            pass  # toujours visible pour tout le personnel interne
        elif cle == "parametres":
            if role not in (Profil.Role.DIRECTION, Profil.Role.CADRE):
                continue
        elif cle not in cles_visibles:
            continue
        modules_nav.append({
            "cle": cle, "nom": data["nom"], "icone": data["icone"],
            "url": f"/pilotage/module/{cle}/",
        })
    return {"modules_nav_auto": modules_nav}


def notifications_non_lues(request):
    """Injecte le nombre de notifications non lues sur toutes les pages."""
    if not request.user.is_authenticated:
        return {}
    from .models import Notification
    return {"nb_notifications_non_lues": Notification.objects.filter(lue=False).count()}