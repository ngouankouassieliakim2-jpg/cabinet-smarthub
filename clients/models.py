from django.db import models
from django.utils import timezone


class Client(models.Model):
    STATUT_CHOICES = [
        ("EN_PREPARATION", "En préparation"),
        ("EN_ATTENTE", "En attente d'activation"),
        ("A_VERIFIER", "En attente de vérification d'identité"),
        ("ACTIF", "Actif"),
        ("SUSPENDU", "Suspendu"),
        ("ARCHIVE", "Archivé"),
    ]

    TYPE_CLIENT_CHOICES = [
        ("PP_INFORMEL", "Personne Physique — secteur informel"),
        ("PP_CONSTITUEE", "Personne Physique légalement constituée"),
        ("PM", "Personne Morale"),
    ]

    # --- Lien vers le devis d'origine (la clé d'entrée) ---
    devis_origine = models.ForeignKey(
        "devis.Devis", on_delete=models.PROTECT, related_name="clients_crees",
        verbose_name="Devis d'origine"
    )

    # --- Compte de connexion du client (créé à la validation) ---
    compte = models.OneToOneField(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="client_lie",
        verbose_name="Compte de connexion",
    )

    # --- Suivi du parcours de première connexion ---
    mdp_change = models.BooleanField("Mot de passe changé", default=False)
    lettre_confirmee = models.BooleanField("Lettre de mission confirmée", default=False)
    consentement_signature_electronique = models.BooleanField(
        "Consentement signature électronique", default=False)
    cgv_acceptees = models.BooleanField("CGV acceptées", default=False)

    # --- Infos d'identité (pré-remplies depuis le devis, puis corrigeables) ---
    nom = models.CharField("Nom / Raison sociale", max_length=200, blank=True)
    type_client = models.CharField("Type de client", max_length=20, choices=TYPE_CLIENT_CHOICES, blank=True)
    ncc = models.CharField("N° Compte Contribuable (NCC)", max_length=20, blank=True)

    # --- Contact ---
    telephone = models.CharField("Téléphone", max_length=30, blank=True)
    email = models.EmailField("Email", blank=True)

    # --- Localisation ---
    ville = models.CharField("Ville", max_length=100, blank=True)
    commune = models.CharField("Commune", max_length=100, blank=True)
    quartier = models.CharField("Quartier", max_length=100, blank=True)

    # --- Informations complémentaires (ajoutées par le secrétariat) ---
    logo_entreprise = models.ImageField("Logo de l'entreprise", upload_to="logos_clients/", blank=True, null=True)
    slogan = models.CharField("Slogan de l'entreprise", max_length=255, blank=True)

    # Utilisateur principal (contact de référence ; pré-rempli depuis le dirigeant du devis)
    user_principal_nom = models.CharField("Utilisateur principal — Nom et prénoms", max_length=200, blank=True)
    user_principal_piece_nature = models.CharField("Utilisateur principal — Nature de la pièce", max_length=100, blank=True)
    user_principal_piece_numero = models.CharField("Utilisateur principal — N° de la pièce", max_length=50, blank=True)
    user_principal_qualite = models.CharField("Utilisateur principal — Qualité", max_length=100, blank=True)

    # Observations du secrétariat (visibles par les autres membres du cabinet)
    observations = models.TextField("Observations sur le client", blank=True)

    # --- Éléments d'activation ---
    email_acces = models.EmailField("Email de réception des accès", blank=True)
    lettre_mission = models.FileField("Lettre de mission signée", upload_to="lettres_mission/", blank=True, null=True)

    # --- Suivi ---
    statut = models.CharField("Statut", max_length=25, choices=STATUT_CHOICES, default="EN_PREPARATION")
    code_client = models.CharField("Code client", max_length=20, unique=True, blank=True)
    date_entree = models.DateTimeField("Date d'entrée au cabinet", auto_now_add=True)
    gestionnaire = models.CharField("Gestionnaire attitré", max_length=100, blank=True)
    notes = models.TextField("Notes internes", blank=True)

    # --- Pré-remplissage des infos depuis le devis ---
    def remplir_depuis_devis(self):
        """Copie les infos du devis d'origine dans les champs du client.
        Appelé à la création du dossier, avant correction par la secrétaire."""
        d = self.devis_origine
        self.nom = d.pm_raison_sociale or d.pp_nom_prenoms or ""
        self.type_client = d.type_client
        self.ncc = d.ncc
        self.telephone = d.telephone
        self.email = d.email
        self.ville = d.siege_ville
        self.commune = d.siege_commune
        self.quartier = d.siege_quartier
        # Utilisateur principal : pré-rempli depuis le dirigeant du devis (modifiable ensuite)
        self.user_principal_nom = d.dirigeant_nom or d.pp_nom_prenoms or ""
        self.user_principal_qualite = d.dirigeant_qualite or ""

    @property
    def type_client_display(self):
        return self.get_type_client_display()

    # --- Génération du code client auto ---
    def save(self, *args, **kwargs):
        if not self.code_client:
            annee = timezone.now().year
            prefixe = f"CLI-{annee}-"
            dernier = Client.objects.filter(code_client__startswith=prefixe).order_by("-code_client").first()
            if dernier:
                nouveau_num = int(dernier.code_client.split("-")[-1]) + 1
            else:
                nouveau_num = 1
            self.code_client = f"{prefixe}{nouveau_num:04d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code_client} — {self.nom or 'Sans nom'}"

    class Meta:
        verbose_name = "Client"
        verbose_name_plural = "Clients"
        ordering = ["-date_entree"]