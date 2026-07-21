from django.test import TestCase

from .models import ParametresMobileMoney, ParametresWhatsAppBusiness


class ParametresIntegrationTests(TestCase):
    def test_mobile_money_configuration_properties(self):
        params = ParametresMobileMoney.objects.create()

        self.assertFalse(params.wave_configure)
        self.assertFalse(params.orange_money_configure)

    def test_mobile_money_wave_signature_fields(self):
        params = ParametresMobileMoney.objects.create(
            wave_signature_activee=True,
            wave_signing_secret="wave_sn_AKS_123",
        )

        self.assertTrue(params.wave_signature_activee)
        self.assertEqual(params.wave_signing_secret, "wave_sn_AKS_123")

    def test_whatsapp_business_configuration_property(self):
        params = ParametresWhatsAppBusiness.objects.create()

        self.assertFalse(params.est_configure)

        params.access_token = "token"
        params.phone_number_id = "123"
        params.save()

        self.assertTrue(params.est_configure)
