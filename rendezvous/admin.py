from django.contrib import admin

from .models import DemandeRendezVous


@admin.register(DemandeRendezVous)
class DemandeRendezVousAdmin(admin.ModelAdmin):
    list_display = ("nom", "motifs", "lieu", "telephone", "date_creation", "statut")
    list_filter = ("statut", "lieu", "date_creation")
    search_fields = ("nom", "telephone", "email", "motifs", "secteur")
    list_editable = ("statut",)
    readonly_fields = ("date_creation",)
    date_hierarchy = "date_creation"