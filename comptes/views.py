from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import FieldError
from django.core.files.base import ContentFile
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.utils import timezone
from django.utils.text import slugify
import base64

from pilotage.modules_data import charger_sous_modules
from .models import DocumentSigne, DelegationSignature, Profil, SignatureElectronique
from .pdf_signature import apposer_signature_sur_pdf, POSITIONS_DISPONIBLES
from .signatures import extraire_signature, signature_vers_png_bytes


def _contexte_comptes(request):
    return {
        "module_actif": {
            "cle": "outils",
            "nom": "Outils",
            "icone": "🛠️",
            "description": "Signature électronique et outils transverses du cabinet.",
        },
        "sous_modules": charger_sous_modules("comptes", request),
    }


@login_required
def aiguillage(request):
    """Carrefour post-connexion : redirige selon le rôle de l'utilisateur.

    L'utilisateur ne voit jamais cette page : elle le renvoie aussitôt
    vers l'interface correspondant à son rôle.
    """
    role = None
    if hasattr(request.user, "profil"):
        role = request.user.profil.role

    if role == Profil.Role.DIRECTION or role == Profil.Role.CADRE:
        return redirect("/pilotage/")
    elif role == Profil.Role.COLLABORATEUR:
        return redirect("/collaborateurs/")
    elif role == Profil.Role.CLIENT:
        return redirect("/portail/")
    else:
        # Utilisateur connecté mais sans rôle défini : on le renvoie
        # à l'accueil de la Vitrine plutôt que de le laisser bloqué.
        return redirect("/")


@login_required
def signature_gerer(request):
    """Gestion de la signature électronique réutilisable de l'utilisateur
    connecté : upload d'une photo de signature manuscrite sur papier blanc,
    extraction automatique (fond retiré), aperçu, puis enregistrement.
    Un utilisateur ne voit et ne gère jamais que SA PROPRE signature."""
    signature_active = SignatureElectronique.objects.filter(
        utilisateur=request.user,
        est_active=True,
    ).first()

    apercu_data_uri = None
    erreur = None

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "enregistrer" and request.POST.get("photo_b64"):
            from django.core.files.base import ContentFile
            try:
                entete, donnees = request.POST["photo_b64"].split(",", 1)
                image_bytes = base64.b64decode(donnees)

                SignatureElectronique.objects.filter(
                    utilisateur=request.user,
                    est_active=True,
                ).update(est_active=False)
                sig = SignatureElectronique.objects.create(utilisateur=request.user)
                sig.image.save("signature.png", ContentFile(image_bytes), save=True)

                messages.success(request, "Votre signature électronique a été enregistrée.")
                return redirect("comptes_signature")
            except Exception as e:
                erreur = f"Impossible d'enregistrer cette signature : {e}"

        else:
            photo = request.FILES.get("photo")
            try:
                seuil = int(request.POST.get("seuil", 195))
            except ValueError:
                seuil = 195
            purete = request.POST.get("purete") == "on"

            if not photo:
                erreur = "Merci de sélectionner une photo de votre signature."
            else:
                try:
                    extraite = extraire_signature(photo.read(), seuil=seuil, purete=purete)
                    png_bytes = signature_vers_png_bytes(extraite)
                    apercu_data_uri = "data:image/png;base64," + base64.b64encode(png_bytes).decode("ascii")
                except Exception as e:
                    erreur = f"Impossible de traiter cette image : {e}"

    ctx = _contexte_comptes(request)
    ctx.update({
        "signature_active": signature_active,
        "apercu_data_uri": apercu_data_uri,
        "erreur": erreur,
    })
    return render(request, "comptes/signature_gerer.html", ctx)


@login_required
def signature_appliquer(request):
    """Appose la signature électronique active de l'utilisateur sur un PDF."""
    signature_active = SignatureElectronique.objects.filter(
        utilisateur=request.user,
        est_active=True,
    ).first()
    documents_signes = DocumentSigne.objects.filter(utilisateur=request.user)
    erreur = None

    if request.method == "POST":
        if not signature_active:
            erreur = "Vous devez d'abord enregistrer une signature électronique active pour signer un document."
        else:
            consentement = request.POST.get("consentement_signature")
            nom_signataire = request.POST.get("nom_signataire", "").strip()
            fichier = request.FILES.get("document")
            position = request.POST.get("position", "bas_droite")
            try:
                numero_page = int(request.POST.get("numero_page", 1))
            except ValueError:
                numero_page = 1

            if not fichier:
                erreur = "Merci de sélectionner un document PDF à signer."
            elif not consentement:
                erreur = "Vous devez accepter l'utilisation de votre signature électronique pour signer ce document."
            elif not nom_signataire:
                erreur = "Merci de renseigner le nom du signataire."
            elif not fichier.name.lower().endswith(".pdf"):
                erreur = "Le document doit être un fichier PDF."
            else:
                try:
                    signature_active.image.open("rb")
                    signature_bytes = signature_active.image.read()
                    signature_active.image.close()

                    original_bytes = fichier.read()
                    x_fraction = request.POST.get("x_fraction")
                    y_fraction = request.POST.get("y_fraction")
                    largeur_pt_page = request.POST.get("largeur_pt")
                    hauteur_pt_page = request.POST.get("hauteur_pt")

                    centre_x_pt = centre_y_pt = None
                    if x_fraction and y_fraction and largeur_pt_page and hauteur_pt_page:
                        lp, hp = float(largeur_pt_page), float(hauteur_pt_page)
                        centre_x_pt = float(x_fraction) * lp
                        centre_y_pt = hp - (float(y_fraction) * hp)

                    signed_pdf = apposer_signature_sur_pdf(
                        original_bytes,
                        signature_bytes,
                        nom_signataire=nom_signataire,
                        numero_page=numero_page,
                        centre_x_pt=centre_x_pt,
                        centre_y_pt=centre_y_pt,
                    )

                    document = DocumentSigne.objects.create(
                        utilisateur=request.user,
                        signature=signature_active,
                        nom_signataire=nom_signataire,
                        consentement_signature=True,
                        titre=fichier.name,
                    )
                    document.fichier_original.save(
                        slugify(f"original-{fichier.name}") + ".pdf",
                        ContentFile(original_bytes),
                        save=False,
                    )
                    document.fichier_signe.save(
                        slugify(f"signee-{fichier.name}") + ".pdf",
                        ContentFile(signed_pdf),
                        save=True,
                    )

                    messages.success(request, "Le document a été signé électroniquement avec succès.")
                    return redirect("comptes_signature_appliquer")
                except Exception as e:
                    erreur = f"Impossible de signer ce document : {e}"

    ctx = _contexte_comptes(request)
    ctx.update({
        "signature_active": signature_active,
        "documents_signes": documents_signes,
        "erreur": erreur,
        "positions": POSITIONS_DISPONIBLES,
    })
    return render(request, "comptes/signature_appliquer.html", ctx)


@login_required
def signature_apercu_page(request):
    """Convertit une page d'un PDF en image, pour permettre le positionnement
    visuel (glisser-déposer) de la signature avant l'apposition définitive."""
    if request.method != "POST":
        return JsonResponse({"erreur": "Méthode non autorisée."}, status=405)

    fichier = request.FILES.get("document")
    if not fichier:
        return JsonResponse({"erreur": "Aucun document fourni."}, status=400)

    try:
        numero_page = int(request.POST.get("numero_page", 1))
    except ValueError:
        numero_page = 1

    try:
        import fitz
        pdf_bytes = fichier.read()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        nb_pages = len(doc)

        index_page = (nb_pages + numero_page) if numero_page < 0 else (numero_page - 1)
        if index_page < 0 or index_page >= nb_pages:
            doc.close()
            return JsonResponse({"erreur": f"Page {numero_page} invalide -- ce document a {nb_pages} page(s)."}, status=400)

        page = doc[index_page]
        pix = page.get_pixmap(dpi=100)
        image_bytes = pix.tobytes("png")
        largeur_pt, hauteur_pt = page.rect.width, page.rect.height
        doc.close()

        return JsonResponse({
            "image": "data:image/png;base64," + base64.b64encode(image_bytes).decode("ascii"),
            "nb_pages": nb_pages,
            "largeur_pt": largeur_pt,
            "hauteur_pt": hauteur_pt,
        })
    except Exception as e:
        return JsonResponse({"erreur": f"Impossible de lire ce PDF : {e}"}, status=400)


@login_required
def documents_a_signer(request):
    from devis.models import Facture

    try:
        factures = Facture.objects.filter(signee_par__isnull=True).exclude(statut="ANNULEE")
    except FieldError:
        factures = Facture.objects.exclude(statut="ANNULEE")

    ctx = _contexte_comptes(request)
    ctx.update({
        "factures": factures,
    })
    return render(request, "comptes/documents_a_signer.html", ctx)


@login_required
def signature_par_ordre(request):
    """Ordres de signature actifs reçus par l'utilisateur connecté."""
    from django.utils import timezone
    from .models import DelegationSignature

    aujourd_hui = timezone.now().date()
    delegations = DelegationSignature.objects.filter(
        delegataire=request.user, mode="ORDRE",
        date_debut__lte=aujourd_hui, date_fin__gte=aujourd_hui,
    ).select_related("delegant")
    ctx = _contexte_comptes(request)
    ctx.update({"delegations": delegations})
    return render(request, "comptes/signature_par_ordre.html", ctx)


@login_required
def signature_par_delegation(request):
    """Délégations de pouvoir actives reçues par l'utilisateur connecté."""
    from django.utils import timezone
    from .models import DelegationSignature

    aujourd_hui = timezone.now().date()
    delegations = DelegationSignature.objects.filter(
        delegataire=request.user, mode="DELEGATION_POUVOIR",
        date_debut__lte=aujourd_hui, date_fin__gte=aujourd_hui,
    ).select_related("delegant")
    ctx = _contexte_comptes(request)
    ctx.update({"delegations": delegations})
    return render(request, "comptes/signature_par_delegation.html", ctx)
