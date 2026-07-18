from django.urls import path
from . import views

urlpatterns = [
    path("", views.liste_employeurs, name="liste_employeurs"),

    # Grille des salaires
    path("grille/", views.grille_salaires, name="paie_grille"),
    path("grille/categorie/ajouter/", views.categorie_ajouter, name="paie_categorie_ajouter"),
    path("grille/categorie/<int:categorie_id>/modifier/", views.categorie_modifier, name="paie_categorie_modifier"),
    path("grille/categorie/<int:categorie_id>/supprimer/", views.categorie_supprimer, name="paie_categorie_supprimer"),
    path("grille/secteur/ajouter/", views.secteur_ajouter, name="paie_secteur_ajouter"),
    path("grille/secteur/<int:secteur_id>/modifier/", views.secteur_modifier, name="paie_secteur_modifier"),

    path("emplois/", views.emplois_liste, name="paie_emplois"),
    path("jours-feries/", views.jours_feries_liste, name="paie_jours_feries"),
    path("jours-feries/<int:ferie_id>/supprimer/", views.jour_ferie_supprimer, name="paie_jour_ferie_supprimer"),
    path("livre-calcul/", views.livre_calcul, name="paie_livre_calcul"),
    path("guide/", views.guide_utilisation, name="paie_guide"),
    path("emplois/ajouter/", views.emploi_ajouter, name="paie_emploi_ajouter"),
    path("emplois/<int:emploi_id>/modifier/", views.emploi_modifier, name="paie_emploi_modifier"),
    path("employeur/<int:employeur_id>/employes/<int:employe_id>/transformer-cdi/", views.employe_transformer_cdi, name="paie_employe_transformer_cdi"),
    path("employeur/<int:employeur_id>/employes/<int:employe_id>/reembaucher/", views.employe_reembaucher, name="paie_employe_reembaucher"),
    path("emplois/<int:emploi_id>/supprimer/", views.emploi_supprimer, name="paie_emploi_supprimer"),

    # Personnel
    path("employeur/<int:employeur_id>/employes/", views.employes_liste, name="paie_employes_liste"),
    path("employeur/<int:employeur_id>/employes/nouveau/", views.employe_creer, name="paie_employe_creer"),
    path("employeur/<int:employeur_id>/employes/<int:employe_id>/modifier/", views.employe_modifier, name="paie_employe_modifier"),
    path("employeur/<int:employeur_id>/journal/", views.journal_personnel, name="paie_journal_personnel"),
    path("employeur/<int:employeur_id>/indicateurs/", views.indicateurs_rh, name="paie_indicateurs_rh"),
    path("actions-rh/<int:employeur_id>/", views.actions_rh_liste, name="paie_actions_rh_liste"),
    path("actions-rh/<int:employeur_id>/salarie/<int:employe_id>/", views.actions_rh_salarie, name="paie_actions_rh_salarie"),
    path("actions-rh/<int:employeur_id>/salarie/<int:employe_id>/historique/", views.bulletin_historique_creer, name="paie_bulletin_historique_creer"),
    path("actions-rh/<int:employeur_id>/salarie/<int:employe_id>/absences/", views.absences_employe, name="paie_absences_employe"),
    path("actions-rh/<int:employeur_id>/salarie/<int:employe_id>/contrat/", views.contrat_generer, name="paie_contrat_generer"),
    path("actions-rh/<int:employeur_id>/salarie/<int:employe_id>/recap/", views.recap_annuel_pdf, name="paie_recap_annuel"),
    path("actions-rh/<int:employeur_id>/salarie/<int:employe_id>/avenant/", views.avenant_generer, name="paie_avenant_generer"),
    path("actions-rh/<int:employeur_id>/salarie/<int:employe_id>/conge/", views.conge_poser, name="paie_conge_poser"),
    path("actions-rh/<int:employeur_id>/salarie/<int:employe_id>/conge-exceptionnel/", views.conge_exceptionnel_poser, name="paie_conge_exceptionnel"),
    path("imports/", views.import_document, name="paie_import_document"),
    path("imports/salaries/<int:employeur_id>/", views.import_salaries_employeur, name="paie_import_salaries"),

    # Rubriques (par employeur)
    path("employeur/<int:employeur_id>/rubriques/", views.rubriques_liste, name="paie_rubriques_liste"),
    path("employeur/<int:employeur_id>/rubriques/nouvelle/", views.rubrique_creer, name="paie_rubrique_creer"),
    path("employeur/<int:employeur_id>/rubriques/<int:rubrique_id>/modifier/", views.rubrique_modifier, name="paie_rubrique_modifier"),
    path("employeur/<int:employeur_id>/rubriques/<int:rubrique_id>/supprimer/", views.rubrique_supprimer, name="paie_rubrique_supprimer"),

    # Traitement
    path("<int:employeur_id>/traitement/", views.traitement_paie, name="traitement_paie"),
    path("<int:employeur_id>/traitement/calcul/", views.traitement_calcul, name="paie_traitement_calcul"),
    path("<int:employeur_id>/bulletin/<int:employe_id>/", views.bulletin_pdf, name="paie_bulletin_pdf"),
    path("<int:employeur_id>/generation-auto/", views.reglage_generation, name="paie_reglage_generation"),
    path("<int:employeur_id>/heures-sup/", views.heures_sup, name="paie_heures_sup"),
    path("<int:employeur_id>/livre-annuel/", views.livre_annuel_pdf, name="paie_livre_annuel"),
    path("<int:employeur_id>/edi-its/", views.declaration_edi_its, name="paie_edi_its"),
    path("<int:employeur_id>/edi-annuel/", views.declaration_edi_annuel, name="paie_edi_annuel"),
    path("<int:employeur_id>/declarations-annuelles/", views.declarations_annuelles, name="paie_declarations_annuelles"),
    path("<int:employeur_id>/cnps-nominative/", views.declaration_cnps, name="paie_cnps_nominative"),
    path("<int:employeur_id>/disa/", views.declaration_disa, name="paie_disa"),
    path("<int:employeur_id>/dasc/", views.saisie_dasc, name="paie_saisie_dasc"),
    path("<int:employeur_id>/reglements-cnps/", views.reglements_cnps, name="paie_reglements_cnps"),
    path("employeur/<int:employeur_id>/employes/<int:employe_id>/prets/", views.prets_employe, name="paie_prets_employe"),
    path("employeur/<int:employeur_id>/employes/<int:employe_id>/prets/<int:pret_id>/justificatif/", views.justificatif_pret_pdf, name="paie_justificatif_pret"),
    path("employeur/<int:employeur_id>/employes/<int:employe_id>/attestations/", views.attestations_employe, name="paie_attestations_employe"),
    path("employeur/<int:employeur_id>/employes/<int:employe_id>/attestation/<str:type_doc>/", views.attestation_pdf, name="paie_attestation_pdf"),
    
    # Navigation & Documents
    path("choisir/<str:section>/", views.choisir_entreprise, name="paie_choisir_entreprise"),
    path("employeur/<int:employeur_id>/documents/", views.documents_periodes, name="paie_documents_periodes"),
    path("employeur/<int:employeur_id>/documents/<int:annee>/<int:mois>/", views.documents_mois, name="paie_documents_mois"),
    path("employeur/nouveau/", views.employeur_nouveau, name="paie_employeur_nouveau"),
    path("employeur/<int:employeur_id>/modifier/", views.employeur_modifier, name="paie_employeur_modifier"),
    path("<int:employeur_id>/bulletins-groupes/", views.bulletins_groupes_pdf, name="paie_bulletins_groupes"),
    path("<int:employeur_id>/ordre-virement/", views.ordre_virement_pdf, name="paie_ordre_virement"),
    path("<int:employeur_id>/livre-mensuel/", views.livre_mensuel_pdf, name="paie_livre_mensuel"),
    path("employeur/<int:employeur_id>/employes/<int:employe_id>/fin-contrat/", views.fin_contrat, name="paie_fin_contrat"),

    path("archives/", views.archives_entreprises, name="paie_archives"),
    path("archives/<int:employeur_id>/", views.archives_entreprise, name="paie_archives_entreprise"),
    path("archives/document/<int:document_id>/", views.archive_telecharger, name="paie_archive_telecharger"),
]