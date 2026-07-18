from django.db import models
from clients.models import Client


class Balance(models.Model):
    """Une balance comptable importée, pour un client et un exercice."""
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="balances")
    exercice = models.IntegerField("Exercice")
    regime_liasse = models.CharField("Régime de liasse", max_length=5, choices=[
        ("NO", "Système Normal"), ("MT", "Système Minimal de Trésorerie"),
        ("BA", "Banques"), ("SGI", "Sociétés de Gestion et d'Intermédiation"),
        ("MF", "Microfinance"), ("AV", "Assurance Vie"), ("AN", "Assurance Non-Vie"),
    ], default="NO")
    importee_le = models.DateTimeField("Importée le", auto_now_add=True)

    class Meta:
        verbose_name = "Balance"
        verbose_name_plural = "Balances"
        unique_together = ("client", "exercice")

    def __str__(self):
        return f"Balance {self.client} — {self.exercice}"


class LigneBalance(models.Model):
    """Une ligne de balance : un compte (client) avec ses 4 colonnes."""
    balance = models.ForeignKey(Balance, on_delete=models.CASCADE, related_name="lignes")
    compte = models.CharField("N° de compte", max_length=15)
    libelle = models.CharField("Libellé du compte", max_length=200, blank=True, default="")
    solde_initial = models.DecimalField("Solde initial (N-1)", max_digits=16, decimal_places=2, default=0)
    mouvement_debit = models.DecimalField("Mouvement débit", max_digits=16, decimal_places=2, default=0)
    mouvement_credit = models.DecimalField("Mouvement crédit", max_digits=16, decimal_places=2, default=0)
    solde_final = models.DecimalField("Solde final (N)", max_digits=16, decimal_places=2, default=0)

    class Meta:
        verbose_name = "Ligne de balance"
        verbose_name_plural = "Lignes de balance"
        ordering = ["compte"]

    def __str__(self):
        return f"{self.compte} — {self.libelle}"


class CompteSyscohada(models.Model):
    """Plan comptable général SYSCOHADA révisé (référentiel officiel, universel).
    max_length=10 : le plan révisé contient des codes à 5 chiffres (ex. 47811)."""
    code = models.CharField("Code du compte", max_length=10, unique=True)
    libelle = models.CharField("Libellé", max_length=250)
    classe = models.IntegerField("Classe (1 à 9)")

    class Meta:
        verbose_name = "Compte SYSCOHADA (plan général)"
        verbose_name_plural = "Plan comptable SYSCOHADA"
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} — {self.libelle}"


class NoteAnnexeDefinition(models.Model):
    """Table maître des notes annexes officielles (référentiel fixe).
    Garantit que la liasse sort toujours complète : une note sans LigneNote
    configurée s'affiche à zéro plutôt que d'être absente."""
    TYPE_CHOICES = [
        ("mouvements", "Mouvements de l'exercice"),
        ("situation", "Situation à la clôture"),
        ("comparatif", "Comparatif N / N-1"),
        ("texte", "Informations qualitatives / texte libre"),
    ]
    CATEGORIE_CHOICES = [
        ("identification", "Page de garde / identification (saisie manuelle une fois par client)"),
        ("etat_financier", "État financier principal (Bilan, Résultat, TFT — agrégation directe des comptes)"),
        ("note_syscohada", "Note annexe SYSCOHADA (calculée via LigneNote)"),
        ("supplementaire_dgi", "Tableau supplémentaire DGI/INS (hors norme OHADA)"),
    ]
    regime_liasse = models.CharField("Régime de liasse", max_length=5, default="NO")
    code_note = models.CharField("Code note", max_length=15, help_text="Ex. NOTE 3A, NOTE 4, NOTE 21")
    libelle = models.CharField("Libellé officiel", max_length=200)
    type_note = models.CharField("Type de note", max_length=20, choices=TYPE_CHOICES, default="situation")
    categorie = models.CharField("Catégorie", max_length=20, choices=CATEGORIE_CHOICES, default="note_syscohada")
    onglet_dgi = models.CharField("Nom de l'onglet dans le fichier officiel DGI", max_length=50, blank=True, default="")
    ordre = models.IntegerField("Ordre d'affichage dans la liasse", default=0)

    class Meta:
        verbose_name = "Note annexe (référentiel maître)"
        verbose_name_plural = "Notes annexes (référentiel maître)"
        unique_together = ("regime_liasse", "code_note")
        ordering = ["regime_liasse", "ordre"]

    def __str__(self):
        return f"{self.code_note} — {self.libelle}"


class LigneNote(models.Model):
    """Référentiel de mapping : quels comptes alimentent quelle ligne de quelle
    note, pour un régime donné. Universel — valable pour tous les clients."""
    SOURCE_CHOICES = [
        ("solde_initial", "Solde initial (ouverture)"),
        ("mouvement_debit", "Mouvement débit (augmentations)"),
        ("mouvement_credit", "Mouvement crédit (diminutions)"),
        ("solde_final", "Solde final (clôture)"),
    ]
    SENS_CHOICES = [
        ("les_deux", "Les deux sens (débiteur ou créditeur)"),
        ("debiteur", "Seulement si le compte est débiteur"),
        ("crediteur", "Seulement si le compte est créditeur"),
    ]
    SIGNE_CHOICES = [
        (1, "Positif (+1) — actif / présentation débit-positif"),
        (-1, "Négatif (−1) — passif / présentation crédit-positif"),
    ]
    regime_liasse = models.CharField("Régime de liasse", max_length=5, default="NO")
    code_note = models.CharField("Code note", max_length=15, help_text="Ex. NOTE 3A, NOTE 3C, NOTE 4")
    libelle_ligne = models.CharField("Libellé de la ligne", max_length=200)
    ref_dgi = models.CharField("Code REF officiel DGI", max_length=10, blank=True, default="",
                                help_text="Ex. AD, AE, AJ... issu du fichier liasse officiel")
    cellule_dgi = models.CharField("Cellule dans le fichier officiel", max_length=30, blank=True, default="",
                                    help_text="Ex. 'NOTE 3A!D17' — onglet + adresse de cellule")
    prefixe_comptes = models.CharField("Préfixe(s) de comptes", max_length=100,
                                       help_text="Ex. '21' ou '211,212,213'")
    source = models.CharField("Colonne source de la balance", max_length=20, choices=SOURCE_CHOICES, default="solde_final")
    sens = models.CharField(
        "Sens du solde retenu", max_length=10, choices=SENS_CHOICES, default="les_deux",
        help_text="N'agréger le compte que s'il va dans ce sens. "
                  "Ex. 52 en 'crediteur' → découvert (trésorerie-passif) ; 411 en 'debiteur' → clients.",
    )
    signe = models.IntegerField(
        "Signe appliqué", choices=SIGNE_CHOICES, default=1,
        help_text="+1 côté actif (débit-positif), −1 côté passif (crédit-positif). "
                  "Le ± du report à nouveau et du résultat en découle automatiquement.",
    )
    ordre = models.IntegerField("Ordre d'affichage", default=0)

    class Meta:
        verbose_name = "Ligne de note (référentiel)"
        verbose_name_plural = "Lignes de notes (référentiel)"
        ordering = ["regime_liasse", "code_note", "ordre"]

    def __str__(self):
        return f"{self.regime_liasse} — {self.code_note} — {self.libelle_ligne}"

class AjustementNote(models.Model):
    """Correction manuelle ponctuelle, appliquée PAR-DESSUS le calcul automatique
    -- jamais à la place. Utilisée uniquement pour ce qu'une balance ne peut
    structurellement pas contenir (virements de poste à poste, réévaluations,
    échéanciers de créances). Le calcul automatique reste la source de vérité
    pour tout ce qui est déductible de la balance."""
    MODE_CHOICES = [
        ("complement_residuel", "Complément soustrait de la ligne calculée automatiquement"),
        ("remplacement", "Remplace intégralement une valeur calculée (ex. prorata placement)"),
    ]
    balance = models.ForeignKey("Balance", on_delete=models.CASCADE, related_name="ajustements")
    code_note = models.CharField("Code note", max_length=15)
    libelle_ligne = models.CharField("Libellé de la rubrique", max_length=200)
    cellule_dgi = models.CharField("Cellule concernée", max_length=30, help_text="Ex. 'NOTE 3A!F17'")
    mode = models.CharField("Mode d'application", max_length=25, choices=MODE_CHOICES, default="complement_residuel")
    montant = models.DecimalField("Montant", max_digits=16, decimal_places=2, default=0)
    commentaire = models.CharField("Justification", max_length=255, blank=True, default="")
    saisi_le = models.DateTimeField("Saisi le", auto_now_add=True)

    class Meta:
        verbose_name = "Ajustement manuel de note"
        verbose_name_plural = "Ajustements manuels de notes"

    def __str__(self):
        return f"{self.balance} — {self.cellule_dgi} = {self.montant}"
    
class LigneImmobilisation(models.Model):
    """Fiche d'immobilisation individuelle (une ligne = un bien).
    Alimente directement SUPPL4, ET affine NOTE 3A/3C/3D avec precision
    (bien par bien) plutot que par prorata quand cette fiche existe."""
    balance = models.ForeignKey("Balance", on_delete=models.CASCADE, related_name="immobilisations")
    compte = models.CharField("N° de compte SYSCOHADA", max_length=15)
    designation = models.CharField("Désignation", max_length=200)
    taux_amortissement = models.DecimalField("Taux d'amortissement (%)", max_digits=5, decimal_places=2)
    date_mise_en_service = models.DateField("Date de mise en service")
    valeur_acquisition = models.DecimalField("Valeur d'acquisition", max_digits=16, decimal_places=2)
    amortissements_anterieurs = models.DecimalField("Amortissements antérieurs", max_digits=16, decimal_places=2, default=0)
    amortissements_exercice = models.DecimalField("Amortissements de l'exercice", max_digits=16, decimal_places=2, default=0)
    date_cession = models.DateField("Date de cession", null=True, blank=True)
    prix_cession = models.DecimalField("Prix de cession", max_digits=16, decimal_places=2, null=True, blank=True)

    class Meta:
        verbose_name = "Ligne d'immobilisation (SUPPL4)"
        verbose_name_plural = "Lignes d'immobilisation (SUPPL4)"
        ordering = ["compte", "date_mise_en_service"]

    @property
    def amortissement_total(self):
        return self.amortissements_anterieurs + self.amortissements_exercice

    @property
    def valeur_residuelle(self):
        return self.valeur_acquisition - self.amortissement_total

    @property
    def plus_value(self):
        if self.prix_cession is None:
            return None
        return max(self.prix_cession - self.valeur_residuelle, 0)

    @property
    def moins_value(self):
        if self.prix_cession is None:
            return None
        return max(self.valeur_residuelle - self.prix_cession, 0)

    def __str__(self):
        return f"{self.compte} — {self.designation}"