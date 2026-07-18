from django.conf import settings
from django.db import models
from django.utils import timezone


class AppelTelephonique(models.Model):
    """Un appel téléphonique reçu, noté manuellement par le secrétariat."""

    class Statut(models.TextChoices):
        A_TRAITER = "A_TRAITER", "À traiter"
        TRAITE = "TRAITE", "Traité"

    # --- Qui a appelé ---
    nom_appelant = models.CharField(max_length=150, verbose_name="Nom de l'appelant")
    telephone = models.CharField(max_length=30, blank=True, verbose_name="Téléphone")

    # --- L'appel ---
    date_appel = models.DateTimeField(default=timezone.now, verbose_name="Date et heure de l'appel")
    objet = models.TextField(verbose_name="Objet de l'appel")

    # --- Reçu par (rempli automatiquement avec l'utilisateur connecté) ---
    recu_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Reçu par",
    )

    # --- Suivi ---
    a_rappeler = models.BooleanField(default=False, verbose_name="À rappeler")
    date_rappel = models.DateField(null=True, blank=True, verbose_name="Date de rappel souhaitée")
    statut = models.CharField(
        max_length=10,
        choices=Statut.choices,
        default=Statut.A_TRAITER,
        verbose_name="Statut",
    )
    notes = models.TextField(blank=True, verbose_name="Notes")

    class Meta:
        verbose_name = "Appel téléphonique"
        verbose_name_plural = "Appels téléphoniques"
        ordering = ["-date_appel"]

    def __str__(self):
        return f"{self.nom_appelant} — {self.date_appel:%d/%m/%Y}"