SOUS_MODULES = [
    # ===================== DEVIS & FACTURATION =====================
    {
        "nom": "Devis", "url": "/devis/", "groupe": "Devis & Facturation",
        "fonctionnalites": [
            {"nom": "Nouveau devis", "url": "/devis/nouveau/"},
            {"nom": "Liste des devis", "url": "/devis/"},
        ],
    },
    {"nom": "Documents", "url": "/devis/documents/", "groupe": "Devis & Facturation"},
    {"nom": "Facturation", "url": "/devis/facturation/", "groupe": "Devis & Facturation"},

    # ===================== RECOUVREMENT =====================
    {"nom": "Gestion des créances", "url": "/devis/creances/", "groupe": "Recouvrement"},
    {"nom": "Créances (Kanban)", "url": "/devis/creances/kanban/", "groupe": "Recouvrement"},
    {"nom": "Mon portefeuille", "url": "/devis/creances/mon-portefeuille/", "groupe": "Recouvrement"},
    {"nom": "Journal des paiements", "url": "/devis/paiements/journal/", "groupe": "Recouvrement"},
    {"nom": "Journal des actions", "url": "/devis/actions-recouvrement/journal/", "groupe": "Recouvrement"},
    {"nom": "Affectation en masse", "url": "/devis/affectation-masse/", "groupe": "Recouvrement"},
    {"nom": "Litiges", "url": "/devis/litiges/", "groupe": "Recouvrement"},
    {"nom": "Litiges (Kanban)", "url": "/devis/litiges/kanban/", "groupe": "Recouvrement"},
    {"nom": "Calendrier des relances", "url": "/devis/relances/calendrier/", "groupe": "Recouvrement"},
    {"nom": "Journal des relances", "url": "/devis/relances/journal/", "groupe": "Recouvrement"},
    {"nom": "Configuration des relances", "url": "/devis/creances/relances/config/", "groupe": "Recouvrement"},
    {"nom": "Journal des automatisations", "url": "/devis/automatisations/journal/", "groupe": "Recouvrement"},
    {"nom": "Prévisions de trésorerie", "url": "/devis/creances/previsions-tresorerie/", "groupe": "Recouvrement"},
    {"nom": "KPI recouvrement", "url": "/devis/creances/kpi/", "groupe": "Recouvrement"},
    {"nom": "KPI recouvreurs", "url": "/devis/creances/kpi-recouvreurs/", "groupe": "Recouvrement"},

    # ===================== DÉPENSES =====================
    {"nom": "Fournisseurs", "url": "/devis/fournisseurs/", "groupe": "Dépenses"},
    {"nom": "Liste des dépenses", "url": "/devis/depenses/", "groupe": "Dépenses"},
    {"nom": "Nouvelle dépense", "url": "/devis/depenses/nouveau/", "groupe": "Dépenses"},
    {"nom": "Dépenses (Kanban)", "url": "/devis/depenses/kanban/", "groupe": "Dépenses"},
    {"nom": "Validation des dépenses", "url": "/devis/depenses/validation/file-attente/", "groupe": "Dépenses"},
    {"nom": "Seuils d'approbation", "url": "/devis/depenses/seuils/", "groupe": "Dépenses"},
    {"nom": "Budgets", "url": "/devis/budgets/", "groupe": "Dépenses"},
    {"nom": "Budgets — Dashboard", "url": "/devis/budgets/dashboard/", "groupe": "Dépenses"},
    {"nom": "Dépenses récurrentes", "url": "/devis/depenses/recurrentes/", "groupe": "Dépenses"},
    {"nom": "Notes de frais", "url": "/devis/notes-de-frais/", "groupe": "Dépenses"},
    {"nom": "KPI Dépenses", "url": "/devis/kpi-depenses/", "groupe": "Dépenses"},

    # ===================== DASHBOARD EXÉCUTIF (manquait totalement) =====================
    {"nom": "Dashboard exécutif", "url": "/devis/dashboard/", "groupe": "Recouvrement"},
]
