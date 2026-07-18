"""
Conversion entre les modèles internes (Facture, LigneFacture) et le format
attendu par l'API FNE de la DGI.
Référence : PROCEDURE D'INTERFACAGE DES ENTREPRISES PAR API (DGI, mai 2025).
"""


def code_taxe_fne(taux_tva, regime_imposition=""):
    """Convertit le taux de TVA interne ('18'/'9'/'0') vers le code TVA FNE.
    TVA  = 18% taux normal
    TVAB = 9%  taux réduit
    TVAC = 0%  exonération conventionnelle
    TVAD = 0%  exonération légale (régimes TEE / RME)
    """
    if taux_tva == "18":
        return "TVA"
    if taux_tva == "9":
        return "TVAB"
    if taux_tva == "0":
        return "TVAD" if regime_imposition == "TEE" else "TVAC"
    return "TVA"


def erreurs_champs_obligatoires(facture):
    """Vérifie tous les champs marqués (O) obligatoire dans la documentation FNE,
    y compris les obligations conditionnelles (ex : NCC obligatoire seulement en B2B).
    Retourne une liste d'erreurs lisibles ; liste vide = la facture peut être certifiée."""
    erreurs = []

    if not facture.client_nom:
        erreurs.append("Le nom / raison sociale du client est obligatoire.")
    if not facture.client_telephone:
        erreurs.append("Le téléphone du client est obligatoire.")
    if not facture.client_email:
        erreurs.append("L'email du client est obligatoire.")
    if not facture.payment_method:
        erreurs.append("La méthode de paiement est obligatoire.")
    if not facture.template:
        erreurs.append("Le modèle de facturation (B2B/B2C/B2G/B2F) est obligatoire.")
    if facture.template == "B2B" and not facture.client_ncc:
        erreurs.append("Le NCC du client est obligatoire pour une facturation B2B.")
    if facture.is_rne and not facture.rne_numero:
        erreurs.append("Le numéro du reçu (RNE) est obligatoire quand la facture est liée à un reçu.")
    if not facture.point_de_vente:
        erreurs.append("Le point de vente est obligatoire (voir Paramètres → FNE).")
    if not facture.etablissement:
        erreurs.append("L'établissement est obligatoire (voir Paramètres → FNE).")
    if facture.devise_etrangere and not facture.taux_devise_etrangere:
        erreurs.append("Le taux de la devise étrangère est obligatoire dès qu'une devise étrangère est renseignée.")

    lignes = list(facture.lignes.all())
    if not lignes:
        erreurs.append("La facture doit contenir au moins une ligne d'article.")
    for ligne in lignes:
        if not ligne.designation:
            erreurs.append("Chaque ligne doit avoir une désignation.")
        if ligne.quantite is None or ligne.quantite <= 0:
            erreurs.append(f"Quantité invalide sur la ligne « {ligne.designation or '—'} ».")
        if ligne.prix_unitaire is None or ligne.prix_unitaire < 0:
            erreurs.append(f"Prix unitaire invalide sur la ligne « {ligne.designation or '—'} ».")

    return erreurs


def construire_payload_fne(facture):
    """Construit le corps JSON exact attendu par POST $url/external/invoices/sign.
    À n'appeler qu'après avoir vérifié que erreurs_champs_obligatoires(facture) == []."""
    regime = facture.devis_source.regime_imposition if facture.devis_source_id else ""

    items = []
    for ligne in facture.lignes.all():
        item = {
            "taxes": [code_taxe_fne(ligne.taux_tva, regime)],
            "reference": ligne.reference or "",
            "description": ligne.designation,
            "quantity": float(ligne.quantite),
            "amount": float(ligne.prix_unitaire),
            "discount": 0,
        }
        if ligne.unite_mesure:
            item["measurementUnit"] = ligne.unite_mesure
        items.append(item)

    payload = {
        "invoiceType": facture.invoice_type,
        "paymentMethod": facture.payment_method,
        "template": facture.template,
        "isRne": facture.is_rne,
        "clientCompanyName": facture.client_nom,
        "clientPhone": facture.client_telephone,
        "clientEmail": facture.client_email,
        "pointOfSale": facture.point_de_vente,
        "establishment": facture.etablissement,
        "foreignCurrency": facture.devise_etrangere or "",
        "foreignCurrencyRate": float(facture.taux_devise_etrangere or 0),
        "items": items,
        "discount": float(facture.remise_montant or 0),
    }
    if facture.template == "B2B" and facture.client_ncc:
        payload["clientNcc"] = facture.client_ncc
    if facture.is_rne and facture.rne_numero:
        payload["rne"] = facture.rne_numero
    if facture.vendeur_nom:
        payload["clientSellerName"] = facture.vendeur_nom
    if facture.message_commercial:
        payload["commercialMessage"] = facture.message_commercial
    if facture.pied_de_page:
        payload["footer"] = facture.pied_de_page

    return payload