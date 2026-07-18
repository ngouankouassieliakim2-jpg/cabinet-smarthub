from django.urls import path
from . import views

# Optionnel mais recommandé : définit un namespace pour cette application


urlpatterns = [
    path("", views.accueil, name="accueil"),
    path("services/", views.services, name="services"),
    path("a-propos/", views.a_propos, name="a_propos"),
    path("contact/", views.contact, name="contact"),
    path("services/<slug:service_slug>/", views.detail_service, name="detail_service"),
]