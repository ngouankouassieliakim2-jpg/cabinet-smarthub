from datetime import date, timedelta
from decimal import Decimal
from django.db import models
from django.utils import timezone


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
        ("BROUILLON", "Brouillon"),
        ("A_CERTIFIER", "À certifier"),
        ("CERTIFIEE", "Certifiée DGI"),
        ("ENVOYEE", "Envoyée"),
        ("PAYEE", "Payée"),
        ("ANNULEE", "Annulée"),
    ]

    numero_facture = models.CharField("Numéro", max_length=30, unique=True, blank=True)
    devis_source = models.ForeignKey(
        "Devis", on_delete=models.PROTECT,
        related_name="factures", null=True, blank=True,
        verbose_name="Lettre de mission / devis source",
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
        super().save(*args, **kwargs)


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
