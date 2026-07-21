from django import forms

from .models import ParametresMobileMoney, ParametresWhatsAppBusiness


class ParametresMobileMoneyForm(forms.ModelForm):
    class Meta:
        model = ParametresMobileMoney
        fields = [
            "wave_environnement",
            "wave_api_key",
            "wave_signature_activee",
            "wave_signing_secret",
            "wave_webhook_secret",
            "om_environnement",
            "om_client_id",
            "om_client_secret",
            "om_merchant_key",
            "om_return_url",
            "om_cancel_url",
            "om_notif_url",
        ]
        widgets = {
            "wave_api_key": forms.PasswordInput(render_value=True),
            "wave_signing_secret": forms.PasswordInput(render_value=True),
            "wave_webhook_secret": forms.PasswordInput(render_value=True),
            "om_client_secret": forms.PasswordInput(render_value=True),
            "om_merchant_key": forms.PasswordInput(render_value=True),
        }


class ParametresWhatsAppBusinessForm(forms.ModelForm):
    class Meta:
        model = ParametresWhatsAppBusiness
        fields = [
            "access_token",
            "phone_number_id",
            "whatsapp_business_account_id",
            "app_id",
            "app_secret",
            "verify_token",
        ]
        widgets = {
            "access_token": forms.PasswordInput(render_value=True),
            "app_secret": forms.PasswordInput(render_value=True),
        }
