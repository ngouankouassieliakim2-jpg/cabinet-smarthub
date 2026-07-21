from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class JournalExecutionCommande(models.Model):
    """Trace générique des exécutions de commandes management."""

    ETAT_CHOICES = [
        ("EN_COURS", "En cours"),
        ("SUCCES", "Succès"),
        ("ERREUR", "Erreur"),
    ]

    commande = models.CharField(max_length=150)
    description = models.CharField(max_length=255, blank=True)
    utilisateur = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True)
    contexte = models.JSONField(default=dict, blank=True)
    objet = models.CharField(max_length=255, blank=True, null=True)
    etat = models.CharField(max_length=20, choices=ETAT_CHOICES, default="EN_COURS")
    resume = models.TextField(blank=True)
    erreur = models.TextField(blank=True)
    date_debut = models.DateTimeField(auto_now_add=True)
    date_fin = models.DateTimeField(null=True, blank=True)
    duree_secondes = models.FloatField(default=0.0)

    def __str__(self):
        return f"{self.commande} — {self.get_etat_display()}"

    class Meta:
        verbose_name = "Exécution de commande"
        verbose_name_plural = "Exécutions de commandes"
        ordering = ["-date_debut"]


class JournalAudit(models.Model):
    """Journal d'audit générique : qui a fait quoi, quand, depuis où,
    sur n'importe quel objet (via GenericForeignKey). Complète les
    historiques métier existants (HistoriqueStatutFacture, etc.) qui
    restent utiles pour leur lecture métier ; ceci est la trace technique
    brute, non filtrée, de toute action notable."""

    ACTION_CHOICES = [
        ("CREATION", "Création"),
        ("MODIFICATION", "Modification"),
        ("SUPPRESSION", "Suppression"),
        ("CONSULTATION", "Consultation"),
        ("EXPORT", "Export"),
        ("ACTION_METIER", "Action métier"),
    ]

    utilisateur = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    description = models.CharField(max_length=255, blank=True)

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    objet = GenericForeignKey("content_type", "object_id")

    adresse_ip = models.GenericIPAddressField(null=True, blank=True)
    date_action = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.utilisateur} — {self.get_action_display()} — {self.date_action:%d/%m/%Y %H:%M}"

    class Meta:
        verbose_name = "Entrée du journal d'audit"
        verbose_name_plural = "Journal d'audit"
        ordering = ["-date_action"]
        indexes = [models.Index(fields=["content_type", "object_id"])]


class NoteInterne(models.Model):
    """Note/commentaire interne générique, réutilisable sur n'importe quel
    modèle métier — remplace la duplication (CommentaireLitige reste en
    place pour compatibilité, migration progressive possible plus tard)."""

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    objet = GenericForeignKey("content_type", "object_id")

    auteur = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True)
    message = models.TextField()
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Note de {self.auteur} — {self.date_creation:%d/%m/%Y}"

    class Meta:
        verbose_name = "Note interne"
        verbose_name_plural = "Notes internes"
        ordering = ["date_creation"]
        indexes = [models.Index(fields=["content_type", "object_id"])]
