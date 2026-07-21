from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from comptes.decorators import role_requis
from comptes.models import Profil
from django.contrib import messages
from django.forms import modelform_factory
from pilotage.modules_data import charger_sous_modules

from .forms import ParametresMobileMoneyForm, ParametresWhatsAppBusinessForm
from .models import (
    CategoriePrestation,
    ConditionsUtilisation,
    ParametresEmail,
    ParametresFNE,
    ParametresMobileMoney,
    ParametresWhatsAppBusiness,
    PrestationCatalogue,
    VariantePrix,
)

CategorieForm = modelform_factory(CategoriePrestation, fields=[
    "nom", "regime", "duree_engagement_mois", "preavis_mois", "modalites_paiement",
])
PrestationForm = modelform_factory(PrestationCatalogue, fields=[
    "categorie", "libelle", "prix_par_defaut", "periodicite",
    "taux_tva", "delai_livraison", "livrable",
])
VarianteForm = modelform_factory(VariantePrix, fields=["prestation", "libelle", "prix"])

EmailForm = modelform_factory(ParametresEmail, fields=[
    "adresse_envoi", "mot_de_passe_app", "nom_expediteur",
])

CGVForm = modelform_factory(ConditionsUtilisation, fields=["texte"])

FNEForm = modelform_factory(ParametresFNE, fields=[
    "environnement", "url_test", "url_production", "api_key",
    "ncc_cabinet", "point_de_vente_defaut", "etablissement_defaut",
])


def _contexte_parametres():
    return {
        "module_actif": {
            "cle": "parametres",
            "nom": "Paramètres",
            "icone": "⚙️",
            "description": "Réglages transversaux du cabinet.",
        },
        "sous_modules": charger_sous_modules("parametres"),
    }


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE)
def catalogue(request):
    categories = CategoriePrestation.objects.all().prefetch_related("prestations__variantes")
    ctx = _contexte_parametres()
    ctx.update({"categories": categories})
    return render(request, "parametres/catalogue.html", ctx)


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE)
def parametres_fne(request):
    params = ParametresFNE.get_solo()
    if request.method == "POST":
        form = FNEForm(request.POST, instance=params)
        if form.is_valid():
            form.save()
            messages.success(request, "Paramètres FNE enregistrés.")
            return redirect("parametres_fne")
    else:
        form = FNEForm(instance=params)
    ctx = _contexte_parametres()
    ctx.update({"form": form, "params": params})
    return render(request, "parametres/parametres_fne.html", ctx)


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE)
def parametres_mobile_money(request):
    params = ParametresMobileMoney.get_solo()
    if request.method == "POST":
        form = ParametresMobileMoneyForm(request.POST, instance=params)
        if form.is_valid():
            form.save()
            messages.success(request, "Paramètres Mobile Money enregistrés.")
            return redirect("parametres_mobile_money")
    else:
        form = ParametresMobileMoneyForm(instance=params)
    ctx = _contexte_parametres()
    ctx.update({
        "form": form,
        "params": params,
        "wave_configure": params.wave_configure,
        "orange_money_configure": params.orange_money_configure,
    })
    return render(request, "parametres/mobile_money.html", ctx)


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE)
def parametres_whatsapp(request):
    params = ParametresWhatsAppBusiness.get_solo()
    if request.method == "POST":
        form = ParametresWhatsAppBusinessForm(request.POST, instance=params)
        if form.is_valid():
            form.save()
            messages.success(request, "Paramètres WhatsApp Business enregistrés.")
            return redirect("parametres_whatsapp")
    else:
        form = ParametresWhatsAppBusinessForm(instance=params)
    ctx = _contexte_parametres()
    ctx.update({"form": form, "params": params, "est_configure": params.est_configure})
    return render(request, "parametres/whatsapp.html", ctx)


# ---------- Catégories ----------
@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE)
def creer_categorie(request):
    if request.method == "POST":
        form = CategorieForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("catalogue")
    else:
        form = CategorieForm()
    ctx = _contexte_parametres()
    ctx.update({"form": form, "titre": "Nouvelle catégorie"})
    return render(request, "parametres/form_categorie.html", ctx)


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE)
def modifier_categorie(request, pk):
    cat = get_object_or_404(CategoriePrestation, pk=pk)
    if request.method == "POST":
        form = CategorieForm(request.POST, instance=cat)
        if form.is_valid():
            form.save()
            return redirect("catalogue")
    else:
        form = CategorieForm(instance=cat)
    ctx = _contexte_parametres()
    ctx.update({"form": form, "titre": "Modifier la catégorie"})
    return render(request, "parametres/form_categorie.html", ctx)


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE)
def supprimer_categorie(request, pk):
    cat = get_object_or_404(CategoriePrestation, pk=pk)
    if request.method == "POST":
        cat.delete()
    return redirect("catalogue")


# ---------- Prestations ----------
@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE)
def creer_prestation(request):
    initial = {}
    cat_id = request.GET.get("categorie")
    if cat_id:
        initial["categorie"] = cat_id
    if request.method == "POST":
        form = PrestationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("catalogue")
    else:
        form = PrestationForm(initial=initial)
    ctx = _contexte_parametres()
    ctx.update({"form": form, "titre": "Nouvelle prestation"})
    return render(request, "parametres/form.html", ctx)


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE)
def modifier_prestation(request, pk):
    p = get_object_or_404(PrestationCatalogue, pk=pk)
    if request.method == "POST":
        form = PrestationForm(request.POST, instance=p)
        if form.is_valid():
            form.save()
            return redirect("catalogue")
    else:
        form = PrestationForm(instance=p)
    ctx = _contexte_parametres()
    ctx.update({"form": form, "titre": "Modifier la prestation"})
    return render(request, "parametres/form.html", ctx)


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE)
def supprimer_prestation(request, pk):
    p = get_object_or_404(PrestationCatalogue, pk=pk)
    if request.method == "POST":
        p.delete()
    return redirect("catalogue")


# ---------- Variantes de prix ----------
@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE)
def creer_variante(request):
    initial = {}
    p_id = request.GET.get("prestation")
    if p_id:
        initial["prestation"] = p_id
    if request.method == "POST":
        form = VarianteForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("catalogue")
    else:
        form = VarianteForm(initial=initial)
    ctx = _contexte_parametres()
    ctx.update({"form": form, "titre": "Nouvelle variante de prix"})
    return render(request, "parametres/form.html", ctx)


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE)
def modifier_variante(request, pk):
    v = get_object_or_404(VariantePrix, pk=pk)
    if request.method == "POST":
        form = VarianteForm(request.POST, instance=v)
        if form.is_valid():
            form.save()
            return redirect("catalogue")
    else:
        form = VarianteForm(instance=v)
    ctx = _contexte_parametres()
    ctx.update({"form": form, "titre": "Modifier la variante"})
    return render(request, "parametres/form.html", ctx)


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE)
def supprimer_variante(request, pk):
    v = get_object_or_404(VariantePrix, pk=pk)
    if request.method == "POST":
        v.delete()
    return redirect("catalogue")


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE)
def parametres_email(request):
    params = ParametresEmail.get_solo()
    if request.method == "POST":
        form = EmailForm(request.POST, instance=params)
        if form.is_valid():
            form.save()
            return redirect("parametres_email")
    else:
        form = EmailForm(instance=params)
    ctx = _contexte_parametres()
    ctx.update({"form": form, "params": params})
    return render(request, "parametres/parametres_email.html", ctx)


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE)
def tester_email(request):
    from .emails import envoyer_email
    params = ParametresEmail.get_solo()
    ok, erreur = envoyer_email(
        [params.adresse_envoi],
        "Test — Cabinet Smart-Hub",
        "Ceci est un email de test envoyé depuis votre application Cabinet Smart-Hub. Si vous le recevez, la configuration fonctionne !",
    )
    if ok:
        messages.success(request, "Email de test envoyé ! Vérifiez votre boîte de réception.")
    else:
        messages.error(request, f"Échec de l'envoi : {erreur}")
    return redirect("parametres_email")


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE)
def parametres_cgv(request):
    cgv = ConditionsUtilisation.get_solo()
    if request.method == "POST":
        form = CGVForm(request.POST, instance=cgv)
        if form.is_valid():
            form.save()
            return redirect("parametres_cgv")
    else:
        form = CGVForm(instance=cgv)
    ctx = _contexte_parametres()
    ctx.update({"form": form, "cgv": cgv})
    return render(request, "parametres/parametres_cgv.html", ctx)
