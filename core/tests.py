from django.test import TestCase
from django.contrib.auth.models import User
from core.models import JournalExecutionCommande
from core.execution import tracer_execution


class JournalExecutionCommandeTests(TestCase):
    def test_tracer_execution_persists_successful_run(self):
        with tracer_execution(
            commande="test_command",
            description="Test de journal d’exécution",
            utilisateur=User.objects.create(username="tester"),
            contexte={"mode": "test"},
        ) as trace:
            trace.resume = "Exécution simulée"

        journal = JournalExecutionCommande.objects.get(commande="test_command")
        self.assertEqual(journal.etat, "SUCCES")
        self.assertEqual(journal.resume, "Exécution simulée")
        self.assertEqual(journal.contexte.get("mode"), "test")
