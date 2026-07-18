from django.db import models
from django.utils import timezone


class Article(models.Model):
    """Un article / actualité publié par le cabinet sur la Vitrine."""

    titre = models.CharField(max_length=200, verbose_name="Titre")
    image = models.ImageField(
        upload_to="actualites/",
        blank=True,
        null=True,
        verbose_name="Image de couverture",
        help_text="Photo principale de l'article (facultative).",
    )
    contenu = models.TextField(verbose_name="Contenu")
    lien_video = models.URLField(
        blank=True,
        verbose_name="Lien vidéo (YouTube, Facebook…)",
        help_text="Facultatif. Collez ici le lien d'une vidéo à afficher dans l'article.",
    )
    date_publication = models.DateTimeField(
        default=timezone.now,
        verbose_name="Date de publication",
    )
    publie = models.BooleanField(
        default=False,
        verbose_name="Publié",
        help_text="Cochez pour rendre l'article visible sur le site. Décoché = brouillon.",
    )

    class Meta:
        verbose_name = "Article"
        verbose_name_plural = "Articles"
        ordering = ["-date_publication"]  # les plus récents en premier

    def __str__(self):
        return self.titre