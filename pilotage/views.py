from django.shortcuts import render, redirect, get_object_or_404
from django.http import Http404
from django.urls import reverse
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.models import User
from comptes.decorators import role_requis
from comptes.models import Profil
from devis.models import Devis
from paie.models import Employeur, Employe
from paie.views import _matricule_auto
from .models import Pole, Poste
from pilotage.modules_data import MODULES, charger_sous_modules, get_module_info, arbre_permissions

MODULES_METIER_CHOIX = [
    (cle, data["nom"]) for cle, data in MODULES.items()
    if cle not in ("outils", "parametres")
]


def _modules_nav():
    """Liste des modules pour la barre horizontale du haut."""
    nav = []
    # Le tableau de bord en premier
    nav.append({"cle": "dashboard", "nom": "Tableau de bord", "icone": "🏠", "url": "/pilotage/"})
    for cle, data in MODULES.items():
        nav.append({"cle": cle, "nom": data["nom"], "icone": data["icone"], "url": f"/pilotage/module/{cle}/"})
    return nav


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE)
def tableau_bord(request):
    """Tableau de bord principal de la Direction."""
    nb_devis_envoyes = Devis.objects.filter(statut="ENVOYE").count()

    chiffres = {
        "ca_mois": "4 250 000",
        "devis_en_cours": nb_devis_envoyes,
        "dossiers_actifs": 18,
        "taux_recouvrement": 76,
    }

    modules = []
    for cle, data in MODULES.items():
        sous_modules = charger_sous_modules(data["app"])
        modules.append({
            "cle": cle, "nom": data["nom"], "icone": data["icone"],
            "url": f"/pilotage/module/{cle}/",
            "branche": len(sous_modules) > 0,
        })

    alertes = [
        {"texte": f"{nb_devis_envoyes} devis envoyé(s) en attente de réponse", "niveau": "info"},
        {"texte": "Déclaration TVA à déposer avant le 15", "niveau": "warning"},
        {"texte": "2 lettres de mission en attente de validation", "niveau": "warning"},
    ]

    stats_vitrine = {
        "visiteurs": 1240, "bouton_top": "Demander un devis", "bouton_top_clics": 87,
        "articles_top": [
            {"titre": "Comment créer son entreprise en Côte d'Ivoire", "lectures": 342},
            {"titre": "La FNE : ce qui change en 2025", "lectures": 289},
            {"titre": "Calculer ses impôts BIC", "lectures": 201},
        ],
    }

    taches = [
        {"titre": "Préparer le bilan ETS SAMTEX", "assignee": "Service Compta", "echeance": "25/06", "statut": "En cours"},
        {"titre": "Relancer client KPMG (devis)", "assignee": "Secrétariat", "echeance": "24/06", "statut": "À faire"},
        {"titre": "Audit social Entreprise XYZ", "assignee": "Service RH", "echeance": "30/06", "statut": "À faire"},
    ]

    return render(request, "pilotage/tableau_bord.html", {
        "chiffres": chiffres, "modules": modules,
        "alertes": alertes, "stats_vitrine": stats_vitrine, "taches": taches,
        # Pour le gabarit :
        "modules_nav": _modules_nav(),
        "module_actif": get_module_info("direction"),
        "sous_modules": charger_sous_modules("pilotage", request),
    })


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE)
def page_module(request, cle):
    """Coquille d'un module : sidebar des sous-modules déclarés (branchement)."""
    data = MODULES.get(cle)
    if not data:
        raise Http404("Module inconnu")

    sous_modules = charger_sous_modules(data["app"])

    return render(request, "pilotage/page_module.html", {
        "cle": cle,
        "module": data,
        # Pour le gabarit :
        "modules_nav": _modules_nav(),
        "module_actif": get_module_info(cle),
        "sous_modules": sous_modules,
    })


@role_requis(Profil.Role.DIRECTION)
def delegations_liste(request):
    """Liste des délégations de signature créées — visible et gérable uniquement par la Direction."""
    from comptes.models import DelegationSignature
    delegations = DelegationSignature.objects.select_related("delegant", "delegataire").all()
    return render(request, "pilotage/delegations_liste.html", {
        "delegations": delegations,
        "modules_nav": _modules_nav(),
        "module_actif": get_module_info("direction"),
        "sous_modules": charger_sous_modules("pilotage", request),
    })


@role_requis(Profil.Role.DIRECTION)
def delegation_creer(request):
    """Création d'une délégation de signature — le délégant est TOUJOURS la personne connectée qui crée la délégation."""
    from comptes.models import DelegationSignature
    from comptes.models import Profil as ProfilModel
    from django.contrib.auth.models import User

    delegataires_possibles = User.objects.filter(
        profil__role__in=[ProfilModel.Role.CADRE, ProfilModel.Role.COLLABORATEUR]
    ).exclude(id=request.user.id)

    if request.method == "POST":
        delegataire_id = request.POST.get("delegataire")
        mode = request.POST.get("mode")
        perimetre = request.POST.get("perimetre", "").strip()
        date_debut = request.POST.get("date_debut")
        date_fin = request.POST.get("date_fin")

        erreurs = []
        if not delegataire_id:
            erreurs.append("Choisissez la personne à qui déléguer.")
        if mode not in ("ORDRE", "DELEGATION_POUVOIR"):
            erreurs.append("Choisissez le régime (par ordre ou par délégation de pouvoir).")
        if not perimetre:
            erreurs.append("Précisez le périmètre ou le motif.")
        if not date_debut or not date_fin:
            erreurs.append("Indiquez la période de validité.")
        elif date_fin < date_debut:
            erreurs.append("La date de fin doit être après la date de début.")

        if not erreurs:
            delegation = DelegationSignature.objects.create(
                delegant=request.user,
                delegataire_id=delegataire_id,
                mode=mode,
                perimetre=perimetre,
                date_debut=date_debut,
                date_fin=date_fin,
                cree_par=request.user,
            )
            from django.template.loader import render_to_string
            from weasyprint import HTML
            from django.core.files.base import ContentFile

            html = render_to_string("devis/_document_delegation.html", {"delegation": delegation})
            pdf_bytes = HTML(string=html, base_url=request.build_absolute_uri("/")).write_pdf()
            delegation.document_preuve.save(
                f"delegation-{delegation.id}.pdf", ContentFile(pdf_bytes), save=True)

            messages.success(request, f"Délégation créée pour {delegation.delegataire.get_full_name() or delegation.delegataire.username}.")
            return redirect("pilotage_delegations_liste")

        for e in erreurs:
            messages.error(request, e)

    return render(request, "pilotage/delegation_creer.html", {
        "delegataires_possibles": delegataires_possibles,
        "modules_nav": _modules_nav(),
        "module_actif": get_module_info("direction"),
        "sous_modules": charger_sous_modules("pilotage", request),
    })


@role_requis(Profil.Role.DIRECTION)
def collaborateurs_liste(request):
    """Comptes internes (Direction, Cadres, Collaborateurs) — gestion centralisée."""
    profils = Profil.objects.filter(
        role__in=[Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR]
    ).select_related("user").order_by("user__first_name")
    return render(request, "pilotage/collaborateurs_liste.html", {
        "profils": profils,
        "modules_nav": _modules_nav(),
        "module_actif": get_module_info("direction"),
        "sous_modules": charger_sous_modules("pilotage", request),
    })


def _employeur_cabinet():
    """Récupère (ou crée une seule fois) l'employeur représentant le
    Cabinet K&L lui-même, pour y rattacher son propre personnel."""
    employeur, _ = Employeur.objects.get_or_create(
        raison_sociale="Cabinet Comptable et Fiscal K&L",
        defaults={"commune": "Daloa"},
    )
    return employeur


@role_requis(Profil.Role.DIRECTION)
def collaborateur_creer(request):
    """Création d'un compte interne — crée en même temps le compte de
    connexion ET la fiche salarié dans Paie (le cabinet se traite comme
    son propre employeur), avec un mot de passe provisoire envoyé par email."""
    from django.contrib.auth.models import User

    if request.method == "POST":
        prenom = request.POST.get("prenom", "").strip()
        nom = request.POST.get("nom", "").strip()
        email = request.POST.get("email", "").strip()
        role = request.POST.get("role")
        poste = request.POST.get("poste", "").strip()
        contrat = request.POST.get("contrat", "CDI")
        date_entree = request.POST.get("date_entree")

        erreurs = []
        if not prenom or not nom:
            erreurs.append("Le prénom et le nom sont obligatoires.")
        if not email:
            erreurs.append("L'email est obligatoire (il servira d'identifiant de connexion).")
        elif User.objects.filter(username=email).exists():
            erreurs.append("Un compte existe déjà avec cet email.")
        if role not in dict(Profil.Role.choices):
            erreurs.append("Choisissez un rôle valide.")
        if not date_entree:
            erreurs.append("La date d'entrée est obligatoire.")

        if not erreurs:
            import secrets, string
            alphabet = string.ascii_letters + string.digits
            mot_de_passe = "".join(secrets.choice(alphabet) for _ in range(10))

            user = User.objects.create_user(
                username=email, email=email, password=mot_de_passe,
                first_name=prenom, last_name=nom,
            )
            Profil.objects.create(user=user, role=role)

            employeur_cabinet = _employeur_cabinet()
            Employe.objects.create(
                employeur=employeur_cabinet,
                utilisateur=user,
                matricule=_matricule_auto(employeur_cabinet),
                nom_prenoms=f"{prenom} {nom}",
                poste=poste,
                contrat=contrat,
                date_entree=date_entree,
            )

            email_envoye, erreur_email = False, ""
            try:
                from parametres.emails import envoyer_email
                sujet = "Votre accès à Cabinet Smart-Hub"
                corps = (
                    f"Bonjour {prenom},\n\n"
                    f"Un compte vient de vous être créé sur Cabinet Smart-Hub, avec le rôle {dict(Profil.Role.choices)[role]}.\n\n"
                    f"Identifiants de connexion :\n"
                    f"  • Email : {email}\n"
                    f"  • Mot de passe provisoire : {mot_de_passe}\n\n"
                    f"Nous vous recommandons de le changer dès votre première connexion.\n\n"
                    f"Cordialement,\nCabinet Comptable & Fiscal K&L"
                )
                email_envoye, erreur_email = envoyer_email([email], sujet, corps, [])
            except Exception as e:
                erreur_email = str(e)

            if email_envoye:
                messages.success(request, f"Compte créé pour {prenom} {nom} — identifiants envoyés par email.")
            else:
                messages.warning(request, f"Compte créé pour {prenom} {nom}, mais l'email n'a pas pu être envoyé "
                                          f"({erreur_email}). Mot de passe provisoire : {mot_de_passe}")
            return redirect("pilotage_collaborateurs_liste")

        for e in erreurs:
            messages.error(request, e)

    return render(request, "pilotage/collaborateur_creer.html", {
        "roles": [(r.value, r.label) for r in Profil.Role if r != Profil.Role.CLIENT],
        "modules_nav": _modules_nav(),
        "module_actif": get_module_info("direction"),
        "sous_modules": None,
    })


@role_requis(Profil.Role.DIRECTION)
def poles_liste(request):
    poles = Pole.objects.select_related("responsable").all()
    return render(request, "pilotage/poles_liste.html", {
        "poles": poles,
        "module_actif": get_module_info("direction"),
        "sous_modules": charger_sous_modules("pilotage", request),
    })


@role_requis(Profil.Role.DIRECTION)
def pole_creer(request):
    if request.method == "POST":
        nom = request.POST.get("nom", "").strip()
        description = request.POST.get("description", "").strip()
        modules_ids = request.POST.getlist("modules_ids")
        sous_modules_urls = request.POST.getlist("sous_modules_urls")
        fonctionnalites_urls = request.POST.getlist("fonctionnalites_urls")
        responsable_id = request.POST.get("responsable") or None

        if not nom:
            messages.error(request, "Le nom du pôle est obligatoire.")
        else:
            Pole.objects.create(
                nom=nom, description=description,
                modules_ids=modules_ids, sous_modules_urls=sous_modules_urls,
                fonctionnalites_urls=fonctionnalites_urls, responsable_id=responsable_id,
            )
            messages.success(request, f"Pôle « {nom} » créé.")
            return redirect("pilotage_poles_liste")

    responsables_possibles = User.objects.filter(
        profil__role__in=[Profil.Role.DIRECTION, Profil.Role.CADRE]
    )
    return render(request, "pilotage/pole_form.html", {
        "titre_page": "Nouveau pôle",
        "arbre": arbre_permissions(),
        "responsables_possibles": responsables_possibles,
        "module_actif": get_module_info("direction"),
        "sous_modules": charger_sous_modules("pilotage", request),
    })


@role_requis(Profil.Role.DIRECTION)
def pole_modifier(request, pole_id):
    pole = get_object_or_404(Pole, id=pole_id)
    if request.method == "POST":
        pole.nom = request.POST.get("nom", "").strip()
        pole.description = request.POST.get("description", "").strip()
        pole.modules_ids = request.POST.getlist("modules_ids")
        pole.sous_modules_urls = request.POST.getlist("sous_modules_urls")
        pole.fonctionnalites_urls = request.POST.getlist("fonctionnalites_urls")
        pole.responsable_id = request.POST.get("responsable") or None
        pole.save()
        messages.success(request, f"Pôle « {pole.nom} » mis à jour.")
        return redirect("pilotage_poles_liste")

    responsables_possibles = User.objects.filter(
        profil__role__in=[Profil.Role.DIRECTION, Profil.Role.CADRE]
    )
    return render(request, "pilotage/pole_form.html", {
        "titre_page": f"Modifier : {pole.nom}",
        "pole": pole,
        "arbre": arbre_permissions(),
        "responsables_possibles": responsables_possibles,
        "module_actif": get_module_info("direction"),
        "sous_modules": charger_sous_modules("pilotage", request),
    })


@role_requis(Profil.Role.DIRECTION)
def pole_supprimer(request, pole_id):
    pole = get_object_or_404(Pole, id=pole_id)
    if request.method == "POST":
        pole.delete()
        messages.success(request, "Pôle supprimé.")
    return redirect("pilotage_poles_liste")


@role_requis(Profil.Role.DIRECTION)
def postes_liste(request):
    postes = Poste.objects.select_related("pole", "poste_parent").all()
    return render(request, "pilotage/postes_liste.html", {
        "postes": postes,
        "module_actif": get_module_info("direction"),
        "sous_modules": charger_sous_modules("pilotage", request),
    })


@role_requis(Profil.Role.DIRECTION)
def poste_creer(request):
    if request.method == "POST":
        intitule = request.POST.get("intitule", "").strip()
        pole_id = request.POST.get("pole")
        poste_parent_id = request.POST.get("poste_parent") or None

        if not intitule or not pole_id:
            messages.error(request, "L'intitulé et le pôle sont obligatoires.")
        else:
            Poste.objects.create(intitule=intitule, pole_id=pole_id, poste_parent_id=poste_parent_id)
            messages.success(request, f"Poste « {intitule} » créé.")
            return redirect("pilotage_postes_liste")

    return render(request, "pilotage/poste_form.html", {
        "titre_page": "Nouveau poste",
        "poles": Pole.objects.all(),
        "postes_possibles": Poste.objects.all(),
        "module_actif": get_module_info("direction"),
        "sous_modules": charger_sous_modules("pilotage", request),
    })


@role_requis(Profil.Role.DIRECTION)
def poste_modifier(request, poste_id):
    poste = get_object_or_404(Poste, id=poste_id)
    if request.method == "POST":
        poste.intitule = request.POST.get("intitule", "").strip()
        poste.pole_id = request.POST.get("pole")
        nouveau_parent_id = request.POST.get("poste_parent") or None
        if nouveau_parent_id and int(nouveau_parent_id) == poste.id:
            messages.error(request, "Un poste ne peut pas être son propre supérieur.")
        else:
            poste.poste_parent_id = nouveau_parent_id
            poste.save()
            messages.success(request, f"Poste « {poste.intitule} » mis à jour.")
            return redirect("pilotage_postes_liste")

    return render(request, "pilotage/poste_form.html", {
        "titre_page": f"Modifier : {poste.intitule}",
        "poste": poste,
        "poles": Pole.objects.all(),
        "postes_possibles": Poste.objects.exclude(id=poste.id),
        "module_actif": get_module_info("direction"),
        "sous_modules": charger_sous_modules("pilotage", request),
    })


@role_requis(Profil.Role.DIRECTION)
def poste_supprimer(request, poste_id):
    poste = get_object_or_404(Poste, id=poste_id)
    if request.method == "POST":
        poste.delete()
        messages.success(request, "Poste supprimé.")
    return redirect("pilotage_postes_liste")


@role_requis(Profil.Role.DIRECTION)
def organigramme(request):
    postes_racines = Poste.objects.filter(poste_parent__isnull=True).select_related("pole")
    return render(request, "pilotage/organigramme.html", {
        "postes_racines": postes_racines,
        "module_actif": get_module_info("direction"),
        "sous_modules": charger_sous_modules("pilotage", request),
    })


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE)
def notifications_liste(request):
    """Liste des notifications avec filtres (type, statut de lecture)."""
    from .models import Notification
    notifications = Notification.objects.all().order_by("-cree_le")
    
    # Filtres
    filtre_type = request.GET.get("type", "")
    filtre_statut = request.GET.get("statut", "")
    
    if filtre_type:
        notifications = notifications.filter(type_notification=filtre_type)
    if filtre_statut == "lues":
        notifications = notifications.filter(lue=True)
    elif filtre_statut == "non_lues":
        notifications = notifications.filter(lue=False)
    
    # Types disponibles pour le filtre
    types_disponibles = Notification.TYPE_CHOICES
    
    return render(request, "pilotage/notifications_liste.html", {
        "notifications": notifications[:50],
        "filtre_type": filtre_type,
        "filtre_statut": filtre_statut,
        "types_disponibles": types_disponibles,
        "reset_url": reverse('pilotage_notifications'),
        "module_actif": get_module_info("direction"),
        "sous_modules": charger_sous_modules("pilotage", request),
    })


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE)
def notification_marquer_lue(request, notification_id):
    """Marquer une notification comme lue."""
    from .models import Notification
    notif = get_object_or_404(Notification, pk=notification_id)
    notif.lue = True
    notif.save()
    if request.method == "POST" and notif.url:
        return redirect(notif.url)
    return redirect("pilotage_notifications")


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE)
def notification_supprimer(request, notification_id):
    """Supprimer une notification."""
    from .models import Notification
    notif = get_object_or_404(Notification, pk=notification_id)
    if request.method == "POST":
        notif.delete()
    return redirect("pilotage_notifications")


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE)
def lettres_a_valider(request):
    dossiers = Devis.objects.filter(lettre_statut="EN_VALIDATION_DIRECTION").order_by("date_envoi")

    return render(request, "pilotage/lettres_a_valider.html", {
        "dossiers": dossiers,
        "modules_nav": _modules_nav(),
        "module_actif": get_module_info("direction"),
        "sous_modules": charger_sous_modules("pilotage", request),
    })


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE)
def lettre_validation_detail(request, devis_id):
    devis = get_object_or_404(Devis, id=devis_id)

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "valider":
            devis.lettre_statut = "VALIDEE_DIRECTION"
            devis.lettre_validee_par = request.user
            devis.lettre_validee_le = timezone.now()
            devis.lettre_motif_refus = ""
            devis.save(update_fields=["lettre_statut", "lettre_validee_par", "lettre_validee_le", "lettre_motif_refus"])
        elif action == "refuser":
            devis.lettre_statut = "BROUILLON"
            devis.lettre_motif_refus = request.POST.get("motif_refus", "").strip()
            devis.save(update_fields=["lettre_statut", "lettre_motif_refus"])
        return redirect("pilotage_lettre_validation_detail", devis_id=devis.id)

    return render(request, "pilotage/lettre_validation_detail.html", {
        "devis": devis,
        "modules_nav": _modules_nav(),
        "module_actif": get_module_info("direction"),
        "sous_modules": None,
    })