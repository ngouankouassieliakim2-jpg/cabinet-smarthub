from django.db import models
from django.utils import timezone


class Notification(models.Model):
    """Alerte/rappel centralisé, affiché dans la cloche de l'interface.
    Générée par une commande planifiée (pas à la volée)."""
    TYPE_CHOICES = [
        ("cdd_echeance", "CDD/Stage — échéance proche"),
        ("fin_essai", "Fin de période d'essai proche"),
    ]
    type_notification = models.CharField("Type", max_length=30, choices=TYPE_CHOICES)
    titre = models.CharField("Titre", max_length=200)
    message = models.CharField("Message", max_length=300)
    url = models.CharField("Lien vers la page concernée", max_length=300, blank=True, default="")
    cle = models.CharField("Clé d'unicité", max_length=200, unique=True,
                           help_text="Empêche de dupliquer la même alerte (ex: type + id salarié + date).")
    lue = models.BooleanField("Lue", default=False)
    cree_le = models.DateTimeField("Créée le", auto_now_add=True)

    def __str__(self):
        return f"{self.titre} ({'lue' if self.lue else 'non lue'})"

    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ["-cree_le"]
