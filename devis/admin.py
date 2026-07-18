from django.contrib import admin
from django.utils.html import format_html, mark_safe
from django.urls import path
from django.shortcuts import redirect
from django.contrib import messages
from .models import Devis, LignePrestation
from .utils import generer_lettre_mission, transformer_devis_en_client


class LignePrestationInline(admin.TabularInline):
    model = LignePrestation
    extra = 3
    fields = ("designation", "periodicite", "quantite", "prix_unitaire", "taux_tva")


@admin.register(Devis)
class DevisAdmin(admin.ModelAdmin):
    list_display = ("numero_devis", "get_nom", "type_client", "statut", "date_creation")
    list_filter = ("type_client", "statut", "regime_imposition")
    search_fields = ("numero_devis", "pm_raison_sociale", "pp_nom_prenoms", "ncc")
    readonly_fields = ("numero_devis", "date_creation", "recap_totaux", "bouton_lettre", "bouton_transformer")
    autocomplete_fields = ("client_rattache",)
    inlines = [LignePrestationInline]

    # --- URLs personnalisées (boutons) ---
    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path("<int:devis_id>/generer-lettre/", self.admin_site.admin_view(self.generer_lettre_view),
                 name="devis_generer_lettre"),
            path("<int:devis_id>/transformer-client/", self.admin_site.admin_view(self.transformer_client_view),
                 name="devis_transformer_client"),
        ]
        return custom + urls

    def generer_lettre_view(self, request, devis_id):
        devis = self.get_object(request, devis_id)
        try:
            generer_lettre_mission(devis)
            self.message_user(request, f"Lettre de mission générée pour {devis.numero_devis}.", messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"Erreur lors de la génération : {e}", messages.ERROR)
        return redirect(request.META.get("HTTP_REFERER", "admin:index"))

    def transformer_client_view(self, request, devis_id):
        devis = self.get_object(request, devis_id)
        if devis.statut == "TRANSFORME":
            self.message_user(request, "Ce devis a déjà été transformé en client.", messages.WARNING)
        else:
            try:
                client = transformer_devis_en_client(devis)
                self.message_user(request, f"Client créé : {client.code_client}. Pensez à saisir son email d'accès.", messages.SUCCESS)
            except Exception as e:
                self.message_user(request, f"Erreur lors de la transformation : {e}", messages.ERROR)
        return redirect(request.META.get("HTTP_REFERER", "admin:index"))

    fieldsets = (
        ("Identification du devis", {
            "fields": ("numero_devis", "type_client", "statut", "client_rattache", "date_creation")
        }),
        ("Personne Physique (si applicable)", {
            "classes": ("collapse",),
            "fields": ("pp_nom_prenoms", "pp_date_naissance", "pp_lieu_naissance", "pp_nationalite",
                       "pp_nom_pere", "pp_nom_mere", "pp_piece_type", "pp_piece_numero",
                       "pp_piece_delivree_le", "pp_piece_delivree_a", "pp_adresse_perso"),
        }),
        ("Personne Morale (si applicable)", {
            "classes": ("collapse",),
            "fields": ("pm_raison_sociale", "pm_nom_commercial", "pm_sigle",
                       "pm_forme_juridique", "pm_capital_social"),
        }),
        ("Identifiants légaux", {
            "classes": ("collapse",),
            "fields": ("ncc", "rccm_numero", "rccm_delivre_le", "rccm_delivre_par",
                       "code_activite", "regime_imposition", "est_employeur")
        }),
        ("Obligations fiscales", {
            "classes": ("collapse",),
            "fields": ("obl_patente", "obl_bic_ba", "obl_bnc", "obl_tva", "obl_tob",
                       "obl_taxe_bois", "obl_its", "obl_airsi", "obl_tse",
                       "obl_impots_fonciers", "obl_impot_micro", "obl_igr", "obl_autres"),
        }),
        ("Localisation du siège", {
            "classes": ("collapse",),
            "fields": ("siege_ville", "siege_commune", "siege_quartier", "siege_rue",
                       "siege_lot", "siege_ilot", "ref_section", "ref_parcelle", "ref_tf", "boite_postale"),
        }),
        ("Contacts", {
            "classes": ("collapse",),
            "fields": ("telephone", "telephone2", "email", "fax")
        }),
        ("Activité", {
            "classes": ("collapse",),
            "fields": ("activite_principale", "activite_date_debut", "autres_activites", "ca_previsionnel")
        }),
        ("Dirigeant / Gérant (Personne Morale)", {
            "classes": ("collapse",),
            "fields": ("dirigeant_nom", "dirigeant_qualite", "dirigeant_bp", "dirigeant_tel", "dirigeant_email"),
        }),
        ("Suivi comptable antérieur", {
            "classes": ("collapse",),
            "fields": ("a_eu_comptable", "comptable_precedent_nom", "comptable_precedent_ncc",
                       "comptable_precedent_adresse", "comptable_precedent_email", "comptable_precedent_tel"),
        }),
        ("Documents scannés à importer", {
            "classes": ("collapse",),
            "fields": ("doc_rccm", "doc_dfe", "doc_cnps", "doc_tribunal_travail",
                       "doc_piece_identite", "doc_contrat_bail", "doc_statuts"),
        }),
        ("Autres établissements", {
            "classes": ("collapse",),
            "fields": ("autres_etablissements",),
        }),
        ("Remise et totaux", {
            "fields": ("remise_pourcentage", "recap_totaux"),
        }),
        ("Suivi interne / Mission", {
            "fields": ("type_mission", "honoraires_proposes", "etat_compta_reprise", "notes_internes",
                       "bouton_lettre", "lettre_mission_pdf", "bouton_transformer"),
        }),
    )

    @admin.display(description="Nom / Raison sociale")
    def get_nom(self, obj):
        return obj.pm_raison_sociale or obj.pp_nom_prenoms or "—"

    @admin.display(description="Récapitulatif des montants")
    def recap_totaux(self, obj):
        if not obj.pk:
            return "Enregistrez d'abord le devis pour voir les totaux."
        return format_html(
            """
            <div style="font-size:14px; line-height:1.8;">
                <b>Total HT brut :</b> {} FCFA<br>
                <b>Remise ({} %) :</b> &ndash; {} FCFA<br>
                <b>Total HT net :</b> {} FCFA<br>
                <b>TVA :</b> {} FCFA<br>
                <hr style="margin:6px 0;">
                <b style="font-size:16px; color:#1F3864;">TOTAL TTC : {} FCFA</b>
            </div>
            """,
            f"{obj.total_ht_brut:,.0f}".replace(",", " "),
            obj.remise_pourcentage,
            f"{obj.montant_remise:,.0f}".replace(",", " "),
            f"{obj.total_ht:,.0f}".replace(",", " "),
            f"{obj.montant_tva:,.0f}".replace(",", " "),
            f"{obj.total_ttc:,.0f}".replace(",", " "),
        )

    @admin.display(description="Lettre de mission")
    def bouton_lettre(self, obj):
        if not obj.pk:
            return "Enregistrez d'abord le devis."
        url = f"/admin/devis/devis/{obj.pk}/generer-lettre/"
        if obj.lettre_mission_pdf:
            return format_html(
                '<a class="button" href="{}" style="background:#1F3864;color:#fff;padding:6px 12px;border-radius:4px;">Régénérer la lettre</a> '
                '&nbsp; <a href="{}" target="_blank" style="color:#1F3864;font-weight:bold;">Voir le PDF actuel</a>',
                url, obj.lettre_mission_pdf.url
            )
        return format_html(
            '<a class="button" href="{}" style="background:#B8960C;color:#fff;padding:6px 12px;border-radius:4px;">Générer la lettre de mission</a>',
            url
        )

    @admin.display(description="Transformation en client")
    def bouton_transformer(self, obj):
        if not obj.pk:
            return "Enregistrez d'abord le devis."
        if obj.statut == "TRANSFORME":
            return mark_safe('<span style="color:green;font-weight:bold;">&#10003; Ce devis a été transformé en client.</span>')
        url = f"/admin/devis/devis/{obj.pk}/transformer-client/"
        return format_html(
            '<a class="button" href="{}" style="background:#16A34A;color:#fff;padding:8px 16px;border-radius:4px;font-weight:bold;">→ Transformer ce devis en client</a>'
            '<p style="color:#888;font-size:11px;margin-top:6px;">Crée le client, récupère la lettre de mission. L\'email d\'accès sera à saisir sur la fiche client.</p>',
            url
        )