from django.db import models
from django.utils import timezone


class DemandeRendezVous(models.Model):
    """Une demande de rendez-vous envoyée depuis la Vitrine."""

    class Lieu(models.TextChoices):
        DALOA = "DALOA", "Daloa (siège)"
        BASSAM = "BASSAM", "Grand-Bassam (succursale)"

    class Statut(models.TextChoices):
        NOUVELLE = "NOUVELLE", "Nouvelle"
        TRAITEE = "TRAITEE", "Traitée"

    class Structure(models.TextChoices):
        INDIVIDUELLE = "INDIVIDUELLE", "Entreprise individuelle"
        SARL = "SARL", "SARL"
        SA = "SA", "SA"
        ASSOCIATION = "ASSOCIATION", "Association"
        ONG = "ONG", "ONG"
        COOPERATIVE = "COOPERATIVE", "Coopérative"
        PARTICULIER = "PARTICULIER", "Particulier"
        AUTRE = "AUTRE", "Autre"

    class Anciennete(models.TextChoices):
        PROJET = "PROJET", "Projet non lancé"
        MOINS_1AN = "MOINS_1AN", "Moins d'un an"
        UN_A_TROIS = "UN_A_TROIS", "1 à 3 ans"
        PLUS_3ANS = "PLUS_3ANS", "Plus de 3 ans"

    class ChiffreAffaires(models.TextChoices):
        MOINS_50M = "MOINS_50M", "Moins de 50 millions FCFA"
        DE_50_200M = "DE_50_200M", "50 à 200 millions FCFA"
        DE_200_500M = "DE_200_500M", "200 à 500 millions FCFA"
        PLUS_500M = "PLUS_500M", "Plus de 500 millions FCFA"
        INCONNU = "INCONNU", "Je ne sais pas encore"

    # --- Coordonnées du prospect ---
    nom = models.CharField(max_length=150, verbose_name="Nom complet")
    telephone = models.CharField(max_length=30, verbose_name="Téléphone")
    email = models.EmailField(blank=True, verbose_name="Email")

    # --- Motifs (multi-choix, stockés en texte : "COMPTABILITE,FISCALITE") ---
    motifs = models.CharField(
        max_length=300,
        verbose_name="Objet(s) de la demande",
        help_text="Un ou plusieurs domaines, séparés par des virgules.",
    )

    # --- Pré-diagnostic (pour préparer le rendez-vous) ---
    structure = models.CharField(
        max_length=20,
        choices=Structure.choices,
        blank=True,
        verbose_name="Type de structure",
    )
    secteur = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Secteur d'activité",
    )
    cabinet_actuel = models.BooleanField(
        default=False,
        verbose_name="A déjà un cabinet comptable",
    )
    anciennete = models.CharField(
        max_length=20,
        choices=Anciennete.choices,
        blank=True,
        verbose_name="Ancienneté de l'activité",
    )
    chiffre_affaires = models.CharField(
        max_length=20,
        choices=ChiffreAffaires.choices,
        blank=True,
        verbose_name="Chiffre d'affaires prévisionnel",
    )

    # --- Rendez-vous souhaité ---
    lieu = models.CharField(
        max_length=10,
        choices=Lieu.choices,
        verbose_name="Lieu de rendez-vous souhaité",
    )
    date_souhaitee = models.DateField(
        blank=True,
        null=True,
        verbose_name="Date souhaitée",
    )
    message = models.TextField(blank=True, verbose_name="Message")

    # --- Suivi (géré par le cabinet) ---
    statut = models.CharField(
        max_length=10,
        choices=Statut.choices,
        default=Statut.NOUVELLE,
        verbose_name="Statut",
    )
    date_creation = models.DateTimeField(
        default=timezone.now,
        verbose_name="Reçue le",
    )

    class Meta:
        verbose_name = "Demande de rendez-vous"
        verbose_name_plural = "Demandes de rendez-vous"
        ordering = ["-date_creation"]

    def __str__(self):
        return f"{self.nom} — {self.get_statut_display()}"