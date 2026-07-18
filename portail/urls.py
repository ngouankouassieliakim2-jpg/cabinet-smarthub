from django.urls import path
from . import views

urlpatterns = [
    path("", views.accueil, name="portail_accueil"),
    path("premiere-connexion/mot-de-passe/", views.premiere_connexion_mdp, name="portail_premiere_connexion_mdp"),
    path("premiere-connexion/lettre/", views.premiere_connexion_lettre, name="portail_premiere_connexion_lettre"),
    path("premiere-connexion/conditions/", views.premiere_connexion_cgv, name="portail_premiere_connexion_cgv"),
]