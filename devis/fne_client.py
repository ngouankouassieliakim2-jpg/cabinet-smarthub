"""Client HTTP pour l'API de certification FNE (DGI Côte d'Ivoire).
Référence : PROCEDURE D'INTERFACAGE DES ENTREPRISES PAR API (DGI, mai 2025)."""
import requests
from django.utils import timezone

from parametres.models import ParametresFNE
from .fne import erreurs_champs_obligatoires, construire_payload_fne


def certifier_facture(facture):
    """Envoie la facture à la plateforme FNE pour certification (POST /external/invoices/sign).
    Retourne (succes: bool, message: str). Met à jour et sauvegarde facture.fne_* dans tous les cas."""
    parametres = ParametresFNE.get_solo()

    if not parametres.est_configure:
        return False, "La clé API FNE n'est pas configurée (Paramètres → FNE)."

    erreurs = erreurs_champs_obligatoires(facture)
    if erreurs:
        return False, "Champs obligatoires manquants : " + " ; ".join(erreurs)

    payload = construire_payload_fne(facture)
    url = f"{parametres.url_active.rstrip('/')}/external/invoices/sign"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {parametres.api_key}",
    }

    try:
        reponse = requests.post(url, json=payload, headers=headers, timeout=30)
    except requests.RequestException as e:
        facture.fne_statut = "ERREUR"
        facture.fne_erreur = f"Connexion impossible à la FNE : {e}"
        facture.save(update_fields=["fne_statut", "fne_erreur"])
        return False, facture.fne_erreur

    if reponse.status_code in (200, 201):
        data = reponse.json()
        facture.fne_statut = "CERTIFIEE"
        facture.fne_ncc_emetteur = data.get("ncc", "")
        facture.fne_reference = data.get("reference", "")
        facture.fne_token = data.get("token", "")
        facture.fne_warning = bool(data.get("warning", False))
        facture.fne_balance_sticker = data.get("balance_sticker")
        facture.fne_invoice_id = (data.get("invoice") or {}).get("id", "")
        facture.fne_date_certification = timezone.now()
        facture.fne_erreur = ""
        if facture.statut == "A_CERTIFIER":
            facture.statut = "CERTIFIEE"
        facture.save()
        return True, "Facture certifiée avec succès."

    # Codes documentés : 400 requête invalide, 401 authentification, 500 endpoint indisponible
    try:
        detail = reponse.json().get("message", reponse.text)
    except ValueError:
        detail = reponse.text
    facture.fne_statut = "ERREUR"
    facture.fne_erreur = f"HTTP {reponse.status_code} : {detail}"
    facture.save(update_fields=["fne_statut", "fne_erreur"])
    return False, facture.fne_erreur


def annuler_facture(facture, lignes_a_retourner):
    """Certifie un avoir (POST /external/invoices/{id}/refund).
    lignes_a_retourner : liste de dicts {"id_fne": <id article FNE>, "quantite": <qte à annuler>}.
    Nécessite que la facture d'origine ait déjà été certifiée (fne_invoice_id rempli)."""
    parametres = ParametresFNE.get_solo()
    if not parametres.est_configure:
        return False, "La clé API FNE n'est pas configurée (Paramètres → FNE)."
    if not facture.fne_invoice_id:
        return False, "Cette facture n'a pas encore été certifiée : impossible de créer un avoir."

    url = f"{parametres.url_active.rstrip('/')}/external/invoices/{facture.fne_invoice_id}/refund"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {parametres.api_key}",
    }
    payload = {"items": [{"id": l["id_fne"], "quantity": l["quantite"]} for l in lignes_a_retourner]}

    try:
        reponse = requests.post(url, json=payload, headers=headers, timeout=30)
    except requests.RequestException as e:
        return False, f"Connexion impossible à la FNE : {e}"

    if reponse.status_code in (200, 201):
        return True, reponse.json()

    try:
        detail = reponse.json().get("message", reponse.text)
    except ValueError:
        detail = reponse.text
    return False, f"HTTP {reponse.status_code} : {detail}"