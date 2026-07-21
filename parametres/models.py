from django.db import models
from solo.models import SingletonModel


class CategoriePrestation(models.Model):
    REGIME_CHOICES = [
        ("RECURRENTE", "Récurrente (suivi régulier)"),
        ("PONCTUELLE", "Ponctuelle (prestation unique)"),
    ]
    nom = models.CharField("Nom de la catégorie", max_length=120)
    regime = models.CharField("Régime", max_length=12, choices=REGIME_CHOICES, default="RECURRENTE")
    duree_engagement_mois = models.PositiveIntegerField(
        "Durée d'engagement (mois) — pour le régime récurrent", default=12,
        help_text="Durée initiale avant tacite reconduction. Ignoré pour le ponctuel.")
    preavis_mois = models.PositiveIntegerField(
        "Préavis de résiliation (mois) — pour le régime récurrent", default=3,
        help_text="Ignoré pour le ponctuel.")
    modalites_paiement = models.CharField(
        "Modalités de paiement", max_length=255, blank=True,
        help_text="Ex : mensuels payables le 5 / à la remise des livrables")

    def __str__(self):
        return f"{self.nom} ({self.get_regime_display()})"

    class Meta:
        verbose_name = "Catégorie de prestation"
        verbose_name_plural = "Catégories de prestations"
        ordering = ["nom"]


class PrestationCatalogue(models.Model):
    TVA_CHOICES = [
        ("18", "TVA 18% (taux normal)"),
        ("9", "TVA 9% (taux réduit)"),
        ("0", "Exonéré (0%)"),
    ]
    categorie = models.ForeignKey(CategoriePrestation, on_delete=models.CASCADE,
                                  related_name="prestations", verbose_name="Catégorie")
    libelle = models.CharField("Libellé de la prestation", max_length=200)
    prix_par_defaut = models.DecimalField("Prix de base (si pas de variantes, FCFA)",
                                          max_digits=12, decimal_places=2, default=0)
    periodicite = models.CharField("Périodicité", max_length=50, blank=True,
                                   help_text="Ex : Mensuel, Trimestriel, Annuel, Ponctuel")
    taux_tva = models.CharField("Taux de TVA", max_length=2, choices=TVA_CHOICES, default="18")
    delai_livraison = models.CharField("Délai de livraison", max_length=100, blank=True,
                                       help_text="Ex : 15 jours ouvrés à compter de la réception des pièces")
    livrable = models.CharField("Livrable (document à remettre)", max_length=255, blank=True,
                                help_text="Ex : États financiers annuels, rapport d'audit…")

    def __str__(self):
        return self.libelle

    class Meta:
        verbose_name = "Prestation"
        verbose_name_plural = "Prestations"
        ordering = ["libelle"]


class VariantePrix(models.Model):
    prestation = models.ForeignKey(PrestationCatalogue, on_delete=models.CASCADE,
                                   related_name="variantes", verbose_name="Prestation")
    libelle = models.CharField("Critère / tranche", max_length=150,
                               help_text="Ex : 1 à 5 salariés, RNI, CA < 50M, secteur BTP…")
    prix = models.DecimalField("Prix (FCFA)", max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.libelle} — {self.prix}"

    class Meta:
        verbose_name = "Variante de prix"
        verbose_name_plural = "Variantes de prix"
        ordering = ["prix"]


class ParametresEmail(models.Model):
    """Réglages d'envoi des emails (fiche unique du cabinet). Réutilisable partout."""
    adresse_envoi = models.EmailField("Adresse Gmail d'envoi", blank=True,
                                      help_text="L'adresse qui enverra les emails")
    mot_de_passe_app = models.CharField("Mot de passe d'application (16 caractères)",
                                        max_length=100, blank=True,
                                        help_text="Code généré par Google, pas le mot de passe Gmail habituel")
    nom_expediteur = models.CharField("Nom de l'expéditeur", max_length=120, blank=True,
                                      default="Cabinet K&L",
                                      help_text="Ex : Cabinet K&L — apparaît comme nom de l'expéditeur")

    def __str__(self):
        return f"Réglages email ({self.adresse_envoi or 'non configuré'})"

    class Meta:
        verbose_name = "Paramètres email"
        verbose_name_plural = "Paramètres email"

    @classmethod
    def get_solo(cls):
        """Récupère la fiche unique (la crée si elle n'existe pas)."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def est_configure(self):
        """Vrai si l'adresse et le mot de passe sont renseignés."""
        return bool(self.adresse_envoi and self.mot_de_passe_app)


class ParametresFNE(models.Model):
    """Réglages d'accès à la plateforme FNE de la DGI (fiche unique du cabinet)."""
    ENVIRONNEMENT_CHOICES = [
        ("TEST", "Environnement de test"),
        ("PROD", "Environnement de production"),
    ]
    environnement = models.CharField("Environnement actif", max_length=5,
                                     choices=ENVIRONNEMENT_CHOICES, default="TEST")
    url_test = models.URLField("URL de l'environnement de test", default="http://54.247.95.108/ws",
                               help_text="Fournie par la DGI — normalement pas besoin d'y toucher")
    url_production = models.URLField("URL de production", blank=True,
                                     help_text="Transmise par la DGI par email, après validation de l'interfaçage")
    api_key = models.CharField("Clé API (Bearer token)", max_length=255, blank=True,
                               help_text="Visible uniquement par le gestionnaire principal, dans l'onglet "
                                         "« Paramétrage » de l'espace FNE, une fois l'interfaçage validé par la DGI")
    ncc_cabinet = models.CharField("NCC du cabinet (émetteur)", max_length=20, blank=True)
    point_de_vente_defaut = models.CharField("Point de vente par défaut", max_length=150, blank=True,
                                             help_text="Utilisé pour pré-remplir les nouvelles factures")
    etablissement_defaut = models.CharField("Établissement par défaut", max_length=150, blank=True)

    class Meta:
        verbose_name = "Paramètres FNE (DGI)"
        verbose_name_plural = "Paramètres FNE (DGI)"

    def __str__(self):
        return f"Paramètres FNE ({self.get_environnement_display()})"

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def url_active(self):
        """L'URL à utiliser réellement, selon l'environnement sélectionné."""
        if self.environnement == "PROD" and self.url_production:
            return self.url_production
        return self.url_test

    @property
    def est_configure(self):
        """Vrai si une clé API est renseignée (condition minimale pour appeler la FNE)."""
        return bool(self.api_key and self.url_active)


class ParametresMobileMoney(SingletonModel):
    """Réglages d'accès aux API Wave et Orange Money (fiche unique du cabinet)."""

    ENVIRONNEMENT_CHOICES = [
        ("TEST", "Environnement de test"),
        ("PROD", "Environnement de production"),
    ]

    wave_environnement = models.CharField(
        "Wave — Environnement actif", max_length=5,
        choices=ENVIRONNEMENT_CHOICES, default="TEST")
    wave_api_key = models.CharField(
        "Wave — Clé API (Bearer token)", max_length=255, blank=True,
        help_text="Format wave_sn_test_... ou wave_sn_prod_..., générée dans le portail Wave Business, section Développeurs")
    wave_signature_activee = models.BooleanField(
        "Wave — Signature des requêtes activée", default=False,
        help_text="⚠️ Une fois activée sur une clé API (côté portail Wave), elle ne peut plus être désactivée sans révoquer la clé et en recréer une nouvelle")
    wave_signing_secret = models.CharField(
        "Wave — Secret de signature (HMAC)", max_length=255, blank=True,
        help_text="Format wave_sn_AKS_... — affiché une seule fois à la création de la clé API si la signature est activée. Sert à signer nos requêtes sortantes (en-tête Wave-Signature), pas à vérifier les webhooks entrants.")
    wave_webhook_secret = models.CharField(
        "Wave — Secret webhook", max_length=255, blank=True,
        help_text="Utilisé pour vérifier l'authenticité des notifications reçues de Wave")

    om_environnement = models.CharField(
        "Orange Money — Environnement actif", max_length=5,
        choices=ENVIRONNEMENT_CHOICES, default="TEST")
    om_client_id = models.CharField(
        "Orange Money — Client ID", max_length=255, blank=True,
        help_text="Fourni par Orange Developer lors de l'inscription au service Web Payment")
    om_client_secret = models.CharField(
        "Orange Money — Client Secret", max_length=255, blank=True)
    om_merchant_key = models.CharField(
        "Orange Money — Clé marchand", max_length=255, blank=True,
        help_text="Distincte du client_id/secret — fournie séparément par Orange")
    om_return_url = models.URLField(
        "Orange Money — URL de retour (paiement réussi)", blank=True)
    om_cancel_url = models.URLField(
        "Orange Money — URL d'annulation", blank=True)
    om_notif_url = models.URLField(
        "Orange Money — URL de notification (webhook)", blank=True,
        help_text="URL de ce serveur qu'Orange appellera pour confirmer un paiement")

    class Meta:
        verbose_name = "Paramètres Mobile Money (Wave / Orange Money)"
        verbose_name_plural = "Paramètres Mobile Money (Wave / Orange Money)"

    def __str__(self):
        return "Paramètres Mobile Money"

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def wave_configure(self):
        return bool(self.wave_api_key)

    @property
    def orange_money_configure(self):
        return bool(self.om_client_id and self.om_client_secret and self.om_merchant_key)


class ParametresWhatsAppBusiness(SingletonModel):
    """Réglages d'accès à l'API WhatsApp Business Cloud (Meta)."""

    access_token = models.CharField(
        "Access Token", max_length=512, blank=True,
        help_text="Idéalement un token permanent généré via un utilisateur système")
    phone_number_id = models.CharField(
        "Phone Number ID", max_length=50, blank=True,
        help_text="Identifiant technique Meta du numéro WhatsApp")
    whatsapp_business_account_id = models.CharField(
        "WhatsApp Business Account ID (WABA)", max_length=50, blank=True)
    app_id = models.CharField("App ID (Meta for Developers)", max_length=50, blank=True)
    app_secret = models.CharField("App Secret", max_length=255, blank=True)
    verify_token = models.CharField(
        "Verify Token (webhook)", max_length=255, blank=True,
        help_text="Chaîne inventée par le cabinet, à renseigner aussi côté Meta")

    class Meta:
        verbose_name = "Paramètres WhatsApp Business"
        verbose_name_plural = "Paramètres WhatsApp Business"

    def __str__(self):
        return "Paramètres WhatsApp Business"

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def est_configure(self):
        return bool(self.access_token and self.phone_number_id)


# ============ CONDITIONS GÉNÉRALES D'UTILISATION ============

TEXTE_CGV_DEFAUT = """CONDITIONS GÉNÉRALES D'UTILISATION DU PORTAIL CLIENT

1. OBJET
Le présent portail est mis à disposition par le Cabinet Comptable & Fiscal K&L afin de faciliter les échanges entre le cabinet et ses clients : transmission de documents, suivi des dossiers, consultation des informations comptables et fiscales.

2. ACCÈS ET IDENTIFIANTS
L'accès au portail est strictement personnel et confidentiel. Le client s'engage à conserver ses identifiants de connexion de manière sécurisée et à ne pas les communiquer à des tiers. Toute action effectuée depuis le compte du client est réputée effectuée par lui-même.

3. UTILISATION DU SERVICE
Le client s'engage à utiliser le portail conformément à sa destination professionnelle. Il s'interdit toute utilisation frauduleuse, ainsi que toute tentative d'accès non autorisé aux systèmes du cabinet.

4. CONFIDENTIALITÉ ET SECRET PROFESSIONNEL
Le cabinet est tenu au secret professionnel. Les informations transmises via le portail sont traitées de manière confidentielle et ne sont accessibles qu'aux collaborateurs habilités du cabinet.

5. DOCUMENTS ET DONNÉES
Le client est responsable de l'exactitude des informations et documents qu'il transmet. Les documents mis à disposition sur le portail sont conservés conformément aux obligations légales et réglementaires en vigueur.

6. DISPONIBILITÉ
Le cabinet s'efforce d'assurer la disponibilité du portail. Toutefois, des interruptions peuvent survenir pour maintenance ou pour des raisons techniques indépendantes de sa volonté.

7. LETTRE DE MISSION
L'utilisation du portail s'inscrit dans le cadre de la mission définie par la lettre de mission signée entre le client et le cabinet. En cas de contradiction, la lettre de mission prévaut.

8. MODIFICATION DES CONDITIONS
Le cabinet se réserve le droit de modifier les présentes conditions. Le client en sera informé et devra les accepter pour continuer à utiliser le portail.

En cochant la case d'acceptation, le client reconnaît avoir lu et accepté l'intégralité des présentes conditions d'utilisation.
"""


class ConditionsUtilisation(models.Model):
    """Le texte des Conditions Générales d'Utilisation, affiché au client
    lors de sa première connexion. Un seul enregistrement (modifiable)."""

    texte = models.TextField("Texte des conditions d'utilisation", blank=True)
    date_modification = models.DateTimeField("Dernière modification", auto_now=True)

    class Meta:
        verbose_name = "Conditions d'utilisation"
        verbose_name_plural = "Conditions d'utilisation"

    def __str__(self):
        return "Conditions Générales d'Utilisation"

    @classmethod
    def get_solo(cls):
        """Récupère l'unique enregistrement (le crée s'il n'existe pas)."""
        obj = cls.objects.first()
        if obj is None:
            obj = cls.objects.create(texte=TEXTE_CGV_DEFAUT)
        return obj