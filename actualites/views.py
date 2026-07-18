from django.shortcuts import render, get_object_or_404

from .models import Article


def liste_articles(request):
    """Page Actualités : liste des articles publiés."""
    articles = Article.objects.filter(publie=True)
    return render(request, "actualites/liste.html", {"articles": articles})


def detail_article(request, article_id):
    """Page de détail d'un article."""
    article = get_object_or_404(Article, id=article_id, publie=True)
    return render(request, "actualites/detail.html", {"article": article})