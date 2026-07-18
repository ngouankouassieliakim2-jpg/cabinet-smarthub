from django.urls import path
from . import views

urlpatterns = [
    path("", views.liste_devis, name="liste_devis"),
    path("nouveau/", views.creer_devis, name="creer_devis"),
    path("<int:devis_id>/", views.detail_devis, name="detail_devis"),
    path("<int:devis_id>/modifier/", views.modifier_devis, name="modifier_devis"),
    path("<int:devis_id>/apercu/", views.apercu_devis, name="apercu_devis"),
    path("<int:devis_id>/generer-note/", views.generer_note, name="generer_note"),
    path("<int:devis_id>/note/", views.apercu_note, name="apercu_note"),
    path("<int:devis_id>/etape-2/", views.devis_etape2, name="devis_etape2"),
    path("<int:devis_id>/etape-3/", views.devis_etape3, name="devis_etape3"),
    path("<int:devis_id>/etape-4/", views.devis_etape4, name="devis_etape4"),
    path("<int:devis_id>/rapport-analyse/", views.rapport_analyse, name="rapport_analyse"),
    path("supprimer-selection/", views.supprimer_devis_multiple, name="supprimer_devis_multiple"),
    path("<int:devis_id>/lettre-mission/", views.lettre_mission, name="lettre_mission"),
    path("<int:devis_id>/etape-5/", views.devis_etape5, name="devis_etape5"),
    path("<int:devis_id>/valider-lettre/", views.valider_et_lettre, name="valider_et_lettre"),
    path("<int:devis_id>/pdf/", views.telecharger_pdf_devis, name="telecharger_pdf_devis"),
    path("<int:devis_id>/proforma/", views.apercu_proforma, name="apercu_proforma"),
    path("facture/nouvelle/", views.facture_creer, name="facture_creer"),
    path("facture/<int:facture_id>/", views.apercu_facture, name="apercu_facture"),
    path("facture/<int:facture_id>/certifier/", views.facture_certifier, name="facture_certifier"),
    path("documents/", views.documents_bibliotheque, name="documents_bibliotheque"),
    path("facturation/", views.facturation_accueil, name="facturation_accueil"),
]