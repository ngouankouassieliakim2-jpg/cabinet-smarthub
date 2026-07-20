from django.core.management.base import BaseCommand
from devis.models import EtapeRelance

ETAPES_DEFAUT = [
    {
        "nom": "Email courtois",
        "delai_jours": 3,
        "type_action": "EMAIL_COURTOIS",
        "sujet_email": "Rappel — facture {numero_facture}",
        "corps_message": (
            "Bonjour, nous vous rappelons que la facture {numero_facture} d'un montant de "
            "{montant_du} FCFA est en attente de règlement. Cordialement, Cabinet K&L."
        ),
    },
    {
        "nom": "Email plus ferme",
        "delai_jours": 10,
        "type_action": "EMAIL_FERME",
        "sujet_email": "Relance — facture {numero_facture} impayée",
        "corps_message": (
            "Bonjour, la facture {numero_facture} ({montant_du} FCFA) demeure impayée à ce jour "
            "({jours_retard} jours de retard). Merci de régulariser rapidement. Cabinet K&L."
        ),
    },
    {
        "nom": "Notification interne",
        "delai_jours": 20,
        "type_action": "NOTIFICATION_INTERNE",
        "sujet_email": "",
        "corps_message": "",
    },
    {
        "nom": "Lettre PDF",
        "delai_jours": 30,
        "type_action": "LETTRE_PDF",
        "sujet_email": "",
        "corps_message": "",
    },
    {
        "nom": "Escalade Direction",
        "delai_jours": 45,
        "type_action": "ESCALADE_DIRECTION",
        "sujet_email": "",
        "corps_message": "",
    },
    {
        "nom": "Alerte contentieux",
        "delai_jours": 60,
        "type_action": "ALERTE_CONTENTIEUX",
        "sujet_email": "",
        "corps_message": "",
    },
]


class Command(BaseCommand):
    help = "Crée les étapes de relance par défaut si elles n'existent pas déjà."

    def handle(self, *args, **options):
        crees = 0
        for data in ETAPES_DEFAUT:
            _, created = EtapeRelance.objects.get_or_create(
                nom=data["nom"], delai_jours=data["delai_jours"], defaults=data
            )
            if created:
                crees += 1
        self.stdout.write(self.style.SUCCESS(f"{crees} étape(s) créée(s)."))
