"""Socle d'archivage des documents produits (Couche 1).
Règle de figement : on remplace tant qu'on est dans l'année civile de création ; figé ensuite."""
from django.utils import timezone


def archiver_document(employeur, type_doc, libelle, cle, contenu, nom_fichier,
                      content_type="application/pdf", employe=None, mois=None, annee=None):
    """
    Enregistre (ou met à jour) un document en archive.

    Règle :
      - Si un document de même 'cle' existe et a été créé CETTE année civile -> on REMPLACE son contenu.
      - Si un document de même 'cle' existe mais date d'une année ANTÉRIEURE -> il est FIGÉ :
        on ne le remplace pas. La fonction renvoie (document_existant, False, "fige").
      - Sinon -> on CRÉE une nouvelle archive.

    Renvoie un tuple : (document, cree_ou_remplace: bool, etat: str)
      etat = "cree" | "remplace" | "fige"
    """
    from .models import DocumentArchive

    annee_civile = timezone.now().year
    existant = DocumentArchive.objects.filter(employeur=employeur, cle=cle).first()

    if existant:
        if existant.annee_creation < annee_civile:
            # Document d'une année passée : figé, on ne touche pas.
            return existant, False, "fige"
        # Même année de création : on remplace le contenu.
        existant.libelle = libelle
        existant.contenu = contenu
        existant.nom_fichier = nom_fichier
        existant.content_type = content_type
        existant.employe = employe
        existant.mois = mois
        existant.annee = annee
        existant.save()
        return existant, True, "remplace"

    # Nouveau document
    doc = DocumentArchive.objects.create(
        employeur=employeur, employe=employe, type_doc=type_doc, libelle=libelle, cle=cle,
        contenu=contenu, nom_fichier=nom_fichier, content_type=content_type,
        mois=mois, annee=annee, annee_creation=annee_civile,
    )
    return doc, True, "cree"


def peut_produire(employeur, cle):
    """Indique si un document identifié par 'cle' peut être (re)produit, ou s'il est figé.
    Renvoie (autorise: bool, annee_creation_ou_None)."""
    from .models import DocumentArchive
    existant = DocumentArchive.objects.filter(employeur=employeur, cle=cle).first()
    if existant and existant.est_fige():
        return False, existant.annee_creation
    return True, (existant.annee_creation if existant else None)

from django.http import HttpResponse


def archiver_et_renvoyer(employeur, contenu, nom_fichier, content_type,
                         type_doc, libelle, cle, employe=None, mois=None, annee=None,
                         disposition="inline"):
    """Archive un document (si non figé) puis renvoie la réponse HTTP pour l'afficher/télécharger.
    Si le document est figé (année passée), on renvoie la version ARCHIVÉE au lieu d'en refaire une.
    disposition : "inline" (affichage navigateur) ou "attachment" (téléchargement forcé)."""
    doc, ok, etat = archiver_document(
        employeur, type_doc, libelle, cle, contenu, nom_fichier,
        content_type=content_type, employe=employe, mois=mois, annee=annee)

    if etat == "fige":
        # Document d'une année passée : on ressort l'archive figée, on ne régénère pas.
        contenu_a_envoyer = bytes(doc.contenu)
        nom = doc.nom_fichier
        ct = doc.content_type
    else:
        contenu_a_envoyer = contenu
        nom = nom_fichier
        ct = content_type

    response = HttpResponse(contenu_a_envoyer, content_type=ct)
    response["Content-Disposition"] = f'{disposition}; filename="{nom}"'
    return response