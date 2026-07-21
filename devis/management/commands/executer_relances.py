from datetime import date
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from devis.models import Facture, EtapeRelance, Relance
from pilotage.models import Notification
from core.execution import tracer_execution

STATUTS_CONCERNES = ["EN_ATTENTE_PAIEMENT", "PARTIELLEMENT_PAYEE", "EN_RETARD"]


class Command(BaseCommand):
    help = "Déclenche les relances dont le délai est atteint, pour chaque facture en retard."

    def handle(self, *args, **options):
        with tracer_execution(
            commande="executer_relances",
            description="Déclenchement des relances automatiques",
            utilisateur=User.objects.filter(is_superuser=True).first(),
            contexte={"statuts_concernes": STATUTS_CONCERNES},
        ) as trace:
            aujourdhui = date.today()
            etapes = list(EtapeRelance.objects.filter(actif=True).order_by("delai_jours"))
            factures = Facture.objects.filter(
                statut__in=STATUTS_CONCERNES,
                date_echeance__isnull=False,
                date_echeance__lt=aujourdhui,
            )

            total_declenchees = 0
            for facture in factures:
                if facture.a_promesse_active:
                    continue
                jours_retard = (aujourdhui - facture.date_echeance).days
                for etape in etapes:
                    if etape.delai_jours > jours_retard:
                        continue
                    if Relance.objects.filter(facture=facture, etape=etape).exists():
                        continue
                    self._declencher(facture, etape, jours_retard)
                    total_declenchees += 1

            trace.resume = f"{total_declenchees} relance(s) déclenchée(s)."
            self.stdout.write(self.style.SUCCESS(trace.resume))

    def _formater_message(self, gabarit, facture, jours_retard):
        return gabarit.format(
            client_nom=facture.client_nom,
            numero_facture=facture.numero_facture,
            montant_du=facture.montant_du,
            jours_retard=jours_retard,
        )

    def _declencher(self, facture, etape, jours_retard):
        reussie, erreur = True, ""
        document_genere = None
        try:
            if etape.type_action in ("EMAIL_COURTOIS", "EMAIL_FERME"):
                self._envoyer_email(facture, etape, jours_retard)
            elif etape.type_action == "NOTIFICATION_INTERNE":
                self._notifier_interne(facture, etape, jours_retard, direction=False)
            elif etape.type_action == "LETTRE_PDF":
                document_genere = self._generer_lettre_pdf(facture, etape, jours_retard)
            elif etape.type_action == "ESCALADE_DIRECTION":
                self._notifier_interne(facture, etape, jours_retard, direction=True)
            elif etape.type_action == "ALERTE_CONTENTIEUX":
                self._notifier_interne(
                    facture, etape, jours_retard, direction=True, urgent=True
                )
        except Exception as e:
            reussie, erreur = False, str(e)

        Relance.objects.create(
            facture=facture,
            etape=etape,
            reussie=reussie,
            erreur=erreur,
            document_genere=document_genere,
        )

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
                "destinataire": facture.recouvreur,
            },
        )

    def _generer_lettre_pdf(self, facture, etape, jours_retard):
        contenu = (
            f"Bonjour {facture.client_nom},\n\n"
            f"Nous vous rappelons que la facture {facture.numero_facture} est en retard de {jours_retard} jours.\n"
            f"Le montant dû s'élève à {facture.montant_du} FCFA.\n\n"
            f"Merci de procéder au règlement dans les meilleurs délais.\n\n"
            f"Cordialement,\nCabinet Smart-Hub"
        )
        pdf_bytes = self._construire_pdf_simple(contenu)
        return ContentFile(pdf_bytes, name=f"relance_{facture.numero_facture}_{etape.id}.pdf")

    def _construire_pdf_simple(self, contenu):
        lignes = contenu.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        texte = "\\n".join(lignes)
        pdf = """%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>
endobj
4 0 obj
<< /Length 0 >>
stream
endstream
endobj
5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
xref
0 6
0000000000 65535 f 
0000000010 00000 n 
0000000062 00000 n 
0000000119 00000 n 
0000000207 00000 n 
0000000300 00000 n 
trailer
<< /Size 6 /Root 1 0 R >>
startxref
0
%%EOF
"""
        return pdf.encode("latin-1", errors="ignore")
