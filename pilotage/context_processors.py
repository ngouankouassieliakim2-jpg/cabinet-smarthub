from .modules_data import MODULES, charger_sous_modules


def sous_modules_auto(request):
    """Injecte automatiquement les sous-modules de la sidebar, déduits du
    namespace de l'app courante (ex: 'devis') — évite d'oublier cette clé
    dans chaque vue. Une vue peut toujours la surcharger explicitement en
    la passant elle-même dans son contexte (elle aura priorité)."""
    if not request.user.is_authenticated:
        return {}
    resolver_match = getattr(request, "resolver_match", None)
    app_name = resolver_match.app_name if resolver_match else None
    if not app_name:
        return {}
    from .modules_data import charger_sous_modules
    return {"sous_modules": charger_sous_modules(app_name, request)}


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

    modules_nav = [{"cle": "dashboard", "nom": "Tableau de bord", "icone": "🏠", "url": "/pilotage/"}]
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
    """Injecte le nombre de notifications non lues sur toutes les pages,
    filtré selon le rôle (même règle que notifications_liste)."""
    if not request.user.is_authenticated:
        return {}
    from django.db.models import Q
    from comptes.models import Profil
    from .models import Notification

    profil = getattr(request.user, "profil", None)
    est_direction_cadre = profil and profil.role in (Profil.Role.DIRECTION, Profil.Role.CADRE)

    if est_direction_cadre:
        count = Notification.objects.filter(lue=False).count()
    else:
        count = Notification.objects.filter(
            Q(destinataire=request.user) | Q(destinataire__isnull=True), lue=False
        ).count()

    return {"nb_notifications_non_lues": count}