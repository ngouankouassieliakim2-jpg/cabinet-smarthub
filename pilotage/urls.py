from django.urls import path
from . import views

urlpatterns = [
    path("", views.tableau_bord, name="tableau_bord"),
    path("module/<str:cle>/", views.page_module, name="page_module"),
    path("notifications/", views.notifications_liste, name="pilotage_notifications"),
    path("notifications/<int:notification_id>/lue/", views.notification_marquer_lue, name="pilotage_notification_lue"),
    path("notifications/<int:notification_id>/supprimer/", views.notification_supprimer, name="pilotage_notification_supprimer"),
    path("delegations/", views.delegations_liste, name="pilotage_delegations_liste"),
    path("delegations/nouvelle/", views.delegation_creer, name="pilotage_delegation_creer"),
    path("collaborateurs/", views.collaborateurs_liste, name="pilotage_collaborateurs_liste"),
    path("collaborateurs/nouveau/", views.collaborateur_creer, name="pilotage_collaborateur_creer"),
    path("collaborateurs/<int:profil_id>/modifier/", views.collaborateur_modifier, name="pilotage_collaborateur_modifier"),
    path("poles/", views.poles_liste, name="pilotage_poles_liste"),
    path("poles/nouveau/", views.pole_creer, name="pilotage_pole_creer"),
    path("poles/<int:pole_id>/modifier/", views.pole_modifier, name="pilotage_pole_modifier"),
    path("poles/<int:pole_id>/supprimer/", views.pole_supprimer, name="pilotage_pole_supprimer"),
    path("postes/", views.postes_liste, name="pilotage_postes_liste"),
    path("postes/nouveau/", views.poste_creer, name="pilotage_poste_creer"),
    path("postes/<int:poste_id>/modifier/", views.poste_modifier, name="pilotage_poste_modifier"),
    path("postes/<int:poste_id>/supprimer/", views.poste_supprimer, name="pilotage_poste_supprimer"),
    path("organigramme/", views.organigramme, name="pilotage_organigramme"),
    path("lettres-a-valider/", views.lettres_a_valider, name="pilotage_lettres_a_valider"),
    path("lettres-a-valider/<int:devis_id>/", views.lettre_validation_detail, name="pilotage_lettre_validation_detail"),
]