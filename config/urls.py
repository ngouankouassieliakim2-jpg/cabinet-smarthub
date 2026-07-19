from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import path, include
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static

from vitrine.sitemaps import VitrineSitemap


urlpatterns = [
    path("admin/", admin.site.urls),
    path("devis/", include("devis.urls")),
    path("paie/", include("paie.urls")),
    path("parametres/", include("parametres.urls")),
    path("clients/", include("clients.urls")),
    path("pilotage/", include("pilotage.urls")),
    path("", include("vitrine.urls")),
    path("comptes/", include("comptes.urls")),
    path("collaborateurs/", include("collaborateurs.urls")),
    path("portail/", include("portail.urls")),
    path("actualites/", include("actualites.urls")),
    path("secretariat/", include("secretariat.urls")),
    path("messagerie/", include("messagerie.urls")),
    path("sitemap.xml", sitemap, {"sitemaps": {"vitrine": VitrineSitemap}}, name="sitemap"),
    path("robots.txt", TemplateView.as_view(template_name="robots.txt", content_type="text/plain")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
