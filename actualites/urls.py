from django.urls import path
from . import views

urlpatterns = [
    path("", views.liste_articles, name="actualites"),
    path("gestion/", views.articles_liste_interne, name="articles_liste_interne"),
    path("gestion/nouveau/", views.article_creer, name="article_creer"),
    path("gestion/<int:article_id>/modifier/", views.article_modifier, name="article_modifier"),
    path("gestion/<int:article_id>/supprimer/", views.article_supprimer, name="article_supprimer"),
    path("<int:article_id>/", views.detail_article, name="detail_article"),
]