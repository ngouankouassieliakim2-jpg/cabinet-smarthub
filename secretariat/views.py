from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from comptes.decorators import role_requis
from comptes.models import Profil

from django.contrib.auth.models import User
from comptes.models import Profil
from comptes.utils import user_can_access_client
import secrets
import string

from rendezvous.models import DemandeRendezVous
from pilotage.modules_data import MODULES, charger_sous_modules

from .forms import AppelForm
from .models import AppelTelephonique

from clients.models import Client
from devis.models import Devis
from devis.porte_entree import (
    construire_form_identification, valider_champs_conditionnels,
    initialiser_documents, documents_a_facturer_non_traites, erreurs_documents,
    documents_bloquants, document_requires_fourniture,
    enregistrer_associes,
)


def _contexte_secretariat():
    """Prépare les variables nécessaires à la barre + sidebar de l'interface Direction,
    pour le module Secrétariat. Réutilisé par toutes les vues du module."""
    # La barre horizontale du haut (mêmes modules que pilotage)
    modules_nav = [{"cle": "dashboard", "nom": "Tableau de bord", "icone": "🏠", "url": "/pilotage/"}]
    for cle, data in MODULES.items():
        modules_nav.append({
            "cle": cle, "nom": data["nom"], "icone": data["icone"],
            "url": f"/pilotage/module/{cle}/",
        })

    data = MODULES.get("secretariat", {})
    return {
        "modules_nav": modules_nav,
        "module_actif": "secretariat",
        "sous_modules": charger_sous_modules("secretariat"),
        "module_nom": data.get("nom", "Secrétariat"),
        "module_icone": data.get("icone", "📅"),
    }


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE)
def agenda(request):
    return render(request, "secretariat/agenda.html", _contexte_secretariat())


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE)
def demandes(request):
    liste = DemandeRendezVous.objects.all()

    # Le compteur de nouvelles se calcule sur le TOTAL (avant filtrage),
    # pour qu'il reste juste même quand on filtre.
    nb_nouvelles = liste.filter(statut=DemandeRendezVous.Statut.NOUVELLE).count()

    # --- Lecture des critères de filtre depuis l'URL ---
    filtre_statut = request.GET.get("statut", "")
    filtre_lieu = request.GET.get("lieu", "")
    recherche = request.GET.get("q", "").strip()

    # --- Application des filtres ---
    if filtre_statut in [DemandeRendezVous.Statut.NOUVELLE, DemandeRendezVous.Statut.TRAITEE]:
        liste = liste.filter(statut=filtre_statut)

    if filtre_lieu in [DemandeRendezVous.Lieu.DALOA, DemandeRendezVous.Lieu.BASSAM]:
        liste = liste.filter(lieu=filtre_lieu)

    if recherche:
        # On cherche dans le nom OU le téléphone
        from django.db.models import Q
        liste = liste.filter(Q(nom__icontains=recherche) | Q(telephone__icontains=recherche))

    contexte = _contexte_secretariat()
    contexte.update({
        "demandes": liste,
        "nb_nouvelles": nb_nouvelles,
        # On renvoie les critères choisis pour les réafficher dans le formulaire
        "filtre_statut": filtre_statut,
        "filtre_lieu": filtre_lieu,
        "recherche": recherche,
    })
    return render(request, "secretariat/demandes.html", contexte)


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE)
def demande_detail(request, demande_id):
    demande = get_object_or_404(DemandeRendezVous, id=demande_id)

    if request.method == "POST":
        nouveau_statut = request.POST.get("statut")
        if nouveau_statut in [DemandeRendezVous.Statut.NOUVELLE, DemandeRendezVous.Statut.TRAITEE]:
            demande.statut = nouveau_statut
            demande.save()
        return redirect("secretariat_demande_detail", demande_id=demande.id)

    contexte = _contexte_secretariat()
    contexte.update({"demande": demande})
    return render(request, "secretariat/demande_detail.html", contexte)


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE)
def accueil(request):
    return render(request, "secretariat/accueil.html", _contexte_secretariat())


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE)
def courrier(request):
    return render(request, "secretariat/courrier.html", _contexte_secretariat())
@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE)
def appels(request):
    """Registre des appels téléphoniques : liste + saisie d'un nouvel appel."""
    # Saisie d'un nouvel appel (POST)
    if request.method == "POST":
        form = AppelForm(request.POST)
        if form.is_valid():
            appel = form.save(commit=False)
            appel.recu_par = request.user  # rempli automatiquement
            appel.save()
            return redirect("secretariat_appels")
    else:
        form = AppelForm()

    liste = AppelTelephonique.objects.all()  # triés par date (récents d'abord)
    nb_a_traiter = liste.filter(statut=AppelTelephonique.Statut.A_TRAITER).count()

    contexte = _contexte_secretariat()
    contexte.update({
        "form": form,
        "appels": liste,
        "nb_a_traiter": nb_a_traiter,
    })
    return render(request, "secretariat/appels.html", contexte)


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE)
def appel_statut(request, appel_id):
    """Bascule le statut d'un appel (à traiter ↔ traité)."""
    appel = get_object_or_404(AppelTelephonique, id=appel_id)
    if request.method == "POST":
        if appel.statut == AppelTelephonique.Statut.A_TRAITER:
            appel.statut = AppelTelephonique.Statut.TRAITE
        else:
            appel.statut = AppelTelephonique.Statut.A_TRAITER
        appel.save()
    return redirect("secretariat_appels")
@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE)
def dossiers(request):
    """Création des dossiers clients : liste des devis à intégrer + dossiers en préparation."""
    # Les devis envoyés qui n'ont PAS encore de dossier client créé
    devis_envoyes = Devis.objects.filter(statut="ENVOYE").exclude(
        id__in=Client.objects.values_list("devis_origine_id", flat=True)
    )
    # Les dossiers déjà en préparation
    dossiers_en_cours = Client.objects.filter(statut="EN_PREPARATION")

    contexte = _contexte_secretariat()
    contexte.update({
        "devis_envoyes": devis_envoyes,
        "dossiers_en_cours": dossiers_en_cours,
    })
    return render(request, "secretariat/dossiers.html", contexte)


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE)
def porte_entree(request):
    devis_envoyes = Devis.objects.filter(statut="ENVOYE").order_by("date_envoi")
    contexte = _contexte_secretariat()
    contexte.update({"devis_envoyes": devis_envoyes})
    return render(request, "secretariat/porte_entree.html", contexte)


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE)
def porte_entree_detail(request, devis_id):
    devis = get_object_or_404(Devis, id=devis_id)
    client = Client.objects.filter(devis_origine=devis).first()
    if client is not None:
        user_can_access_client(request.user, client)

    initialiser_documents(devis)
    document_errors = {}

    if request.method == "POST":
        form = construire_form_identification(devis, data=request.POST)
        if form.is_valid():
            erreurs_conditionnelles = valider_champs_conditionnels(devis, form)
            document_errors = erreurs_documents(devis, request)
            if erreurs_conditionnelles or document_errors:
                for champ, erreur in erreurs_conditionnelles.items():
                    form.add_error(champ, erreur)
                if document_errors:
                    form.add_error(None, "Certains documents marqués « Fourni » n'ont pas de fichier joint.")
            else:
                devis = form.save()
                enregistrer_associes(devis, request)
                for document in devis.documents.all():
                    statut = request.POST.get(f"doc_{document.id}_statut", document.statut)
                    commentaire = request.POST.get(f"doc_{document.id}_commentaire", document.commentaire)
                    fichier = request.FILES.get(f"doc_{document.id}_fichier")
                    if statut != document.statut or commentaire != document.commentaire or fichier:
                        document.statut = statut
                        document.commentaire = commentaire
                        if fichier:
                            document.fichier = fichier
                        document.save()
                return redirect("secretariat_porte_entree_detail", devis_id=devis.id)
    else:
        form = construire_form_identification(devis)

    documents = devis.documents.all().order_by("type_document")
    contexte = _contexte_secretariat()
    contexte.update({
        "devis": devis,
        "client": client,
        "form": form,
        "documents": documents,
        "documents_bloquants": documents_bloquants(devis),
        "documents_a_facturer_non_traites": documents_a_facturer_non_traites(devis),
        "document_requires_fourniture": document_requires_fourniture(devis),
        "document_errors": document_errors,
    })
    return render(request, "secretariat/porte_entree_detail.html", contexte)


def activer_client(client, email_acces=None):
    """Crée le compte client, génère un mot de passe temporaire et renvoie le résultat."""
    if client.compte is not None:
        return False, "Ce client a déjà un compte actif."

    email_acces = (email_acces or client.email or "").strip()
    if not email_acces:
        return False, "Aucune adresse email valide n'a été trouvée."

    alphabet = string.ascii_letters + string.digits
    mot_de_passe = "".join(secrets.choice(alphabet) for _ in range(10))

    user = User.objects.create_user(username=email_acces, email=email_acces, password=mot_de_passe)
    Profil.objects.create(user=user, role=Profil.Role.CLIENT)

    client.compte = user
    client.email_acces = email_acces
    client.statut = "EN_ATTENTE"
    client.save()

    email_envoye, erreur_email = False, ""
    try:
        from parametres.emails import envoyer_email
        sujet = "Vos accès au portail Cabinet K&L"
        corps = (
            f"Bonjour {client.nom},\n\n"
            f"Votre compte client a été créé sur le portail du Cabinet Comptable & Fiscal K&L.\n\n"
            f"Voici vos identifiants de connexion :\n"
            f"  • Email : {email_acces}\n"
            f"  • Mot de passe provisoire : {mot_de_passe}\n\n"
            f"À votre première connexion, il vous sera demandé de changer ce mot de passe, "
            f"de confirmer la lettre de mission et d'accepter les conditions d'utilisation.\n\n"
            f"Cordialement,\n"
            f"Cabinet Comptable & Fiscal K&L\n"
            f"Tél : 27 32 70 44 04\n"
            f"cabinetkl120@gmail.com"
        )
        email_envoye, erreur_email = envoyer_email([email_acces], sujet, corps, [])
    except Exception as e:
        erreur_email = str(e)

    return True, {
        "email": email_acces,
        "mot_de_passe": mot_de_passe,
        "email_envoye": email_envoye,
        "erreur_email": erreur_email,
    }


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE)
def porte_entree_soumettre(request, devis_id):
    """Soumet le devis à la Direction pour validation de la lettre de mission."""
    devis = get_object_or_404(Devis, id=devis_id)
    client = Client.objects.filter(devis_origine=devis).first()
    if client is not None:
        user_can_access_client(request.user, client)

    if request.method != "POST":
        return redirect("secretariat_porte_entree_detail", devis_id=devis.id)

    # Marquer le devis comme prêt à validation par Direction
    devis.lettre_statut = "EN_VALIDATION_DIRECTION"
    devis.lettre_soumise_le = timezone.now()
    devis.lettre_soumise_par = request.user
    devis.save(update_fields=["lettre_statut", "lettre_soumise_le", "lettre_soumise_par"])

    return redirect("secretariat_porte_entree_detail", devis_id=devis.id)


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE)
def dossier_config(request, devis_id):
    """Configuration d'un dossier client : édition directe du devis + infos du dossier client."""
    devis = get_object_or_404(Devis, id=devis_id)
    client = Client.objects.filter(devis_origine=devis).first()

    if request.method == "POST":
        # --- 1. Mise à jour des infos du DEVIS (correction directe) ---
        devis.pm_raison_sociale = request.POST.get("pm_raison_sociale", "").strip()
        devis.pm_nom_commercial = request.POST.get("pm_nom_commercial", "").strip()
        devis.pm_forme_juridique = request.POST.get("pm_forme_juridique", "").strip()
        devis.pp_nom_prenoms = request.POST.get("pp_nom_prenoms", "").strip()
        devis.ncc = request.POST.get("ncc", "").strip()
        devis.rccm_numero = request.POST.get("rccm_numero", "").strip()
        devis.code_activite = request.POST.get("code_activite", "").strip()
        devis.telephone = request.POST.get("telephone", "").strip()
        devis.telephone2 = request.POST.get("telephone2", "").strip()
        devis.email = request.POST.get("email", "").strip()
        devis.siege_ville = request.POST.get("siege_ville", "").strip()
        devis.siege_commune = request.POST.get("siege_commune", "").strip()
        devis.siege_quartier = request.POST.get("siege_quartier", "").strip()
        devis.siege_rue = request.POST.get("siege_rue", "").strip()
        devis.activite_principale = request.POST.get("activite_principale", "").strip()
        devis.dirigeant_nom = request.POST.get("dirigeant_nom", "").strip()
        devis.dirigeant_qualite = request.POST.get("dirigeant_qualite", "").strip()
        devis.dirigeant_tel = request.POST.get("dirigeant_tel", "").strip()
        devis.dirigeant_email = request.POST.get("dirigeant_email", "").strip()
        devis.type_client = request.POST.get("type_client", "")
        devis.save()

        # --- 2. Création / mise à jour du DOSSIER CLIENT ---
        if client is None:
            client = Client(devis_origine=devis)
        # On reprend les infos depuis le devis (qu'on vient de corriger)
        client.remplir_depuis_devis()
        # Champs propres au dossier client
        client.slogan = request.POST.get("slogan", "").strip()
        client.user_principal_nom = request.POST.get("user_principal_nom", "").strip()
        client.user_principal_piece_nature = request.POST.get("user_principal_piece_nature", "").strip()
        client.user_principal_piece_numero = request.POST.get("user_principal_piece_numero", "").strip()
        client.user_principal_qualite = request.POST.get("user_principal_qualite", "").strip()
        client.gestionnaire = request.POST.get("gestionnaire", "").strip()
        client.observations = request.POST.get("observations", "").strip()
        client.notes = request.POST.get("notes", "").strip()
        if request.FILES.get("logo_entreprise"):
            client.logo_entreprise = request.FILES["logo_entreprise"]
        client.statut = "EN_PREPARATION"
        client.save()

        return redirect("secretariat_dossiers")

    contexte = _contexte_secretariat()
    contexte.update({"devis": devis, "client": client})
    return render(request, "secretariat/dossier_config.html", contexte)

@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE)
def dossier_activer(request, client_id):
    """Active un dossier client : crée le compte client et envoie les identifiants."""
    client = get_object_or_404(Client, id=client_id)
    deja_active = client.compte is not None
    identifiants = None

    if request.method == "POST" and not deja_active:
        email_acces = request.POST.get("email_acces", "").strip()
        if request.FILES.get("lettre_mission"):
            client.lettre_mission = request.FILES["lettre_mission"]
            client.save(update_fields=["lettre_mission"])
        else:
            devis = client.devis_origine
            if not devis.lettre_mission_pdf:
                from devis.utils import generer_lettre_mission
                generer_lettre_mission(devis)
            if devis.lettre_mission_pdf and not client.lettre_mission:
                client.lettre_mission = devis.lettre_mission_pdf
                client.save(update_fields=["lettre_mission"])

        succes, resultat = activer_client(client, email_acces)
        if succes:
            devis = client.devis_origine
            devis.statut = "VALIDE"
            if devis.lettre_statut == "VALIDEE_DIRECTION":
                devis.lettre_statut = "ENVOYEE_CLIENT"
                devis.save(update_fields=["statut", "lettre_statut"])
            else:
                devis.save(update_fields=["statut"])
            identifiants = resultat

    contexte = _contexte_secretariat()
    contexte.update({
        "client": client,
        "deja_active": deja_active,
        "identifiants": identifiants,
    })
    return render(request, "secretariat/dossier_activer.html", contexte)