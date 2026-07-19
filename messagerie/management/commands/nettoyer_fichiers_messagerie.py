from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from messagerie.models import Message

DELAI_EXPIRATION_JOURS = 30
DELAI_RAPPEL_JOURS = 25


class Command(BaseCommand):
    help = "Envoie un rappel avant expiration, puis supprime les fichiers de messagerie trop anciens (le message texte reste)."

    def handle(self, *args, **options):
        maintenant = timezone.now()
        seuil_rappel = maintenant - timedelta(days=DELAI_RAPPEL_JOURS)
        seuil_suppression = maintenant - timedelta(days=DELAI_EXPIRATION_JOURS)

        a_rappeler = Message.objects.filter(
            envoye_le__lte=seuil_rappel, envoye_le__gt=seuil_suppression,
            rappel_expiration_envoye=False,
        ).exclude(fichier="")

        nb_rappels = 0
        for m in a_rappeler:
            jours_restants = DELAI_EXPIRATION_JOURS - (maintenant - m.envoye_le).days
            Message.objects.create(
                conversation=m.conversation,
                expediteur=None,
                texte=f"⚠️ Le fichier « {m.nom_fichier_original} » sera supprimé automatiquement dans {jours_restants} jours. Téléchargez-le si vous souhaitez le conserver.",
            )
            m.rappel_expiration_envoye = True
            m.save(update_fields=["rappel_expiration_envoye"])
            nb_rappels += 1

        a_supprimer = Message.objects.filter(envoye_le__lte=seuil_suppression).exclude(fichier="")
        nb_supprimes = 0
        for m in a_supprimer:
            m.fichier.delete(save=False)
            m.nom_fichier_original = f"{m.nom_fichier_original} (fichier expiré)"
            m.save(update_fields=["fichier", "nom_fichier_original"])
            nb_supprimes += 1

        self.stdout.write(f"{nb_rappels} rappel(s) envoyé(s) dans les conversations, {nb_supprimes} fichier(s) supprimé(s).")
