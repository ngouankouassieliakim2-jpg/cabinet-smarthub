from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseBadRequest
from django.utils import timezone
from datetime import timedelta
from django.db.models import Max, Q, OuterRef, Subquery, IntegerField, Count
from django.db import transaction
from django.core.exceptions import ValidationError

from .models import Conversation, Participation, Message

@login_required
def conversations_liste(request):
    """
    Liste des conversations de l'utilisateur avec :
    - 1 seule requête SQL principale (optimisation N+1).
    - Annotation du dernier message (ID et texte) via Subquery.
    - Calcul performant des messages non lus sans boucles SQL.
    """
    # 1. Sous-requête pour récupérer l'ID du dernier message de chaque conversation
    dernier_msg_subquery = Message.objects.filter(
        conversation=OuterRef('conversation_id')
    ).order_by('-envoye_le', '-id')

    # 2. Récupération des participations annotées
    participations = (
        Participation.objects.filter(utilisateur=request.user)
        .select_related("conversation")
        .annotate(
            dernier_msg_date=Max("conversation__messages__envoye_le"),
            dernier_msg_id=Subquery(dernier_msg_subquery.values('id')[:1]),
            dernier_msg_texte=Subquery(dernier_msg_subquery.values('texte')[:1]),
            dernier_msg_expediteur=Subquery(dernier_msg_subquery.values('expediteur__username')[:1]),
        )
        .order_by("-dernier_msg_date")
    )

    # 3. Optimisation pour le nom affiché (on précharge les autres membres d'un seul coup)
    # Évite le N+1 sur `conv.participations.exclude(...)`
    conv_ids = [p.conversation_id for p in participations]
    autres_participants = (
        Participation.objects.filter(conversation_id__in=conv_ids)
        .exclude(utilisateur=request.user)
        .select_related("utilisateur")
    )
    
    # Map conversation_id -> autre utilisateur
    map_autres = {p.conversation_id: p.utilisateur.username for p in autres_participants}

    conversations = []
    for p in participations:
        conv = p.conversation
        
        # Reconstitution de l'objet virtuel du dernier message sans refaire de requête SQL
        dernier_message = None
        if p.dernier_msg_id:
            dernier_message = {
                "id": p.dernier_msg_id,
                "texte": p.dernier_msg_texte,
                "envoye_le": p.dernier_msg_date,
                "expediteur_username": p.dernier_msg_expediteur
            }

        # Calcul du nombre de non-lus optimisé en base de données
        qs_non_lus = conv.messages.exclude(expediteur=request.user)
        if p.dernier_message_lu_id:
            nb_non_lus = qs_non_lus.filter(id__gt=p.dernier_message_lu_id).count()
        else:
            nb_non_lus = qs_non_lus.count()

        # Choix du nom de la conversation
        if conv.type_conversation == "direct":
            nom_affiche = map_autres.get(conv.id, "?")
        else:
            nom_affiche = conv.nom or f"Groupe #{conv.id}"

        conversations.append({
            "conversation": conv,
            "nom_affiche": nom_affiche,
            "dernier_message": dernier_message,
            "nb_non_lus": nb_non_lus,
        })

    ctx = {"conversations": conversations}
    return render(request, "messagerie/conversations_liste.html", ctx)


@login_required
def conversation_ouvrir(request, conversation_id):
    """Affiche une conversation, gère l'envoi et marque comme lu."""
    conversation = get_object_or_404(Conversation, pk=conversation_id)
    participation = get_object_or_404(Participation, conversation=conversation, utilisateur=request.user)

    # select_related sur l'expéditeur pour éviter le N+1 dans la boucle d'affichage du template
    messages_liste = conversation.messages.select_related("expediteur").all()

    if request.method == "POST":
        texte = request.POST.get("texte", "").strip()
        fichier = request.FILES.get("fichier")
        latitude = request.POST.get("latitude")
        longitude = request.POST.get("longitude")
        
        if latitude and longitude and not (texte or fichier):
            texte = "Localisation partagée"

        if texte or fichier or (latitude and longitude):
            with transaction.atomic():
                msg = Message.objects.create(
                    conversation=conversation,
                    expediteur=request.user,
                    texte=texte,
                    fichier=fichier,
                    nom_fichier_original=fichier.name if fichier else ("Localisation" if latitude and longitude else ""),
                    latitude=latitude or None,
                    longitude=longitude or None,
                )
                # Mise à jour directe du dernier message lu de l'expéditeur
                participation.dernier_message_lu = msg
                participation.save()
                
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"ok": True, "message_id": msg.id})

            return redirect("messagerie_conversation", conversation_id=conversation.id)

    # Sécurisation du marquage comme lu à l'ouverture
    dernier = messages_liste.last()
    if dernier and (not participation.dernier_message_lu or participation.dernier_message_lu.id < dernier.id):
        participation.dernier_message_lu = dernier
        participation.save(update_fields=['dernier_message_lu'])

    # Récupération optimisée du nom affiché
    if conversation.type_conversation == "direct":
        autre = conversation.participations.exclude(utilisateur=request.user).select_related("utilisateur").first()
        nom_affiche = autre.utilisateur.username if autre else "?"
    else:
        nom_affiche = conversation.nom or f"Groupe #{conversation.id}"

    messages_vus = _messages_vus_par_autre(conversation, request.user)
    if conversation.type_conversation == "direct":
        autre_part = conversation.participations.exclude(utilisateur=request.user).select_related("utilisateur__profil").first()
        presence = _texte_presence(autre_part.utilisateur.profil.derniere_activite) if autre_part and hasattr(autre_part.utilisateur, "profil") else ""
    else:
        presence = ""

    ctx = {
        "conversation": conversation,
        "messages_liste": messages_liste,
        "nom_affiche": nom_affiche,
        "messages_vus": messages_vus,
        "presence": presence,
    }
    return render(request, "messagerie/conversation.html", ctx)


def _texte_presence(derniere_activite):
    if not derniere_activite:
        return "Jamais connecté"
    maintenant = timezone.now()
    if (maintenant - derniere_activite) < timedelta(minutes=3):
        return "En ligne"
    diff = maintenant - derniere_activite
    if diff < timedelta(hours=1):
        return f"Vu il y a {int(diff.total_seconds() // 60)} min"
    if derniere_activite.date() == maintenant.date():
        return f"Vu aujourd'hui à {timezone.localtime(derniere_activite).strftime('%H:%M')}"
    if diff < timedelta(days=2):
        return f"Vu hier à {timezone.localtime(derniere_activite).strftime('%H:%M')}"
    return f"Vu le {timezone.localtime(derniere_activite).strftime('%d/%m/%Y')}"


def _messages_vus_par_autre(conversation, moi):
    """Pour une conversation directe : IDs de MES messages déjà lus par l'autre."""
    if conversation.type_conversation != "direct":
        return set()
    autre_p = conversation.participations.exclude(utilisateur=moi).select_related("dernier_message_lu").first()
    if not autre_p or not autre_p.dernier_message_lu_id:
        return set()
    return set(
        conversation.messages.filter(
            expediteur=moi, id__lte=autre_p.dernier_message_lu_id
        ).values_list("id", flat=True)
    )


@login_required
def messages_actualiser(request, conversation_id):
    """Endpoint JSON optimisé pour le polling."""
    conversation = get_object_or_404(Conversation, pk=conversation_id)
    get_object_or_404(Participation, conversation=conversation, utilisateur=request.user)

    depuis_id = int(request.GET.get("depuis", 0))
    nouveaux = conversation.messages.filter(id__gt=depuis_id).select_related("expediteur")

    messages_vus = _messages_vus_par_autre(conversation, request.user)
    data = [{
        "id": m.id,
        "expediteur": m.expediteur.username if m.expediteur else "?",
        "est_moi": m.expediteur_id == request.user.id,
        "texte": m.texte,
        "fichier_url": m.fichier.url if m.fichier else None,
        "nom_fichier": m.nom_fichier_original,
        "latitude": float(m.latitude) if m.latitude is not None else None,
        "longitude": float(m.longitude) if m.longitude is not None else None,
        "est_audio": m.est_audio(),
        "heure": m.envoye_le.strftime("%H:%M"),
        "vu": m.id in messages_vus,
    } for m in nouveaux]

    return JsonResponse({"messages": data})


@login_required
def reunion_obtenir(request, conversation_id):
    conversation = get_object_or_404(Conversation, pk=conversation_id)
    get_object_or_404(Participation, conversation=conversation, utilisateur=request.user)
    return JsonResponse({"cle_reunion": conversation.obtenir_reunion()})


@login_required
def nouvelle_conversation(request):
    """
    Création sécurisée de canaux de discussion.
    Intègre la validation des entrées et l'atomicité des transactions SQL.
    """
    if request.method == "POST":
        type_conv = request.POST.get("type_conversation", "direct")
        
        if type_conv == "direct":
            autre_id = request.POST.get("utilisateur_id")
            if not autre_id:
                return HttpResponseBadRequest("ID du destinataire manquant.")
                
            autre = get_object_or_404(User, pk=autre_id)
            
            # Vérification et réutilisation d'un canal direct existant
            existante = (
                Conversation.objects.filter(type_conversation="direct", participations__utilisateur=request.user)
                .filter(participations__utilisateur=autre)
                .first()
            )
            if existante:
                return redirect("messagerie_conversation", conversation_id=existante.id)
            
            # Écriture sécurisée des participations
            with transaction.atomic():
                conv = Conversation.objects.create(type_conversation="direct", cree_par=request.user)
                Participation.objects.create(conversation=conv, utilisateur=request.user)
                Participation.objects.create(conversation=conv, utilisateur=autre)
                
        else:
            # Traitement Groupe
            nom = request.POST.get("nom", "").strip()
            ids = request.POST.getlist("utilisateurs")
            
            # --- VALIDATION MÉTIER ---
            if not nom:
                return render(request, "messagerie/nouvelle_conversation.html", {
                    "error": "Le nom du groupe ne peut pas être vide.",
                    "utilisateurs": User.objects.exclude(id=request.user.id).order_by("username")
                })
            
            if len(nom) > 150:
                return render(request, "messagerie/nouvelle_conversation.html", {
                    "error": "Le nom du groupe est trop long (max 150 caractères).",
                    "utilisateurs": User.objects.exclude(id=request.user.id).order_by("username")
                })

            if not ids:
                return render(request, "messagerie/nouvelle_conversation.html", {
                    "error": "Vous devez sélectionner au moins un collaborateur pour former un groupe.",
                    "utilisateurs": User.objects.exclude(id=request.user.id).order_by("username")
                })

            # Écriture atomique du groupe et de ses membres
            with transaction.atomic():
                conv = Conversation.objects.create(type_conversation="groupe", nom=nom, cree_par=request.user)
                # Créateur automatiquement administrateur
                Participation.objects.create(conversation=conv, utilisateur=request.user, est_admin=True)
                
                # Ajout des autres membres
                for uid in ids:
                    Participation.objects.get_or_create(conversation=conv, utilisateur_id=uid)
                    
        return redirect("messagerie_conversation", conversation_id=conv.id)

    utilisateurs = User.objects.exclude(id=request.user.id).order_by("username")
    ctx = {"utilisateurs": utilisateurs}
    return render(request, "messagerie/nouvelle_conversation.html", ctx)