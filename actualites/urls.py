from django.urls import path
from . import views

urlpatterns = [
    path("", views.liste_articles, name="actualites"),
    path("<int:article_id>/", views.detail_article, name="detail_article"),
]