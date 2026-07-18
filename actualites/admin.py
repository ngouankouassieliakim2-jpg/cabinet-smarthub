from django.contrib import admin

from .models import Article


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ("titre", "date_publication", "publie")
    list_filter = ("publie", "date_publication")
    search_fields = ("titre", "contenu")
    list_editable = ("publie",)  # cocher/décocher "publié" directement depuis la liste
    date_hierarchy = "date_publication"