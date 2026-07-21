from datetime import date
from django.db import models
from django.contrib.auth.models import User


class Profil(models.Model):
    """Profil étendu lié 1-à-1 à un compte utilisateur Django.

    Sert à attacher un RÔLE à chaque utilisateur. Ce rôle déterminera,
    après connexion, vers quelle interface l'utilisateur sera dirigé.
    """

    class Role(models.TextChoices):
        DIRECTION = "DIRECTION", "Direction"
        CADRE = "CADRE", "Cadre"
        COLLABORATEUR = "COLLABORATEUR", "Collaborateur"
        CLIENT = "CLIENT", "Client"

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profil",
        verbose_name="Compte utilisateur",
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        verbose_name="Rôle",
    )
    pole = models.ForeignKey(
        "pilotage.Pole", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="membres", verbose_name="Pôle",
    )
    poste = models.ForeignKey(
        "pilotage.Poste", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="titulaires", verbose_name="Poste",
    )
    postes_secondaires = models.ManyToManyField(
        "pilotage.Poste",
        blank=True,
        related_name="titulaires_secondaires",
        verbose_name="Postes secondaires",
    )
    derniere_activite = models.DateTimeField("Dernière activité", null=True, blank=True)

    class Meta:
        verbose_name = "Profil"
        verbose_name_plural = "Profils"

    def __str__(self):
        return f"{self.user.username} — {self.get_role_display()}"

    def _postes_references(self):
        postes = []
        if self.poste:
            postes.append(self.poste)
        postes.extend(list(self.postes_secondaires.all()))
        return [poste for poste in postes if poste is not None]

    def _libelles_postes(self):
        return [poste.intitule.lower() for poste in self._postes_references() if poste and poste.intitule]

    def est_recouvreur(self):
        if self.role in (self.Role.DIRECTION, self.Role.CADRE):
            return True
        libelles = self._libelles_postes()
        mots_cles = ["recouvreur", "recouvrement", "créance", "créances", "contentieux", "relance"]
        return any(any(mot in libelle for mot in mots_cles) for libelle in libelles)

    def ajouter_poste_secondaire(self, poste):
        if poste is None:
            return None
        if self.poste_id == getattr(poste, "id", None):
            raise ValueError("Le poste secondaire ne peut pas être identique au poste principal.")
        if self.postes_secondaires.filter(id=poste.id).exists():
            return poste
        if self.postes_secondaires.count() >= 2:
            raise ValueError("Un profil ne peut avoir que deux postes secondaires au maximum.")
        self.postes_secondaires.add(poste)
        return poste


class SignatureElectronique(models.Model):
    """Signature électronique réutilisable, extraite d'une photo/scan d'une
    signature manuscrite sur papier blanc (fond retiré automatiquement).
    Un utilisateur peut avoir plusieurs signatures dans son historique ;
    une seule est 'active' à la fois (utilisée pour l'apposition automatique)."""
    utilisateur = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="signatures",
        verbose_name="Utilisateur",
    )
    image = models.ImageField("Signature (fond transparent)", upload_to="signatures/")
    image_originale = models.ImageField(
        "Photo / scan d'origine",
        upload_to="signatures/originales/",
        blank=True,
        null=True,
    )
    est_active = models.BooleanField("Signature active", default=True)
    date_creation = models.DateTimeField("Créée le", auto_now_add=True)

    class Meta:
        verbose_name = "Signature électronique"
        verbose_name_plural = "Signatures électroniques"
        ordering = ["-date_creation"]

    def __str__(self):
        return f"Signature de {self.utilisateur.get_full_name() or self.utilisateur.username} ({self.date_creation:%d/%m/%Y})"


class DocumentSigne(models.Model):
    utilisateur = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="documents_signes",
        verbose_name="Utilisateur",
    )
    fichier_original = models.FileField(
        "Document original",
        upload_to="documents_signes/originals/",
    )
    fichier_signe = models.FileField(
        "Document signé",
        upload_to="documents_signes/signes/",
    )
    signature = models.ForeignKey(
        SignatureElectronique,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="documents_signes",
        verbose_name="Signature utilisée",
    )
    nom_signataire = models.CharField("Nom du signataire", max_length=200)
    consentement_signature = models.BooleanField("Consentement signature électronique", default=False)
    titre = models.CharField("Titre du document", max_length=200, blank=True)
    description = models.TextField("Description", blank=True)
    date_signe = models.DateTimeField("Date de signature", auto_now_add=True)

    class Meta:
        verbose_name = "Document signé"
        verbose_name_plural = "Documents signés"
        ordering = ["-date_signe"]

    def __str__(self):
        titre = self.titre or self.fichier_original.name
        return f"{titre} signé par {self.nom_signataire} le {self.date_signe:%d/%m/%Y}"


class DelegationSignature(models.Model):
    class Mode(models.TextChoices):
        ORDRE = 'ORDRE', 'Par ordre'
        DELEGATION_POUVOIR = 'DELEGATION_POUVOIR', 'Par délégation de pouvoir'

    delegant = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='delegations_donnees',
        verbose_name='Délégant',
    )
    delegataire = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='delegations_recues',
        verbose_name='Délégataire',
    )
    mode = models.CharField(
        'Régime',
        max_length=25,
        choices=Mode.choices,
    )
    perimetre = models.CharField('Périmètre / motif', max_length=255)
    date_debut = models.DateField('Date de début')
    date_fin = models.DateField('Date de fin')
    document_preuve = models.FileField(
        'Document preuve',
        upload_to='delegations/preuves/',
        blank=True,
        null=True,
    )
    est_active = models.BooleanField('Active', default=True)
    cree_par = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='delegations_creees',
        null=True,
        blank=True,
        verbose_name='Créé par',
    )
    date_creation = models.DateTimeField('Créée le', auto_now_add=True)

    class Meta:
        verbose_name = 'Délégation de signature'
        verbose_name_plural = 'Délégations de signature'
        ordering = ['-date_creation']

    def __str__(self):
        return (
            f'{self.get_mode_display()} de {self.delegant.get_full_name() or self.delegant.username} ' +
            f'à {self.delegataire.get_full_name() or self.delegataire.username} ' +
            f'du {self.date_debut:%d/%m/%Y} au {self.date_fin:%d/%m/%Y}'
        )

