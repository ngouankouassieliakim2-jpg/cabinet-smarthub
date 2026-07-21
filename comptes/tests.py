from django.contrib.auth.models import User
from django.test import TestCase

from comptes.models import Profil
from pilotage.models import Pole, Poste


class ProfilTests(TestCase):
    def test_le_profil_limite_les_postes_secondaires_a_deux(self):
        user = User.objects.create_user(username="profil-test", password="secret")
        pole = Pole.objects.create(nom="Direction")
        poste_principal = Poste.objects.create(intitule="Responsable recouvrement", pole=pole)
        poste_secondaire_1 = Poste.objects.create(intitule="Assistant recouvrement", pole=pole)
        poste_secondaire_2 = Poste.objects.create(intitule="Analyste créances", pole=pole)
        poste_secondaire_3 = Poste.objects.create(intitule="Coordinateur contentieux", pole=pole)

        profil = Profil.objects.create(user=user, role=Profil.Role.CADRE, poste=poste_principal)
        profil.postes_secondaires.add(poste_secondaire_1, poste_secondaire_2)

        with self.assertRaises(ValueError):
            profil.ajouter_poste_secondaire(poste_secondaire_3)
