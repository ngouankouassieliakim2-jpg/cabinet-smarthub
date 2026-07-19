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
    Format attendu dans <app>/sous_modules.py :
        SOUS_MODULES = [
            {"nom": "Devis", "url": "/devis/"},
            ...
        ]
    """
    import importlib
    try:
        module = importlib.import_module(f"{nom_app}.sous_modules")
    except ModuleNotFoundError:
        return []
    except Exception:
        return []

    sous_modules = list(getattr(module, "SOUS_MODULES", []))

    # Extension optionnelle : un module peut définir sous_modules_dynamiques(request)
    # pour ajouter des entrées propres à l'utilisateur connecté (ex : délégations
    # actives). Si cette fonction n'existe pas, ce mécanisme est simplement
    # ignoré -- 100% rétrocompatible avec tous les modules existants.
    fonction_dynamique = getattr(module, "sous_modules_dynamiques", None)
    if fonction_dynamique and request is not None:
        try:
            sous_modules = sous_modules + fonction_dynamique(request)
        except Exception:
            pass

    return sous_modules


def get_module_info(cle):
    """Retourne les données du module actif ou None si le module est introuvable."""
    data = MODULES.get(cle)
    if not data:
        return None
    return {"cle": cle, **data}