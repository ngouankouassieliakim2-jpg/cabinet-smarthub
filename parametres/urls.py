from django.urls import path
from . import views

urlpatterns = [
    path("", views.catalogue, name="catalogue"),
    path("categorie/nouvelle/", views.creer_categorie, name="creer_categorie"),
    path("categorie/<int:pk>/modifier/", views.modifier_categorie, name="modifier_categorie"),
    path("categorie/<int:pk>/supprimer/", views.supprimer_categorie, name="supprimer_categorie"),
    path("prestation/nouvelle/", views.creer_prestation, name="creer_prestation"),
    path("prestation/<int:pk>/modifier/", views.modifier_prestation, name="modifier_prestation"),
    path("prestation/<int:pk>/supprimer/", views.supprimer_prestation, name="supprimer_prestation"),
    path("variante/nouvelle/", views.creer_variante, name="creer_variante"),
    path("variante/<int:pk>/modifier/", views.modifier_variante, name="modifier_variante"),
    path("variante/<int:pk>/supprimer/", views.supprimer_variante, name="supprimer_variante"),
    path("email/", views.parametres_email, name="parametres_email"),
    path("email/test/", views.tester_email, name="tester_email"),
    path("fne/", views.parametres_fne, name="parametres_fne"),
    path("cgv/", views.parametres_cgv, name="parametres_cgv"),
]