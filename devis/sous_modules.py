SOUS_MODULES = [
    {
        "nom": "Devis", "url": "/devis/",
        "fonctionnalites": [
            {"nom": "Nouveau devis", "url": "/devis/nouveau/"},
            {"nom": "Liste des devis", "url": "/devis/"},
        ],
    },
    {"nom": "Documents", "url": "/devis/documents/"},
    {"nom": "Facturation", "url": "/devis/facturation/"},
    {
        "nom": "Gestion des créances",
        "url": "/devis/creances/",
        "groupe": "Recouvrement",
    },
    {
        "nom": "Journal des paiements",
        "url": "devis:journal_paiements",
        "groupe": "Recouvrement",
    },
    {
        "nom": "Journal des actions",
        "url": "devis:journal_actions",
        "groupe": "Recouvrement",
    },
    {
        "nom": "Affectation en masse",
        "url": "devis:affectation_masse",
        "groupe": "Recouvrement",
    },
    {
        "nom": "Journal des relances",
        "url": "devis:journal_relances",
        "groupe": "Recouvrement",
    },
    {
        "nom": "Calendrier des relances",
        "url": "devis:calendrier_relances",
        "groupe": "Recouvrement",
    },
    {
        "nom": "Litiges",
        "url": "devis:liste_litiges",
        "groupe": "Recouvrement",
    },
    {
        "nom": "Litiges (Kanban)",
        "url": "devis:kanban_litiges",
        "groupe": "Recouvrement",
    },
    {
        "nom": "Créances (Kanban)",
        "url": "/devis/creances/kanban/",
        "groupe": "Recouvrement",
    },
    {
        "nom": "Mon portefeuille",
        "url": "/devis/creances/mon-portefeuille/",
        "groupe": "Recouvrement",
    },
    {
        "nom": "KPI global",
        "url": "/devis/creances/kpi/",
        "groupe": "Recouvrement",
    },
    {
        "nom": "KPI recouvreurs",
        "url": "/devis/creances/kpi-recouvreurs/",
        "groupe": "Recouvrement",
    },
    {
        "nom": "Fournisseurs",
        "url": "/devis/fournisseurs/",
        "groupe": "Dépenses",
    },
    {
        "nom": "Liste des dépenses",
        "url": "/devis/depenses/",
        "groupe": "Dépenses",
    },
    {
        "nom": "Nouvelle dépense",
        "url": "/devis/depenses/nouveau/",
        "groupe": "Dépenses",
    },
    {        "nom": "Prévisions de trésorerie",
        "url": "/devis/creances/previsions-tresorerie/",
        "groupe": "Recouvrement",
    },
    {
        "nom": "Configuration des relances",
        "url": "/devis/creances/relances/config/",
        "groupe": "Recouvrement",
    },
]
