from contextlib import contextmanager
from datetime import datetime
import json
import traceback

from django.contrib.auth.models import User
from django.db import transaction

from .models import JournalExecutionCommande


@contextmanager
def tracer_execution(commande, description="", utilisateur=None, contexte=None, objet=None):
    """Enregistre automatiquement une exécution de commande management."""
    journal = JournalExecutionCommande.objects.create(
        commande=commande,
        description=description or "",
        utilisateur=utilisateur,
        contexte=contexte or {},
        objet=objet,
        etat="EN_COURS",
    )
    started_at = datetime.now()
    try:
        yield journal
        journal.etat = "SUCCES"
        journal.resume = getattr(journal, "resume", "") or "Commande exécutée avec succès"
        journal.date_fin = datetime.now()
        journal.duree_secondes = max(0, (journal.date_fin - started_at).total_seconds())
        journal.save(update_fields=["etat", "resume", "date_fin", "duree_secondes"])
    except Exception as exc:
        journal.etat = "ERREUR"
        journal.resume = str(exc)
        journal.erreur = traceback.format_exc()
        journal.date_fin = datetime.now()
        journal.duree_secondes = max(0, (journal.date_fin - started_at).total_seconds())
        journal.save(update_fields=["etat", "resume", "erreur", "date_fin", "duree_secondes"])
        raise
