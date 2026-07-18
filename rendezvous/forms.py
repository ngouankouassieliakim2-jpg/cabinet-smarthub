from django import forms

from .models import DemandeRendezVous


# Les motifs proposés en cases à cocher (valeur stockée, libellé affiché).
MOTIFS_CHOIX = [
    ("COMPTABILITE", "Comptabilité"),
    ("FISCALITE", "Fiscalité"),
    ("AUDIT", "Audit"),
    ("RH", "Ressources humaines"),
    ("FORMATION", "Formation"),
    ("CONSEIL", "Conseil"),
    ("ORGANISATION", "Organisation & stratégie"),
    ("AIDES", "Aides publiques et privées"),
    ("RENSEIGNEMENTS", "Renseignements généraux"),
    ("AUTRE", "Autre"),
]


class DemandeRendezVousForm(forms.ModelForm):
    # Champ "à part" : cases à cocher multiples, non lié directement au modèle.
    motifs = forms.MultipleChoiceField(
        choices=MOTIFS_CHOIX,
        widget=forms.CheckboxSelectMultiple,
        label="Objet(s) de la demande",
        help_text="Cochez tout ce qui vous concerne.",
    )

    class Meta:
        model = DemandeRendezVous
        fields = [
            "nom", "telephone", "email",
            "motifs",
            "structure", "secteur", "cabinet_actuel", "anciennete", "chiffre_affaires",
            "lieu", "date_souhaitee", "message",
        ]
        widgets = {
            "nom": forms.TextInput(attrs={"placeholder": "Votre nom et prénom"}),
            "telephone": forms.TextInput(attrs={"placeholder": "Ex. 07 07 31 59 64"}),
            "email": forms.EmailInput(attrs={"placeholder": "votre@email.com (facultatif)"}),
            "secteur": forms.TextInput(attrs={"placeholder": "Ex. Commerce, BTP, agriculture…"}),
            "date_souhaitee": forms.DateInput(attrs={"type": "date"}),
            "message": forms.Textarea(attrs={"rows": 4, "placeholder": "Précisez votre demande (facultatif)"}),
        }
        labels = {
            "nom": "Nom complet",
            "telephone": "Téléphone",
            "email": "Email",
            "structure": "Type de structure",
            "secteur": "Secteur d'activité",
            "cabinet_actuel": "J'ai déjà un cabinet comptable",
            "anciennete": "Ancienneté de l'activité",
            "chiffre_affaires": "Chiffre d'affaires prévisionnel",
            "lieu": "Lieu de rendez-vous souhaité",
            "date_souhaitee": "Date souhaitée",
            "message": "Message",
        }

    def clean_motifs(self):
        # On transforme la liste de cases cochées en texte "A,B,C" pour le modèle.
        liste = self.cleaned_data["motifs"]
        return ",".join(liste)