from datetime import timedelta


def jours_relances():
    """Retourne la liste des jours (depuis l'envoi) où une relance est prévue.
    Calendrier :
      - Mois 1 : tous les 5 jours → J+5,10,15,20,25,30 (6 relances)
      - Mois 2 à 4 : une par mois → J+60, J+90, J+120 (3 relances)
      - Mois 5 à 12 : 5 relances → J+150,210,270,330,365
      - Après 1 an : une par an → J+730, J+1095, ...
    """
    jours = [5, 10, 15, 20, 25, 30]          # mois 1
    jours += [60, 90, 120]                    # mois 2-4
    jours += [150, 210, 270, 330, 365]        # mois 5-12
    # Après 1 an : une relance par an pendant quelques années
    jours += [730, 1095, 1460, 1825]
    return jours


def prochaine_relance(devis):
    """Retourne la date de la prochaine relance prévue, ou None si terminé.
    Se base sur date_envoi et le nombre de relances déjà faites."""
    if not devis.date_envoi:
        return None
    jours = jours_relances()
    n = devis.nombre_relances
    if n >= len(jours):
        return None  # toutes les relances prévues ont été faites
    return devis.date_envoi + timedelta(days=jours[n])


def relance_due(devis, aujourdhui=None):
    """Vrai si une relance est due aujourd'hui (ou en retard) pour ce devis."""
    from datetime import date
    if aujourdhui is None:
        aujourdhui = date.today()
    # On ne relance que les devis ENVOYÉS
    if devis.statut != "ENVOYE":
        return False
    prochaine = prochaine_relance(devis)
    if prochaine is None:
        return False
    return prochaine <= aujourdhui
def envoyer_relances_dues(request=None):
    """Parcourt les devis ENVOYÉS et envoie automatiquement les relances dues.
    Retourne le nombre de relances envoyées. Réutilisable par un planificateur plus tard."""
    from datetime import date
    from .models import Devis
    from .pdf import generer_pdf_devis
    from parametres.emails import envoyer_email

    aujourdhui = date.today()
    nb_envoyees = 0

    # On ne traite que les devis encore "Envoyé" avec une date d'envoi et un email
    devis_list = Devis.objects.filter(statut="ENVOYE").exclude(date_envoi=None)

    for devis in devis_list:
        if not devis.email:
            continue
        if not relance_due(devis, aujourdhui):
            continue

        try:
            pdf_bytes = generer_pdf_devis(devis, request)

            if devis.type_client == "PM":
                nom_client = devis.pm_raison_sociale or "Madame, Monsieur"
            else:
                nom_client = devis.pp_nom_prenoms or "Madame, Monsieur"

            sujet = f"Rappel — Votre devis {devis.numero_devis} (Cabinet K&L)"
            corps = (
                f"Bonjour {nom_client},\n\n"
                f"Nous nous permettons de revenir vers vous concernant notre devis "
                f"n° {devis.numero_devis}, que nous vous avons adressé précédemment.\n\n"
                f"Sauf erreur de notre part, nous n'avons pas encore reçu votre retour. "
                f"Nous vous le transmettons à nouveau ci-joint pour rappel et restons "
                f"à votre entière disposition pour toute question ou ajustement.\n\n"
                f"Dans l'attente de votre retour, veuillez agréer nos salutations distinguées.\n\n"
                f"Cabinet Comptable & Fiscal K&L\n"
                f"Tél : 27 32 70 44 04\n"
                f"cabinetkl120@gmail.com"
            )

            fichiers = [(f"Devis-{devis.numero_devis}.pdf", pdf_bytes, "application/pdf")]
            ok, _ = envoyer_email([devis.email], sujet, corps, fichiers)

            if ok:
                devis.nombre_relances += 1
                devis.date_derniere_relance = aujourdhui
                devis.save()
                nb_envoyees += 1
        except Exception:
            # On ignore les erreurs individuelles pour ne pas bloquer les autres relances
            continue

    return nb_envoyees