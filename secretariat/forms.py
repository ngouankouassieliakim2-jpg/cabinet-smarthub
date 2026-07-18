from django import forms

from .models import AppelTelephonique


class AppelForm(forms.ModelForm):
    class Meta:
        model = AppelTelephonique
        fields = ["nom_appelant", "telephone", "objet", "a_rappeler", "date_rappel", "notes"]
        widgets = {
            "nom_appelant": forms.TextInput(attrs={"placeholder": "Nom de la personne qui a appelé"}),
            "telephone": forms.TextInput(attrs={"placeholder": "Ex. 07 07 31 59 64 (facultatif)"}),
            "objet": forms.Textarea(attrs={"rows": 2, "placeholder": "Pourquoi a-t-elle appelé ?"}),
            "date_rappel": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 2, "placeholder": "Détails éventuels (facultatif)"}),
        }
        labels = {
            "nom_appelant": "Nom de l'appelant",
            "telephone": "Téléphone",
            "objet": "Objet de l'appel",
            "a_rappeler": "À rappeler",
            "date_rappel": "Date de rappel souhaitée",
            "notes": "Notes",
        }