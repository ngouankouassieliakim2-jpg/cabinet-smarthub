from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="comptes/login.html"),
        name="login",
    ),
    path(
        "logout/",
        auth_views.LogoutView.as_view(),
        name="logout",
    ),
    path("signature/", views.signature_gerer, name="comptes_signature"),
    path("signature/apposer/", views.signature_appliquer, name="comptes_signature_appliquer"),
    path("signature/apercu-page/", views.signature_apercu_page, name="comptes_signature_apercu_page"),
    path("documents-a-signer/", views.documents_a_signer, name="comptes_documents_a_signer"),
    path("signature/ordre/", views.signature_par_ordre, name="comptes_signature_ordre"),
    path("signature/delegation/", views.signature_par_delegation, name="comptes_signature_delegation"),
    path("aiguillage/", views.aiguillage, name="aiguillage"),
]