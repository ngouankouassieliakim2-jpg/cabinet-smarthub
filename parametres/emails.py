from django.core.mail import EmailMessage
from django.core.mail import get_connection
from .models import ParametresEmail


def envoyer_email(destinataires, sujet, message, fichiers=None):
    """
    Fonction d'envoi centrale, réutilisable partout dans le projet.

    - destinataires : liste d'adresses email (ex : ["client@mail.com"])
    - sujet : texte du sujet
    - message : corps du message
    - fichiers : liste optionnelle de tuples (nom_fichier, contenu_bytes, type_mime)

    Retourne (True, "") si envoyé, sinon (False, "message d'erreur").
    """
    params = ParametresEmail.get_solo()

    if not params.est_configure:
        return False, "L'envoi d'emails n'est pas configuré (Paramètres → Email d'envoi)."

    if isinstance(destinataires, str):
        destinataires = [destinataires]
    destinataires = [d for d in destinataires if d]
    if not destinataires:
        return False, "Aucun destinataire valide."

    try:
        # Connexion SMTP avec les réglages saisis dans Paramètres
        connection = get_connection(
            backend="django.core.mail.backends.smtp.EmailBackend",
            host="smtp.gmail.com",
            port=587,
            username=params.adresse_envoi,
            password=params.mot_de_passe_app,
            use_tls=True,
        )

        expediteur = f"{params.nom_expediteur} <{params.adresse_envoi}>"
        email = EmailMessage(
            subject=sujet,
            body=message,
            from_email=expediteur,
            to=destinataires,
            connection=connection,
        )

        # Pièces jointes éventuelles
        if fichiers:
            for nom, contenu, mime in fichiers:
                email.attach(nom, contenu, mime)

        email.send(fail_silently=False)
        return True, ""

    except Exception as e:
        return False, str(e)