# Les 10 modules + Paramètres : définition LÉGÈRE.
# "app" = nom du module Python qui déclare ses sous-modules (fichier <app>/sous_modules.py).
# Si l'app n'a pas ce fichier → coquille vide ("à venir au branchement").

MODULES = {
    "direction":     {"nom": "Direction",                "icone": "🏛️", "app": "pilotage", "description": "Pilotage stratégique du cabinet."},
    "secretariat":   {"nom": "Secrétariat",              "icone": "📅", "app": "secretariat", "description": "Gestion documentaire, courriers et dossiers."},
    "recouvrement":  {"nom": "Recouvrement & Dépenses",  "icone": "📄", "app": "devis", "description": "Suivi du portefeuille clients et des encaissements."},
    "social-rh":     {"nom": "Social & RH",              "icone": "👥", "app": "paie", "description": "Gestion des salariés, paie et obligations sociales."},
    "comptabilite":  {"nom": "Comptabilité & Fiscalité", "icone": "📊", "app": "comptabilite", "description": "Production comptable, TVA et états financiers."},
    "formation":     {"nom": "Formation & Conseil",      "icone": "🎓", "app": "formation", "description": "Accompagnement, formation et montée en compétences."},
    "marketing":     {"nom": "Marketing & Image",        "icone": "📣", "app": "actualites", "description": "Visibilité, communication et image de marque."},
    "logistique":    {"nom": "Logistique & Livraison",   "icone": "🚚", "app": "logistique", "description": "Optimisation des flux et suivi des livraisons."},
    "outils":        {"nom": "Outils",                    "icone": "🛠️", "app": "comptes"},
    "parametres":    {"nom": "Paramètres",               "icone": "⚙️", "app": "parametres", "description": "Configuration globale et accès aux réglages."},
}


def charger_sous_modules(nom_app, request=None):
    """
    Cherche un fichier <app>/sous_modules.py qui contient une liste SOUS_MODULES.
    Retourne la liste si elle existe, sinon une liste vide (module pas encore branché).
    """
    import importlib
    try:
        module = importlib.import_module(f"{nom_app}.sous_modules")
    except ModuleNotFoundError:
        return []
    except Exception:
        return []
    sous_modules = list(getattr(module, "SOUS_MODULES", []))
    fonction_dynamique = getattr(module, "sous_modules_dynamiques", None)
    if fonction_dynamique and request is not None:
        try:
            sous_modules = sous_modules + fonction_dynamique(request)
        except Exception:
            pass

    # Marque comme "actif" le sous-module de la page actuelle, y compris ses
    # pages filles (ex: /postes/nouveau/ reste actif pour /postes/) -- sauf
    # pour une URL racine générique (comme /pilotage/ tout seul), qui ne doit
    # matcher qu'exactement, sinon elle capterait toutes les autres pages.
    if request is not None:
        chemin = request.path
        for sm in sous_modules:
            url_sm = sm.get("url", "")
            if not url_sm:
                sm["actif"] = False
            elif chemin == url_sm:
                sm["actif"] = True
            elif url_sm.rstrip("/").count("/") <= 1:
                sm["actif"] = False
            else:
                sm["actif"] = chemin.startswith(url_sm)

    return sous_modules


def get_module_info(cle):
    """Retourne les données du module actif ou None si le module est introuvable."""
    data = MODULES.get(cle)
    if not data:
        return None
    return {"cle": cle, **data}


def arbre_permissions():
    """Module -> Sous-modules -> Fonctionnalités (si déclarées), pour l'écran Pôles."""
    arbre = []
    for cle, data in MODULES.items():
        if cle in ("outils", "parametres"):
            continue
        arbre.append({
            "cle": cle, "nom": data["nom"], "icone": data["icone"],
            "sous_modules": charger_sous_modules(data["app"]),
        })
    return arbre


def modules_visibles_pour(user):
    """Clés des modules métier visibles pour cet utilisateur, selon son rôle et son pôle.
    Direction/Cadre voient tout. Un Collaborateur ne voit que les modules de son pôle
    (accès complet), plus tout module dont il n'a qu'un sous-module ou une
    fonctionnalité précise (pour pouvoir seulement y naviguer)."""
    from comptes.models import Profil
    profil = getattr(user, "profil", None)
    if not profil:
        return []
    if profil.role in (Profil.Role.DIRECTION, Profil.Role.CADRE):
        return list(MODULES.keys())

    pole = profil.pole
    if not pole:
        return []

    visibles = set(pole.modules_ids)
    for module in arbre_permissions():
        if module["cle"] in visibles:
            continue
        for sm in module["sous_modules"]:
            if sm["url"] in pole.sous_modules_urls:
                visibles.add(module["cle"])
                break
            if any(f["url"] in pole.fonctionnalites_urls for f in sm.get("fonctionnalites", [])):
                visibles.add(module["cle"])
                break
    return list(visibles)
