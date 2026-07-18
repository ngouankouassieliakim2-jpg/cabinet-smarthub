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
    path("lettres-a-valider/", views.lettres_a_valider, name="pilotage_lettres_a_valider"),
    path("lettres-a-valider/<int:devis_id>/", views.lettre_validation_detail, name="pilotage_lettre_validation_detail"),
]