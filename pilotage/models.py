from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User


class Notification(models.Model):
    """Alerte/rappel centralisé, affiché dans la cloche de l'interface.
    Générée par une commande planifiée (pas à la volée)."""
    TYPE_CHOICES = [
        ("cdd_echeance", "CDD/Stage — échéance proche"),
        ("fin_essai", "Fin de période d'essai proche"),
        ("relance_notification_interne", "Recouvrement — notification interne"),
        ("relance_escalade_direction", "Recouvrement — escalade Direction"),
        ("relance_alerte_contentieux", "Recouvrement — alerte contentieux"),
        ("promesse_rompue", "Recouvrement — promesse rompue"),
        ("budget_alerte", "Budget — seuil atteint"),
    ]
    type_notification = models.CharField("Type", max_length=30, choices=TYPE_CHOICES)
    titre = models.CharField("Titre", max_length=200)
    message = models.CharField("Message", max_length=300)
    url = models.CharField("Lien vers la page concernée", max_length=300, blank=True, default="")
    cle = models.CharField("Clé d'unicité", max_length=200, unique=True,
                           help_text="Empêche de dupliquer la même alerte (ex: type + id salarié + date).")
    destinataire = models.ForeignKey(
        "auth.User", on_delete=models.CASCADE, null=True, blank=True,
        related_name="notifications_recues",
        help_text="Si vide, notification générale (visible par tous, comme avant). "
                   "Si rempli, visible par ce destinataire précis + toujours par Direction/Cadre.")
    lue = models.BooleanField("Lue", default=False)
    cree_le = models.DateTimeField("Créée le", auto_now_add=True)

    def __str__(self):
        return f"{self.titre} ({'lue' if self.lue else 'non lue'})"

    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ["-cree_le"]


class Pole(models.Model):
    """Un pôle/service du cabinet (ex: Social & RH, Comptabilité & Fiscalité).
    Détermine quels modules métier ses membres peuvent voir dans la barre du haut."""
    nom = models.CharField("Nom du pôle", max_length=100)
    description = models.TextField("Description", blank=True)
    modules_ids = models.JSONField(
        "Modules accessibles", default=list,
        help_text="Clés des modules métier (ex: ['social-rh']) que ce pôle peut voir.",
    )
    sous_modules_urls = models.JSONField(
        "Sous-modules accessibles", default=list,
        help_text="Accès à un sous-module précis, sans donner tout le module.",
    )
    fonctionnalites_urls = models.JSONField(
        "Fonctionnalités accessibles", default=list,
        help_text="Accès à une action précise (ex: 'Nouveau devis'), comme un outil isolé.",
    )
    responsable = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="poles_diriges", verbose_name="Responsable du pôle",
    )

    class Meta:
        verbose_name = "Pôle"
        verbose_name_plural = "Pôles"
        ordering = ["nom"]

    def __str__(self):
        return self.nom


class Poste(models.Model):
    """Un poste précis au sein d'un pôle (ex: Comptable senior, Assistant RH).
    Sert à l'organigramme et à l'affichage sur les documents."""
    intitule = models.CharField("Intitulé du poste", max_length=150)
    pole = models.ForeignKey(Pole, on_delete=models.CASCADE, related_name="postes", verbose_name="Pôle")
    poste_parent = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="postes_subordonnes", verbose_name="Rattaché à (poste hiérarchique supérieur)",
    )

    class Meta:
        verbose_name = "Poste"
        verbose_name_plural = "Postes"
        ordering = ["pole__nom", "intitule"]

    def __str__(self):
        return f"{self.intitule} ({self.pole.nom})"
