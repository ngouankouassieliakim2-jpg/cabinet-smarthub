from django.urls import path
from . import views

urlpatterns = [
    path("agenda/", views.agenda, name="secretariat_agenda"),
    path("demandes/", views.demandes, name="secretariat_demandes"),
    path("demandes/<int:demande_id>/", views.demande_detail, name="secretariat_demande_detail"),
    path("appels/", views.appels, name="secretariat_appels"),
    path("appels/<int:appel_id>/statut/", views.appel_statut, name="secretariat_appel_statut"),
    path("accueil/", views.accueil, name="secretariat_accueil"),
    path("courrier/", views.courrier, name="secretariat_courrier"),
    path("porte-entree/", views.porte_entree, name="secretariat_porte_entree"),
    path("porte-entree/<int:devis_id>/", views.porte_entree_detail, name="secretariat_porte_entree_detail"),
    path("porte-entree/<int:devis_id>/soumettre/", views.porte_entree_soumettre, name="secretariat_porte_entree_soumettre"),
    path("dossiers/", views.dossiers, name="secretariat_dossiers"),
    path("dossiers/<int:devis_id>/configurer/", views.dossier_config, name="secretariat_dossier_config"),
    path("dossiers/<int:client_id>/activer/", views.dossier_activer, name="secretariat_dossier_activer"),
]