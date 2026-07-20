from django import forms
from django.contrib.auth.models import User
from .models import (
    Paiement, Facture, Avoir, Remboursement, Compensation,
    EtapeRelance, Litige, PieceJointeLitige, CommentaireLitige,
    ActionRecouvrement, Fournisseur, ContratFournisseur,
    CategorieDepense, Depense, PaiementDepense, DocumentDepense,
)


class PaiementForm(forms.ModelForm):
    class Meta:
        model = Paiement
        fields = [
            "montant", "date_paiement", "mode_paiement",
            "operateur_mobile_money", "reference_transaction_externe",
            "banque", "reference_bancaire", "justificatif", "commentaire",
        ]
        widgets = {
            "date_paiement": forms.DateInput(attrs={"type": "date"}),
            "commentaire": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, facture=None, **kwargs):
        self.facture = facture
        super().__init__(*args, **kwargs)
        if facture is not None:
            self.fields["montant"].widget.attrs["max"] = facture.solde_restant

    def clean_montant(self):
        montant = self.cleaned_data["montant"]
        if montant <= 0:
            raise forms.ValidationError("Le montant doit être supérieur à zéro.")
        return montant


class TransitionStatutForm(forms.Form):
    nouveau_statut = forms.ChoiceField(choices=[])
    commentaire = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2}),
        required=True,
        label="Motif",
    )

    def __init__(self, *args, facture=None, user=None, **kwargs):
        self.facture = facture
        self.user = user
        super().__init__(*args, **kwargs)
        possibles = facture.transitions_possibles(user=user) if facture else []
        self.fields["nouveau_statut"].choices = [
            (code, dict(Facture.STATUT_CHOICES).get(code, code)) for code in possibles
        ]

    def clean_nouveau_statut(self):
        valeur = self.cleaned_data["nouveau_statut"]
        if not self.facture.peut_transitionner_vers(valeur, user=self.user):
            raise forms.ValidationError("Cette transition n'est pas autorisée depuis le statut actuel.")
        return valeur


class AvoirForm(forms.ModelForm):
    class Meta:
        model = Avoir
        fields = ["montant", "type_avoir", "motif"]
        widgets = {"motif": forms.Textarea(attrs={"rows": 2})}

    def __init__(self, *args, facture=None, **kwargs):
        self.facture = facture
        super().__init__(*args, **kwargs)

    def clean_montant(self):
        montant = self.cleaned_data["montant"]
        if montant <= 0:
            raise forms.ValidationError("Le montant doit être supérieur à zéro.")
        if self.facture and montant > self.facture.montant_du:
            raise forms.ValidationError("L'avoir dépasse le montant restant dû sur la facture.")
        return montant


class RemboursementForm(forms.ModelForm):
    class Meta:
        model = Remboursement
        fields = ["montant", "date_remboursement", "mode_remboursement", "reference", "justificatif", "commentaire"]
        widgets = {
            "date_remboursement": forms.DateInput(attrs={"type": "date"}),
            "commentaire": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, facture=None, **kwargs):
        self.facture = facture
        super().__init__(*args, **kwargs)

    def clean_montant(self):
        montant = self.cleaned_data["montant"]
        if montant <= 0:
            raise forms.ValidationError("Le montant doit être supérieur à zéro.")
        if self.facture and montant > self.facture.trop_percu_disponible:
            raise forms.ValidationError("Le remboursement dépasse le trop-perçu disponible.")
        return montant


class CompensationForm(forms.Form):
    facture_cible = forms.ModelChoiceField(queryset=Facture.objects.none(), label="Facture à solder")
    montant = forms.DecimalField(max_digits=12, decimal_places=0)
    commentaire = forms.CharField(widget=forms.Textarea(attrs={"rows": 2}), required=False)

    def __init__(self, *args, facture=None, **kwargs):
        self.facture = facture
        super().__init__(*args, **kwargs)
        if facture is not None:
            self.fields["facture_cible"].queryset = Facture.objects.filter(
                client_nom=facture.client_nom
            ).exclude(pk=facture.pk).exclude(statut__in=["PAYEE", "ANNULEE", "IRRECOUVRABLE"])

    def clean_montant(self):
        montant = self.cleaned_data["montant"]
        if montant <= 0:
            raise forms.ValidationError("Le montant doit être supérieur à zéro.")
        if self.facture and montant > self.facture.trop_percu_disponible:
            raise forms.ValidationError("La compensation dépasse le trop-perçu disponible.")
        return montant

    def clean(self):
        cleaned = super().clean()
        facture_cible = cleaned.get("facture_cible")
        montant = cleaned.get("montant")
        if facture_cible and montant and montant > facture_cible.solde_restant:
            raise forms.ValidationError("Le montant dépasse le solde restant dû sur la facture cible.")
        return cleaned


class EtapeRelanceForm(forms.ModelForm):
    class Meta:
        model = EtapeRelance
        fields = ["nom", "delai_jours", "type_action", "sujet_email", "corps_message", "actif"]
        widgets = {
            "corps_message": forms.Textarea(attrs={"rows": 4}),
        }
        help_texts = {
            "corps_message": "Variables disponibles : {client_nom}, {numero_facture}, {montant_du}, {jours_retard}",
        }


class LitigeForm(forms.ModelForm):
    class Meta:
        model = Litige
        fields = ["motif_type", "description"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }


class CommentaireLitigeForm(forms.ModelForm):
    class Meta:
        model = CommentaireLitige
        fields = ["message"]
        widgets = {
            "message": forms.Textarea(attrs={"rows": 2}),
        }


class PieceJointeLitigeForm(forms.ModelForm):
    class Meta:
        model = PieceJointeLitige
        fields = ["libelle", "fichier"]


class AffectationRecouvreurForm(forms.Form):
    recouvreur = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True), required=False, label="Recouvreur"
    )


class ActionRecouvrementForm(forms.ModelForm):
    class Meta:
        model = ActionRecouvrement
        fields = ["type_action", "commentaire"]
        widgets = {"commentaire": forms.Textarea(attrs={"rows": 2})}


class ResolutionLitigeForm(forms.Form):
    commentaire = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3}),
        label="Résolution"
    )


class NoteInterneForm(forms.Form):
    message = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2}),
        label="Note interne",
    )


class FournisseurForm(forms.ModelForm):
    class Meta:
        model = Fournisseur
        fields = ["raison_sociale", "ncc", "contact_nom", "telephone", "email",
                  "adresse", "delai_paiement_jours", "notation", "actif", "notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 3})}


class ContratFournisseurForm(forms.ModelForm):
    class Meta:
        model = ContratFournisseur
        fields = ["libelle", "fichier", "date_debut", "date_fin"]
        widgets = {
            "date_debut": forms.DateInput(attrs={"type": "date"}),
            "date_fin": forms.DateInput(attrs={"type": "date"}),
        }


class DepenseForm(forms.ModelForm):
    class Meta:
        model = Depense
        fields = ["fournisseur", "categorie", "montant_ht", "taux_tva",
                  "date_facture", "date_echeance", "mode_paiement",
                  "compte_bancaire", "observations", "est_recurrente"]
        widgets = {
            "date_facture": forms.DateInput(attrs={"type": "date"}),
            "date_echeance": forms.DateInput(attrs={"type": "date"}),
            "observations": forms.Textarea(attrs={"rows": 2}),
        }


class DocumentDepenseForm(forms.ModelForm):
    class Meta:
        model = DocumentDepense
        fields = ["type_document", "fichier"]


class PaiementDepenseForm(forms.ModelForm):
    class Meta:
        model = PaiementDepense
        fields = [
            "montant", "date_paiement", "mode_paiement",
            "operateur_mobile_money", "reference_transaction_externe",
            "reference_bancaire", "justificatif", "commentaire"
        ]
        widgets = {
            "date_paiement": forms.DateInput(attrs={"type": "date"}),
            "commentaire": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, depense=None, **kwargs):
        self.depense = depense
        super().__init__(*args, **kwargs)

    def clean_montant(self):
        montant = self.cleaned_data["montant"]
        if montant <= 0:
            raise forms.ValidationError("Le montant doit être supérieur à zéro.")
        return montant
