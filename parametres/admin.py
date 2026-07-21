from django.contrib import admin
from .models import (
    CategoriePrestation,
    ParametresEmail,
    ParametresFNE,
    ParametresMobileMoney,
    ParametresWhatsAppBusiness,
    PrestationCatalogue,
)

admin.site.register(CategoriePrestation)
admin.site.register(PrestationCatalogue)
admin.site.register(ParametresEmail)
admin.site.register(ParametresFNE)
admin.site.register(ParametresMobileMoney)
admin.site.register(ParametresWhatsAppBusiness)