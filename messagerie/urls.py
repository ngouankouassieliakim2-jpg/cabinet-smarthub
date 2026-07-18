from django.urls import path
from . import views

urlpatterns = [
    path("", views.conversations_liste, name="messagerie_liste"),
    path("nouvelle/", views.nouvelle_conversation, name="messagerie_nouvelle"),
    path("<int:conversation_id>/", views.conversation_ouvrir, name="messagerie_conversation"),
    path("<int:conversation_id>/actualiser/", views.messages_actualiser, name="messagerie_actualiser"),
]
