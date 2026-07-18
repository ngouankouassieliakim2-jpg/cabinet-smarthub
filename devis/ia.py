import json
import time
from django.conf import settings
from google import genai


def _appeler_gemini(instructions):
    """Appelle Gemini avec ré-essais et modèle de secours. Retourne le texte brut nettoyé, ou lève une exception."""
    client_gemini = genai.Client(api_key=settings.GEMINI_API_KEY)

    # Modèles essayés dans l'ordre : principal, puis secours
    modeles = ["gemini-2.5-flash", "gemini-2.0-flash"]

    derniere_erreur = ""
    for modele in modeles:
        # 5 tentatives par modèle, attente croissante (2s, 4s, 6s, 8s, 10s)
        for tentative in range(5):
            try:
                reponse = client_gemini.models.generate_content(
                    model=modele,
                    contents=instructions,
                )
                texte = reponse.text.strip()
                # Nettoyer d'éventuelles balises markdown ```json ... ```
                if texte.startswith("```"):
                    texte = texte.split("```")[1]
                    if texte.startswith("json"):
                        texte = texte[4:]
                    texte = texte.strip()
                return texte
            except Exception as e:
                derniere_erreur = str(e)
                surcharge = ("503" in derniere_erreur
                             or "UNAVAILABLE" in derniere_erreur
                             or "overloaded" in derniere_erreur.lower())
                if surcharge:
                    time.sleep(2 * (tentative + 1))  # 2s, 4s, 6s, 8s, 10s
                    continue
                else:
                    break  # erreur autre que surcharge : on passe au modèle suivant
        # échec du modèle courant → on tente le modèle de secours

    raise Exception(f"Gemini indisponible après ré-essais et secours : {derniere_erreur}")


def generer_note_explicative(devis):
    """Demande à Gemini une note structurée en blocs (JSON) et la retourne en dict Python."""

    # Construction de la liste des prestations
    lignes_list = []
    for ligne in devis.lignes.all():
        periodicite = ligne.periodicite or "ponctuel"
        lignes_list.append(
            f"- {ligne.designation} ({periodicite}) : quantité {ligne.quantite}, "
            f"prix unitaire {ligne.prix_unitaire} FCFA, total {ligne.total_ht} FCFA"
        )
    lignes_txt = "\n".join(lignes_list)

    if devis.type_client == "PM":
        client = devis.pm_raison_sociale or "le client"
    else:
        client = devis.pp_nom_prenoms or "le client"

    # ===================== LE PROMPT (adapté au type de client) =====================
    if devis.type_client == "PP_INFORMEL":
        consignes_ton = """CONSIGNES DE TON (TRES IMPORTANT) :
- Le client est un PARTICULIER ou un petit acteur du secteur informel. Il ne connait RIEN a la comptabilite, a la fiscalite ni a la gestion d'entreprise.
- Ecris comme si tu parlais a un ami qui decouvre tout : phrases TRES COURTES, mots SIMPLES du quotidien, AUCUN terme technique.
- Si tu dois mentionner une notion (taxe, declaration...), explique-la immediatement avec une image simple ou un exemple concret.
- Sois chaleureux, rassurant et encourageant. Le but : que la personne se sente en confiance et comprenne EXACTEMENT ce qu'elle paie et pourquoi.
- Explique concretement ce que le cabinet va FAIRE pour elle, et en quoi ca l'aide.
- Bannis absolument le jargon (pas de SYSCOHADA, regime d'imposition, exercice comptable, etc.). Utilise des mots que tout le monde comprend.
- Garde des blocs courts (1 a 3 phrases simples chacun)."""
    else:
        consignes_ton = """CONSIGNES DE TON :
- Adopte un ton professionnel, courtois et clair, adapte a un client en Cote d'Ivoire.
- Explique EN LANGAGE SIMPLE chaque type de prestation et son utilite (vulgarise les termes comptables/fiscaux).
- Adapte le NOMBRE de blocs a la complexite du devis : un devis simple = peu de blocs, un devis riche = plus de blocs. Regroupe les prestations par theme."""

    instructions = f"""Tu es un assistant redactionnel pour un cabinet comptable et fiscal ivoirien (Cabinet K&L).
Ta tache : rediger une NOTE EXPLICATIVE qui accompagne un devis, destinee au client.

CONTEXTE DU DEVIS :
- Numero : {devis.numero_devis}
- Client : {client}
- Objet de la mission : {devis.type_mission or "Prestation"}
- Prestations :
{lignes_txt}
- Total HT brut : {devis.total_ht_brut} FCFA
- Remise : {devis.remise_pourcentage}%
- Total TTC : {devis.total_ttc} FCFA

{consignes_ton}

CONSIGNES COMMUNES :
- Prevois toujours un bloc final sur le prix et le reglement, en precisant simplement que ce montant couvre uniquement le travail du cabinet (les sommes eventuelles a payer a l'Etat ou a l'administration ne sont pas comprises).
- Si une remise est appliquee (remise superieure a 0), mentionne-la comme un geste commercial.
- N'invente AUCUN chiffre : utilise uniquement les montants fournis.

FORMAT DE REPONSE OBLIGATOIRE :
Reponds UNIQUEMENT avec un objet JSON valide, sans texte avant ni apres, sans balises markdown.
Structure exacte :
{{
  "intro": "Phrase d'introduction apres 'Madame, Monsieur,' (1 a 2 phrases).",
  "blocs": [
    {{"titre": "Titre court du bloc", "contenu": "Texte explicatif du bloc."}},
    {{"titre": "Autre titre", "contenu": "..."}}
  ],
  "conclusion": "Phrase de disponibilite et de remerciement pour conclure."
}}"""

    try:
        texte = _appeler_gemini(instructions)
        return json.loads(texte)
    except Exception:
        return {
            "intro": "",
            "blocs": [],
            "conclusion": "",
        }


def analyser_dossier(devis):
    """Confronte les données du dossier au devis et renvoie une analyse structurée (JSON)."""

    # Prestations du devis
    lignes_list = []
    for ligne in devis.lignes.all():
        lignes_list.append(f"- {ligne.designation} ({ligne.periodicite or 'ponctuel'}) : {ligne.total_ht} FCFA")
    lignes_txt = "\n".join(lignes_list) if lignes_list else "(aucune prestation)"

    # Obligations fiscales cochées
    obligations = []
    mapping_obl = {
        "obl_patente": "Patente", "obl_bic_ba": "BIC/BA", "obl_bnc": "BNC",
        "obl_tva": "TVA", "obl_tob": "TOB", "obl_its": "ITS", "obl_airsi": "AIRSI",
        "obl_tse": "TSE", "obl_impots_fonciers": "Impôts fonciers",
        "obl_impot_micro": "Impôt microentreprises/TEE", "obl_igr": "IGR",
    }
    for champ, nom in mapping_obl.items():
        if getattr(devis, champ, False):
            obligations.append(nom)
    obligations_txt = ", ".join(obligations) if obligations else "(aucune cochée)"

    # Présence des documents
    docs = []
    mapping_docs = {
        "doc_rccm": "RCCM", "doc_dfe": "DFE", "doc_cnps": "Attestation CNPS",
        "doc_piece_identite": "Pièce d'identité", "doc_statuts": "Statuts",
    }
    for champ, nom in mapping_docs.items():
        present = bool(getattr(devis, champ, None))
        docs.append(f"{nom} : {'fourni' if present else 'MANQUANT'}")
    docs_txt = "\n".join(docs)

    if devis.type_client == "PM":
        client = devis.pm_raison_sociale or "le client"
    else:
        client = devis.pp_nom_prenoms or "le client"

    instructions = f"""Tu es un expert-comptable et fiscaliste ivoirien chargé d'un CONTRÔLE QUALITÉ d'un dossier client avant l'envoi d'un devis.
Analyse la cohérence entre le PROFIL du client et les PRESTATIONS du devis, et repère les manques, incohérences et points de vigilance.

PROFIL DU CLIENT :
- Type : {devis.get_type_client_display()}
- Client : {client}
- Régime d'imposition : {devis.get_regime_imposition_display() or "non renseigné"}
- Qualité d'employeur : {"OUI" if devis.est_employeur else "NON"}
- Activité principale : {devis.activite_principale or "non renseignée"}
- Obligations fiscales déclarées : {obligations_txt}

PRESTATIONS DU DEVIS :
{lignes_txt}
- Total TTC : {devis.total_ttc} FCFA

DOCUMENTS DU DOSSIER :
{docs_txt}

CONSIGNES D'ANALYSE (TRÈS IMPORTANTES) :
Le devis reflète CE QUE LE CLIENT A DEMANDÉ. Ton rôle n'est PAS de proposer d'ajouter des prestations que le client n'a pas sollicitées.

RÈGLE D'OR : Si une prestation n'est PAS dans le devis, cela signifie que le client ne l'a pas demandée → NE PAS la signaler comme un manque, NE PAS suggérer de l'ajouter.

Tu dois UNIQUEMENT signaler :
1. Les INCOHÉRENCES RÉELLES ET GRAVES, c'est-à-dire les cas où une obligation légale fondamentale est manifestement absente alors qu'elle est INDISPENSABLE au vu du profil. Exemple type : la TENUE DE COMPTABILITÉ RÉGULIÈRE — si le client est au RNI ou RSI (qui imposent une comptabilité complète) et qu'AUCUNE prestation de tenue/établissement de comptabilité n'est au devis, c'est une incohérence à signaler (le reste de la mission s'appuie dessus).
2. Les éléments du DEVIS lui-même qui posent problème : une prestation ponctuelle sans délai, un montant manifestement incohérent, une ligne ambiguë.
3. Les DOCUMENTS réellement manquants ET nécessaires au vu du profil (ex : employeur sans attestation CNPS).

Tu ne dois PAS :
- Suggérer d'ajouter des prestations « pertinentes » ou « habituelles » que le client n'a pas demandées.
- Lister comme « manque » une obligation fiscale cochée mais non facturée, SAUF si c'est la comptabilité régulière indispensable (voir point 1).
- Faire du remplissage : si tout est cohérent, dis-le simplement.

Reste factuel, sobre, et collé au devis réel. Mieux vaut peu de remarques pertinentes que beaucoup de suggestions inutiles. N'invente jamais de données.

FORMAT DE RÉPONSE OBLIGATOIRE (JSON valide uniquement, sans texte ni balises markdown) :
{{
  "synthese": "1 à 2 phrases : le devis est-il cohérent avec le profil, ou y a-t-il un vrai point d'attention ?",
  "incoherences": ["incohérence réelle et grave détectée (ex : comptabilité régulière absente alors que RNI)", "..."],
  "points_devis": ["point d'attention sur le devis lui-même (délai manquant, etc.)", "..."],
  "documents": ["document réellement manquant et nécessaire", "..."],
  "niveau_risque": "FAIBLE | MOYEN | ÉLEVÉ"
}}
Si une liste est vide, mets-la à []. Le niveau de risque est ÉLEVÉ uniquement si une obligation fondamentale (comptabilité) manque ; MOYEN pour un point d'attention secondaire ; FAIBLE si le devis est cohérent."""

    try:
        texte = _appeler_gemini(instructions)
        return json.loads(texte)
    except Exception:
        return {
            "synthese": "Analyse momentanément indisponible (service surchargé). Réessayez dans quelques instants.",
            "incoherences": [], "points_devis": [], "documents": [],
            "niveau_risque": "—",
        }