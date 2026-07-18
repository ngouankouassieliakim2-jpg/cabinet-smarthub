from django.contrib import admin
from django.utils.html import format_html
from .models import Client


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("code_client", "get_nom", "get_ncc", "statut", "date_entree")
    list_filter = ("statut",)
    search_fields = ("code_client", "email_acces", "devis_origine__numero_devis",
                     "devis_origine__pm_raison_sociale", "devis_origine__pp_nom_prenoms")
    readonly_fields = ("code_client", "date_entree", "infos_devis")
    autocomplete_fields = ("devis_origine",)

    fieldsets = (
        ("Devis d'origine (saisir le devis)", {
            "fields": ("devis_origine", "infos_devis"),
            "description": "Sélectionnez le devis. Toutes les informations du client seront récupérées automatiquement.",
        }),
        ("Activation du client", {
            "fields": ("email_acces", "lettre_mission"),
        }),
        ("Suivi interne", {
            "fields": ("code_client", "statut", "gestionnaire", "date_entree", "notes"),
        }),
    )

    @admin.display(description="Nom / Raison sociale")
    def get_nom(self, obj):
        return obj.nom

    @admin.display(description="NCC")
    def get_ncc(self, obj):
        return obj.ncc or "—"

    @admin.display(description="Informations récupérées du devis")
    def infos_devis(self, obj):
        if not obj.pk:
            return "Sélectionnez un devis et enregistrez pour voir les informations récupérées."
        d = obj.devis_origine
        return format_html(
            """
            <div style="font-size:13px; line-height:1.8; background:#f5f5f5; padding:12px; border-radius:6px;">
                <b>Numéro de devis :</b> {}<br>
                <b>Type :</b> {}<br>
                <b>Nom / Raison sociale :</b> {}<br>
                <b>NCC :</b> {}<br>
                <b>Téléphone :</b> {}<br>
                <b>Email (devis) :</b> {}<br>
                <b>Montant TTC du devis :</b> {} FCFA
            </div>
            """,
            d.numero_devis,
            d.get_type_client_display(),
            d.pm_raison_sociale or d.pp_nom_prenoms or "—",
            d.ncc or "—",
            d.telephone or "—",
            d.email or "—",
            f"{d.total_ttc:,.0f}".replace(",", " "),
        )