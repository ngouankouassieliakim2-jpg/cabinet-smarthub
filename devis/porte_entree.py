"""Règles du dossier d'identification (sous-module « Porte d'entrée »).
Centralise : la construction du formulaire d'identification complet (enrichi
pour couvrir les besoins des autres modules), les documents requis et leur
conditionnement, et l'enregistrement des associés.
"""
import json
from django import forms as django_forms
from django.forms import modelform_factory

from .models import DocumentPiece, Associe

# ===================== FORMULAIRE D'IDENTIFICATION (Porte d'entrée) =====================

CHAMPS_IDENTITE = {
    "PM": ["pm_raison_sociale", "pm_nom_commercial", "pm_sigle", "pm_forme_juridique", "pm_capital_social"],
    "PP_CONSTITUEE": ["pp_nom_prenoms", "pp_date_naissance", "pp_lieu_naissance", "pp_nationalite",
                      "pp_nom_pere", "pp_nom_mere", "pp_piece_type", "pp_piece_numero",
                      "pp_piece_delivree_le", "pp_piece_delivree_a", "pp_adresse_perso"],
    "PP_INFORMEL": ["pp_nom_prenoms", "pp_piece_type", "pp_piece_numero", "pp_adresse_perso"],
}

# Identifiants légaux : NCC/RCCM/régime/centre des impôts servent à la fois à la
# Comptabilité/Fiscalité et à la Paie (fiche Employeur) — d'où centre_impots et
# numero_cnps, absents de l'ancien formulaire.
CHAMPS_LEGAUX = ["ncc", "code_cdi", "rccm_numero", "rccm_delivre_le", "rccm_delivre_par",
                 "code_activite", "regime_imposition", "centre_impots",
                 "est_employeur", "nombre_salaries", "numero_cnps"]

CHAMPS_OBLIGATIONS = ["obl_patente", "obl_bic_ba", "obl_bnc", "obl_tva", "obl_tob", "obl_taxe_bois",
                      "obl_its", "obl_airsi", "obl_tse", "obl_impots_fonciers", "obl_impot_micro",
                      "obl_igr", "obl_autres"]

CHAMPS_EXONERATION = ["exoneration_type", "exoneration_fondement", "exoneration_debut", "exoneration_fin"]

CHAMPS_SIEGE = ["siege_ville", "siege_commune", "siege_quartier", "siege_rue", "siege_lot",
                "siege_ilot", "ref_section", "ref_parcelle", "ref_tf", "boite_postale"]

CHAMPS_CONTACTS = ["telephone", "telephone2", "email", "fax"]

CHAMPS_ACTIVITE = ["activite_principale", "activite_date_debut", "autres_activites",
                   "ca_previsionnel", "ca_annee_precedente"]

CHAMPS_DIRIGEANT = ["dirigeant_nom", "dirigeant_qualite", "dirigeant_bp", "dirigeant_tel", "dirigeant_email"]

CHAMPS_PROPRIETAIRE = ["proprietaire_nom", "proprietaire_ncc", "proprietaire_adresse",
                       "proprietaire_email", "proprietaire_tel"]

CHAMPS_MISSION = ["regime_mission", "date_effet_mission", "duree_mission_mois",
                  "exercice_concerne", "modalites_paiement", "jour_emission_facture",
                  "lieu_signature"]

CHAMPS_SUIVI_ANTERIEUR = ["a_eu_comptable", "comptable_precedent_nom", "comptable_precedent_ncc",
                          "comptable_precedent_adresse", "comptable_precedent_email", "comptable_precedent_tel"]

CHAMPS_VISA = ["signataire_nom", "signataire_qualite", "declaration_lieu", "declaration_date"]

# Champs obligatoires par type de client — volontairement beaucoup plus large que
# l'ancienne étape 2 : tout ce qui sert à un autre module en aval devient obligatoire ici.
CHAMPS_OBLIGATOIRES = {
    "PM": ["pm_raison_sociale", "pm_forme_juridique", "ncc", "rccm_numero", "code_activite",
           "regime_imposition", "centre_impots", "siege_ville", "siege_commune",
           "telephone", "email", "activite_principale",
           "dirigeant_nom", "dirigeant_qualite", "dirigeant_tel",
           "regime_mission", "date_effet_mission"],
    "PP_CONSTITUEE": ["pp_nom_prenoms", "pp_piece_numero", "ncc", "rccm_numero", "code_activite",
                      "regime_imposition", "centre_impots", "siege_ville", "siege_commune",
                      "telephone", "email", "activite_principale",
                      "regime_mission", "date_effet_mission"],
    "PP_INFORMEL": ["pp_nom_prenoms", "pp_piece_numero", "telephone", "activite_principale",
                     "regime_mission", "date_effet_mission"],
}


def champs_formulaire(type_client):
    """Construit la liste complète des champs du formulaire d'identification, selon le type de client."""
    champs = list(CHAMPS_IDENTITE.get(type_client, []))
    if type_client in ("PM", "PP_CONSTITUEE"):
        champs += CHAMPS_LEGAUX + CHAMPS_OBLIGATIONS + CHAMPS_EXONERATION + CHAMPS_SIEGE
    champs += CHAMPS_CONTACTS
    if type_client in ("PM", "PP_CONSTITUEE"):
        champs += ["autres_etablissements"]
    champs += CHAMPS_ACTIVITE
    if type_client == "PM":
        champs += CHAMPS_DIRIGEANT
    if type_client in ("PM", "PP_CONSTITUEE"):
        champs += CHAMPS_PROPRIETAIRE + CHAMPS_SUIVI_ANTERIEUR + CHAMPS_VISA
    champs += CHAMPS_MISSION
    return champs


def construire_form_identification(devis, data=None):
    """Construit le ModelForm d'identification complète, avec tous les champs
    obligatoires pertinents pour ce type de client (Porte d'entrée)."""
    champs = champs_formulaire(devis.type_client)
    DevisForm = modelform_factory(devis.__class__, fields=champs)

    champs_date = ["rccm_delivre_le", "activite_date_debut", "pp_date_naissance",
                   "pp_piece_delivree_le", "exoneration_debut", "exoneration_fin", "declaration_date",
                   "date_effet_mission"]
    for nom_champ in champs_date:
        if nom_champ in DevisForm.base_fields:
            DevisForm.base_fields[nom_champ].widget = django_forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")
            DevisForm.base_fields[nom_champ].input_formats = ["%Y-%m-%d"]

    form = DevisForm(data, instance=devis) if data is not None else DevisForm(instance=devis)

    for nom in CHAMPS_OBLIGATOIRES.get(devis.type_client, []):
        if nom in form.fields:
            form.fields[nom].required = True

    return form


def valider_champs_conditionnels(devis, form):
    """Obligations conditionnelles que Django ne sait pas exprimer nativement au
    niveau du champ seul (dépendent de la valeur d'un AUTRE champ du même
    formulaire) : numero_cnps et nombre_salaries deviennent obligatoires dès que
    'est_employeur' est coché. Renvoie un dict {champ: message} ; vide = OK."""
    erreurs = {}
    est_employeur = form.cleaned_data.get("est_employeur", devis.est_employeur)
    if est_employeur:
        if not form.cleaned_data.get("numero_cnps"):
            erreurs["numero_cnps"] = ("Le numéro employeur CNPS est obligatoire dès que "
                                      "« Qualité d'employeur » est coché (nécessaire pour le module Paie/RH).")
        if not form.cleaned_data.get("nombre_salaries"):
            erreurs["nombre_salaries"] = ("Le nombre de salariés est obligatoire dès que "
                                          "« Qualité d'employeur » est coché.")
    return erreurs


def enregistrer_associes(devis, request):
    """Enregistre les associés envoyés en JSON depuis le formulaire (Porte d'entrée)."""
    associes_json = request.POST.get("associes_data", "[]")
    try:
        associes = json.loads(associes_json)
    except Exception:
        associes = []
    devis.associes.all().delete()
    for a in associes:
        nom = (a.get("nom") or "").strip()
        if not nom:
            continue
        Associe.objects.create(
            devis=devis, nom=nom,
            adresse=a.get("adresse", ""), nationalite=a.get("nationalite", ""),
            part_montant=a.get("montant") or 0, part_pourcentage=a.get("pourcentage") or 0,
        )


# ===================== DOCUMENTS =====================

DOCUMENTS_REQUIS_PAR_TYPE = {
    "PM": ["RCCM", "DFE", "STATUTS", "INSPECTION_TRAVAIL", "CNPS", "PIECE_GERANT", "CONTRAT_BAIL"],
    "PP_CONSTITUEE": ["RCCM", "DFE", "INSPECTION_TRAVAIL", "CNPS", "PIECE_GERANT", "CONTRAT_BAIL"],
    "PP_INFORMEL": ["PIECE_GERANT"],
}


def documents_requis_pour(devis):
    return DOCUMENTS_REQUIS_PAR_TYPE.get(devis.type_client, [])


def initialiser_documents(devis):
    """Idempotent : crée les lignes DocumentPiece requises si elles n'existent pas encore."""
    for code in documents_requis_pour(devis):
        DocumentPiece.objects.get_or_create(devis=devis, type_document=code)
    return devis.documents.all()


def documents_a_facturer_non_traites(devis):
    """Documents marqués Absent (donc à établir par le cabinet, facturable) pour
    lesquels aucune ligne de prestation n'a encore été ajoutée au devis."""
    return devis.documents.filter(statut="ABSENT", ligne_facturable_ajoutee=False)


def documents_fournis(devis):
    """Documents Fournis avec un fichier réellement attaché — c'est cette liste
    qui doit apparaître dans la lettre de mission comme « pièces en notre
    possession » : le client la relit avant de signer, et signale lui-même
    tout document manquant ou mal coché."""
    return devis.documents.filter(statut="FOURNI").exclude(fichier="")


def erreurs_documents(devis, request):
    """Un document marqué Fourni doit obligatoirement avoir un fichier — déjà
    attaché, ou envoyé dans cette même requête. Renvoie {document_id: message},
    vide si tout est cohérent."""
    erreurs = {}
    for doc in devis.documents.all():
        statut_poste = request.POST.get(f"doc_{doc.id}_statut", doc.statut)
        a_deja_fichier = bool(doc.fichier)
        nouveau_fichier = request.FILES.get(f"doc_{doc.id}_fichier")
        if statut_poste == "FOURNI" and not a_deja_fichier and not nouveau_fichier:
            erreurs[doc.id] = "Le fichier est obligatoire pour marquer ce document comme fourni."
    return erreurs


def documents_bloquants(devis):
    """Documents manquants qui bloquent la validation de l'identification."""
    return devis.documents.filter(statut="ABSENT")


def document_requires_fourniture(devis):
    """Renvoie une fonction utilisable en template pour indiquer si un type est requis."""
    requis = set(documents_requis_pour(devis))

    def _requires(type_document):
        return type_document in requis

    return _requires
