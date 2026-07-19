from django.db import models
from django.utils import timezone


class SecteurActivite(models.Model):
    """Un secteur d'activité (convention collective) : porte sa grille de salaires et son taux AT."""

    nom = models.CharField("Nom du secteur", max_length=150, unique=True)
    description = models.CharField("Description", max_length=255, blank=True)
    taux_at = models.DecimalField("Taux Accident de Travail du secteur (%)", max_digits=5, decimal_places=2, default=3)
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nom

    class Meta:
        verbose_name = "Secteur d'activité"
        verbose_name_plural = "Secteurs d'activité"
        ordering = ["nom"]


class CategorieSalaire(models.Model):
    """La grille des salaires catégoriels, propre à chaque secteur."""

    secteur = models.ForeignKey(SecteurActivite, on_delete=models.CASCADE, related_name="grille", verbose_name="Secteur")
    code = models.CharField("Catégorie", max_length=20)
    salaire_minimum = models.DecimalField("Salaire minimum catégoriel (FCFA)", max_digits=12, decimal_places=2)
    ordre = models.IntegerField("Ordre d'affichage", default=0)

    def __str__(self):
        return f"{self.secteur.nom} — {self.code} : {self.salaire_minimum:,.0f} FCFA".replace(",", " ")

    class Meta:
        verbose_name = "Catégorie de salaire"
        verbose_name_plural = "Grille des salaires"
        ordering = ["secteur", "ordre"]
        unique_together = ("secteur", "code")


class Employeur(models.Model):
    """Une entité qui a des salariés : le cabinet OU un client OU une entité externe.
    Chaque employeur = son propre 'LOGIPAIE' (ses paramètres, primes, banques, employés)."""

    ARRONDI_CHOICES = [
        (1, "Au franc près"),
        (5, "Aux 5 F"),
        (10, "Aux 10 F"),
        (100, "Aux 100 F"),
    ]

    # Lien optionnel vers un client existant
    client = models.OneToOneField(
        "clients.Client", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="employeur", verbose_name="Client rattaché (laisser vide si cabinet ou externe)"
    )

    # Infos propres de l'employeur
    raison_sociale = models.CharField("Raison sociale", max_length=200)
    sigle = models.CharField("Sigle", max_length=50, blank=True)
    logo = models.ImageField("Logo de l'entreprise", upload_to="logos_employeurs/", blank=True, null=True)
    adresse = models.CharField("Adresse", max_length=255, blank=True)
    commune = models.CharField("Commune", max_length=100, blank=True)
    boite_postale = models.CharField("Boîte postale", max_length=50, blank=True)
    centre_impots = models.CharField("Centre des impôts", max_length=100, blank=True)
    rccm = models.CharField("RCCM N°", max_length=50, blank=True)
    ncc = models.CharField("NCC", max_length=20, blank=True)
    numero_cnps = models.CharField("N° employeur CNPS", max_length=30, blank=True)

    # Secteur d'activité (porte la grille de salaires et le taux AT)
    secteur = models.ForeignKey(
        "SecteurActivite", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="employeurs", verbose_name="Secteur d'activité"
    )

    # Réglages propres à l'entreprise (ton onglet PARAMÈTRES)
    signataire_nom = models.CharField("Nom du signataire", max_length=150, blank=True)
    signataire_qualite = models.CharField("Qualité du signataire", max_length=100, blank=True)
    jours_conges_par_mois = models.DecimalField("Jours de congés acquis par mois", max_digits=4, decimal_places=2, default=2.2)
    plafond_transport_exonere = models.DecimalField("Montant exonéré prime de transport (FCFA)", max_digits=10, decimal_places=2, default=30000)
    arrondi_net = models.IntegerField("Arrondi du net à payer", choices=ARRONDI_CHOICES, default=5)

    # Exercice comptable & apparence des documents de paie
    date_debut_premier_exercice = models.DateField(
        "Date de début du premier exercice", null=True, blank=True,
        help_text="Début d'activité, ou début de reprise si le client est repris, "
                  "ou année de la lettre de mission par défaut."
    )
    couleur_documents = models.CharField(
        "Couleur des documents de paie", max_length=7, blank=True, default="#e91e63",
        help_text="Code hexadécimal, ex. #e91e63 (rose K&L) ou #2e7d32 (vert)."
    )

    # RIB émetteur de l'entreprise (compte depuis lequel les salaires sont virés)
    banque_nom = models.CharField("Banque", max_length=100, blank=True, default="")
    banque_code = models.CharField("Code banque", max_length=5, blank=True, default="")
    banque_guichet = models.CharField("Code guichet (agence)", max_length=5, blank=True, default="")
    banque_numero_compte = models.CharField("Numéro de compte", max_length=20, blank=True, default="")
    banque_cle_rib = models.CharField("Clé RIB", max_length=2, blank=True, default="")
    banque_iban = models.CharField("IBAN", max_length=34, blank=True, default="")
    banque_intitule = models.CharField("Intitulé du compte (titulaire)", max_length=150, blank=True, default="")

    est_cabinet = models.BooleanField("Est le cabinet lui-même", default=False)
    date_creation = models.DateTimeField("Date d'ajout", auto_now_add=True)

    @property
    def nom_affiche(self):
        return self.raison_sociale

    def __str__(self):
        return self.raison_sociale

    class Meta:
        verbose_name = "Employeur"
        verbose_name_plural = "Employeurs"
        ordering = ["raison_sociale"]


class ParametrePaie(models.Model):
    """Les taux de cotisations d'UNE entreprise. Chaque employeur a les siens."""

    employeur = models.OneToOneField(
        Employeur, on_delete=models.CASCADE, related_name="parametres", verbose_name="Employeur"
    )

    # CNPS (en %)
    taux_cnps_retraite_salarie = models.DecimalField("CNPS Retraite - part salarié (%)", max_digits=5, decimal_places=2, default=6.3)
    taux_cnps_retraite_employeur = models.DecimalField("CNPS Retraite - part employeur (%)", max_digits=5, decimal_places=2, default=7.7)
    taux_cnps_pf = models.DecimalField("CNPS Prestations Familiales (%)", max_digits=5, decimal_places=2, default=5.0)
    taux_cnps_maternite = models.DecimalField("CNPS Assurance Maternité (%)", max_digits=5, decimal_places=2, default=0.75)
    plafond_cnps = models.DecimalField("Plafond mensuel CNPS (FCFA)", max_digits=12, decimal_places=2, default=3375000)

    # FDFP (en %)
    taux_fdfp_ta = models.DecimalField("FDFP Taxe d'Apprentissage (%)", max_digits=5, decimal_places=2, default=0.4)
    taux_fdfp_fpc = models.DecimalField("FDFP Formation Prof. Continue (%)", max_digits=5, decimal_places=2, default=1.2)
    # Impôts sur salaires à la charge de l'employeur (en %)
    taux_ce_local = models.DecimalField("Contribution employeur — local (%)", max_digits=5, decimal_places=2, default=0)
    taux_ce_expatrie = models.DecimalField("Contribution employeur — expatrié (%)", max_digits=5, decimal_places=2, default=9.2)
    taux_cn = models.DecimalField("Contribution nationale (%)", max_digits=5, decimal_places=2, default=1.2)

    # CMU (forfait)
    montant_cmu = models.DecimalField("CMU (forfait par personne, FCFA)", max_digits=10, decimal_places=2, default=1000)

    def __str__(self):
        return f"Paramètres de {self.employeur.raison_sociale}"

    class Meta:
        verbose_name = "Paramètre de paie"
        verbose_name_plural = "Paramètres de paie"


class PrimeConfiguree(models.Model):
    """La liste des primes/indemnités d'UNE entreprise (ta zone 'INDEMNITES ET PRIMES').
    Définie une fois, puis piochée dans les bulletins."""

    TRAITEMENT_CHOICES = [
        ("exonere", "Exonéré (ni impôt ni cotisation)"),
        ("imposable", "Imposable / cotisable à 100%"),
        ("abattement", "Imposable après abattement de 10%"),
        ("plafonne", "Exonéré jusqu'à un plafond, imposable au-delà"),
    ]

    employeur = models.ForeignKey(Employeur, on_delete=models.CASCADE, related_name="primes_configurees", verbose_name="Employeur")
    libelle = models.CharField("Libellé de la prime", max_length=100)
    traitement_fiscal = models.CharField("Nature fiscale", max_length=12, choices=TRAITEMENT_CHOICES, default="imposable")
    soumis_cnps = models.BooleanField("Soumise à la CNPS", default=True)
    montant_par_defaut = models.DecimalField("Montant par défaut (modifiable, FCFA)", max_digits=12, decimal_places=2, default=0)
    type_rubrique = models.CharField("Type", max_length=10, default="GAIN", choices=[("GAIN", "Gain (prime / indemnité)"), ("RETENUE", "Retenue")])
    plafond_exoneration = models.DecimalField(
        "Plafond d'exonération (FCFA)", max_digits=12, decimal_places=2, default=0,
        help_text="Utilisé uniquement si la nature fiscale est « Exonéré jusqu'à un plafond ». Ex : transport 30 000."
    )
    ordre = models.IntegerField("Ordre", default=0)

    def __str__(self):
        return f"{self.libelle} ({self.employeur.sigle or self.employeur.raison_sociale})"

    class Meta:
        verbose_name = "Prime configurée"
        verbose_name_plural = "Primes configurées (par entreprise)"
        ordering = ["employeur", "ordre"]


class Banque(models.Model):
    """La liste des banques d'UNE entreprise (ta zone 'LISTE DES BANQUES')."""

    employeur = models.ForeignKey(Employeur, on_delete=models.CASCADE, related_name="banques", verbose_name="Employeur")
    nom = models.CharField("Nom de la banque", max_length=100)
    code_banque = models.CharField("Code banque", max_length=5, blank=True, default="")
    code_guichet = models.CharField("Code guichet (agence)", max_length=5, blank=True, default="")
    numero_compte = models.CharField("Numéro de compte", max_length=20, blank=True, default="")
    cle_rib = models.CharField("Clé RIB", max_length=2, blank=True, default="")
    iban = models.CharField("IBAN", max_length=34, blank=True, default="")
    intitule_compte = models.CharField("Intitulé du compte", max_length=150, blank=True, default="")
    est_principal = models.BooleanField("Compte principal (émetteur des virements)", default=False)

    def __str__(self):
        return self.nom

    class Meta:
        verbose_name = "Banque"
        verbose_name_plural = "Banques (par entreprise)"
        ordering = ["nom"]


class Employe(models.Model):
    """Un salarié, rattaché à un employeur. Conservé en permanence, même après départ."""

    CIVILITE_CHOICES = [
        ("M.", "Monsieur"),
        ("Mme", "Madame"),
        ("Mlle", "Mademoiselle"),
    ]
    SEXE_CHOICES = [
        ("M", "Masculin"),
        ("F", "Féminin"),
    ]
    SITUATION_CHOICES = [
        ("celibataire", "Célibataire"),
        ("marie", "Marié(e)"),
        ("divorce", "Divorcé(e)"),
        ("veuf", "Veuf(ve)"),
    ]
    CONTRAT_CHOICES = [
        ("CDI", "CDI"),
        ("CDD", "CDD"),
        ("STAGE", "Stage"),
    ]
    PAIEMENT_CHOICES = [
        ("virement", "Virement bancaire"),
        ("especes", "Espèces"),
        ("cheque", "Chèque"),
        ("mobile", "Mobile Money"),
    ]
    STATUT_CHOICES = [
        ("ACTIF", "Actif"),
        ("SORTI", "Sorti"),
        ("SUSPENDU", "Suspendu"),
    ]
    TYPE_SALAIRE_CHOICES = [
        ("mensuel", "Mensuel"),
        ("journalier", "Journalier"),
    ]
    REGIME_CHOICES = [
        ("general", "Général"),
        ("agricole", "Agricole"),
        ("expatrie", "Expatrié"),
    ]

    # Rattachement
    employeur = models.ForeignKey(Employeur, on_delete=models.CASCADE, related_name="employes", verbose_name="Employeur")
    utilisateur = models.OneToOneField(
        "auth.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="fiche_employe", verbose_name="Compte utilisateur (si personnel du cabinet)"
    )

    # Identité
    matricule = models.CharField("Matricule", max_length=30)
    civilite = models.CharField("Civilité", max_length=5, choices=CIVILITE_CHOICES, default="M.")
    nom_prenoms = models.CharField("Noms & Prénoms", max_length=200)
    sexe = models.CharField("Sexe", max_length=1, choices=SEXE_CHOICES, default="M")
    date_naissance = models.DateField("Date de naissance", null=True, blank=True)
    lieu_naissance = models.CharField("Lieu de naissance", max_length=150, blank=True)
    nature_piece = models.CharField("Nature pièce d'identité", max_length=50, blank=True)
    numero_piece = models.CharField("Numéro pièce d'identité", max_length=50, blank=True)
    nationalite = models.CharField("Nationalité", max_length=100, default="IVOIRIENNE")
    situation_matrimoniale = models.CharField("Situation matrimoniale", max_length=15, choices=SITUATION_CHOICES, default="celibataire")
    nombre_enfants = models.IntegerField("Nombre d'enfants", default=0)
    adresse = models.CharField("Adresse", max_length=255, blank=True)
    telephone = models.CharField("Téléphone", max_length=30, blank=True)
    lieu_habitation = models.CharField("Lieu d'habitation", max_length=150, blank=True)
    lieu_travail = models.CharField("Lieu d'exécution du contrat", max_length=200, blank=True,
                                     help_text="Laisser vide pour utiliser l'adresse de l'entreprise par défaut.")
    poste = models.CharField("Poste occupé", max_length=150, blank=True,
                              help_text="Intitulé du poste réellement occupé (ex. Comptable, Chauffeur) — distinct du code emploi réglementaire.")
    duree_essai_mois = models.IntegerField("Durée de la période d'essai (mois)", null=True, blank=True,
                                           help_text="Renseignée automatiquement lors de la génération du contrat.")

    # Contrat & poste
    contrat = models.CharField("Type de contrat", max_length=10, choices=CONTRAT_CHOICES, default="CDI")
    date_signature_contrat = models.DateField("Date de signature du contrat", null=True, blank=True)
    duree_cdd_mois = models.IntegerField("Durée CDD (mois)", null=True, blank=True)
    date_entree = models.DateField("Date d'entrée")
    date_sortie = models.DateField("Date de sortie", null=True, blank=True)
    direction = models.CharField("Direction", max_length=100, blank=True)
    service = models.CharField("Service", max_length=100, blank=True)
    emploi = models.CharField("Emploi", max_length=100, blank=True)
    code_emploi = models.CharField("Code emploi", max_length=30, blank=True)
    emploi_ref = models.ForeignKey("Emploi", on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Emploi (liste)")
    regime = models.CharField("Régime", max_length=15, choices=REGIME_CHOICES, default="general")
    categorie = models.CharField("Catégorie", max_length=20, blank=True)
    type_salaire = models.CharField("Type de salaire", max_length=15, choices=TYPE_SALAIRE_CHOICES, default="mensuel")
    salaire_base = models.DecimalField("Salaire de base (FCFA)", max_digits=12, decimal_places=2, default=0)
    sursalaire = models.DecimalField("Sursalaire (complément au salaire catégoriel, FCFA)", max_digits=12, decimal_places=2, default=0)
    cmu_conjoint_a_charge = models.BooleanField("Conjoint à charge pour la CMU (conjoint sans emploi)", default=False)
    cmu_enfants_a_charge = models.BooleanField("Enfants à charge pour la CMU (décocher si le conjoint les couvre)", default=True)

    # Social
    non_soumis_cnps = models.BooleanField("Non soumis à la CNPS", default=False)
    numero_cnps = models.CharField("N° CNPS", max_length=30, blank=True)

    # Paiement
    MODE_PAIEMENT_CHOICES = [("mensuel", "Mensuel"), ("journalier", "Journalier"), ("ponctuel", "Ponctuel")]
    mode_paiement = models.CharField("Mode de paiement", max_length=15, choices=PAIEMENT_CHOICES, default="especes")
    numero_compte = models.CharField("Numéro de compte bancaire", max_length=50, blank=True)
    banque = models.CharField("Banque", max_length=100, blank=True)
    banque_code = models.CharField("Code banque", max_length=5, blank=True, default="")
    banque_guichet = models.CharField("Code guichet (agence)", max_length=5, blank=True, default="")
    banque_cle_rib = models.CharField("Clé RIB", max_length=2, blank=True, default="")
    banque_iban = models.CharField("IBAN", max_length=34, blank=True, default="")

    # Suivi
    # Suivi
    statut = models.CharField("Statut", max_length=15, choices=STATUT_CHOICES, default="ACTIF")
    motif_sortie = models.CharField("Motif de sortie", max_length=100, blank=True)

    # ===== Calcul des parts IGR (logique reprise de ton Excel) =====
    @property
    def parts_igr(self):
        from decimal import Decimal
        s = self.situation_matrimoniale
        if s != "celibataire":
            base = Decimal("2")
        elif self.nombre_enfants == 0:
            base = Decimal("1")
        else:
            base = Decimal("1.5")
        total = base + (Decimal(self.nombre_enfants) * Decimal("0.5"))
        return min(total, Decimal("5"))

    # ===== Ancienneté en années =====
    @property
    def anciennete_annees(self):
        fin = self.date_sortie or timezone.now().date()
        if not self.date_entree:
            return 0
        return (fin - self.date_entree).days // 365

    # ===== Taux prime d'ancienneté (barème CCI) =====
    @property
    def taux_anciennete(self):
        ans = self.anciennete_annees
        if ans < 2:
            return 0
        return min(2 + (ans - 2), 30)  # 2% à 2 ans, +1%/an

    def __str__(self):
        return f"{self.matricule} — {self.nom_prenoms}"
    @property
    def cumul_cdd_jours(self):
        """Nombre de jours écoulés depuis l'entrée, pour un CDD en cours."""
        from datetime import date
        if "CDD" not in (self.contrat or "").upper() or not self.date_entree:
            return 0
        fin = self.date_sortie or date.today()
        return max((fin - self.date_entree).days, 0)

    @property
    def alerte_requalification_cdd(self):
        """True si un CDD atteint/dépasse 2 ans de cumul (→ requalification en CDI, art. 15.4 & 15.10)."""
        return self.cumul_cdd_jours >= 730  # 2 ans

    @property
    def cdd_mois_ecoules(self):
        """Cumul du CDD exprimé en mois (arrondi), pour l'affichage."""
        return round(self.cumul_cdd_jours / 30.44, 1)

    @property
    def jours_avant_echeance(self):
        """Nombre de jours avant la fin du contrat (CDD/Stage), ou None si non applicable."""
        from datetime import date
        if self.contrat not in ("CDD", "STAGE") or not self.date_sortie or self.statut != "ACTIF":
            return None
        return (self.date_sortie - date.today()).days

    @property
    def echeance_proche(self):
        """True si le contrat CDD/Stage arrive à échéance dans 30 jours ou moins (et pas déjà dépassé)."""
        j = self.jours_avant_echeance
        return j is not None and 0 <= j <= 30
    
    @property
    def fin_essai_proche(self):
        """True si la période d'essai réelle (durée connue via le contrat généré) se termine dans 7 jours ou moins."""
        from datetime import date
        if not self.date_entree or not self.duree_essai_mois or self.statut != "ACTIF":
            return None
        mois_total = self.date_entree.month - 1 + self.duree_essai_mois
        annee_fin = self.date_entree.year + mois_total // 12
        mois_fin = mois_total % 12 + 1
        import calendar
        jour_fin = min(self.date_entree.day, calendar.monthrange(annee_fin, mois_fin)[1])
        fin_essai = self.date_entree.replace(year=annee_fin, month=mois_fin, day=jour_fin)
        jours_restants = (fin_essai - date.today()).days
        return 0 <= jours_restants <= 7
    
    def est_actif_sur(self, mois, annee):
        """True si le salarié est en activité pendant ce mois (entrée ≤ mois ≤ sortie)."""
        from datetime import date
        if self.statut == "SUSPENDU":
            return False
        # Dernier jour du mois considéré
        if mois == 12:
            fin_mois = date(annee, 12, 31)
        else:
            fin_mois = date(annee, mois + 1, 1) - timezone.timedelta(days=1)
        debut_mois = date(annee, mois, 1)
        # Pas encore entré : l'entrée est après la fin du mois
        if self.date_entree and self.date_entree > fin_mois:
            return False
        # Déjà sorti : la sortie est avant le début du mois
        if self.date_sortie and self.date_sortie < debut_mois:
            return False
        return True

    class Meta:
        verbose_name = "Employé"
        verbose_name_plural = "Employés"
        ordering = ["nom_prenoms"]
        unique_together = ("employeur", "matricule")
    


class BulletinPaie(models.Model):
    """Un bulletin de paie pour un employé, pour un mois. = une ligne de la feuille TRAITEMENT DE LA PAIE."""

    MOIS_CHOICES = [
        (1, "Janvier"), (2, "Février"), (3, "Mars"), (4, "Avril"),
        (5, "Mai"), (6, "Juin"), (7, "Juillet"), (8, "Août"),
        (9, "Septembre"), (10, "Octobre"), (11, "Novembre"), (12, "Décembre"),
    ]

    employe = models.ForeignKey(Employe, on_delete=models.CASCADE, related_name="bulletins", verbose_name="Employé")
    mois = models.IntegerField("Mois", choices=MOIS_CHOICES)
    annee = models.IntegerField("Année")

    # --- Variables du mois ---
    jours_travailles = models.DecimalField("Jours travaillés", max_digits=4, decimal_places=1, default=30)

    # --- GAINS ---
    salaire_base = models.DecimalField("Salaire de base", max_digits=12, decimal_places=2, default=0)
    sursalaire = models.DecimalField("Sursalaire", max_digits=12, decimal_places=2, default=0)
    heures_sup = models.DecimalField("Heures supplémentaires (montant)", max_digits=12, decimal_places=2, default=0)
    hsup_15 = models.DecimalField("Heures sup à 15%", max_digits=6, decimal_places=2, default=0)
    hsup_50 = models.DecimalField("Heures sup à 50%", max_digits=6, decimal_places=2, default=0)
    hsup_75 = models.DecimalField("Heures sup à 75%", max_digits=6, decimal_places=2, default=0)
    hsup_100 = models.DecimalField("Heures sup à 100%", max_digits=6, decimal_places=2, default=0)
    prime_transport = models.DecimalField("Prime de transport", max_digits=12, decimal_places=2, default=0)
    conge_paye = models.DecimalField("Congé payé", max_digits=12, decimal_places=2, default=0)
    conge_date_debut = models.DateField("Début du congé", null=True, blank=True)
    conge_date_fin = models.DateField("Fin du congé", null=True, blank=True)
    gratification = models.DecimalField("Gratification", max_digits=12, decimal_places=2, default=0)
    preavis = models.DecimalField("Préavis", max_digits=12, decimal_places=2, default=0)
    indemnite_licenciement = models.DecimalField("Indemnité de licenciement", max_digits=12, decimal_places=2, default=0)
    indemnite_transactionnelle = models.DecimalField("Indemnité transactionnelle de rupture", max_digits=12, decimal_places=2, default=0)
    frais_funeraires = models.DecimalField("Frais funéraires", max_digits=12, decimal_places=2, default=0)
    prime_precarite = models.DecimalField("Prime de précarité (fin de CDD)", max_digits=12, decimal_places=2, default=0)
    est_solde_tout_compte = models.BooleanField("Solde de tout compte", default=False)
    motif_sortie = models.CharField("Motif de sortie", max_length=60, blank=True)

    est_historique = models.BooleanField("Bulletin historique (repris, montants figés)", default=False)
    its_historique = models.DecimalField("ITS historique (figé)", max_digits=12, decimal_places=2, null=True, blank=True)
    cnps_salarie_historique = models.DecimalField("CNPS salarié historique (figé)", max_digits=12, decimal_places=2, null=True, blank=True)
    cmu_salarie_historique = models.DecimalField("CMU salarié historique (figé)", max_digits=12, decimal_places=2, null=True, blank=True)
    net_historique = models.DecimalField("Net payé historique (figé)", max_digits=12, decimal_places=2, null=True, blank=True)

    # --- RETENUES (hors ITS / CNPS, qui seront calculés) ---
    avance_acompte = models.DecimalField("Avance / Acompte", max_digits=12, decimal_places=2, default=0)
    montant_pret = models.DecimalField("Remboursement de prêt", max_digits=12, decimal_places=2, default=0)
    decaissement_pret = models.DecimalField("Décaissement de prêt (gain non imposable)", max_digits=12, decimal_places=2, default=0)
    autres_retenues = models.DecimalField("Autres retenues", max_digits=12, decimal_places=2, default=0)

    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Bulletin {self.get_mois_display()} {self.annee} — {self.employe.nom_prenoms}"

    class Meta:
        verbose_name = "Bulletin de paie"
        verbose_name_plural = "Bulletins de paie"
        ordering = ["-annee", "-mois"]
        unique_together = ("employe", "mois", "annee")


class LignePrime(models.Model):
    """Une prime/indemnité sur un bulletin. Peut être piochée dans les primes configurées
    de l'entreprise, ou saisie librement."""

    TRAITEMENT_CHOICES = [
        ("exonere", "Exonéré (ni impôt ni cotisation)"),
        ("imposable", "Imposable / cotisable à 100%"),
        ("abattement", "Imposable après abattement de 10%"),
        ("plafonne", "Exonéré jusqu'à un plafond, imposable au-delà"),
    ]

    bulletin = models.ForeignKey(BulletinPaie, on_delete=models.CASCADE, related_name="primes", verbose_name="Bulletin")
    prime_configuree = models.ForeignKey(
        PrimeConfiguree, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="utilisations", verbose_name="Prime du catalogue (optionnel)"
    )
    libelle = models.CharField("Libellé de la prime", max_length=100)
    montant = models.DecimalField("Montant", max_digits=12, decimal_places=2, default=0)
    type_rubrique = models.CharField("Type", max_length=10, default="GAIN", choices=[("GAIN", "Gain (prime / indemnité)"), ("RETENUE", "Retenue")])
    traitement_fiscal = models.CharField("Traitement fiscal (ITS)", max_length=12, choices=TRAITEMENT_CHOICES, default="imposable")
    soumis_cnps = models.BooleanField("Soumis à la CNPS", default=True)
    plafond_exoneration = models.DecimalField("Plafond d'exonération (FCFA)", max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.libelle} : {self.montant}"

    class Meta:
        verbose_name = "Prime / indemnité"
        verbose_name_plural = "Primes / indemnités"

class RubriqueRecurrente(models.Model):
    """Une rubrique du catalogue attachée à un salarié, avec un montant propre.
    Elle reviendra automatiquement sur chaque bulletin du salarié."""
    employe = models.ForeignKey(Employe, on_delete=models.CASCADE, related_name="rubriques_recurrentes", verbose_name="Salarié")
    rubrique = models.ForeignKey(PrimeConfiguree, on_delete=models.CASCADE, related_name="+", verbose_name="Rubrique")
    montant = models.DecimalField("Montant", max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.employe.nom_prenoms} — {self.rubrique.libelle} : {self.montant}"

    class Meta:
        verbose_name = "Rubrique récurrente du salarié"
        verbose_name_plural = "Rubriques récurrentes des salariés"

class Emploi(models.Model):
    """Emploi / code emploi configurable, réutilisé sur la fiche du personnel."""
    code = models.CharField("Code emploi", max_length=20)
    libelle = models.CharField("Libellé de l'emploi", max_length=100)
    ordre = models.IntegerField("Ordre", default=0)

    def __str__(self):
        return f"{self.code} — {self.libelle}"

    class Meta:
        verbose_name = "Emploi"
        verbose_name_plural = "Emplois"
        ordering = ["ordre", "code"]

class PeriodeEmploi(models.Model):
    """Historique d'une période d'emploi close (départ puis réembauche).
    La fiche Employe ne garde que la période EN COURS ; chaque période antérieure est archivée ici."""

    employe = models.ForeignKey(Employe, on_delete=models.CASCADE, related_name="periodes_anterieures", verbose_name="Salarié")
    matricule = models.CharField("Matricule utilisé sur cette période", max_length=30)
    contrat = models.CharField("Type de contrat", max_length=10, choices=Employe.CONTRAT_CHOICES)
    date_entree = models.DateField("Date d'entrée")
    date_sortie = models.DateField("Date de sortie")
    motif_sortie = models.CharField("Motif de sortie", max_length=100, blank=True)
    date_cloture = models.DateTimeField("Clôturée le", auto_now_add=True)

    def __str__(self):
        return f"{self.employe.nom_prenoms} — {self.matricule} ({self.date_entree} → {self.date_sortie})"

    class Meta:
        verbose_name = "Période d'emploi antérieure"
        verbose_name_plural = "Périodes d'emploi antérieures"
        ordering = ["-date_sortie"]

class ReglageGenerationAuto(models.Model):
    """Réglage de la génération automatique de la paie, par entreprise."""
    employeur = models.OneToOneField(Employeur, on_delete=models.CASCADE, related_name="reglage_generation", verbose_name="Employeur")
    active = models.BooleanField("Génération automatique activée", default=False)
    jour_du_mois = models.IntegerField("Jour du mois pour générer", default=28,
                                       help_text="Ex. 28. Utilise 31 pour « dernier jour du mois ».")
    derniere_execution = models.DateField("Dernière génération effectuée", null=True, blank=True)

    def __str__(self):
        etat = "activée" if self.active else "désactivée"
        return f"Génération auto {etat} — {self.employeur.raison_sociale}"

    class Meta:
        verbose_name = "Réglage de génération automatique"
        verbose_name_plural = "Réglages de génération automatique"
class DeclarationDASC(models.Model):
    """Montants saisis pour le DASC d'une entreprise et d'un exercice (par trimestre)."""
    employeur = models.ForeignKey(Employeur, on_delete=models.CASCADE, related_name="declarations_dasc")
    annee = models.IntegerField("Exercice")

    cotisations_t1 = models.DecimalField("Cotisations déclarées 1T", max_digits=14, decimal_places=2, default=0)
    cotisations_t2 = models.DecimalField("Cotisations déclarées 2T", max_digits=14, decimal_places=2, default=0)
    cotisations_t3 = models.DecimalField("Cotisations déclarées 3T", max_digits=14, decimal_places=2, default=0)
    cotisations_t4 = models.DecimalField("Cotisations déclarées 4T", max_digits=14, decimal_places=2, default=0)

    paiements_t1 = models.DecimalField("Paiements effectués 1T", max_digits=14, decimal_places=2, default=0)
    paiements_t2 = models.DecimalField("Paiements effectués 2T", max_digits=14, decimal_places=2, default=0)
    paiements_t3 = models.DecimalField("Paiements effectués 3T", max_digits=14, decimal_places=2, default=0)
    paiements_t4 = models.DecimalField("Paiements effectués 4T", max_digits=14, decimal_places=2, default=0)

    class Meta:
        verbose_name = "Déclaration DASC"
        verbose_name_plural = "Déclarations DASC"
        unique_together = ("employeur", "annee")

    def __str__(self):
        return f"DASC {self.employeur.raison_sociale} — {self.annee}"
class ReglementCNPS(models.Model):
    employeur = models.ForeignKey(Employeur, on_delete=models.CASCADE, related_name="reglements_cnps")
    annee = models.IntegerField("Exercice")
    mois = models.IntegerField("Mois")  # 1 à 12

    montant_paye = models.DecimalField("Montant payé", max_digits=14, decimal_places=2, default=0)
    date_paiement = models.DateField("Date du paiement", null=True, blank=True)
    reference = models.CharField("Référence du paiement", max_length=100, blank=True)

    class Meta:
        verbose_name = "Règlement CNPS"
        verbose_name_plural = "Règlements CNPS"
        unique_together = ("employeur", "annee", "mois")
        ordering = ["annee", "mois"]

    def __str__(self):
        return f"{self.employeur.raison_sociale} — {self.mois}/{self.annee}"
class Pret(models.Model):
    """Prêt sans intérêt accordé à un salarié, remboursé par mensualités sur le bulletin."""
    employe = models.ForeignKey(Employe, on_delete=models.CASCADE, related_name="prets")
    montant = models.DecimalField("Montant emprunté", max_digits=12, decimal_places=2)
    mensualite = models.DecimalField("Mensualité", max_digits=12, decimal_places=2)
    date_debut = models.DateField("Date de début (1er remboursement)")
    motif = models.CharField("Motif", max_length=200, blank=True)
    decaisse = models.BooleanField("Décaissement effectué (versé au salarié)", default=False)
    solde = models.BooleanField("Prêt soldé", default=False)
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Prêt"
        verbose_name_plural = "Prêts"
        ordering = ["-cree_le"]

    def total_rembourse(self):
        return round(sum((float(r.montant) for r in self.remboursements.all()), 0.0))

    def capital_restant(self):
        return round(float(self.montant) - self.total_rembourse())

    def est_actif(self):
        return not self.solde and self.capital_restant() > 0

    def __str__(self):
        return f"Prêt {self.montant} — {self.employe.nom_prenoms}"


class RemboursementPret(models.Model):
    """Une mensualité de remboursement, reportée sur le bulletin d'un mois (retenue)."""
    pret = models.ForeignKey(Pret, on_delete=models.CASCADE, related_name="remboursements")
    mois = models.IntegerField()
    annee = models.IntegerField()
    montant = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        unique_together = ("pret", "mois", "annee")
        ordering = ["annee", "mois"]

class DocumentArchive(models.Model):
    """Archive d'un document produit (PDF/Excel), stocké en base.
    Règle de figement : modifiable tant qu'on est dans l'année civile de création ; figé ensuite."""
    employeur = models.ForeignKey(Employeur, on_delete=models.CASCADE, related_name="documents_archives")
    employe = models.ForeignKey(Employe, on_delete=models.SET_NULL, null=True, blank=True, related_name="documents_archives")

    type_doc = models.CharField("Type de document", max_length=50)   # ex: 'bulletin', 'attestation_travail'...
    libelle = models.CharField("Libellé", max_length=200)            # ex: "Attestation de travail — SAM-00001"
    cle = models.CharField("Clé d'unicité", max_length=200, db_index=True)  # identifie un doc (type+cible+période)

    # Le fichier stocké en base
    contenu = models.BinaryField("Contenu du fichier")
    nom_fichier = models.CharField("Nom du fichier", max_length=200)
    content_type = models.CharField("Type MIME", max_length=100, default="application/pdf")

    # Rattachements / tri
    mois = models.IntegerField("Mois", null=True, blank=True)
    annee = models.IntegerField("Année (exercice)", null=True, blank=True)

    cree_le = models.DateTimeField("Créé le", auto_now_add=True)
    modifie_le = models.DateTimeField("Modifié le", auto_now=True)
    annee_creation = models.IntegerField("Année civile de création")  # sert au figement

    class Meta:
        verbose_name = "Document archivé"
        verbose_name_plural = "Documents archivés"
        ordering = ["-cree_le"]

    def est_fige(self):
        """Figé si l'année civile actuelle est postérieure à l'année de création."""
        from django.utils import timezone
        return timezone.now().year > self.annee_creation

    def __str__(self):
        return f"{self.libelle} ({self.employeur.raison_sociale})"


class Conge(models.Model):
    """Un congé posé par un salarié (période réelle départ → retour).
    Enregistrement maître : sert d'historique et alimente le champ conge_paye des bulletins concernés.
    L'indemnité est répartie sur les mois touchés (portion par mois)."""
    employe = models.ForeignKey(Employe, on_delete=models.CASCADE, related_name="conges", verbose_name="Salarié")
    TYPE_CHOICES = [
        ("annuel", "Congé annuel (décompté du compteur)"),
        ("exceptionnel", "Congé exceptionnel (mariage, décès, naissance…)"),
    ]
    type_conge = models.CharField("Type de congé", max_length=15, choices=TYPE_CHOICES, default="annuel")
    date_depart = models.DateField("Date de départ en congé")
    date_retour = models.DateField("Date de retour (reprise du travail)")
    jours_ouvrables = models.IntegerField("Jours ouvrables de congé", default=0)
    montant_total = models.DecimalField("Indemnité totale de congé (FCFA)", max_digits=12, decimal_places=2, default=0)
    motif = models.CharField("Motif (facultatif)", max_length=200, blank=True, default="")
    cree_le = models.DateTimeField("Créé le", auto_now_add=True)

    def __str__(self):
        return f"Congé {self.employe.nom_prenoms} ({self.date_depart} → {self.date_retour})"

    class Meta:
        verbose_name = "Congé"
        verbose_name_plural = "Congés"
        ordering = ["-date_depart"]


class Absence(models.Model):
    """Une période d'absence d'un salarié, saisie via le pointage."""
    MOTIF_CHOICES = [
        ("maladie", "Maladie justifiée (salaire maintenu)"),
        ("injustifiee", "Absence injustifiée (salaire réduit)"),
        ("autorisee_non_payee", "Absence autorisée non payée (salaire réduit)"),
        ("autre", "Autre motif"),
    ]
    employe = models.ForeignKey(Employe, on_delete=models.CASCADE, related_name="absences", verbose_name="Salarié")
    date_debut = models.DateField("Date de début")
    date_fin = models.DateField("Date de fin")
    motif = models.CharField("Motif", max_length=25, choices=MOTIF_CHOICES, default="maladie")
    retire_jours = models.BooleanField(
        "Retirer les jours du bulletin (impact salaire)", default=True,
        help_text="Décoche si l'absence ne doit pas réduire le salaire, malgré le motif.")
    justificatif = models.CharField("Référence du justificatif (facultatif)", max_length=200, blank=True, default="")
    cree_le = models.DateTimeField("Enregistré le", auto_now_add=True)

    @property
    def impacte_salaire(self):
        if self.motif == "maladie":
            return False  # toujours neutre, quelle que soit la case cochée
        return self.retire_jours

    def __str__(self):
        return f"Absence {self.employe.nom_prenoms} ({self.date_debut} → {self.date_fin})"

    class Meta:
        verbose_name = "Absence"
        verbose_name_plural = "Absences"
        ordering = ["-date_debut"]


class JourFerie(models.Model):
    """Un jour férié chômé, saisi par le cabinet. Utilisé pour exclure ces jours du décompte des congés.
    Les fêtes à date variable (Aïd, Pâques mobile…) sont saisies chaque année."""
    date = models.DateField("Date du jour férié", unique=True)
    libelle = models.CharField("Libellé", max_length=100)

    def __str__(self):
        return f"{self.date:%d/%m/%Y} — {self.libelle}"

    class Meta:
        verbose_name = "Jour férié"
        verbose_name_plural = "Jours fériés"
        ordering = ["date"]

class MouvementPersonnel(models.Model):
    """Journal des mouvements RH significatifs : embauche, sortie, transformation, réembauche."""
    TYPE_CHOICES = [
        ("embauche", "Embauche"),
        ("transformation_cdi", "Transformation CDD → CDI"),
        ("sortie", "Sortie / fin de contrat"),
        ("reembauche", "Réembauche"),
        ("changement_salaire", "Changement de salaire"),
        ("changement_poste", "Changement de poste"),
    ]
    employe = models.ForeignKey(Employe, on_delete=models.CASCADE, related_name="mouvements", verbose_name="Salarié")
    employeur = models.ForeignKey(Employeur, on_delete=models.CASCADE, related_name="mouvements_personnel", verbose_name="Employeur")
    type_mouvement = models.CharField("Type de mouvement", max_length=20, choices=TYPE_CHOICES)
    date_mouvement = models.DateField("Date du mouvement")
    detail = models.CharField("Détail", max_length=250, blank=True, default="")
    cree_le = models.DateTimeField("Enregistré le", auto_now_add=True)

    def __str__(self):
        return f"{self.get_type_mouvement_display()} — {self.employe.nom_prenoms} ({self.date_mouvement})"

    class Meta:
        verbose_name = "Mouvement du personnel"
        verbose_name_plural = "Mouvements du personnel"
        ordering = ["-date_mouvement", "-cree_le"]