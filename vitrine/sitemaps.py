from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .services_data import SERVICES_DATA


class VitrineSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        pages_statiques = ["accueil", "services", "a_propos", "contact"]
        services = [f"service:{slug}" for slug in SERVICES_DATA.keys()]
        return pages_statiques + services

    def location(self, item):
        if item.startswith("service:"):
            slug = item.split(":", 1)[1]
            return reverse("detail_service", args=[slug])
        return reverse(item)
