from django.contrib import admin
from django.utils.html import format_html
from .calculs import calculer_bulletin
from .models import (
    SecteurActivite, CategorieSalaire, Employeur, ParametrePaie,
    PrimeConfiguree, Banque, Employe, BulletinPaie, LignePrime
)


# ---------- SECTEUR + grille ----------
class CategorieSalaireInline(admin.TabularInline):
    model = CategorieSalaire
    extra = 5
    fields = ("ordre", "code", "salaire_minimum")


@admin.register(SecteurActivite)
class SecteurActiviteAdmin(admin.ModelAdmin):
    list_display = ("nom", "taux_at")
    search_fields = ("nom",)
    inlines = [CategorieSalaireInline]


# ---------- EMPLOYEUR + ses paramètres, primes, banques ----------
class ParametrePaieInline(admin.StackedInline):
    model = ParametrePaie
    extra = 0
    can_delete = False


class PrimeConfigureeInline(admin.TabularInline):
    model = PrimeConfiguree
    extra = 3
    fields = ("ordre", "libelle", "traitement_fiscal", "soumis_cnps", "montant_par_defaut")


class BanqueInline(admin.TabularInline):
    model = Banque
    extra = 3
    fields = ("nom",)


@admin.register(Employeur)
class EmployeurAdmin(admin.ModelAdmin):
    list_display = ("raison_sociale", "secteur", "ncc", "numero_cnps", "est_cabinet")
    list_filter = ("secteur",)
    search_fields = ("raison_sociale", "ncc")
    inlines = [ParametrePaieInline, PrimeConfigureeInline, BanqueInline]


# ---------- EMPLOYÉ ----------
@admin.register(Employe)
class EmployeAdmin(admin.ModelAdmin):
    list_display = ("matricule", "nom_prenoms", "employeur", "categorie", "salaire_base", "statut")
    list_filter = ("statut", "contrat", "employeur")
    search_fields = ("matricule", "nom_prenoms", "numero_cnps")


# ---------- BULLETIN + primes + aperçu du calcul ----------
class LignePrimeInline(admin.TabularInline):
    model = LignePrime
    extra = 2
    fields = ("prime_configuree", "libelle", "montant", "traitement_fiscal", "soumis_cnps")


@admin.register(BulletinPaie)
class BulletinPaieAdmin(admin.ModelAdmin):
    list_display = ("employe", "mois", "annee", "salaire_base", "jours_travailles")
    list_filter = ("annee", "mois", "employe__employeur")
    search_fields = ("employe__nom_prenoms", "employe__matricule")
    inlines = [LignePrimeInline]
    readonly_fields = ("apercu_calcul",)

    @admin.display(description="APERÇU DU CALCUL")
    def apercu_calcul(self, obj):
        if not obj.pk:
            return "Enregistrez d'abord le bulletin pour voir le calcul."
        c = calculer_bulletin(obj)
        def f(v):
            return f"{v:,.0f}".replace(",", " ")
        return format_html(
            """
            <div style="font-size:13px; line-height:1.8; max-width:500px;">
                <b style="color:#1F3864;">GAINS</b><br>
                Prime d'ancienneté : {} FCFA<br>
                <b>TOTAL DES GAINS : {} FCFA</b><br><br>
                <b style="color:#1F3864;">BASES DE CALCUL</b><br>
                Brut fiscal : {} FCFA<br>
                Brut social : {} FCFA<br>
                Parts IGR : {}<br><br>
                <b style="color:#C0392B;">RETENUES SALARIÉ</b><br>
                ITS (avant RICF) : {} FCFA<br>
                RICF : - {} FCFA<br>
                ITS final : {} FCFA<br>
                CNPS retraite : {} FCFA<br>
                CMU : {} FCFA<br>
                <b>TOTAL RETENUES : {} FCFA</b><br><br>
                <b style="font-size:16px; color:#16A34A;">NET À PAYER : {} FCFA</b><br>
                <span style="color:#888;">(net exact : {} FCFA)</span><br><br>
                <b style="color:#888;">CHARGES PATRONALES : {} FCFA</b>
            </div>
            """,
            f(c["prime_anciennete"]), f(c["total_gains"]),
            f(c["brut_fiscal"]), f(c["brut_social"]), c["parts_igr"],
            f(c["its_brut"]), f(c["ricf"]), f(c["its_final"]),
            f(c["cnps_retraite_salarie"]), f(c["cmu"]), f(c["total_retenues"]),
            f(c["net_arrondi"]), f(c["net"]), f(c["total_charges_patronales"]),
        )