"""Génération des contrats de travail (CDI, CDD, Stage) — gabarits à trous, sans IA.
Sources : Code du travail ivoirien (loi 2015-532), Décret n°2024-900 (période d'essai)."""
from django.template.loader import render_to_string
from weasyprint import HTML

DUREE_ESSAI = {
    "horaire": "huit (8) jours",
    "mensuel": "un (1) mois",
    "maitrise": "deux (2) mois",
    "cadre": "trois (3) mois",
}

MOTIFS_CDD_PRECIS_LIBELLES = {
    "accroissement": "un accroissement temporaire d'activité",
    "occasionnel": "l'exécution d'une tâche précise et temporaire",
    "saisonnier": "un travail à caractère saisonnier",
    "autre": "un motif particulier précisé ci-après",
}
MOTIFS_CDD_IMPRECIS_LIBELLES = {
    "remplacement": "le remplacement d'un travailleur absent, dont le contrat est suspendu, ou dans l'attente de l'entrée en service d'un travailleur recruté en contrat à durée indéterminée",
    "saison": "la durée d'une saison",
    "surcroit": "un surcroît occasionnel de travail",
    "inhabituelle": "une activité inhabituelle de l'entreprise",
}


def generer_contrat_cdd(employe, options, request=None, utilisateur_signataire=None):
    """options : dict avec niveau_essai, lieu_travail, avantages_nature, description_poste,
    clauses_particulieres, type_terme, motif_cdd, motif_cdd_precision,
    motif_cdd_imprecis, evenement_terme."""
    from datetime import timedelta
    employeur = employe.employeur
    duree_essai = DUREE_ESSAI.get(options.get("niveau_essai", "mensuel"), "un (1) mois")

    if options.get("lieu_travail"):
        lieu = options["lieu_travail"]
    else:
        parties_lieu = [p for p in [employeur.adresse, employeur.commune] if p]
        lieu = ", ".join(parties_lieu) if parties_lieu else "au siège de l'entreprise"

    est_imprecis = options.get("type_terme") == "imprecis"
    date_fin = None
    motif_libelle = None
    evenement_terme = ""

    if est_imprecis:
        motif_libelle = MOTIFS_CDD_IMPRECIS_LIBELLES.get(options.get("motif_cdd_imprecis", ""), "")
        evenement_terme = options.get("evenement_terme", "")
    else:
        motif_cdd = options.get("motif_cdd", "")
        if motif_cdd:
            motif_libelle = MOTIFS_CDD_PRECIS_LIBELLES.get(motif_cdd, "")
        if employe.date_entree and employe.duree_cdd_mois:
            mois_total = employe.date_entree.month - 1 + employe.duree_cdd_mois
            annee_fin = employe.date_entree.year + mois_total // 12
            mois_fin = mois_total % 12 + 1
            import calendar
            jour_fin = min(employe.date_entree.day, calendar.monthrange(annee_fin, mois_fin)[1])
            date_fin = employe.date_entree.replace(year=annee_fin, month=mois_fin, day=jour_fin) - timedelta(days=1)

    from comptes.signature_pdf import preparer_signature_pdf
    from .documents_utils import generer_reference_document, generer_qr_code_data_uri
    signature_data_uri, mention_signature = preparer_signature_pdf(utilisateur_signataire)
    reference = generer_reference_document("CTR")
    qr_data_uri = generer_qr_code_data_uri(f"Cabinet Smart-Hub — Contrat {reference} — {employe.nom_prenoms}")

    html_string = render_to_string("paie/contrat_cdd.html", {
        "employeur": employeur, "employe": employe,
        "duree_essai": duree_essai, "lieu_travail": lieu,
        "avantages_nature": options.get("avantages_nature", ""),
        "description_poste": options.get("description_poste", ""),
        "clauses_particulieres": options.get("clauses_particulieres", ""),
        "est_imprecis": est_imprecis,
        "motif_libelle": motif_libelle,
        "motif_precision": options.get("motif_cdd_precision", ""),
        "evenement_terme": evenement_terme,
        "date_fin": date_fin,
        "signature_data_uri": signature_data_uri,
        "mention_signature": mention_signature,
        "reference": reference,
        "qr_data_uri": qr_data_uri,
    })
    base = request.build_absolute_uri("/") if request is not None else "http://127.0.0.1:8000/"
    return HTML(string=html_string, base_url=base).write_pdf()


def generer_contrat_stage(employe, options, request=None, utilisateur_signataire=None):
    """options : dict avec type_stage, etablissement_formation, indemnite_stage, maitre_stage,
    lieu_travail, description_poste, clauses_particulieres."""
    from datetime import timedelta
    employeur = employe.employeur

    if options.get("lieu_travail"):
        lieu = options["lieu_travail"]
    else:
        parties_lieu = [p for p in [employeur.adresse, employeur.commune] if p]
        lieu = ", ".join(parties_lieu) if parties_lieu else "au siège de l'entreprise"

    est_ecole = options.get("type_stage") == "ecole"

    date_fin = None
    if employe.date_entree and employe.duree_cdd_mois:
        mois_total = employe.date_entree.month - 1 + employe.duree_cdd_mois
        annee_fin = employe.date_entree.year + mois_total // 12
        mois_fin = mois_total % 12 + 1
        import calendar
        jour_fin = min(employe.date_entree.day, calendar.monthrange(annee_fin, mois_fin)[1])
        date_fin = employe.date_entree.replace(year=annee_fin, month=mois_fin, day=jour_fin) - timedelta(days=1)

    from comptes.signature_pdf import preparer_signature_pdf
    from .documents_utils import generer_reference_document, generer_qr_code_data_uri
    signature_data_uri, mention_signature = preparer_signature_pdf(utilisateur_signataire)
    reference = generer_reference_document("STG")
    qr_data_uri = generer_qr_code_data_uri(f"Cabinet Smart-Hub — Contrat {reference} — {employe.nom_prenoms}")

    html_string = render_to_string("paie/contrat_stage.html", {
        "employeur": employeur, "employe": employe,
        "lieu_travail": lieu, "est_ecole": est_ecole,
        "etablissement_formation": options.get("etablissement_formation", ""),
        "indemnite_stage": options.get("indemnite_stage"),
        "maitre_stage": options.get("maitre_stage", ""),
        "description_poste": options.get("description_poste", ""),
        "clauses_particulieres": options.get("clauses_particulieres", ""),
        "date_fin": date_fin,
        "signature_data_uri": signature_data_uri,
        "mention_signature": mention_signature,
        "reference": reference,
        "qr_data_uri": qr_data_uri,
    })
    base = request.build_absolute_uri("/") if request is not None else "http://127.0.0.1:8000/"
    return HTML(string=html_string, base_url=base).write_pdf()


def generer_avenant_reconduction(employe, nouvelle_date_fin, motif_reconduction, request=None, utilisateur_signataire=None):
    """Avenant de reconduction pour CDD ou Stage. Calcule la durée cumulée et alerte si dépassement légal."""
    employeur = employe.employeur
    est_stage = employe.contrat == "STAGE"
    limite_mois = 12 if est_stage else 24
    limite_texte = "douze (12) mois" if est_stage else "deux (2) ans"
    article_limite = "13.14" if est_stage else "15.4"

    duree_cumulee_jours = (nouvelle_date_fin - employe.date_entree).days if employe.date_entree else 0
    duree_cumulee_mois = round(duree_cumulee_jours / 30.44, 1)
    depassement = duree_cumulee_mois > limite_mois

    from comptes.signature_pdf import preparer_signature_pdf
    from .documents_utils import generer_reference_document, generer_qr_code_data_uri
    signature_data_uri, mention_signature = preparer_signature_pdf(utilisateur_signataire)
    reference = generer_reference_document("AVN")
    qr_data_uri = generer_qr_code_data_uri(f"Cabinet Smart-Hub — Avenant {reference} — {employe.nom_prenoms}")

    html_string = render_to_string("paie/avenant_reconduction.html", {
        "employeur": employeur, "employe": employe,
        "est_stage": est_stage, "limite_texte": limite_texte, "article_limite": article_limite,
        "ancienne_date_fin": employe.date_sortie,
        "nouvelle_date_fin": nouvelle_date_fin,
        "motif_reconduction": motif_reconduction,
        "duree_cumulee_mois": duree_cumulee_mois,
        "depassement": depassement,
        "signature_data_uri": signature_data_uri,
        "mention_signature": mention_signature,
        "reference": reference,
        "qr_data_uri": qr_data_uri,
    })
    base = request.build_absolute_uri("/") if request is not None else "http://127.0.0.1:8000/"
    return HTML(string=html_string, base_url=base).write_pdf(), depassement


def generer_contrat_cdi(employe, options, request=None, utilisateur_signataire=None):
    """options : dict avec niveau_essai, lieu_travail, avantages_nature, description_poste, clauses_particulieres."""
    employeur = employe.employeur
    duree_essai = DUREE_ESSAI.get(options.get("niveau_essai", "mensuel"), "un (1) mois")
    if options.get("lieu_travail"):
        lieu = options["lieu_travail"]
    else:
        parties_lieu = [p for p in [employeur.adresse, employeur.commune] if p]
        lieu = ", ".join(parties_lieu) if parties_lieu else "au siège de l'entreprise"

    from comptes.signature_pdf import preparer_signature_pdf
    from .documents_utils import generer_reference_document, generer_qr_code_data_uri
    signature_data_uri, mention_signature = preparer_signature_pdf(utilisateur_signataire)
    reference = generer_reference_document("CDI")
    qr_data_uri = generer_qr_code_data_uri(f"Cabinet Smart-Hub — Contrat {reference} — {employe.nom_prenoms}")

    html_string = render_to_string("paie/contrat_cdi.html", {
        "employeur": employeur, "employe": employe,
        "duree_essai": duree_essai, "lieu_travail": lieu,
        "avantages_nature": options.get("avantages_nature", ""),
        "description_poste": options.get("description_poste", ""),
        "clauses_particulieres": options.get("clauses_particulieres", ""),
        "signature_data_uri": signature_data_uri,
        "mention_signature": mention_signature,
        "reference": reference,
        "qr_data_uri": qr_data_uri,
    })
    base = request.build_absolute_uri("/") if request is not None else "http://127.0.0.1:8000/"
    return HTML(string=html_string, base_url=base).write_pdf()
