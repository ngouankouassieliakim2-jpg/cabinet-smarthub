from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from .models import Profil


class ProfilInline(admin.StackedInline):
    model = Profil
    can_delete = False
    max_num = 1
    extra = 1
    verbose_name_plural = "Profil (rôle)"


class UtilisateurAdmin(UserAdmin):
    inlines = [ProfilInline]
    list_display = (
        "username", "email", "first_name", "last_name", "is_staff", "afficher_role",
    )

    @admin.display(description="Rôle")
    def afficher_role(self, obj):
        # obj est un User : on lit son profil lié s'il existe.
        if hasattr(obj, "profil"):
            return obj.profil.get_role_display()
        return "—"


# On remplace l'admin User par défaut par le nôtre.
admin.site.unregister(User)
admin.site.register(User, UtilisateurAdmin)