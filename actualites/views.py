from django.contrib import messages
from django.forms import modelform_factory
from django.shortcuts import render, get_object_or_404, redirect

from comptes.decorators import role_requis
from comptes.models import Profil
from pilotage.modules_data import charger_sous_modules, get_module_info

from .models import Article

ArticleForm = modelform_factory(Article, fields=[
    "titre", "image", "contenu", "lien_video", "date_publication", "publie",
])


def _contexte_actualites(request):
    return {
        "module_actif": get_module_info("marketing"),
        "sous_modules": charger_sous_modules("actualites", request),
    }


def liste_articles(request):
    """Page Actualités : liste des articles publiés."""
    articles = Article.objects.filter(publie=True)
    return render(request, "actualites/liste.html", {"articles": articles})


def detail_article(request, article_id):
    """Page de détail d'un article."""
    article = get_object_or_404(Article, id=article_id, publie=True)
    return render(request, "actualites/detail.html", {"article": article})


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def articles_liste_interne(request):
    """Vue interne : tous les articles (publiés + brouillons), pour la gestion."""
    articles = Article.objects.all()
    ctx = _contexte_actualites(request)
    ctx.update({"articles": articles})
    return render(request, "actualites/articles_liste_interne.html", ctx)


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def article_creer(request):
    if request.method == "POST":
        form = ArticleForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Article créé.")
            return redirect("articles_liste_interne")
    else:
        form = ArticleForm()
    ctx = _contexte_actualites(request)
    ctx.update({"form": form, "titre_page": "Nouvel article"})
    return render(request, "actualites/article_form.html", ctx)


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def article_modifier(request, article_id):
    article = get_object_or_404(Article, id=article_id)
    if request.method == "POST":
        form = ArticleForm(request.POST, request.FILES, instance=article)
        if form.is_valid():
            form.save()
            messages.success(request, "Article mis à jour.")
            return redirect("articles_liste_interne")
    else:
        form = ArticleForm(instance=article)
    ctx = _contexte_actualites(request)
    ctx.update({"form": form, "titre_page": f"Modifier : {article.titre}", "article": article})
    return render(request, "actualites/article_form.html", ctx)


@role_requis(Profil.Role.DIRECTION, Profil.Role.CADRE, Profil.Role.COLLABORATEUR)
def article_supprimer(request, article_id):
    article = get_object_or_404(Article, id=article_id)
    if request.method == "POST":
        article.delete()
        messages.success(request, "Article supprimé.")
    return redirect("articles_liste_interne")
