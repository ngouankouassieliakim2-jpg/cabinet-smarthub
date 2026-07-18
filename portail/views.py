from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from django.contrib.auth import update_session_auth_hash
from django.shortcuts import redirect
from clients.models import Client


def get_portail_module_actif():
    return {
        "cle": "portail",
        "nom": "Portail client",
        "icone": "🧾",
        "description": "Suivi sécurisé de vos dossiers et échanges avec le cabinet.",
    }


@login_required
def accueil(request):
    """Accueil du Portail Client (coquille niveau 3)."""
    return render(request, "portail/accueil.html", {
        "module_actif": get_portail_module_actif(),
    })

@login_required
def premiere_connexion_mdp(request):
    """Étape 1 du parcours d'accueil : changement du mot de passe provisoire."""
    # On récupère le client lié au compte connecté
    client = Client.objects.filter(compte=request.user).first()

    erreur = None
    if request.method == "POST":
        nouveau = request.POST.get("nouveau_mdp", "")
        confirmation = request.POST.get("confirmation_mdp", "")

        if len(nouveau) < 6:
            erreur = "Le mot de passe doit contenir au moins 6 caractères."
        elif nouveau != confirmation:
            erreur = "Les deux mots de passe ne correspondent pas."
        else:
            # On change le mot de passe
            request.user.set_password(nouveau)
            request.user.save()
            # Important : garder l'utilisateur connecté après le changement
            update_session_auth_hash(request, request.user)
            # On marque l'étape comme faite et on passe à la lettre de mission
            if client:
                client.mdp_change = True
                client.save()
            return redirect("portail_premiere_connexion_lettre")

    return render(request, "portail/premiere_connexion_mdp.html", {
        "client": client,
        "erreur": erreur,
        "module_actif": get_portail_module_actif(),
    })

@login_required
def premiere_connexion_lettre(request):
    """Étape 2 du parcours : consultation et confirmation de la lettre de mission."""
    client = Client.objects.filter(compte=request.user).first()

    erreur = None
    lettre_document = None
    if client:
        lettre_document = client.lettre_mission or getattr(client.devis_origine, "lettre_mission_pdf", None)

    if request.method == "POST":
        confirme = request.POST.get("confirme_lettre")
        consentement = request.POST.get("consentement_signature")
        nom_signataire = request.POST.get("nom_signataire", "").strip()

        if not confirme:
            erreur = "Vous devez confirmer avoir pris connaissance de la lettre de mission pour continuer."
        elif not consentement:
            erreur = "Vous devez accepter l'utilisation de votre signature électronique pour signer ce document."
        elif not nom_signataire:
            erreur = "Merci de renseigner le nom du signataire."
        else:
            if client:
                client.lettre_confirmee = True
                client.consentement_signature_electronique = True
                client.save()
                devis = getattr(client, "devis_origine", None)
                if devis:
                    devis.lettre_statut = "SIGNEE_CLIENT"
                    devis.lettre_signee_client_le = timezone.now()
                    devis.lettre_signataire_client = nom_signataire
                    devis.save(update_fields=["lettre_statut", "lettre_signee_client_le", "lettre_signataire_client"])
            return redirect("portail_premiere_connexion_cgv")

    return render(request, "portail/premiere_connexion_lettre.html", {
        "client": client,
        "lettre_document": lettre_document,
        "erreur": erreur,
        "module_actif": get_portail_module_actif(),
    })
@login_required
def premiere_connexion_cgv(request):
    """Étape 3 (dernière) : lecture et acceptation des CGV → client actif."""
    from parametres.models import ConditionsUtilisation
    client = Client.objects.filter(compte=request.user).first()
    cgv = ConditionsUtilisation.get_solo()

    erreur = None
    if request.method == "POST":
        accepte = request.POST.get("accepte_cgv")
        if not accepte:
            erreur = "Vous devez accepter les conditions d'utilisation pour finaliser votre inscription."
        else:
            if client:
                client.cgv_acceptees = True
                # Le parcours est terminé → le client devient ACTIF
                client.statut = "ACTIF"
                client.save()
            return redirect("portail_accueil")

    return render(request, "portail/premiere_connexion_cgv.html", {
        "client": client,
        "cgv": cgv,
        "erreur": erreur,
        "module_actif": get_portail_module_actif(),
    })