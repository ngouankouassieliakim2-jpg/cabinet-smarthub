from .modules_data import MODULES, charger_sous_modules


def navigation(request):
    """Injecte la barre du haut (modules) dans toutes les pages automatiquement."""
    modules_nav = [{"cle": "dashboard", "nom": "Tableau de bord", "icone": "🏠", "url": "/pilotage/"}]
    for cle, data in MODULES.items():
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