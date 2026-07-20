from datetime import date
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from devis.models import Facture, EtapeRelance, Relance
from pilotage.models import Notification

STATUTS_CONCERNES = ["EN_ATTENTE_PAIEMENT", "PARTIELLEMENT_PAYEE", "EN_RETARD"]


class Command(BaseCommand):
    help = "Déclenche les relances dont le délai est atteint, pour chaque facture en retard."

    def handle(self, *args, **options):
        aujourdhui = date.today()
        etapes = list(EtapeRelance.objects.filter(actif=True).order_by("delai_jours"))
        factures = Facture.objects.filter(
            statut__in=STATUTS_CONCERNES,
            date_echeance__isnull=False,
            date_echeance__lt=aujourdhui,
        )

        total_declenchees = 0
        for facture in factures:
            jours_retard = (aujourdhui - facture.date_echeance).days
            for etape in etapes:
                if etape.delai_jours > jours_retard:
                    continue
                if Relance.objects.filter(facture=facture, etape=etape).exists():
                    continue
                self._declencher(facture, etape, jours_retard)
                total_declenchees += 1

        self.stdout.write(self.style.SUCCESS(f"{total_declenchees} relance(s) déclenchée(s)."))

    def _formater_message(self, gabarit, facture, jours_retard):
        return gabarit.format(
            client_nom=facture.client_nom,
            numero_facture=facture.numero_facture,
            montant_du=facture.montant_du,
            jours_retard=jours_retard,
        )

    def _declencher(self, facture, etape, jours_retard):
        reussie, erreur = True, ""
        try:
            if etape.type_action in ("EMAIL_COURTOIS", "EMAIL_FERME"):
                self._envoyer_email(facture, etape, jours_retard)
            elif etape.type_action == "NOTIFICATION_INTERNE":
                self._notifier_interne(facture, etape, jours_retard, direction=False)
            elif etape.type_action == "LETTRE_PDF":
                self._generer_lettre_pdf(facture, etape, jours_retard)
            elif etape.type_action == "ESCALADE_DIRECTION":
                self._notifier_interne(facture, etape, jours_retard, direction=True)
            elif etape.type_action == "ALERTE_CONTENTIEUX":
                self._notifier_interne(
                    facture, etape, jours_retard, direction=True, urgent=True
                )
        except Exception as e:
            reussie, erreur = False, str(e)

        Relance.objects.create(facture=facture, etape=etape, reussie=reussie, erreur=erreur)

    def _envoyer_email(self, facture, etape, jours_retard):
        if not facture.client_email:
            raise ValueError("Facture sans email client — impossible d'envoyer la relance.")
        sujet = self._formater_message(etape.sujet_email, facture, jours_retard)
        corps = self._formater_message(etape.corps_message, facture, jours_retard)
        send_mail(sujet, corps, settings.DEFAULT_FROM_EMAIL, [facture.client_email])

    def _notifier_interne(self, facture, etape, jours_retard, direction=False, urgent=False):
        prefixe = "🔴 " if urgent else ("⚠️ " if direction else "")
        titre = f"{prefixe}{etape.nom} — {facture.numero_facture}"
        if facture.recouvreur:
            titre += f" ({facture.recouvreur})"
        titre = titre[:200]
        message = (
            f"{facture.client_nom} — {facture.montant_du} FCFA dû, "
            f"{jours_retard} jours de retard."
        )[:300]

        cle = f"relance_{etape.type_action.lower()}_facture{facture.id}_etape{etape.id}"

        Notification.objects.get_or_create(
            cle=cle,
            defaults={
                "type_notification": f"relance_{etape.type_action.lower()}",
                "titre": titre,
                "message": message,
                "url": reverse("devis:detail_creance", args=[facture.id]),
            },
        )

    def _generer_lettre_pdf(self, facture, etape, jours_retard):
        # TODO : générer le PDF de relance via WeasyPrint ou autre.
        pass
