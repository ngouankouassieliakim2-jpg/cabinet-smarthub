import secrets

from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator
from django.db import models
from django.contrib.auth.models import User


def valider_taille_fichier(fichier):
    limite = 1024 * 1024 * 1024  # 1 Go
    if fichier.size > limite:
        raise ValidationError("Le fichier dépasse la limite autorisée de 1 Go.")


class Conversation(models.Model):
    TYPE_CHOICES = [
        ("direct", "Conversation directe (à deux)"),
        ("groupe", "Groupe"),
    ]
    type_conversation = models.CharField("Type", max_length=10, choices=TYPE_CHOICES, default="direct")
    nom = models.CharField("Nom du groupe", max_length=150, blank=True, default="",
                           help_text="Utilisé uniquement pour un groupe.")
    cree_par = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="conversations_creees")
    cree_le = models.DateTimeField("Créée le", auto_now_add=True)
    cle_reunion = models.CharField("Clé de la salle de réunion", max_length=64, blank=True, default="")

    def obtenir_reunion(self):
        """Génère la salle de visio une seule fois, puis la réutilise à chaque
        appel -- tous les participants d'une même conversation rejoignent
        toujours la même salle."""
        if not self.cle_reunion:
            self.cle_reunion = f"cabinetkl-{secrets.token_urlsafe(16)}"
            self.save(update_fields=["cle_reunion"])
        return self.cle_reunion

    def __str__(self):
        if self.type_conversation == "groupe":
            return self.nom or f"Groupe #{self.id}"
        noms = [p.utilisateur.username for p in self.participations.all()]
        return " ↔ ".join(noms)

    class Meta:
        verbose_name = "Conversation"
        verbose_name_plural = "Conversations"
        ordering = ["-cree_le"]

class Participation(models.Model):
    """Un utilisateur dans une conversation, avec son statut de lecture."""
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="participations")
    utilisateur = models.ForeignKey(User, on_delete=models.CASCADE, related_name="participations_chat")
    est_admin = models.BooleanField("Administrateur du groupe", default=False)
    rejoint_le = models.DateTimeField("A rejoint le", auto_now_add=True)
    dernier_message_lu = models.ForeignKey(
        "Message", on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
        help_text="Sert à calculer le nombre de messages non lus.")

    def __str__(self):
        return f"{self.utilisateur.username} — {self.conversation}"

    class Meta:
        verbose_name = "Participation"
        verbose_name_plural = "Participations"
        unique_together = ("conversation", "utilisateur")

class Message(models.Model):
    """Un message texte et/ou pièce jointe dans une conversation."""
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    expediteur = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="messages_envoyes")
    texte = models.TextField("Message", blank=True, default="", validators=[MaxLengthValidator(2000)])
    fichier = models.FileField(
        "Pièce jointe", upload_to="messagerie/%Y/%m/", blank=True, null=True,
        validators=[valider_taille_fichier],
    )
    rappel_expiration_envoye = models.BooleanField("Rappel de suppression envoyé", default=False)
    nom_fichier_original = models.CharField("Nom du fichier", max_length=255, blank=True, default="")
    latitude = models.DecimalField("Latitude", max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField("Longitude", max_digits=9, decimal_places=6, null=True, blank=True)
    envoye_le = models.DateTimeField("Envoyé le", auto_now_add=True)

    def est_audio(self):
        if not self.nom_fichier_original:
            return False
        return self.nom_fichier_original.lower().endswith((".webm", ".mp3", ".wav", ".ogg", ".m4a", ".aac"))

    def __str__(self):
        return f"{self.expediteur} — {self.envoye_le:%d/%m/%Y %H:%M}"

    class Meta:
        verbose_name = "Message"
        verbose_name_plural = "Messages"
        ordering = ["envoye_le"]

