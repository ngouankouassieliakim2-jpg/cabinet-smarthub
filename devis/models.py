from datetime import date, datetime, timedelta
from decimal import Decimal
from django.db import models
from django.db.models import Sum
from django.utils import timezone


class Budget(models.Model):
    categorie = models.ForeignKey("CategorieDepense", on_delete=models.PROTECT, related_name="budgets")
    exercice = models.PositiveIntegerField("Exercice (année)")
    mois = models.PositiveSmallIntegerField(
        "Mois", null=True, blank=True,
        help_text="Laisser vide pour un budget annuel, ou préciser 1-12 pour un budget mensuel")
    montant_alloue = models.DecimalField("Montant alloué", max_digits=12, decimal_places=0)
    actif = models.BooleanField("Actif", default=True)

    cree_par = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    SEUILS_ALERTE = [80, 90, 100]

    def _bornes_periode(self):
        if self.mois:
            debut = date(self.exercice, self.mois, 1)
            fin = date(self.exercice, self.mois + 1, 1) - timedelta(days=1) if self.mois < 12 else date(self.exercice, 12, 31)
        else:
            debut = date(self.exercice, 1, 1)
            fin = date(self.exercice, 12, 31)
        return debut, fin

    @property
    def consomme(self):
        debut, fin = self._bornes_periode()
        total = Depense.objects.filter(
            categorie=self.categorie, date_facture__gte=debut, date_facture__lte=fin,
        ).exclude(statut="ANNULEE").aggregate(total=Sum("montant_ht"))["total"]
        return total or Decimal("0")

    @property
    def disponible(self):
        return self.montant_alloue - self.consomme

    @property
    def taux_consommation(self):
        if self.montant_alloue == 0:
            return Decimal("0")
        return round((self.consomme / self.montant_alloue) * 100, 1)

    @classmethod
    def budget_disponible_pour(cls, categorie, a_date):
        if isinstance(a_date, str):
            a_date = datetime.strptime(a_date, "%Y-%m-%d").date()
        if isinstance(a_date, datetime):
            a_date = a_date.date()
        mensuel = cls.objects.filter(
            categorie=categorie, exercice=a_date.year, mois=a_date.month, actif=True).first()
        if mensuel:
            return mensuel
        return cls.objects.filter(
            categorie=categorie, exercice=a_date.year, mois__isnull=True, actif=True).first()

    def __str__(self):
        periode = f"{self.mois:02d}/{self.exercice}" if self.mois else str(self.exercice)
        return f"{self.categorie} — {periode} ({self.montant_alloue} FCFA)"

    class Meta:
        verbose_name = "Budget"
        verbose_name_plural = "Budgets"
        ordering = ["-exercice", "categorie"]
        constraints = [
            models.UniqueConstraint(fields=["categorie", "exercice", "mois"], name="unique_budget_periode")
        ]




class Devis(models.Model):
    # ===================== LISTES DE CHOIX =====================
    TYPE_CLIENT_CHOICES = [
        ("PP_INFORMEL", "Personne Physique — secteur informel"),
        ("PP_CONSTITUEE", "Personne Physique légalement constituée"),
        ("PM", "Personne Morale"),
    ]
    REGIME_CHOICES = [
        ("RNI", "Réel Normal d'Imposition (RNI)"),
        ("RSI", "Réel Simplifié d'Imposition (RSI)"),
        ("IM", "Impôt des Microentreprises (IM)"),
        ("TEE", "Taxe d'État de l'Entreprenant (TEE)"),
    ]
    STATUT_CHOICES = [
        ("BROUILLON", "Brouillon"),
        ("ENVOYE", "Envoyé au prospect"),
        ("VALIDE", "Validé (client intégré)"),
    ]
    REGIME_MISSION_CHOICES = [
        ("RECURRENTE", "Mission récurrente (suivi régulier)"),
        ("PONCTUELLE", "Mission ponctuelle (prestation unique)"),
    ]

    # ===================== SECTION 0 : ENTRÉE =====================
    numero_devis = models.CharField("Numéro de devis", max_length=20, unique=True, blank=True)
    type_client = models.CharField("Type de client", max_length=20, choices=TYPE_CLIENT_CHOICES, default="PM")
    statut = models.CharField("Statut du devis", max_length=15, choices=STATUT_CHOICES, default="BROUILLON")
    date_envoi = models.DateField("Date d'envoi au prospect", null=True, blank=True)
    nombre_relances = models.PositiveIntegerField("Nombre de relances effectuées", default=0)
    date_derniere_relance = models.DateField("Date de la dernière relance", null=True, blank=True)
    client_rattache = models.ForeignKey(
        "clients.Client", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="devis_supplementaires", verbose_name="Client rattaché (si client existant)"
    )
    date_creation = models.DateTimeField("Date de création", auto_now_add=True)
    date_modification = models.DateTimeField("Dernière modification", auto_now=True)

    # ============ SECTION 1A : IDENTITÉ — PERSONNE PHYSIQUE ============
    pp_nom_prenoms = models.CharField("Nom et prénoms", max_length=200, blank=True)
    pp_date_naissance = models.DateField("Date de naissance", null=True, blank=True)
    pp_lieu_naissance = models.CharField("Lieu de naissance", max_length=150, blank=True)
    pp_nationalite = models.CharField("Nationalité", max_length=100, blank=True)
    pp_nom_pere = models.CharField("Nom du père", max_length=200, blank=True)
    pp_nom_mere = models.CharField("Nom de la mère", max_length=200, blank=True)
    pp_piece_type = models.CharField("Type de pièce d'identité", max_length=50, blank=True)
    pp_piece_numero = models.CharField("N° de la pièce", max_length=50, blank=True)
    pp_piece_delivree_le = models.DateField("Pièce délivrée le", null=True, blank=True)
    pp_piece_delivree_a = models.CharField("Pièce délivrée à", max_length=100, blank=True)
    pp_adresse_perso = models.CharField("Adresse personnelle", max_length=255, blank=True)

    # ============ SECTION 1B : IDENTITÉ — PERSONNE MORALE ============
    pm_raison_sociale = models.CharField("Raison sociale", max_length=200, blank=True)
    pm_nom_commercial = models.CharField("Nom commercial", max_length=200, blank=True)
    pm_sigle = models.CharField("Sigle", max_length=50, blank=True)
    pm_forme_juridique = models.CharField("Forme juridique", max_length=100, blank=True)
    pm_capital_social = models.CharField("Capital social", max_length=50, blank=True)

    # ============ SECTION 2 : IDENTIFIANTS LÉGAUX (communs) ============
    ncc = models.CharField("N° Compte Contribuable (NCC)", max_length=20, blank=True)
    code_cdi = models.CharField("Code CDI", max_length=50, blank=True)
    rccm_numero = models.CharField("N° RCCM / RSC", max_length=50, blank=True)
    rccm_delivre_le = models.DateField("RCCM délivré le", null=True, blank=True)
    rccm_delivre_par = models.CharField("RCCM délivré par", max_length=150, blank=True)
    code_activite = models.CharField("Code activité", max_length=50, blank=True)
    regime_imposition = models.CharField("Régime d'imposition", max_length=5, choices=REGIME_CHOICES, blank=True)
    est_employeur = models.BooleanField("Qualité d'employeur", default=False)
    nombre_salaries = models.PositiveIntegerField("Nombre de salariés", default=0, null=True, blank=True,
                                                  help_text="Sert à déterminer les tranches de prix (paie, CNPS)")

    # ============ SECTION 3 : OBLIGATIONS FISCALES ============
    obl_patente = models.BooleanField("Patente", default=False)
    obl_bic_ba = models.BooleanField("Impôt BIC/BA", default=False)
    obl_bnc = models.BooleanField("Impôt BNC", default=False)
    obl_tva = models.BooleanField("TVA", default=False)
    obl_tob = models.BooleanField("TOB", default=False)
    obl_taxe_bois = models.BooleanField("Taxe ventes de bois en grumes", default=False)
    obl_its = models.BooleanField("ITS", default=False)
    obl_airsi = models.BooleanField("AIRSI", default=False)
    obl_tse = models.BooleanField("TSE", default=False)
    obl_impots_fonciers = models.BooleanField("Impôts fonciers", default=False)
    obl_impot_micro = models.BooleanField("Impôt microentreprises / TEE", default=False)
    obl_igr = models.BooleanField("IGR", default=False)
    obl_autres = models.CharField("Autres obligations fiscales", max_length=255, blank=True)

    EXONERATION_CHOICES = [
        ("AUCUNE", "Aucune"),
        ("TOTALE", "Exonération totale"),
        ("PARTIELLE", "Exonération partielle"),
    ]
    exoneration_type = models.CharField("Type d'exonération", max_length=10,
                                        choices=EXONERATION_CHOICES, default="AUCUNE", blank=True)
    exoneration_debut = models.DateField("Exonération — début", null=True, blank=True)
    exoneration_fin = models.DateField("Exonération — fin", null=True, blank=True)
    exoneration_fondement = models.CharField("Fondement de l'exonération", max_length=200, blank=True,
                                             help_text="Code des Investissements, Code minier, Code pétrolier, Régime franc, Autres…")

    # ============ SECTION 4 : LOCALISATION DU SIÈGE ============
    siege_ville = models.CharField("Ville", max_length=100, blank=True)
    siege_commune = models.CharField("Commune", max_length=100, blank=True)
    siege_quartier = models.CharField("Quartier", max_length=100, blank=True)
    siege_rue = models.CharField("Rue", max_length=150, blank=True)
    siege_lot = models.CharField("Lot", max_length=50, blank=True)
    siege_ilot = models.CharField("Ilot", max_length=50, blank=True)
    ref_section = models.CharField("Réf. cadastrale — Section", max_length=50, blank=True)
    ref_parcelle = models.CharField("Réf. cadastrale — Parcelle", max_length=50, blank=True)
    ref_tf = models.CharField("Titre Foncier N°", max_length=50, blank=True)
    boite_postale = models.CharField("Boîte postale", max_length=50, blank=True)

    # ============ SECTION 5 : CONTACTS ============
    telephone = models.CharField("Téléphone", max_length=30, blank=True)
    telephone2 = models.CharField("Téléphone 2", max_length=30, blank=True)
    email = models.EmailField("Email", blank=True)
    fax = models.CharField("Fax", max_length=30, blank=True)

    # ============ SECTION 6 : ACTIVITÉ ============
    activite_principale = models.CharField("Activité principale (nature exacte)", max_length=255, blank=True)
    activite_date_debut = models.DateField("Date de début d'activité", null=True, blank=True)
    autres_activites = models.TextField("Autres activités", blank=True)
    ca_previsionnel = models.CharField("Chiffre d'affaires prévisionnel", max_length=50, blank=True)
    ca_annee_precedente = models.CharField("Chiffre d'affaires de l'année précédente", max_length=50, blank=True)

    # ============ SECTION 7 : DIRIGEANT / GÉRANT (PM) ============
    dirigeant_nom = models.CharField("Nom et prénoms du dirigeant", max_length=200, blank=True)
    dirigeant_qualite = models.CharField("Qualité du dirigeant", max_length=100, blank=True)
    dirigeant_bp = models.CharField("BP du dirigeant", max_length=50, blank=True)
    dirigeant_tel = models.CharField("Téléphone du dirigeant", max_length=30, blank=True)
    dirigeant_email = models.EmailField("Email du dirigeant", blank=True)

    # Propriétaire du local professionnel (DFE rubrique H-a)
    proprietaire_nom = models.CharField("Propriétaire du local — Nom / Raison sociale", max_length=200, blank=True)
    proprietaire_ncc = models.CharField("Propriétaire du local — NCC", max_length=20, blank=True)
    proprietaire_adresse = models.CharField("Propriétaire du local — Adresse", max_length=255, blank=True)
    proprietaire_email = models.EmailField("Propriétaire du local — Email", blank=True)
    proprietaire_tel = models.CharField("Propriétaire du local — Téléphone", max_length=30, blank=True)

    # ============ SECTION 9 : SUIVI COMPTABLE ANTÉRIEUR ============
    a_eu_comptable = models.BooleanField("A déjà eu un cabinet/comptable", default=False)
    comptable_precedent_nom = models.CharField("Nom du cabinet/comptable précédent", max_length=200, blank=True)
    comptable_precedent_ncc = models.CharField("NCC du cabinet précédent", max_length=20, blank=True)
    comptable_precedent_adresse = models.CharField("Adresse du cabinet précédent", max_length=255, blank=True)
    comptable_precedent_email = models.EmailField("Email du cabinet précédent", blank=True)
    comptable_precedent_tel = models.CharField("Téléphone du cabinet précédent", max_length=30, blank=True)

    # ============ SECTION 10 : AUTRES ÉTABLISSEMENTS ============
    autres_etablissements = models.TextField("Autres établissements (entrepôt, magasin, succursale, usine, boutique...)", blank=True)

    # ============ SECTION 11 : DOCUMENTS SCANNÉS ============
    doc_rccm = models.FileField("RCCM (scan)", upload_to="documents/rccm/", blank=True, null=True)
    doc_dfe = models.FileField("DFE — Déclaration Fiscale d'Existence (scan)", upload_to="documents/dfe/", blank=True, null=True)
    doc_cnps = models.FileField("Attestation immatriculation CNPS (scan)", upload_to="documents/cnps/", blank=True, null=True)
    doc_tribunal_travail = models.FileField("Déclaration au Tribunal du Travail (scan)", upload_to="documents/tribunal/", blank=True, null=True)
    doc_piece_identite = models.FileField("Pièce d'identité du dirigeant/demandeur (scan)", upload_to="documents/pieces/", blank=True, null=True)
    doc_contrat_bail = models.FileField("Contrat de bail (si local loué)", upload_to="documents/baux/", blank=True, null=True)
    doc_statuts = models.FileField("Statuts de la société (PM)", upload_to="documents/statuts/", blank=True, null=True)

    # Visa et signature (DFE rubrique I)
    signataire_nom = models.CharField("Nom du signataire de la déclaration", max_length=200, blank=True)
    signataire_qualite = models.CharField("Qualité du signataire", max_length=100, blank=True)
    declaration_lieu = models.CharField("Déclaration faite à", max_length=100, blank=True)
    declaration_date = models.DateField("Date de la déclaration", null=True, blank=True)

    # ============ LETTRE DE MISSION GÉNÉRÉE (PDF) ============
    lettre_mission_pdf = models.FileField("Lettre de mission (PDF généré)", upload_to="lettres_mission/", blank=True, null=True)
    note_explicative = models.JSONField("Note explicative (générée par IA)", blank=True, null=True)

    # ============ REMISE GLOBALE ============
    remise_pourcentage = models.DecimalField("Remise globale (%)", max_digits=5, decimal_places=2, default=0,
                                              help_text="Remise appliquée sur le total HT (ex : 10 pour 10%)")

    # ============ SECTION 12 : SUIVI INTERNE / MISSION ============
    type_mission = models.CharField("Type de mission envisagée", max_length=200, blank=True)
    honoraires_proposes = models.CharField("Honoraires proposés", max_length=100, blank=True)
    etat_compta_reprise = models.CharField("État de la comptabilité à la reprise", max_length=255, blank=True)
    notes_internes = models.TextField("Notes internes", blank=True)

    # ===== Éléments pour la lettre de mission =====
    regime_mission = models.CharField("Régime de la mission", max_length=12,
                                      choices=REGIME_MISSION_CHOICES, default="RECURRENTE")
    date_effet_mission = models.DateField("Date d'effet de la mission", null=True, blank=True)
    duree_mission_mois = models.PositiveIntegerField("Durée de la mission (mois)",
                                                     default=12, null=True, blank=True)
    exercice_concerne = models.CharField("Exercice comptable concerné", max_length=9, blank=True,
                                         help_text="Ex : 2026")
    modalites_paiement = models.CharField("Modalités de paiement des honoraires", max_length=255,
                                          blank=True, help_text="Ex : mensuels payables le 5 de chaque mois")
    lieu_signature = models.CharField("Lieu de signature", max_length=100, default="Abidjan", blank=True)

    # ===== Génération automatique des factures récurrentes =====
    # La fréquence elle-même n'est PAS redéfinie ici : elle est déjà portée par
    # LignePrestation.periodicite (héritée du catalogue) — un même devis peut
    # mélanger des lignes mensuelles et annuelles. Seul le jour de génération
    # est réglable, il s'applique à tous les groupes de périodicité de ce devis.
    jour_emission_facture = models.PositiveSmallIntegerField(
        "Jour d'émission des factures récurrentes", default=5,
        help_text="Jour du mois où les factures récurrentes de cette mission sont générées automatiquement (plafonné les mois courts).")

    # ===== Modules concernés par ce dossier (case à cocher, Porte d'entrée) =====
    # Stocke une liste de clés parmi celles de pilotage.modules_data.MODULES
    # (ex : ["comptabilite", "social-rh"]). Volontairement une simple liste et non
    # une vraie relation en base tant que le chantier "Droits / Pôles" n'est pas
    # démarré — évite de figer un schéma avant que ce chantier soit cadré.
    modules_concernes = models.JSONField(
        "Modules concernés par ce dossier", default=list, blank=True,
        help_text="Modules métier qui interviendront sur ce dossier tout au long de la mission.")

    # ===== Circuit de validation de la lettre de mission (Porte d'entrée → Direction → Client) =====
    LETTRE_STATUT_CHOICES = [
        ("BROUILLON", "Brouillon (Porte d'entrée en cours)"),
        ("EN_VALIDATION_DIRECTION", "En attente de validation Direction"),
        ("VALIDEE_DIRECTION", "Validée et signée par la Direction"),
        ("ENVOYEE_CLIENT", "Envoyée au client"),
        ("SIGNEE_CLIENT", "Signée par le client"),
    ]
    lettre_statut = models.CharField(
        "Statut de la lettre de mission", max_length=25,
        choices=LETTRE_STATUT_CHOICES, default="BROUILLON")

    lettre_soumise_le = models.DateTimeField("Soumise à la Direction le", null=True, blank=True)
    lettre_soumise_par = models.ForeignKey(
        "auth.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="dossiers_soumis_direction", verbose_name="Soumise par (secrétariat)")

    lettre_validee_le = models.DateTimeField("Validée et signée (Direction) le", null=True, blank=True)
    lettre_validee_par = models.ForeignKey(
        "auth.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="dossiers_valides_direction", verbose_name="Validée par (Direction)")
    lettre_motif_refus = models.TextField(
        "Motif du refus / des corrections demandées", blank=True,
        help_text="Rempli par la Direction si le dossier est renvoyé au secrétariat pour correction.")

    lettre_signee_client_le = models.DateTimeField("Signée par le client le", null=True, blank=True)
    lettre_signataire_client = models.CharField(
        "Signataire client", max_length=200, blank=True,
        help_text="Nom de la personne ayant signé la lettre de mission côté client."
    )

    # ===== Identifiants utiles aux AUTRES modules (Paie/RH, Comptabilité/Fiscalité) =====
    centre_impots = models.CharField("Centre des impôts", max_length=150, blank=True,
                                     help_text="Utile pour la Comptabilité/Fiscalité et pour la Paie (fiche Employeur)")
    numero_cnps = models.CharField("N° employeur CNPS", max_length=30, blank=True,
                                   help_text="Numéro d'immatriculation employeur à la CNPS — nécessaire dès que 'Qualité d'employeur' est coché, utilisé par le module Paie/RH")

    # ===================== TOTAUX CALCULÉS =====================
    @property
    def total_ht_brut(self):
        return sum((ligne.total_ht for ligne in self.lignes.all()), Decimal("0"))

    @property
    def montant_remise(self):
        return self.total_ht_brut * (self.remise_pourcentage / Decimal("100"))

    @property
    def total_ht(self):
        return self.total_ht_brut - self.montant_remise

    @property
    def montant_tva(self):
        tva_brute = sum((ligne.montant_tva for ligne in self.lignes.all()), Decimal("0"))
        if self.total_ht_brut > 0:
            ratio_apres_remise = self.total_ht / self.total_ht_brut
            return tva_brute * ratio_apres_remise
        return Decimal("0")

    @property
    def total_ttc(self):
        return self.total_ht + self.montant_tva

    @property
    def est_modifiable(self):
        limite = self.date_modification + timedelta(days=30)
        return timezone.now() <= limite

    @property
    def date_limite_modification(self):
        return self.date_modification + timedelta(days=30)
    
    # ===================== GÉNÉRATION DU CODE AUTO =====================
    def save(self, *args, **kwargs):
        if not self.numero_devis:
            annee = timezone.now().year
            prefixe = f"DEV-{annee}-"
            dernier = Devis.objects.filter(numero_devis__startswith=prefixe).order_by("-numero_devis").first()
            if dernier:
                dernier_num = int(dernier.numero_devis.split("-")[-1])
                nouveau_num = dernier_num + 1
            else:
                nouveau_num = 1
            self.numero_devis = f"{prefixe}{nouveau_num:04d}"
        super().save(*args, **kwargs)

    def __str__(self):
        nom = self.pm_raison_sociale or self.pp_nom_prenoms or "Sans nom"
        return f"{self.numero_devis} — {nom}"

    class Meta:
        verbose_name = "Devis"
        verbose_name_plural = "Devis"
        ordering = ["-date_creation"]


class LignePrestation(models.Model):
    TVA_CHOICES = [
        ("18", "TVA 18% (taux normal)"),
        ("9", "TVA 9% (taux réduit)"),
        ("0", "Exonéré (0%)"),
    ]

    devis = models.ForeignKey(Devis, on_delete=models.CASCADE, related_name="lignes", verbose_name="Devis")
    designation = models.CharField("Désignation de la prestation", max_length=255)
    periodicite = models.CharField("Périodicité", max_length=50, blank=True,
                                   help_text="Ex : Mensuel, Trimestriel, Annuel, Ponctuel")
    quantite = models.DecimalField("Quantité", max_digits=10, decimal_places=2, default=1)
    prix_unitaire = models.DecimalField("Prix unitaire HT (FCFA)", max_digits=12, decimal_places=2, default=0)
    taux_tva = models.CharField("Taux de TVA", max_length=2, choices=TVA_CHOICES, default="18")

    @property
    def total_ht(self):
        return self.quantite * self.prix_unitaire

    @property
    def montant_tva(self):
        return self.total_ht * (Decimal(self.taux_tva) / Decimal("100"))

    @property
    def total_ttc(self):
        return self.total_ht + self.montant_tva

    def __str__(self):
        return f"{self.designation} ({self.total_ht} FCFA)"

    class Meta:
        verbose_name = "Ligne de prestation"
        verbose_name_plural = "Lignes de prestations"


class Associe(models.Model):
    """Associé ou actionnaire d'une personne morale (DFE rubrique F)."""
    devis = models.ForeignKey(Devis, on_delete=models.CASCADE, related_name="associes", verbose_name="Devis")
    nom = models.CharField("Nom et prénoms ou raison sociale", max_length=200)
    adresse = models.CharField("Adresse", max_length=255, blank=True)
    nationalite = models.CharField("Nationalité", max_length=100, blank=True)
    part_montant = models.DecimalField("Montant de la part (FCFA)", max_digits=15, decimal_places=2, default=0)
    part_pourcentage = models.DecimalField("Part (%)", max_digits=5, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.nom} ({self.part_pourcentage} %)"

    class Meta:
        verbose_name = "Associé / Actionnaire"
        verbose_name_plural = "Associés / Actionnaires"
        ordering = ["-part_pourcentage"]


class DocumentPiece(models.Model):
    """Pièce du dossier d'identification, collectée à Porte d'entrée.
    Remplace à terme les champs fichiers fixes (doc_rccm, doc_dfe, ...) par une
    ligne par document, avec un statut à 4 états qui permet de tracer un document
    absent — et, le cas échéant, de déclencher son ajout comme prestation facturable.
    NOTE : les anciens champs doc_* restent sur Devis pour l'instant (dossiers déjà
    en cours) ; le nouveau formulaire Porte d'entrée (Phase 3) n'utilisera plus que
    ce modèle-ci."""

    TYPE_CHOICES = [
        ("RCCM", "RCCM"),
        ("DFE", "DFE — Déclaration Fiscale d'Existence"),
        ("STATUTS", "Statuts de la société"),
        ("INSPECTION_TRAVAIL", "Déclaration à l'Inspection du Travail"),
        ("CNPS", "Notification d'immatriculation CNPS"),
        ("PIECE_GERANT", "Pièce d'identité du gérant / dirigeant"),
        ("CONTRAT_BAIL", "Contrat de bail"),
        ("AUTRE", "Autre document comptable ou administratif"),
    ]
    STATUT_CHOICES = [
        ("IGNORE", "Ignoré"),
        ("FOURNI", "Fourni"),
        ("ABSENT", "Absent — à établir par le cabinet (facturable)"),
    ]

    devis = models.ForeignKey(Devis, on_delete=models.CASCADE, related_name="documents", verbose_name="Devis / dossier")
    type_document = models.CharField("Type de document", max_length=20, choices=TYPE_CHOICES)
    libelle_libre = models.CharField(
        "Libellé (si Autre)", max_length=200, blank=True,
        help_text="Uniquement utilisé pour le type 'Autre document comptable ou administratif'")
    statut = models.CharField("Statut", max_length=15, choices=STATUT_CHOICES, default="IGNORE")
    fichier = models.FileField("Fichier", upload_to="documents/porte_entree/", blank=True, null=True)
    commentaire = models.CharField("Commentaire", max_length=255, blank=True)
    ligne_facturable_ajoutee = models.BooleanField(
        "Ligne de prestation ajoutée pour ce document", default=False,
        help_text="Coché automatiquement dès qu'une ligne de prestation a été ajoutée au devis pour ce document manquant.")
    date_maj = models.DateTimeField("Dernière mise à jour", auto_now=True)

    def __str__(self):
        libelle = self.libelle_libre if (self.type_document == "AUTRE" and self.libelle_libre) else self.get_type_document_display()
        return f"{libelle} — {self.get_statut_display()}"

    class Meta:
        verbose_name = "Pièce du dossier"
        verbose_name_plural = "Pièces du dossier"
        ordering = ["type_document"]


class Facture(models.Model):
    TYPE_CHOICES = [
        ("PONCTUELLE", "Ponctuelle"),
        ("RECURRENTE", "Récurrente"),
    ]
    FREQUENCE_CHOICES = [
        ("MENSUEL", "Mensuel"),
        ("TRIMESTRIEL", "Trimestriel"),
        ("SEMESTRIEL", "Semestriel"),
        ("ANNUEL", "Annuel"),
    ]
    STATUT_CHOICES = [
        # Flux principal
        ("BROUILLON", "Brouillon"),
        ("EMISE", "Émise (FNE)"),
        ("EN_ATTENTE_PAIEMENT", "En attente de paiement"),
        ("PARTIELLEMENT_PAYEE", "Partiellement payée"),
        ("PAYEE", "Payée"),

        # Branche contestation
        ("CONTESTEE", "Contestée"),
        ("EN_LITIGE", "En litige"),
        ("CORRIGEE", "Corrigée"),

        # Retard (calculé automatiquement)
        ("EN_RETARD", "En retard"),

        # Statuts d'exception / terminaux
        ("EN_CONTENTIEUX", "En contentieux"),
        ("IRRECOUVRABLE", "Irrécouvrable"),
        ("ANNULEE", "Annulée"),
    ]

    TRANSITIONS_AUTORISEES = {
        "EN_ATTENTE_PAIEMENT": ["EN_CONTENTIEUX", "ANNULEE"],
        "PARTIELLEMENT_PAYEE": ["EN_CONTENTIEUX"],
        "EN_RETARD": ["EN_CONTENTIEUX", "IRRECOUVRABLE"],
        "EN_CONTENTIEUX": ["IRRECOUVRABLE", "EN_ATTENTE_PAIEMENT"],
        "BROUILLON": ["ANNULEE"],
        # CONTESTEE / EN_LITIGE / CORRIGEE retirés : gérés exclusivement par
        # le cycle de vie de Litige (ouvrir_litige/passer_en_cours/resoudre/
        # abandonner) — un seul point de passage, cf. Litiges sous-module.
    }

    TRANSITIONS_RESTREINTES = {"EN_CONTENTIEUX", "IRRECOUVRABLE", "ANNULEE"}

    DELAI_ECHEANCE_DEFAUT_JOURS = 30  # ajustable ; deviendra un paramètre configurable au sous-module Paramétrage

    numero_facture = models.CharField("Numéro", max_length=30, unique=True, blank=True)
    devis_source = models.ForeignKey(
        "Devis", on_delete=models.PROTECT,
        related_name="factures", null=True, blank=True,
        verbose_name="Lettre de mission / devis source",
    )
    recouvreur = models.ForeignKey(
        "auth.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="portefeuille_creances", verbose_name="Recouvreur affecté"
    )

    client_nom = models.CharField("Client", max_length=255)
    client_ncc = models.CharField("NCC client", max_length=30, blank=True)

    type_facturation = models.CharField(max_length=20, choices=TYPE_CHOICES, default="PONCTUELLE")
    frequence = models.CharField(
        max_length=20, choices=FREQUENCE_CHOICES, blank=True,
        help_text="Uniquement si la facturation est récurrente",
    )
    date_signature = models.DateField(
        "Date de signature de la lettre", null=True, blank=True,
        help_text="Déclencheur de la facturation (saisi manuellement pour l'instant)",
    )

    montant_ht = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    montant_tva = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    montant_ttc = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    remise_montant = models.DecimalField(
        "Remise (montant FCFA)", max_digits=12, decimal_places=0, default=0,
        help_text="Reportée depuis la remise du devis d'origine au moment de la génération")

    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default="BROUILLON")

    date_creation = models.DateTimeField(auto_now_add=True)
    date_emission = models.DateField(null=True, blank=True)
    date_echeance = models.DateField(
        "Date d'échéance", null=True, blank=True,
        help_text="Calculée automatiquement à l'émission (voir save()), modifiable au cas par cas.")

    archive = models.BooleanField("Archivée", default=False)
    date_archivage = models.DateTimeField("Date d'archivage", null=True, blank=True)

    def archiver(self, utilisateur=None):
        if self.statut not in ("PAYEE", "ANNULEE", "IRRECOUVRABLE"):
            raise ValueError("Seule une facture soldée, annulée ou irrécouvrable peut être archivée.")
        self.archive = True
        self.date_archivage = timezone.now()
        self.save(update_fields=["archive", "date_archivage"])

    def restaurer(self, utilisateur=None):
        self.archive = False
        self.date_archivage = None
        self.save(update_fields=["archive", "date_archivage"])

    # ============================================================
    # CHAMPS FNE — DGI (voir PROCEDURE D'INTERFACAGE PAR API, mai 2025)
    # Champs marqués (O) = obligatoires pour l'appel /external/invoices/sign.
    # ============================================================
    INVOICE_TYPE_CHOICES = [("sale", "Vente")]
    PAYMENT_METHOD_CHOICES = [
        ("cash", "Espèces"),
        ("card", "Carte bancaire"),
        ("check", "Chèque"),
        ("mobile-money", "Mobile Money"),
        ("transfer", "Virement bancaire"),
        ("deferred", "À terme"),
    ]
    TEMPLATE_CHOICES = [
        ("B2B", "Entreprise / professionnel (avec NCC)"),
        ("B2F", "Client à l'international"),
        ("B2G", "Institution gouvernementale"),
        ("B2C", "Particulier"),
    ]
    DEVISE_ETRANGERE_CHOICES = [
        ("", "Aucune (facturation en FCFA / XOF)"),
        ("XOF", "Franc CFA (XOF)"),
        ("USD", "Dollar Américain (USD)"),
        ("EUR", "Euro (EUR)"),
        ("JPY", "Yen Japonais (JPY)"),
        ("CAD", "Dollar Canadien (CAD)"),
        ("GBP", "Livre Sterling Britannique (GBP)"),
        ("AUD", "Dollar Australien (AUD)"),
        ("CNH", "Yuan Chinois (CNH)"),
        ("CHF", "Franc Suisse (CHF)"),
        ("HKD", "Dollar Hong Kong (HKD)"),
        ("NZD", "Dollar Néo-Zélandais (NZD)"),
    ]

    invoice_type = models.CharField("Type FNE", max_length=10, choices=INVOICE_TYPE_CHOICES, default="sale")
    payment_method = models.CharField("Méthode de paiement (O)", max_length=15, choices=PAYMENT_METHOD_CHOICES, blank=True)
    template = models.CharField("Modèle de facturation FNE (O)", max_length=3, choices=TEMPLATE_CHOICES, blank=True)
    is_rne = models.BooleanField("Facture liée à un reçu (RNE) ? (O)", default=False)
    rne_numero = models.CharField("Numéro du reçu — RNE (O si liée à un reçu)", max_length=50, blank=True)

    client_telephone = models.CharField("Téléphone client (O)", max_length=30, blank=True)
    client_email = models.EmailField("Email client (O)", max_length=254, blank=True)
    vendeur_nom = models.CharField("Nom du vendeur (facultatif)", max_length=150, blank=True)

    point_de_vente = models.CharField("Point de vente (O)", max_length=150, blank=True)
    etablissement = models.CharField("Établissement (O)", max_length=150, blank=True)

    message_commercial = models.CharField("Message commercial", max_length=255, blank=True)
    pied_de_page = models.CharField("Message de bas de facture", max_length=255, blank=True)
    devise_etrangere = models.CharField("Devise étrangère", max_length=3, choices=DEVISE_ETRANGERE_CHOICES, blank=True)
    taux_devise_etrangere = models.DecimalField(
        "Taux de la devise étrangère (O si devise étrangère renseignée)",
        max_digits=10, decimal_places=4, default=0)

    # --- FNE : rempli après certification DGI (vide pour l'instant) ---
    fne_reference = models.CharField("Référence FNE", max_length=100, blank=True)
    fne_token = models.CharField("Token FNE (QR code)", max_length=255, blank=True)
    fne_sticker = models.CharField("Sticker FNE", max_length=100, blank=True)

    FNE_STATUT_CHOICES = [
        ("NON_CERTIFIEE", "Non certifiée"),
        ("CERTIFIEE", "Certifiée"),
        ("ERREUR", "Erreur de certification"),
    ]
    fne_statut = models.CharField("Statut FNE", max_length=15, choices=FNE_STATUT_CHOICES, default="NON_CERTIFIEE")
    fne_invoice_id = models.CharField("ID interne FNE (nécessaire pour un avoir)", max_length=100, blank=True)
    fne_ncc_emetteur = models.CharField("NCC émetteur (retour FNE)", max_length=20, blank=True)
    fne_warning = models.BooleanField("Alerte stock sticker (retour FNE)", default=False)
    fne_balance_sticker = models.IntegerField("Solde de stickers restants (retour FNE)", null=True, blank=True)
    fne_date_certification = models.DateTimeField("Certifiée le", null=True, blank=True)
    fne_erreur = models.TextField("Dernière erreur de certification", blank=True)

    class Meta:
        ordering = ["-date_creation"]
        verbose_name = "Facture"
        verbose_name_plural = "Factures"

    def __str__(self):
        return f"{self.numero_facture} — {self.client_nom}"

    def save(self, *args, **kwargs):
        if not self.numero_facture:
            annee = date.today().year
            prefix = f"FAC-{annee}-"
            derniere = Facture.objects.filter(numero_facture__startswith=prefix).order_by("-numero_facture").first()
            if derniere:
                try:
                    dernier_num = int(derniere.numero_facture.split("-")[-1])
                except ValueError:
                    dernier_num = 0
            else:
                dernier_num = 0
            self.numero_facture = f"{prefix}{dernier_num + 1:04d}"

        if self.date_emission and not self.date_echeance:
            self.date_echeance = self.date_emission + timedelta(days=self.DELAI_ECHEANCE_DEFAUT_JOURS)

        super().save(*args, **kwargs)

    @property
    def total_avoirs(self):
        return self.avoirs.aggregate(total=Sum("montant"))["total"] or Decimal("0")

    @property
    def montant_du(self):
        return self.montant_ttc - self.total_avoirs

    @property
    def montant_paye(self):
        paiements = self.paiements.aggregate(total=Sum("montant"))["total"] or Decimal("0")
        compensations_recues = self.compensations_recues.aggregate(total=Sum("montant"))["total"] or Decimal("0")
        return paiements + compensations_recues

    @property
    def solde_restant(self):
        return self.montant_du - self.montant_paye

    @property
    def trop_percu_brut(self):
        solde = self.solde_restant
        return -solde if solde < 0 else Decimal("0")

    @property
    def trop_percu_utilise(self):
        remb = self.remboursements.aggregate(total=Sum("montant"))["total"] or Decimal("0")
        comp = self.compensations_emises.aggregate(total=Sum("montant"))["total"] or Decimal("0")
        return remb + comp

    @property
    def trop_percu_disponible(self):
        return self.trop_percu_brut - self.trop_percu_utilise

    def enregistrer_avoir(self, montant, type_avoir, motif, utilisateur=None):
        if montant <= 0:
            raise ValueError("Le montant de l'avoir doit être supérieur à zéro.")
        if montant > self.montant_du:
            raise ValueError("L'avoir dépasse le montant restant dû sur la facture.")
        avoir = Avoir.objects.create(
            facture=self, montant=montant, type_avoir=type_avoir,
            motif=motif, cree_par=utilisateur,
        )
        if self.solde_restant <= 0:
            self.changer_statut("PAYEE", utilisateur=utilisateur, commentaire=f"Soldée par avoir {avoir.numero_avoir}")
        return avoir

    def enregistrer_remboursement(self, montant, utilisateur=None, **kwargs):
        if montant <= 0:
            raise ValueError("Le montant du remboursement doit être supérieur à zéro.")
        if montant > self.trop_percu_disponible:
            raise ValueError("Le remboursement dépasse le trop-perçu disponible.")
        return Remboursement.objects.create(
            facture=self, montant=montant, utilisateur=utilisateur, **kwargs)

    def enregistrer_compensation(self, facture_cible, montant, utilisateur=None, commentaire=""):
        if montant <= 0:
            raise ValueError("Le montant de la compensation doit être supérieur à zéro.")
        if montant > self.trop_percu_disponible:
            raise ValueError("La compensation dépasse le trop-perçu disponible sur cette facture.")
        if montant > facture_cible.solde_restant:
            raise ValueError("La compensation dépasse le solde restant dû sur la facture cible.")

        compensation = Compensation.objects.create(
            facture_source=self, facture_cible=facture_cible,
            montant=montant, utilisateur=utilisateur, commentaire=commentaire,
        )

        if facture_cible.solde_restant <= 0:
            facture_cible.changer_statut(
                "PAYEE", utilisateur=utilisateur,
                commentaire=f"Soldée par compensation depuis {self.numero_facture}")
        else:
            facture_cible.changer_statut(
                "PARTIELLEMENT_PAYEE", utilisateur=utilisateur,
                commentaire=f"Paiement partiel par compensation depuis {self.numero_facture}")

        return compensation

    def ouvrir_litige(self, motif_type, description, utilisateur=None):
        from .models import Litige  # évite un souci d'ordre de déclaration si déplacé un jour
        if self.statut not in Litige.STATUTS_SOURCE_AUTORISES:
            raise ValueError("Un litige ne peut pas être ouvert depuis ce statut de facture.")
        if self.litiges.filter(statut__in=["OUVERT", "EN_COURS"]).exists():
            raise ValueError("Un litige est déjà en cours sur cette facture.")
        litige = Litige.objects.create(
            facture=self, motif_type=motif_type, description=description, ouvert_par=utilisateur)
        self.changer_statut(
            "CONTESTEE", utilisateur=utilisateur,
            commentaire=f"Litige #{litige.id} ouvert ({litige.get_motif_type_display()})")
        return litige

    def transitions_possibles(self, user=None):
        possibles = self.TRANSITIONS_AUTORISEES.get(self.statut, [])
        if user is not None:
            profil = getattr(user, "profil", None)
            from comptes.models import Profil
            est_direction_cadre = profil and profil.role in (Profil.Role.DIRECTION, Profil.Role.CADRE)
            if not est_direction_cadre:
                possibles = [p for p in possibles if p not in self.TRANSITIONS_RESTREINTES]
        return possibles

    def peut_transitionner_vers(self, nouveau_statut, user=None):
        return nouveau_statut in self.transitions_possibles(user=user)

    def enregistrer_promesse(self, montant_promis, date_promise, commentaire="", responsable=None):
        if montant_promis <= 0:
            raise ValueError("Le montant promis doit être supérieur à zéro.")
        if self.promesses.filter(statut="EN_COURS").exists():
            raise ValueError("Une promesse est déjà en cours sur cette facture.")
        return PromessePaiement.objects.create(
            facture=self,
            montant_promis=montant_promis,
            date_promise=date_promise,
            commentaire=commentaire,
            responsable=responsable,
        )

    @property
    def a_promesse_active(self):
        return self.promesses.filter(statut="EN_COURS").exists()


class PromessePaiement(models.Model):
    STATUT_CHOICES = [
        ("EN_COURS", "En cours"),
        ("TENUE", "Tenue (paiement reçu à temps)"),
        ("ROMPUE", "Rompue (échéance dépassée sans paiement)"),
        ("ANNULEE", "Annulée"),
    ]

    facture = models.ForeignKey(
        Facture, on_delete=models.CASCADE, related_name="promesses"
    )
    montant_promis = models.DecimalField("Montant promis", max_digits=12, decimal_places=0)
    date_promise = models.DateField("Date promise de paiement")
    commentaire = models.TextField(blank=True)
    statut = models.CharField(max_length=15, choices=STATUT_CHOICES, default="EN_COURS")

    responsable = models.ForeignKey(
        "auth.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="promesses_enregistrees",
        help_text="Collaborateur ayant reçu la promesse (recouvreur en général)",
    )

    date_creation = models.DateTimeField(auto_now_add=True)
    date_verification = models.DateTimeField(null=True, blank=True)

    def verifier(self):
        """Vérifie automatiquement si la promesse a été tenue — appelée par
        la commande verifier_promesses. Ne change rien si déjà tranchée
        (TENUE/ROMPUE/ANNULEE) ou si la date promise n'est pas encore passée."""
        if self.statut != "EN_COURS":
            return
        if date.today() < self.date_promise:
            return

        if self.facture.solde_restant <= 0 or self.facture.statut == "PAYEE":
            self.statut = "TENUE"
        else:
            self.statut = "ROMPUE"
            self._notifier_rupture()
        self.date_verification = timezone.now()
        self.save(update_fields=["statut", "date_verification"])

    def _notifier_rupture(self):
        from django.urls import reverse
        from pilotage.models import Notification

        cle = f"promesse_rompue_facture{self.facture_id}_promesse{self.id}"
        Notification.objects.get_or_create(
            cle=cle,
            defaults={
                "type_notification": "promesse_rompue",
                "titre": f"Promesse rompue — {self.facture.numero_facture}",
                "message": f"La promesse de paiement sur {self.facture.numero_facture} n'a pas été honorée.",
                "url": reverse("devis:detail_creance", args=[self.facture_id]),
                "destinataire": self.facture.recouvreur or self.responsable,
            },
        )

    def annuler(self, utilisateur=None):
        if self.statut != "EN_COURS":
            raise ValueError("Seule une promesse en cours peut être annulée.")
        self.statut = "ANNULEE"
        self.date_verification = timezone.now()
        self.save(update_fields=["statut", "date_verification"])

    def __str__(self):
        return f"Promesse {self.montant_promis} FCFA le {self.date_promise} — {self.facture.numero_facture}"

    class Meta:
        verbose_name = "Promesse de paiement"
        verbose_name_plural = "Promesses de paiement"
        ordering = ["-date_creation"]


class EtapeRelance(models.Model):
    TYPE_ACTION_CHOICES = [
        ("EMAIL_COURTOIS", "Email courtois"),
        ("EMAIL_FERME", "Email plus ferme"),
        ("NOTIFICATION_INTERNE", "Notification interne"),
        ("LETTRE_PDF", "Lettre PDF"),
        ("ESCALADE_DIRECTION", "Escalade Direction"),
        ("ALERTE_CONTENTIEUX", "Alerte contentieux (décision Direction requise)"),
    ]

    nom = models.CharField("Nom de l'étape", max_length=100)
    delai_jours = models.PositiveIntegerField(
        "Déclenchement à J+", help_text="Jours après la date d'échéance"
    )
    type_action = models.CharField(max_length=25, choices=TYPE_ACTION_CHOICES)
    sujet_email = models.CharField("Sujet (si email)", max_length=200, blank=True)
    corps_message = models.TextField(
        "Corps du message", blank=True,
        help_text="Variables disponibles : {client_nom}, {numero_facture}, {montant_du}, {jours_retard}"
    )
    actif = models.BooleanField("Étape active", default=True)

    def __str__(self):
        return f"J+{self.delai_jours} — {self.nom}"

    class Meta:
        verbose_name = "Étape de relance"
        verbose_name_plural = "Étapes de relance"
        ordering = ["delai_jours"]


class Relance(models.Model):
    facture = models.ForeignKey(Facture, on_delete=models.CASCADE, related_name="relances")
    etape = models.ForeignKey(
        EtapeRelance, on_delete=models.PROTECT, related_name="relances_declenchees"
    )
    date_declenchement = models.DateTimeField(auto_now_add=True)
    reussie = models.BooleanField(default=True)
    erreur = models.TextField(blank=True)
    document_genere = models.FileField(upload_to="relances/lettres/", blank=True, null=True)

    def __str__(self):
        return f"{self.etape.nom} — {self.facture.numero_facture} ({self.date_declenchement:%d/%m/%Y})"

    class Meta:
        verbose_name = "Relance déclenchée"
        verbose_name_plural = "Relances déclenchées"
        ordering = ["-date_declenchement"]
        unique_together = ("facture", "etape")


class ActionRecouvrement(models.Model):
    TYPE_CHOICES = [
        ("APPEL", "Appel téléphonique"),
        ("EMAIL", "Email envoyé"),
        ("VISITE", "Visite / rendez-vous"),
        ("AUTRE", "Autre action"),
    ]

    facture = models.ForeignKey(Facture, on_delete=models.CASCADE, related_name="actions_recouvrement")
    recouvreur = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True)
    type_action = models.CharField(max_length=10, choices=TYPE_CHOICES)
    commentaire = models.TextField(blank=True)
    date_action = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_type_action_display()} — {self.facture.numero_facture} ({self.date_action:%d/%m/%Y})"

    class Meta:
        verbose_name = "Action de recouvrement"
        verbose_name_plural = "Actions de recouvrement"
        ordering = ["-date_action"]


class Litige(models.Model):
    MOTIF_CHOICES = [
        ("ERREUR_FACTURE", "Erreur de facture"),
        ("PRESTATION_INCOMPLETE", "Prestation incomplète"),
        ("DESACCORD", "Désaccord"),
        ("AUTRE", "Autre"),
    ]
    STATUT_CHOICES = [
        ("OUVERT", "Ouvert"),
        ("EN_COURS", "En cours d'instruction"),
        ("RESOLU", "Résolu"),
        ("ABANDONNE", "Abandonné"),
    ]
    STATUTS_SOURCE_AUTORISES = ["EN_ATTENTE_PAIEMENT", "PARTIELLEMENT_PAYEE", "EN_RETARD"]

    facture = models.ForeignKey(Facture, on_delete=models.CASCADE, related_name="litiges")
    motif_type = models.CharField("Motif", max_length=25, choices=MOTIF_CHOICES)
    description = models.TextField("Description")
    statut = models.CharField(max_length=15, choices=STATUT_CHOICES, default="OUVERT")

    ouvert_par = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="litiges_ouverts")
    date_ouverture = models.DateTimeField(auto_now_add=True)

    date_resolution = models.DateTimeField(null=True, blank=True)
    resolution_commentaire = models.TextField(blank=True)

    def __str__(self):
        return f"Litige #{self.id} — {self.facture.numero_facture} ({self.get_statut_display()})"

    def passer_en_cours(self, utilisateur=None):
        if self.statut != "OUVERT":
            raise ValueError("Seul un litige ouvert peut passer en instruction.")
        self.statut = "EN_COURS"
        self.save(update_fields=["statut"])
        self.facture.changer_statut(
            "EN_LITIGE", utilisateur=utilisateur,
            commentaire=f"Litige #{self.id} en cours d'instruction")

    def resoudre(self, commentaire, utilisateur=None):
        if self.statut != "EN_COURS":
            raise ValueError("Seul un litige en instruction peut être résolu.")
        self.statut = "RESOLU"
        self.date_resolution = timezone.now()
        self.resolution_commentaire = commentaire
        self.save(update_fields=["statut", "date_resolution", "resolution_commentaire"])
        self.facture.changer_statut(
            "CORRIGEE", utilisateur=utilisateur,
            commentaire=f"Litige #{self.id} résolu : {commentaire}")

    def abandonner(self, utilisateur=None, commentaire=""):
        if self.statut not in ("OUVERT", "EN_COURS"):
            raise ValueError("Ce litige ne peut plus être abandonné.")
        self.statut = "ABANDONNE"
        self.date_resolution = timezone.now()
        self.resolution_commentaire = commentaire
        self.save(update_fields=["statut", "date_resolution", "resolution_commentaire"])
        self.facture.changer_statut(
            "EN_ATTENTE_PAIEMENT", utilisateur=utilisateur,
            commentaire=f"Litige #{self.id} abandonné" + (f" : {commentaire}" if commentaire else ""))

    class Meta:
        verbose_name = "Litige"
        verbose_name_plural = "Litiges"
        ordering = ["-date_ouverture"]


class PieceJointeLitige(models.Model):
    litige = models.ForeignKey(Litige, on_delete=models.CASCADE, related_name="pieces")
    libelle = models.CharField("Libellé", max_length=200)
    fichier = models.FileField("Fichier", upload_to="litiges/pieces/")
    ajoute_par = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True)
    date_ajout = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.libelle

    class Meta:
        verbose_name = "Pièce jointe (litige)"
        verbose_name_plural = "Pièces jointes (litiges)"
        ordering = ["-date_ajout"]


class CommentaireLitige(models.Model):
    litige = models.ForeignKey(Litige, on_delete=models.CASCADE, related_name="commentaires")
    auteur = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True)
    message = models.TextField()
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.auteur} — {self.date_creation:%d/%m/%Y}"

    class Meta:
        verbose_name = "Commentaire (litige)"
        verbose_name_plural = "Commentaires (litiges)"
        ordering = ["date_creation"]


class HistoriqueStatutFacture(models.Model):
    facture = models.ForeignKey(
        "Facture", on_delete=models.CASCADE, related_name="historique_statuts")
    ancien_statut = models.CharField(max_length=25, blank=True)
    nouveau_statut = models.CharField(max_length=25)
    date_changement = models.DateTimeField(auto_now_add=True)
    utilisateur = models.ForeignKey(
        "auth.User", on_delete=models.SET_NULL, null=True, blank=True)
    commentaire = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.facture.numero_facture} : {self.ancien_statut} → {self.nouveau_statut}"

    class Meta:
        verbose_name = "Historique de statut (facture)"
        verbose_name_plural = "Historiques de statuts (factures)"
        ordering = ["date_changement"]


class Paiement(models.Model):
    MODE_CHOICES = [
        ("ESPECES", "Espèces"),
        ("CHEQUE", "Chèque"),
        ("VIREMENT", "Virement bancaire"),
        ("MOBILE_MONEY", "Mobile Money"),
        ("CARTE", "Carte bancaire"),
    ]
    OPERATEUR_MOBILE_MONEY_CHOICES = [
        ("", "—"),
        ("WAVE", "Wave"),
        ("ORANGE_MONEY", "Orange Money"),
        ("AUTRE", "Autre"),
    ]

    facture = models.ForeignKey(
        Facture, on_delete=models.PROTECT, related_name="paiements")
    montant = models.DecimalField("Montant", max_digits=12, decimal_places=0)
    date_paiement = models.DateField("Date du paiement", default=date.today)
    mode_paiement = models.CharField(max_length=15, choices=MODE_CHOICES, blank=True)
    operateur_mobile_money = models.CharField(
        "Opérateur mobile money", max_length=15, choices=OPERATEUR_MOBILE_MONEY_CHOICES, blank=True)
    reference_transaction_externe = models.CharField(
        "Référence transaction (API opérateur)", max_length=100, blank=True,
        help_text="ID de transaction Wave/Orange Money — rempli manuellement pour l'instant, automatiquement une fois l'API branchée")
    banque = models.CharField("Banque / établissement", max_length=100, blank=True)
    reference_bancaire = models.CharField("Référence bancaire", max_length=100, blank=True)
    justificatif = models.FileField(
        "Justificatif", upload_to="paiements/justificatifs/", blank=True, null=True)
    commentaire = models.CharField(max_length=255, blank=True)
    reconcilie_automatiquement = models.BooleanField(
        "Réconcilié automatiquement via API", default=False,
        help_text="Toujours False tant que l'intégration API n'existe pas — sert de marqueur pour distinguer les paiements saisis à la main de ceux confirmés par webhook, une fois construit")

    utilisateur = models.ForeignKey(
        "auth.User", on_delete=models.SET_NULL, null=True, blank=True)
    date_enregistrement = models.DateTimeField("Enregistré le", auto_now_add=True)

    def __str__(self):
        return f"{self.montant} FCFA — {self.facture.numero_facture} ({self.date_paiement})"

    class Meta:
        verbose_name = "Paiement"
        verbose_name_plural = "Paiements"
        ordering = ["date_paiement"]


class Avoir(models.Model):
    TYPE_CHOICES = [
        ("CORRECTION", "Correction d'erreur de facturation"),
        ("GESTE_COMMERCIAL", "Geste commercial"),
        ("ANNULATION_PARTIELLE", "Annulation partielle de prestation"),
        ("RESOLUTION_LITIGE", "Résolution de litige"),
    ]

    numero_avoir = models.CharField("Numéro", max_length=30, unique=True, blank=True)
    facture = models.ForeignKey(Facture, on_delete=models.PROTECT, related_name="avoirs")
    montant = models.DecimalField("Montant", max_digits=12, decimal_places=0)
    type_avoir = models.CharField(max_length=25, choices=TYPE_CHOICES)
    motif = models.TextField("Motif")

    certifie_fne = models.BooleanField("Certifié FNE", default=False)

    cree_par = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.numero_avoir:
            annee = date.today().year
            prefix = f"AV-{annee}-"
            dernier = Avoir.objects.filter(numero_avoir__startswith=prefix).order_by("-numero_avoir").first()
            dernier_num = int(dernier.numero_avoir.split("-")[-1]) if dernier else 0
            self.numero_avoir = f"{prefix}{dernier_num + 1:04d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.numero_avoir} — {self.montant} FCFA sur {self.facture.numero_facture}"

    class Meta:
        verbose_name = "Avoir"
        verbose_name_plural = "Avoirs"
        ordering = ["-date_creation"]


class Remboursement(models.Model):
    MODE_CHOICES = Paiement.MODE_CHOICES

    facture = models.ForeignKey(Facture, on_delete=models.PROTECT, related_name="remboursements")
    montant = models.DecimalField("Montant", max_digits=12, decimal_places=0)
    date_remboursement = models.DateField(default=date.today)
    mode_remboursement = models.CharField(max_length=15, choices=MODE_CHOICES, blank=True)
    reference = models.CharField("Référence", max_length=100, blank=True)
    justificatif = models.FileField(upload_to="remboursements/justificatifs/", blank=True, null=True)
    commentaire = models.CharField(max_length=255, blank=True)

    utilisateur = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True)
    date_enregistrement = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Remboursement {self.montant} FCFA — {self.facture.numero_facture}"

    class Meta:
        verbose_name = "Remboursement"
        verbose_name_plural = "Remboursements"
        ordering = ["-date_remboursement"]


class Compensation(models.Model):
    """Trop-perçu d'une facture appliqué au solde restant d'une autre facture
    (même client). Compte comme un paiement côté facture_cible."""
    facture_source = models.ForeignKey(
        Facture, on_delete=models.PROTECT, related_name="compensations_emises",
        verbose_name="Facture en trop-perçu")
    facture_cible = models.ForeignKey(
        Facture, on_delete=models.PROTECT, related_name="compensations_recues",
        verbose_name="Facture soldée")
    montant = models.DecimalField("Montant", max_digits=12, decimal_places=0)
    commentaire = models.CharField(max_length=255, blank=True)

    utilisateur = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.montant} FCFA : {self.facture_source.numero_facture} → {self.facture_cible.numero_facture}"

    class Meta:
        verbose_name = "Compensation"
        verbose_name_plural = "Compensations"
        ordering = ["-date_creation"]


class Fournisseur(models.Model):
    NOTATION_CHOICES = [(i, str(i)) for i in range(1, 6)]

    raison_sociale = models.CharField("Raison sociale", max_length=200)
    ncc = models.CharField("NCC", max_length=20, blank=True)
    contact_nom = models.CharField("Nom du contact", max_length=150, blank=True)
    telephone = models.CharField("Téléphone", max_length=30, blank=True)
    email = models.EmailField("Email", blank=True)
    adresse = models.CharField("Adresse", max_length=255, blank=True)

    delai_paiement_jours = models.PositiveIntegerField(
        "Délai de paiement négocié (jours)", default=30, null=True, blank=True)
    notation = models.PositiveSmallIntegerField(
        "Notation", choices=NOTATION_CHOICES, null=True, blank=True)
    actif = models.BooleanField("Actif", default=True)
    notes = models.TextField("Notes internes", blank=True)

    date_creation = models.DateTimeField(auto_now_add=True)

    # NOTE : historique / total acheté / factures liées ne sont PAS des champs
    # stockés ici — ce seront des propriétés calculées depuis les dépenses liées,
    # dès que le sous-module "Dépenses" (le suivant) existera. Voir COMMENTAIRES.md.

    @property
    def total_achete(self):
        return self.depenses.exclude(statut="ANNULEE").aggregate(
            total=Sum("montant_ht"))["total"] or Decimal("0")

    @property
    def nombre_factures(self):
        return self.depenses.exclude(statut="ANNULEE").count()

    def __str__(self):
        return self.raison_sociale

    class Meta:
        verbose_name = "Fournisseur"
        verbose_name_plural = "Fournisseurs"
        ordering = ["raison_sociale"]


class ContratFournisseur(models.Model):
    fournisseur = models.ForeignKey(Fournisseur, on_delete=models.CASCADE, related_name="contrats")
    libelle = models.CharField("Libellé", max_length=200)
    fichier = models.FileField("Fichier", upload_to="fournisseurs/contrats/")
    date_debut = models.DateField("Date de début", null=True, blank=True)
    date_fin = models.DateField("Date de fin", null=True, blank=True)
    date_ajout = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.libelle} — {self.fournisseur}"

    class Meta:
        verbose_name = "Contrat fournisseur"
        verbose_name_plural = "Contrats fournisseurs"
        ordering = ["-date_ajout"]


class CategorieDepense(models.Model):
    nom = models.CharField("Nom", max_length=100)
    parent = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="sous_categories", verbose_name="Catégorie parente")

    def __str__(self):
        return f"{self.parent} > {self.nom}" if self.parent else self.nom

    class Meta:
        verbose_name = "Catégorie de dépense"
        verbose_name_plural = "Catégories de dépenses"
        ordering = ["nom"]


class SeuilApprobation(models.Model):
    NIVEAU_CHOICES = [
        ("CADRE", "Chef de service (Cadre)"),
        ("DIRECTION", "Direction"),
    ]
    borne_min = models.DecimalField("À partir de (FCFA)", max_digits=12, decimal_places=0, default=0)
    borne_max = models.DecimalField(
        "Jusqu'à (FCFA)", max_digits=12, decimal_places=0, null=True, blank=True,
        help_text="Laisser vide pour 'et plus'"
    )
    niveau_requis = models.CharField(max_length=15, choices=NIVEAU_CHOICES)
    actif = models.BooleanField(default=True)

    def __str__(self):
        borne = f"{self.borne_min} — {self.borne_max or '∞'} FCFA"
        return f"{borne} → {self.get_niveau_requis_display()}"

    class Meta:
        verbose_name = "Seuil d'approbation"
        verbose_name_plural = "Seuils d'approbation"
        ordering = ["borne_min"]

    @classmethod
    def niveau_requis_pour(cls, montant):
        seuil = cls.objects.filter(actif=True, borne_min__lte=montant).filter(
            models.Q(borne_max__gte=montant) | models.Q(borne_max__isnull=True)
        ).order_by("-borne_min").first()
        return seuil.niveau_requis if seuil else "DIRECTION"


class NoteDeFrais(models.Model):
    STATUT_CHOICES = [
        ("BROUILLON", "Brouillon"),
        ("SOUMISE", "Soumise"),
        ("VALIDEE", "Validée"),
        ("REJETEE", "Rejetée"),
        ("REMBOURSEE", "Remboursée"),
    ]
    TYPE_FRAIS_CHOICES = [
        ("MISSION", "Mission"),
        ("TRANSPORT", "Transport"),
        ("HEBERGEMENT", "Hébergement"),
        ("REPAS", "Repas"),
        ("AUTRE", "Autre"),
    ]

    collaborateur = models.ForeignKey("auth.User", on_delete=models.CASCADE, related_name="notes_de_frais")
    objet = models.CharField("Objet", max_length=200, blank=True)
    periode_debut = models.DateField("Période — début", null=True, blank=True)
    periode_fin = models.DateField("Période — fin", null=True, blank=True)
    statut = models.CharField(max_length=15, choices=STATUT_CHOICES, default="BROUILLON")

    date_soumission = models.DateTimeField(null=True, blank=True)
    soumise_par = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="notes_de_frais_soumises")
    date_validation = models.DateTimeField(null=True, blank=True)
    validee_par = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="notes_de_frais_validees")
    motif_rejet = models.TextField(blank=True)

    date_remboursement = models.DateField(null=True, blank=True)
    mode_remboursement = models.CharField(max_length=15, choices=Paiement.MODE_CHOICES, blank=True)
    reference_remboursement = models.CharField("Référence de remboursement", max_length=100, blank=True)
    rembourse_par = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="notes_de_frais_remboursees")

    date_creation = models.DateTimeField(auto_now_add=True)

    @property
    def montant_total(self):
        return self.lignes.aggregate(total=Sum("montant"))["total"] or Decimal("0")

    def soumettre(self, utilisateur=None):
        if self.statut != "BROUILLON":
            raise ValueError("Seule une note en brouillon peut être soumise.")
        if not self.lignes.exists():
            raise ValueError("Une note de frais doit contenir au moins une ligne.")
        self.statut = "SOUMISE"
        self.date_soumission = timezone.now()
        self.soumise_par = utilisateur
        self.save(update_fields=["statut", "date_soumission", "soumise_par"])

    def valider(self, utilisateur=None):
        if self.statut != "SOUMISE":
            raise ValueError("Seule une note soumise peut être validée.")
        self.statut = "VALIDEE"
        self.date_validation = timezone.now()
        self.validee_par = utilisateur
        self.save(update_fields=["statut", "date_validation", "validee_par"])

    def rejeter(self, motif, utilisateur=None):
        if self.statut != "SOUMISE":
            raise ValueError("Seule une note soumise peut être rejetée.")
        self.statut = "REJETEE"
        self.motif_rejet = motif
        self.save(update_fields=["statut", "motif_rejet"])

    def renvoyer_en_brouillon(self, utilisateur=None):
        if self.statut != "REJETEE":
            raise ValueError("Seule une note rejetée peut être renvoyée en brouillon.")
        self.statut = "BROUILLON"
        self.motif_rejet = ""
        self.save(update_fields=["statut", "motif_rejet"])

    def marquer_remboursee(self, mode, reference="", date_remb=None, utilisateur=None):
        if self.statut != "VALIDEE":
            raise ValueError("Seule une note validée peut être marquée comme remboursée.")
        self.statut = "REMBOURSEE"
        self.mode_remboursement = mode
        self.reference_remboursement = reference
        self.date_remboursement = date_remb or date.today()
        self.rembourse_par = utilisateur
        self.save(update_fields=["statut", "mode_remboursement", "reference_remboursement", "date_remboursement", "rembourse_par"])

    def __str__(self):
        return f"Note de frais #{self.id} — {self.collaborateur}"

    class Meta:
        verbose_name = "Note de frais"
        verbose_name_plural = "Notes de frais"
        ordering = ["-date_creation"]


class LigneNoteDeFrais(models.Model):
    note = models.ForeignKey(NoteDeFrais, on_delete=models.CASCADE, related_name="lignes")
    type_frais = models.CharField("Type de frais", max_length=15, choices=NoteDeFrais.TYPE_FRAIS_CHOICES)
    date_depense = models.DateField("Date de dépense")
    description = models.CharField("Description", max_length=250)
    montant = models.DecimalField("Montant", max_digits=12, decimal_places=0)

    def __str__(self):
        return f"{self.get_type_frais_display()} — {self.description}"

    class Meta:
        verbose_name = "Ligne de note de frais"
        verbose_name_plural = "Lignes de notes de frais"
        ordering = ["date_depense"]


class DepenseRecurrente(models.Model):
    FREQUENCE_CHOICES = [
        ("MENSUEL", "Mensuel"),
        ("TRIMESTRIEL", "Trimestriel"),
        ("ANNUEL", "Annuel"),
    ]

    libelle = models.CharField("Libellé", max_length=200)
    fournisseur = models.ForeignKey(Fournisseur, on_delete=models.PROTECT, related_name="depenses_recurrentes")
    categorie = models.ForeignKey(CategorieDepense, on_delete=models.PROTECT, related_name="depenses_recurrentes")
    montant_ht = models.DecimalField("Montant HT", max_digits=12, decimal_places=0)
    taux_tva = models.CharField(max_length=2, choices=LignePrestation.TVA_CHOICES, default="18")

    frequence = models.CharField(max_length=15, choices=FREQUENCE_CHOICES)
    jour_generation = models.PositiveSmallIntegerField(
        "Jour du mois de génération", default=1,
        help_text="Plafonné automatiquement les mois courts (comme jour_emission_facture sur Devis)")
    mois_generation = models.PositiveSmallIntegerField(
        "Mois de génération (si annuel)", null=True, blank=True,
        help_text="Uniquement pour une fréquence annuelle")

    date_debut = models.DateField("Début de la récurrence", default=date.today)
    date_fin = models.DateField("Fin de la récurrence", null=True, blank=True)
    actif = models.BooleanField(default=True)

    derniere_generation = models.DateField(null=True, blank=True)

    cree_par = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    def _prochaine_echeance(self, apres):
        if self.frequence == "MENSUEL":
            annee, mois = apres.year, apres.month + 1
            if mois > 12:
                annee, mois = annee + 1, 1
        elif self.frequence == "TRIMESTRIEL":
            annee, mois = apres.year, apres.month + 3
            while mois > 12:
                annee, mois = annee + 1, mois - 12
        else:
            annee, mois = apres.year + 1, self.mois_generation or apres.month

        jours_par_mois = [31, 29 if annee % 4 == 0 and (annee % 100 != 0 or annee % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        jour = min(self.jour_generation, jours_par_mois[mois - 1])
        return date(annee, mois, jour)

    def echeances_dues(self, jusqu_au):
        depart = self.derniere_generation or (self.date_debut - timedelta(days=1))
        echeances = []
        courante = self._prochaine_echeance(depart)
        while courante <= jusqu_au and (not self.date_fin or courante <= self.date_fin):
            echeances.append(courante)
            courante = self._prochaine_echeance(courante)
        return echeances

    def generer_depense(self, date_echeance, utilisateur=None):
        if GenerationDepenseRecurrente.objects.filter(recurrente=self, date_echeance=date_echeance).exists():
            return None
        depense = Depense.objects.create(
            fournisseur=self.fournisseur,
            categorie=self.categorie,
            montant_ht=self.montant_ht,
            taux_tva=self.taux_tva,
            date_facture=date_echeance,
            est_recurrente=True,
            cree_par=utilisateur,
            observations=f"Générée automatiquement — {self.libelle}",
        )
        GenerationDepenseRecurrente.objects.create(recurrente=self, date_echeance=date_echeance, depense=depense)
        self.derniere_generation = date_echeance
        self.save(update_fields=["derniere_generation"])
        return depense

    def __str__(self):
        return f"{self.libelle} — {self.get_frequence_display()}"

    class Meta:
        verbose_name = "Dépense récurrente"
        verbose_name_plural = "Dépenses récurrentes"
        ordering = ["libelle"]


class GenerationDepenseRecurrente(models.Model):
    recurrente = models.ForeignKey(DepenseRecurrente, on_delete=models.CASCADE, related_name="generations")
    date_echeance = models.DateField()
    depense = models.ForeignKey("Depense", on_delete=models.CASCADE, related_name="generation_recurrente")
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("recurrente", "date_echeance")
        ordering = ["-date_echeance"]


class Depense(models.Model):
    MODE_PAIEMENT_CHOICES = Paiement.MODE_CHOICES

    STATUT_CHOICES = [
        ("A_PAYER", "À payer"),
        ("PROGRAMME", "Programmé"),
        ("PARTIELLEMENT_PAYEE", "Partiellement payée"),
        ("PAYEE", "Payée"),
        ("EN_RETARD", "En retard"),
        ("ANNULEE", "Annulée"),
    ]

    STATUT_VALIDATION_CHOICES = [
        ("BROUILLON", "Brouillon"),
        ("SOUMISE", "Soumise, en attente de validation"),
        ("VALIDEE", "Validée"),
        ("REJETEE", "Rejetée"),
    ]

    numero_depense = models.CharField("Numéro", max_length=30, unique=True, blank=True)
    fournisseur = models.ForeignKey(
        Fournisseur, on_delete=models.PROTECT, related_name="depenses")
    categorie = models.ForeignKey(
        CategorieDepense, on_delete=models.PROTECT, related_name="depenses")

    montant_ht = models.DecimalField("Montant HT", max_digits=12, decimal_places=0)
    taux_tva = models.CharField(
        "Taux de TVA", max_length=2, choices=LignePrestation.TVA_CHOICES, default="18")

    date_facture = models.DateField("Date de la facture fournisseur")
    date_echeance = models.DateField("Date d'échéance", null=True, blank=True)

    mode_paiement = models.CharField(max_length=15, choices=MODE_PAIEMENT_CHOICES, blank=True)
    compte_bancaire = models.CharField("Compte bancaire", max_length=100, blank=True)
    observations = models.TextField(blank=True)

    statut = models.CharField(max_length=25, choices=STATUT_CHOICES, default="A_PAYER")
    archive = models.BooleanField("Archivée", default=False)
    date_archivage = models.DateTimeField(null=True, blank=True)

    statut_validation = models.CharField(max_length=15, choices=STATUT_VALIDATION_CHOICES, default="BROUILLON")
    niveau_requis = models.CharField(max_length=15, choices=SeuilApprobation.NIVEAU_CHOICES, blank=True)

    date_soumission = models.DateTimeField(null=True, blank=True)
    soumise_par = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="depenses_soumises")

    date_validation = models.DateTimeField(null=True, blank=True)
    validee_par = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="depenses_validees")
    motif_rejet = models.TextField(blank=True)

    depassement_autorise = models.BooleanField("Dépassement budgétaire autorisé", default=False)
    depassement_autorise_par = models.ForeignKey(
        "auth.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="depenses_derogees")
    motif_depassement = models.TextField(blank=True)

    est_recurrente = models.BooleanField("Dépense récurrente", default=False)

    cree_par = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    DELAI_ECHEANCE_DEFAUT_JOURS = 30

    @property
    def montant_tva(self):
        return self.montant_ht * (Decimal(self.taux_tva) / Decimal("100"))

    @property
    def montant_ttc(self):
        return self.montant_ht + self.montant_tva

    @property
    def montant_paye(self):
        return self.paiements.aggregate(total=Sum("montant"))["total"] or Decimal("0")

    @property
    def solde_restant(self):
        return self.montant_ttc - self.montant_paye

    def save(self, *args, **kwargs):
        if not self.numero_depense:
            annee = date.today().year
            prefix = f"DEP-{annee}-"
            derniere = Depense.objects.filter(numero_depense__startswith=prefix).order_by("-numero_depense").first()
            dernier_num = int(derniere.numero_depense.split("-")[-1]) if derniere else 0
            self.numero_depense = f"{prefix}{dernier_num + 1:04d}"

        if self.date_facture and not self.date_echeance:
            delai = self.fournisseur.delai_paiement_jours or self.DELAI_ECHEANCE_DEFAUT_JOURS
            date_facture = self.date_facture
            if isinstance(date_facture, str):
                date_facture = date.fromisoformat(date_facture)
            self.date_echeance = date_facture + timedelta(days=delai)

        super().save(*args, **kwargs)

    def changer_statut(self, nouveau_statut, utilisateur=None, commentaire=""):
        ancien_statut = self.statut
        if ancien_statut == nouveau_statut:
            return
        self.statut = nouveau_statut
        self.save(update_fields=["statut"])
        HistoriqueStatutDepense.objects.create(
            depense=self, ancien_statut=ancien_statut, nouveau_statut=nouveau_statut,
            utilisateur=utilisateur, commentaire=commentaire,
        )

    def verifier_budget(self):
        """Retourne (ok: bool, budget: Budget|None, message: str)."""
        if self.depassement_autorise:
            return True, None, "Dépassement autorisé par la Direction."

        budget = Budget.budget_disponible_pour(self.categorie, self.date_facture)
        if budget is None:
            return True, None, "Aucun budget défini pour cette catégorie/période — pas de contrôle possible."

        if budget.disponible >= self.montant_ht:
            return True, budget, "Budget disponible suffisant."
        return False, budget, f"Dépassement : {budget.disponible} FCFA disponibles, {self.montant_ht} FCFA demandés."

    def soumettre(self, utilisateur=None):
        if self.statut_validation != "BROUILLON":
            raise ValueError("Seule une dépense en brouillon peut être soumise.")

        ok, budget, message = self.verifier_budget()
        if not ok:
            raise BudgetDepasseError(message, budget)

        self.niveau_requis = SeuilApprobation.niveau_requis_pour(self.montant_ttc)
        self.statut_validation = "SOUMISE"
        self.date_soumission = timezone.now()
        self.soumise_par = utilisateur
        self.save(update_fields=["niveau_requis", "statut_validation", "date_soumission", "soumise_par"])
        HistoriqueValidationDepense.objects.create(
            depense=self, action="SOUMISE", utilisateur=utilisateur, commentaire=message
        )

    def accorder_derogation(self, motif, utilisateur=None):
        self.depassement_autorise = True
        self.depassement_autorise_par = utilisateur
        self.motif_depassement = motif
        self.save(update_fields=["depassement_autorise", "depassement_autorise_par", "motif_depassement"])
        HistoriqueValidationDepense.objects.create(
            depense=self, action="DEROGATION_BUDGET", utilisateur=utilisateur, commentaire=motif
        )

    def valider(self, utilisateur=None, commentaire=""):
        if self.statut_validation != "SOUMISE":
            raise ValueError("Seule une dépense soumise peut être validée.")
        self.statut_validation = "VALIDEE"
        self.date_validation = timezone.now()
        self.validee_par = utilisateur
        self.save(update_fields=["statut_validation", "date_validation", "validee_par"])
        HistoriqueValidationDepense.objects.create(
            depense=self, action="VALIDEE", utilisateur=utilisateur, commentaire=commentaire
        )

    def rejeter(self, motif, utilisateur=None):
        if self.statut_validation != "SOUMISE":
            raise ValueError("Seule une dépense soumise peut être rejetée.")
        self.statut_validation = "REJETEE"
        self.motif_rejet = motif
        self.save(update_fields=["statut_validation", "motif_rejet"])
        HistoriqueValidationDepense.objects.create(depense=self, action="REJETEE", utilisateur=utilisateur, commentaire=motif)

    def renvoyer_en_brouillon(self, utilisateur=None):
        """Permet de corriger une dépense rejetée et de la resoumettre."""
        if self.statut_validation != "REJETEE":
            raise ValueError("Seule une dépense rejetée peut être renvoyée en brouillon.")
        self.statut_validation = "BROUILLON"
        self.motif_rejet = ""
        self.save(update_fields=["statut_validation", "motif_rejet"])
        HistoriqueValidationDepense.objects.create(depense=self, action="RENVOYEE_BROUILLON", utilisateur=utilisateur)

    def enregistrer_paiement(self, montant, utilisateur=None, **kwargs):
        if self.statut_validation != "VALIDEE":
            raise ValueError("Cette dépense doit être validée avant tout paiement.")
        PaiementDepense.objects.create(depense=self, montant=montant, utilisateur=utilisateur, **kwargs)
        if self.solde_restant <= 0:
            self.changer_statut("PAYEE", utilisateur=utilisateur)
        else:
            self.changer_statut("PARTIELLEMENT_PAYEE", utilisateur=utilisateur)

    def archiver(self, utilisateur=None):
        if self.statut not in ("PAYEE", "ANNULEE"):
            raise ValueError("Seule une dépense payée ou annulée peut être archivée.")
        self.archive = True
        self.date_archivage = timezone.now()
        self.save(update_fields=["archive", "date_archivage"])

    def restaurer(self, utilisateur=None):
        self.archive = False
        self.date_archivage = None
        self.save(update_fields=["archive", "date_archivage"])

    def __str__(self):
        return f"{self.numero_depense} — {self.fournisseur} ({self.montant_ttc} FCFA)"

    class Meta:
        verbose_name = "Dépense"
        verbose_name_plural = "Dépenses"
        ordering = ["-date_facture"]


class BudgetDepasseError(Exception):
    def __init__(self, message, budget=None):
        super().__init__(message)
        self.budget = budget


class HistoriqueValidationDepense(models.Model):
    ACTION_CHOICES = [
        ("SOUMISE", "Soumise"),
        ("VALIDEE", "Validée"),
        ("REJETEE", "Rejetée"),
        ("RENVOYEE_BROUILLON", "Renvoyée en brouillon"),
        ("DEROGATION_BUDGET", "Dérogation de dépassement budgétaire accordée"),
    ]
    depense = models.ForeignKey(Depense, on_delete=models.CASCADE, related_name="historique_validations")
    action = models.CharField(max_length=25, choices=ACTION_CHOICES)
    utilisateur = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True)
    commentaire = models.TextField(blank=True)
    date_action = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.depense.numero_depense} : {self.get_action_display()}"

    class Meta:
        verbose_name = "Historique de validation (dépense)"
        verbose_name_plural = "Historiques de validation (dépenses)"
        ordering = ["date_action"]


class PaiementDepense(models.Model):
    depense = models.ForeignKey(Depense, on_delete=models.PROTECT, related_name="paiements")
    montant = models.DecimalField("Montant", max_digits=12, decimal_places=0)
    date_paiement = models.DateField("Date du paiement", default=date.today)
    mode_paiement = models.CharField(max_length=15, choices=Paiement.MODE_CHOICES, blank=True)
    operateur_mobile_money = models.CharField(
        "Opérateur mobile money", max_length=15, choices=Paiement.OPERATEUR_MOBILE_MONEY_CHOICES, blank=True)
    reference_transaction_externe = models.CharField(
        "Référence transaction (API opérateur)", max_length=100, blank=True,
        help_text="ID de transaction Wave/Orange Money — rempli manuellement pour l'instant, automatiquement une fois l'API branchée")
    reference_bancaire = models.CharField("Référence bancaire", max_length=100, blank=True)
    justificatif = models.FileField(upload_to="depenses/paiements/", blank=True, null=True)
    commentaire = models.CharField(max_length=255, blank=True)
    reconcilie_automatiquement = models.BooleanField(
        "Réconcilié automatiquement via API", default=False,
        help_text="Toujours False tant que l'intégration API n'existe pas — sert de marqueur pour distinguer les paiements saisis à la main de ceux confirmés par webhook, une fois construit")

    utilisateur = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True)
    date_enregistrement = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.montant} FCFA — {self.depense.numero_depense}"

    class Meta:
        verbose_name = "Paiement (dépense)"
        verbose_name_plural = "Paiements (dépenses)"
        ordering = ["-date_paiement"]


class DocumentDepense(models.Model):
    TYPE_CHOICES = [
        ("FACTURE", "Facture PDF"),
        ("RECU", "Reçu"),
        ("PHOTO", "Photo"),
        ("DEVIS", "Devis"),
        ("BON_COMMANDE", "Bon de commande"),
    ]
    depense = models.ForeignKey(Depense, on_delete=models.CASCADE, related_name="documents")
    type_document = models.CharField(max_length=15, choices=TYPE_CHOICES)
    fichier = models.FileField(upload_to="depenses/documents/")
    date_ajout = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_type_document_display()} — {self.depense.numero_depense}"

    class Meta:
        verbose_name = "Document (dépense)"
        verbose_name_plural = "Documents (dépenses)"
        ordering = ["-date_ajout"]


class HistoriqueStatutDepense(models.Model):
    depense = models.ForeignKey(Depense, on_delete=models.CASCADE, related_name="historique_statuts")
    ancien_statut = models.CharField(max_length=25, blank=True)
    nouveau_statut = models.CharField(max_length=25)
    date_changement = models.DateTimeField(auto_now_add=True)
    utilisateur = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True)
    commentaire = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.depense.numero_depense} : {self.ancien_statut} → {self.nouveau_statut}"

    class Meta:
        verbose_name = "Historique de statut (dépense)"
        verbose_name_plural = "Historiques de statuts (dépenses)"
        ordering = ["date_changement"]


class LigneFacture(models.Model):
    facture = models.ForeignKey(
        "Facture", on_delete=models.CASCADE,
        related_name="lignes", verbose_name="Facture"
    )
    designation = models.CharField("Désignation", max_length=255)
    reference = models.CharField("Référence article", max_length=50, blank=True)
    unite_mesure = models.CharField("Unité de mesure", max_length=30, blank=True,
                                    help_text="Ex : mois, forfait, heure")
    quantite = models.DecimalField("Quantité", max_digits=10, decimal_places=2, default=1)
    prix_unitaire = models.DecimalField("Prix unitaire HT", max_digits=12, decimal_places=2, default=0)
    taux_tva = models.CharField("Taux de TVA", max_length=2, choices=LignePrestation.TVA_CHOICES, default="18")

    @property
    def total_ht(self):
        return self.quantite * self.prix_unitaire

    @property
    def montant_tva(self):
        return self.total_ht * (Decimal(self.taux_tva) / Decimal("100"))

    @property
    def total_ttc(self):
        return self.total_ht + self.montant_tva

    def __str__(self):
        return f"{self.designation} ({self.total_ht} FCFA)"

    class Meta:
        verbose_name = "Ligne de facture"
        verbose_name_plural = "Lignes de factures"
