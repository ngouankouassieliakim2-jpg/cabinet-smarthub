from datetime import date, timedelta
from decimal import Decimal
from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase

from devis.models import (
    CategorieDepense, Depense, DepenseRecurrente, Fournisseur,
    GenerationDepenseRecurrente, SeuilApprobation, NoteDeFrais, LigneNoteDeFrais,
    Facture, EtapeRelance, PromessePaiement, Relance,
)
from devis.kpi_depenses import depenses_par_categorie, depenses_par_service
from pilotage.models import Notification


class ValidationDepenseTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="tester", password="secret")
        self.fournisseur = Fournisseur.objects.create(raison_sociale="Fournisseur test")
        self.categorie = CategorieDepense.objects.create(nom="Frais généraux")
        self.seuil = SeuilApprobation.objects.create(
            borne_min=0,
            borne_max=99999,
            niveau_requis="CADRE",
        )

    def test_soumission_et_validation_dune_depense(self):
        depense = Depense.objects.create(
            fournisseur=self.fournisseur,
            categorie=self.categorie,
            montant_ht=Decimal("100000"),
            taux_tva="18",
            date_facture="2026-07-20",
        )

        depense.soumettre(utilisateur=self.user)
        self.assertEqual(depense.statut_validation, "SOUMISE")
        self.assertEqual(depense.niveau_requis, "DIRECTION")

        depense.valider(utilisateur=self.user, commentaire="ok")
        self.assertEqual(depense.statut_validation, "VALIDEE")

    def test_le_paiement_est_bloque_jusqu_a_validation(self):
        depense = Depense.objects.create(
            fournisseur=self.fournisseur,
            categorie=self.categorie,
            montant_ht=Decimal("100000"),
            taux_tva="18",
            date_facture="2026-07-20",
        )

        with self.assertRaises(ValueError):
            depense.enregistrer_paiement(Decimal("50000"), utilisateur=self.user)

    def test_seed_seuils_approbation_cree_les_seuils_par_defaut(self):
        SeuilApprobation.objects.all().delete()

        call_command("seed_seuils_approbation")

        self.assertEqual(SeuilApprobation.objects.count(), 3)

    def test_generation_dune_depense_recurrente_cree_une_entree_unique(self):
        recurrente = DepenseRecurrente.objects.create(
            libelle="Abonnement mensuel",
            fournisseur=self.fournisseur,
            categorie=self.categorie,
            montant_ht=Decimal("50000"),
            taux_tva="18",
            frequence="MENSUEL",
            jour_generation=15,
            date_debut=date(2026, 1, 1),
            actif=True,
            cree_par=self.user,
        )

        depense = recurrente.generer_depense(date(2026, 7, 15), utilisateur=self.user)

        self.assertIsNotNone(depense)
        self.assertTrue(depense.est_recurrente)
        self.assertEqual(GenerationDepenseRecurrente.objects.count(), 1)
        self.assertEqual(
            GenerationDepenseRecurrente.objects.get(recurrente=recurrente, date_echeance=date(2026, 7, 15)).depense,
            depense,
        )

        doublon = recurrente.generer_depense(date(2026, 7, 15), utilisateur=self.user)
        self.assertIsNone(doublon)

    def test_kpi_depenses_agrege_en_sql_par_categorie_et_service(self):
        depense = Depense.objects.create(
            fournisseur=self.fournisseur,
            categorie=self.categorie,
            montant_ht=Decimal("150000"),
            taux_tva="18",
            date_facture=date(2026, 7, 20),
            cree_par=self.user,
        )

        resultats = depenses_par_categorie(depuis=date(2026, 1, 1))
        self.assertEqual(resultats[0]["categorie__nom"], self.categorie.nom)
        self.assertEqual(resultats[0]["total"], depense.montant_ht)

        services = depenses_par_service(depuis=date(2026, 1, 1))
        self.assertIn("Non renseigné", [s["cree_par__profil__pole__nom"] for s in services])

    def test_note_de_frais_passe_par_le_cycle_de_validation(self):
        note = NoteDeFrais.objects.create(
            collaborateur=self.user,
            periode_debut=date(2026, 7, 1),
            periode_fin=date(2026, 7, 7),
        )
        LigneNoteDeFrais.objects.create(
            note=note,
            type_frais="MISSION",
            date_depense=date(2026, 7, 3),
            description="Déplacement",
            montant=Decimal("25000"),
        )

        note.soumettre()
        self.assertEqual(note.statut, "SOUMISE")

        note.valider(utilisateur=self.user)
        self.assertEqual(note.statut, "VALIDEE")

        note.marquer_remboursee(mode="VIREMENT", reference="REF-1", date_remb=date(2026, 7, 10))
        self.assertEqual(note.statut, "REMBOURSEE")

    def test_une_promesse_rompue_cree_une_notification(self):
        facture = Facture.objects.create(
            client_nom="Client test",
            montant_ttc=Decimal("100000"),
            statut="EN_ATTENTE_PAIEMENT",
            date_emission=date.today() - timedelta(days=10),
            date_echeance=date.today() - timedelta(days=1),
        )
        promesse = PromessePaiement.objects.create(
            facture=facture,
            montant_promis=Decimal("50000"),
            date_promise=date.today() - timedelta(days=1),
        )

        promesse.verifier()

        self.assertEqual(promesse.statut, "ROMPUE")
        self.assertTrue(Notification.objects.filter(cle__startswith="promesse_rompue").exists())

    def test_une_relance_n_est_pas_declenchee_si_une_promesse_est_active(self):
        facture = Facture.objects.create(
            client_nom="Client test",
            montant_ttc=Decimal("100000"),
            statut="EN_ATTENTE_PAIEMENT",
            date_emission=date.today() - timedelta(days=10),
            date_echeance=date.today() - timedelta(days=1),
            client_email="client@example.com",
        )
        PromessePaiement.objects.create(
            facture=facture,
            montant_promis=Decimal("50000"),
            date_promise=date.today(),
            statut="EN_COURS",
        )
        EtapeRelance.objects.create(
            nom="Relance test",
            delai_jours=0,
            type_action="NOTIFICATION_INTERNE",
        )

        call_command("executer_relances")

        self.assertEqual(Relance.objects.filter(facture=facture).count(), 0)
