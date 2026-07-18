from django import forms
from .models import Absence, PrimeConfiguree, SecteurActivite, CategorieSalaire, Employe, Emploi, Employeur, Conge, JourFerie, BulletinPaie
from clients.models import Client
from .calculs_rupture import MOTIF_CHOICES

class RubriqueForm(forms.ModelForm):
    class Meta:
        model = PrimeConfiguree
        fields = [
            "type_rubrique", "libelle", "traitement_fiscal", "plafond_exoneration",
            "montant_par_defaut", "soumis_cnps", "ordre",
        ]


class SecteurForm(forms.ModelForm):
    class Meta:
        model = SecteurActivite
        fields = ["nom", "taux_at"]


class CategorieForm(forms.ModelForm):
    class Meta:
        model = CategorieSalaire
        fields = ["secteur", "code", "salaire_minimum", "ordre"]


class EmployeForm(forms.ModelForm):
    class Meta:
        model = Employe
        fields = [
            "matricule", "civilite", "nom_prenoms", "sexe", "date_naissance", "lieu_naissance",
            "nature_piece", "numero_piece", "nationalite", "situation_matrimoniale", "nombre_enfants",
            "adresse", "telephone", "lieu_habitation",
            "contrat", "date_signature_contrat", "duree_cdd_mois", "date_entree", "date_sortie",
            "direction", "service", "poste", "emploi_ref", "regime", "type_salaire", "statut",
            "categorie", "sursalaire", "cmu_conjoint_a_charge", "cmu_enfants_a_charge",
            "non_soumis_cnps", "numero_cnps",
            "mode_paiement", "numero_compte", "banque",
        ]
        widgets = {
            "date_naissance": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "date_signature_contrat": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "date_entree": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "date_sortie": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def __init__(self, *args, employeur=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._employeur = employeur

        # Champs obligatoires
        for champ in ["nom_prenoms", "categorie", "date_entree", "contrat", "mode_paiement"]:
            if champ in self.fields:
                self.fields[champ].required = True

        # Catégorie = liste déroulante des catégories de la convention de l'entreprise
        choix = [("", "— Choisir une catégorie —")]
        self.categorie_vide = True
        self.convention_nom = ""
        if employeur and employeur.secteur:
            self.convention_nom = employeur.secteur.nom
            cats = employeur.secteur.grille.all()
            for c in cats:
                choix.append((c.code, f"{c.code} — {c.salaire_minimum:,.0f} F".replace(",", " ")))
            self.categorie_vide = (len(choix) <= 1)
        valeur = self.instance.categorie if (self.instance and self.instance.pk) else None
        self.fields["categorie"] = forms.ChoiceField(choices=choix, required=True, label="Catégorie", initial=valeur)

class AbsenceForm(forms.ModelForm):
    class Meta:
        model = Absence
        fields = ["date_debut", "date_fin", "motif", "retire_jours", "justificatif"]
        widgets = {
            "date_debut": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "date_fin": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def clean(self):
        cleaned = super().clean()
        dd, df = cleaned.get("date_debut"), cleaned.get("date_fin")
        if dd and df and df < dd:
            self.add_error("date_fin", "La date de fin doit être après la date de début.")
        return cleaned

class BulletinHistoriqueForm(forms.Form):
    mois = forms.ChoiceField(choices=BulletinPaie.MOIS_CHOICES, label="Mois")
    annee = forms.IntegerField(label="Année", min_value=2015, max_value=2030)
    net_historique = forms.DecimalField(label="Net payé", max_digits=12, decimal_places=0)
    its_historique = forms.DecimalField(label="ITS retenu (facultatif)", required=False, max_digits=12, decimal_places=0)
    cnps_salarie_historique = forms.DecimalField(label="CNPS salarié retenue (facultatif)", required=False, max_digits=12, decimal_places=0)
    cmu_salarie_historique = forms.DecimalField(label="CMU salariée retenue (facultatif)", required=False, max_digits=12, decimal_places=0)


class EmployeurDepuisClientForm(forms.Form):
    client = forms.ModelChoiceField(
        queryset=Client.objects.none(),
        label="Entreprise cliente",
        empty_label="— Choisir un client —",
    )
    secteur = forms.ModelChoiceField(
        queryset=SecteurActivite.objects.none(),
        label="Convention collective (secteur)",
        empty_label="— Choisir la convention —",
    )
    banque_nom = forms.CharField(label="Banque", max_length=100, required=False)
    banque_code = forms.CharField(label="Code banque", max_length=5, required=False)
    banque_guichet = forms.CharField(label="Code guichet (agence)", max_length=5, required=False)
    banque_numero_compte = forms.CharField(label="Numéro de compte", max_length=20, required=False)
    banque_cle_rib = forms.CharField(label="Clé RIB", max_length=2, required=False)
    banque_iban = forms.CharField(label="IBAN", max_length=34, required=False)
    banque_intitule = forms.CharField(label="Intitulé du compte (titulaire)", max_length=150, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Seuls les clients qui ne sont pas déjà employeurs
        self.fields["client"].queryset = Client.objects.filter(employeur__isnull=True).order_by("nom")
        self.fields["secteur"].queryset = SecteurActivite.objects.all().order_by("nom")

class FinContratForm(forms.Form):
    motif = forms.ChoiceField(choices=MOTIF_CHOICES, label="Motif de la rupture")
    date_fin = forms.DateField(label="Date de sortie effective",
                               widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))

class AvenantForm(forms.Form):
    nouvelle_date_fin = forms.DateField(
        label="Nouvelle date de fin",
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )
    motif_reconduction = forms.CharField(
        label="Motif de la reconduction",
        required=False,
        max_length=250,
        widget=forms.Textarea(attrs={"rows": 2}),
    )


class ImportDocumentForm(forms.Form):
    NATURE_CHOICES = [
        ("contrat_signe", "Contrat de travail signé"),
        ("avenant_signe", "Avenant signé"),
        ("attestation_externe", "Attestation ou certificat externe"),
        ("piece_identite", "Pièce d'identité / diplôme"),
        ("autre", "Autre document"),
    ]
    nature = forms.ChoiceField(choices=NATURE_CHOICES, label="Nature du document")
    employeur = forms.ModelChoiceField(queryset=None, label="Entreprise")
    employe = forms.ModelChoiceField(queryset=None, label="Salarié (si applicable)", required=False)
    libelle = forms.CharField(
        label="Libellé du document",
        max_length=200,
        help_text="Ex. « Contrat signé — Jean Kouassi »",
    )
    fichier = forms.FileField(label="Fichier")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import Employeur, Employe
        self.fields["employeur"].queryset = Employeur.objects.all().order_by("raison_sociale")
        self.fields["employe"].queryset = Employe.objects.none()
        if "employeur" in self.data:
            try:
                emp_id = int(self.data.get("employeur"))
                self.fields["employe"].queryset = Employe.objects.filter(employeur_id=emp_id).order_by("nom_prenoms")
            except (ValueError, TypeError):
                pass

    def clean(self):
        cleaned = super().clean()
        nature = cleaned.get("nature")
        if nature in ("contrat_signe", "avenant_signe") and not cleaned.get("employe"):
            self.add_error("employe", "Le salarié est obligatoire pour un contrat ou un avenant.")
        return cleaned


class EmploiForm(forms.ModelForm):
    class Meta:
        model = Emploi
        fields = ["code", "libelle", "ordre"]

class PretForm(forms.Form):
    MODE_CHOICES = [("nombre", "Par nombre de mensualités"), ("mensualite", "Par montant de mensualité")]
    montant = forms.DecimalField(label="Montant emprunté (FCFA)")
    mode = forms.ChoiceField(choices=MODE_CHOICES, label="Définir le remboursement")
    nombre_mensualites = forms.IntegerField(label="Nombre de mensualités", required=False, min_value=1)
    mensualite = forms.DecimalField(label="Montant de la mensualité (FCFA)", required=False)
    date_debut = forms.DateField(label="Date du 1er remboursement",
                                 widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))
    motif = forms.CharField(label="Motif (facultatif)", required=False)

    def clean(self):
        d = super().clean()
        if d.get("mode") == "nombre" and not d.get("nombre_mensualites"):
            self.add_error("nombre_mensualites", "Indique le nombre de mensualités.")
        if d.get("mode") == "mensualite" and not d.get("mensualite"):
            self.add_error("mensualite", "Indique le montant de la mensualité.")
        return d


class EmployeurForm(forms.ModelForm):
    """Modifie UNIQUEMENT le RIB émetteur de l'entreprise (le reste vient de devis)."""
    class Meta:
        model = Employeur
        fields = [
            "banque_nom", "banque_code", "banque_guichet",
            "banque_numero_compte", "banque_cle_rib",
            "banque_iban", "banque_intitule",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # RIB obligatoire pour pouvoir produire un ordre de virement
        for champ in ["banque_nom", "banque_numero_compte"]:
            if champ in self.fields:
                self.fields[champ].required = True


class JourFerieForm(forms.ModelForm):
    class Meta:
        model = JourFerie
        fields = ["date", "libelle"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

class CongePoserForm(forms.Form):
    TYPE_CHOICES = [
        ("annuel", "Congé annuel"),
        ("exceptionnel", "Congé exceptionnel (mariage, décès, naissance…)"),
    ]
    type_conge = forms.ChoiceField(choices=TYPE_CHOICES, label="Type de congé", initial="annuel")
    date_depart = forms.DateField(label="Date de départ",
                                  widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))
    date_retour = forms.DateField(label="Date de retour (reprise du travail)",
                                  widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))
    motif = forms.CharField(label="Motif (facultatif)", required=False, max_length=200)

    def clean(self):
        d = super().clean()
        dep, ret = d.get("date_depart"), d.get("date_retour")
        if dep and ret and ret <= dep:
            self.add_error("date_retour", "La date de retour doit être après la date de départ.")
        return d


class CongeExceptionnelForm(forms.Form):
    MOTIF_CHOICES = [
        ("mariage", "Mariage du salarié"),
        ("naissance", "Naissance d'un enfant"),
        ("deces_proche", "Décès d'un proche"),
        ("autre", "Autre événement familial"),
    ]
    motif = forms.ChoiceField(choices=MOTIF_CHOICES, label="Motif")
    date_depart = forms.DateField(label="Date de départ", widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))
    date_retour = forms.DateField(label="Date de retour", widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))
    precision = forms.CharField(label="Précision (facultatif)", required=False, max_length=250)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("date_depart") and cleaned.get("date_retour") and cleaned["date_retour"] <= cleaned["date_depart"]:
            self.add_error("date_retour", "La date de retour doit être après le départ.")
        return cleaned


class ContratGenerationForm(forms.Form):
    NIVEAU_ESSAI_CHOICES = [
        ("horaire", "Payé à l'heure/journée (essai 8 jours)"),
        ("mensuel", "Payé au mois (essai 1 mois)"),
        ("maitrise", "Agent de maîtrise / technicien (essai 2 mois)"),
        ("cadre", "Ingénieur / cadre (essai 3 mois)"),
    ]
    niveau_essai = forms.ChoiceField(choices=NIVEAU_ESSAI_CHOICES, label="Catégorie pour la période d'essai", initial="mensuel")
    TYPE_TERME_CHOICES = [
        ("precis", "Terme précis (durée fixée à l'avance)"),
        ("imprecis", "Terme imprécis (lié à un événement)"),
    ]
    type_terme = forms.ChoiceField(choices=TYPE_TERME_CHOICES, label="Type de terme (CDD)", required=False, initial="precis")

    MOTIF_CDD_PRECIS_CHOICES = [
        ("", "— Sélectionner (facultatif) —"),
        ("accroissement", "Accroissement temporaire d'activité"),
        ("occasionnel", "Exécution d'une tâche précise et temporaire"),
        ("saisonnier", "Travail à caractère saisonnier"),
        ("autre", "Autre motif (à préciser)"),
    ]
    motif_cdd = forms.ChoiceField(choices=MOTIF_CDD_PRECIS_CHOICES, label="Motif (terme précis)", required=False)

    MOTIF_CDD_IMPRECIS_CHOICES = [
        ("", "— Sélectionner —"),
        ("remplacement", "Remplacement d'un travailleur absent, suspendu, ou attente d'un CDI"),
        ("saison", "Durée d'une saison"),
        ("surcroit", "Surcroît occasionnel de travail"),
        ("inhabituelle", "Activité inhabituelle de l'entreprise"),
    ]
    motif_cdd_imprecis = forms.ChoiceField(choices=MOTIF_CDD_IMPRECIS_CHOICES, label="Motif (terme imprécis — obligatoire)", required=False)
    evenement_terme = forms.CharField(label="Événement qui mettra fin au contrat", required=False, max_length=250,
                                      help_text="Ex. « le retour de Mme X, actuellement en congé maternité »." )
    motif_cdd_precision = forms.CharField(label="Précision sur le motif", required=False, max_length=250)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("type_terme") == "imprecis" and not cleaned.get("motif_cdd_imprecis"):
            self.add_error("motif_cdd_imprecis", "Le motif est obligatoire pour un CDD à terme imprécis (art. 15.6).")
        return cleaned

    TYPE_STAGE_CHOICES = [
        ("qualification", "Stage de qualification ou d'expérience professionnelle (rémunéré)"),
        ("ecole", "Stage-école — validation de diplôme (non rémunéré)"),
    ]
    type_stage = forms.ChoiceField(choices=TYPE_STAGE_CHOICES, label="Type de stage", required=False, initial="qualification")
    etablissement_formation = forms.CharField(label="Établissement de formation (facultatif)", required=False, max_length=200,
                                              help_text="Pour un stage-école : nom de l'école/université.")
    indemnite_stage = forms.DecimalField(label="Indemnité mensuelle de stage (FCFA)", required=False, max_digits=12, decimal_places=0,
                                         help_text="Obligatoire pour un stage de qualification (≥ 50% du salaire minimum catégoriel).")
    maitre_stage = forms.CharField(label="Maître de stage / superviseur (facultatif)", required=False, max_length=150)
    lieu_travail = forms.CharField(label="Lieu de travail (facultatif)", required=False, max_length=200)
    avantages_nature = forms.CharField(label="Avantages en nature (facultatif)", required=False, max_length=300,
                                        help_text="Ex. logement, véhicule de fonction… Laisser vide si aucun.")
    description_poste = forms.CharField(label="Description du poste et missions (Annexe 1)", required=False,
                                        widget=forms.Textarea(attrs={"rows": 5}),
                                        help_text="Détaille les tâches et responsabilités — figurera en annexe.")
    clauses_particulieres = forms.CharField(label="Clauses particulières (facultatif)", required=False, widget=forms.Textarea(attrs={"rows": 3}))