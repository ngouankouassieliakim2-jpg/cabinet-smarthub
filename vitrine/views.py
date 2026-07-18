# vitrine/views.py

import logging
from django.shortcuts import render, redirect
from django.urls import reverse
from django.http import Http404
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.utils.html import strip_tags

from actualites.models import Article
from rendezvous.forms import DemandeRendezVousForm
from .services_data import SERVICES_DATA

# Configuration du logger pour le suivi de production
logger = logging.getLogger(__name__)


def accueil(request):
    """Page d'accueil publique de la Vitrine (Affiche les 3 articles les plus récents)."""
    derniers_articles = Article.objects.filter(publie=True).order_by("-date_publication")[:3]
    return render(request, "vitrine/accueil.html", {"derniers_articles": derniers_articles})


def a_propos(request):
    """Page de présentation du cabinet."""
    return render(request, "vitrine/a_propos.html")


def contact(request):
    """Page de contact + traitement du formulaire de rendez-vous avec email HTML pro."""
    if request.method == "POST":
        form = DemandeRendezVousForm(request.POST)
        if form.is_valid():
            demande = form.save()

            # Construction du contenu Email au format HTML
            sujet = f"⚠️ Nouvelle demande de rendez-vous — {demande.nom}"
            html_message = f"""
            <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; border: 1px solid #e0e0e0; padding: 20px; border-radius: 8px;">
                    <h2 style="color: #C81E6E; border-bottom: 2px solid #FF4081; padding-bottom: 10px; margin-top: 0;">
                        Détails du Rendez-vous
                    </h2>
                    <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
                        <tr style="background-color: #f9f9f9;">
                            <td style="padding: 10px; font-weight: bold; width: 35%; border-bottom: 1px solid #eee;">Nom :</td>
                            <td style="padding: 10px; border-bottom: 1px solid #eee;">{demande.nom}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px; font-weight: bold; border-bottom: 1px solid #eee;">Téléphone :</td>
                            <td style="padding: 10px; border-bottom: 1px solid #eee;">{demande.telephone}</td>
                        </tr>
                        <tr style="background-color: #f9f9f9;">
                            <td style="padding: 10px; font-weight: bold; border-bottom: 1px solid #eee;">Email :</td>
                            <td style="padding: 10px; border-bottom: 1px solid #eee;">{demande.email or '—'}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px; font-weight: bold; border-bottom: 1px solid #eee;">Objet(s) :</td>
                            <td style="padding: 10px; border-bottom: 1px solid #eee;">{demande.motifs}</td>
                        </tr>
                        <tr style="background-color: #f9f9f9;">
                            <td style="padding: 10px; font-weight: bold; border-bottom: 1px solid #eee;">Structure :</td>
                            <td style="padding: 10px; border-bottom: 1px solid #eee;">{demande.get_structure_display() or '—'}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px; font-weight: bold; border-bottom: 1px solid #eee;">Secteur :</td>
                            <td style="padding: 10px; border-bottom: 1px solid #eee;">{demande.secteur or '—'}</td>
                        </tr>
                        <tr style="background-color: #f9f9f9;">
                            <td style="padding: 10px; font-weight: bold; border-bottom: 1px solid #eee;">Cabinet actuel :</td>
                            <td style="padding: 10px; border-bottom: 1px solid #eee;">{'Oui' if demande.cabinet_actuel else 'Non'}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px; font-weight: bold; border-bottom: 1px solid #eee;">Chiffre d'Affaires :</td>
                            <td style="padding: 10px; border-bottom: 1px solid #eee;">{demande.get_chiffre_affaires_display() or '—'}</td>
                        </tr>
                        <tr style="background-color: #f9f9f9;">
                            <td style="padding: 10px; font-weight: bold; border-bottom: 1px solid #eee;">Lieu souhaité :</td>
                            <td style="padding: 10px; border-bottom: 1px solid #eee;">{demande.get_lieu_display()}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px; font-weight: bold; border-bottom: 1px solid #eee;">Date souhaitée :</td>
                            <td style="padding: 10px; border-bottom: 1px solid #eee;">{demande.date_souhaitee or '—'}</td>
                        </tr>
                    </table>
                    <div style="margin-top: 20px; padding: 15px; background-color: #f5f5f5; border-radius: 4px; border-left: 4px solid #C81E6E;">
                        <h4 style="margin: 0 0 10px 0; color: #333;">Message du client :</h4>
                        <p style="margin: 0; font-style: italic;">{demande.message or 'Aucun message supplémentaire.'}</p>
                    </div>
                </body>
            </html>
            """
            plain_message = strip_tags(html_message)

            try:
                send_mail(
                    subject=sujet,
                    message=plain_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[settings.CONTACT_EMAIL],
                    fail_silently=False,
                    html_message=html_message
                )
            except Exception as e:
                logger.exception("Erreur critique lors de l'envoi de l'email de rendez-vous : %s", e)

            messages.success(
                request,
                "Votre demande a bien été enregistrée. Notre équipe vous recontactera dans les plus brefs délais."
            )
            return redirect("contact")
    else:
        # Pré-remplissage intelligent du motif si passé en paramètre d'URL (ex: ?service=comptabilite)
        initial_service = request.GET.get("service")
        initial_data = {}
        if initial_service:
            initial_data["motifs"] = [initial_service]
            
        form = DemandeRendezVousForm(initial=initial_data)

    return render(request, "vitrine/contact.html", {"form": form})


def detail_service(request, service_slug):
    """Ancienne URL /services/<slug>/ : conservée pour ne casser aucun lien déjà
    partagé ou indexé, mais redirige désormais vers la section détaillée
    correspondante sur la page unique /services/#slug (voir services.html)."""
    if service_slug not in SERVICES_DATA:
        raise Http404("Le service demandé est introuvable.")
    return redirect(f"{reverse('services')}#{service_slug}")


def services(request):
    """Page présentant les domaines d'intervention avec tous les détails."""
    context = {
        'services': SERVICES_DATA  # On passe tout le dictionnaire
    }
    return render(request, "vitrine/services.html", context)