# Recouvrement & Dépenses — Suivi des manques

Règle : chaque sous-module se construit jusqu'à sa finition complète.
Si un manque dépend d'un autre sous-module pas encore fait, on le note
ici et on continue — on revient le régler une fois ce sous-module atteint.

### Règle de process (ajoutée 20/07/2026)
- Toujours coller les modèles AVANT les vues qui les importent. Si Copilot
  applique les fichiers dans un ordre différent de celui donné par Claude,
  vérifier avec `python manage.py makemigrations <app>` que "No changes
  detected" ne cache pas un modèle oublié — un ImportError au démarrage
  du serveur est souvent le symptôme, pas la cause.

---

## Sous-module : Gestion des créances — TERMINÉ (20/07/2026)

Statuts, historisation, paiements (versements multiples + trop-perçu signalé),
transitions contrôlées (dont statuts d'exception réservés Direction/Cadre),
vues liste + détail avec filtres, bascule automatique EN_RETARD via commande
de management. Migration appliquée.

## Sous-module : Paiements — TERMINÉ (20/07/2026)

Avoirs, remboursements et compensations pour traiter le trop-perçu.
- Avoirs enregistrés dans les créances avec contrôle de montant et mise à jour
du statut de la facture.
- Remboursements gérés via montant, mode et justificatif.
- Compensations appliquées vers une autre facture du même client.

### Signalé par Eliakim (20/07/2026) — à prendre en compte pour plus tard
- [ ] Intégration prévue : API Wave et API Orange Money pour paiements
      mobile money. Ces API permettraient un suivi des flux financiers sur
      les comptes cabinet — donc potentiellement une réconciliation
      automatique des paiements (webhook → Paiement/PaiementDepense créé ou
      confirmé automatiquement), sans saisie manuelle.
- [x] Préparation faite maintenant (sans construire l'intégration) : champs
      operateur_mobile_money, reference_transaction_externe,
      reconcilie_automatiquement ajoutés sur Paiement ET PaiementDepense.
      reconcilie_automatiquement volontairement absent des formulaires
      (réservé à une écriture programmatique future).
- [ ] Reste à faire quand les clés API seront disponibles : webhook de
      réception, mapping référence transaction → Facture/Depense, logique
      de rapprochement si le montant ne correspond pas exactement (paiement
      partiel via mobile money, frais opérateur déduits, etc. — question
      métier à trancher avec Eliakim à ce moment-là, pas maintenant).
- [ ] Ce chantier rejoint la même catégorie que FNE et WhatsApp Business :
      bloqué sur une dépendance externe (clé API), pas un problème de code.

### Remarques de conception
- Les avoirs ne sont pas encore certifiés FNE automatiquement.
- La compensation s'appuie sur le nom du client pour trouver les factures cibles.
  Cette logique est documentée comme dette technique.
- [ ] Affectation en masse des recouvreurs : implémentée côté SQL via `update()`.
  Audit matérialisé dans le journal, mais attention au fait que le callback `save()`
  n'est pas déclenché pour chaque facture individuelle.

### Résolu (dépendance levée)
- [x] 20/07/2026 — _notifier_interne() branché sur pilotage.models.Notification
      (get_or_create avec clé d'unicité par facture+étape).

### Limitation découverte, à trancher
- [ ] pilotage.Notification n'a AUCUN champ destinataire (pas de FK User, pas
      de rôle) — la cloche affiche vraisemblablement les notifications à TOUS
      les utilisateurs connectés, pas seulement Direction/Cadre. Donc
      NOTIFICATION_INTERNE, ESCALADE_DIRECTION et ALERTE_CONTENTIEUX sont
      visibles par tout le monde ayant accès à la cloche, pas ciblées.
      Deux options pour plus tard : (a) ajouter un champ destinataire/rôle à
      Notification (impacte aussi les notifications Paie existantes — à
      coordonner), ou (b) accepter la visibilité large pour l'instant (le
      titre "⚠️/🔴" suffit à indiquer la gravité). Décision à prendre avec
      Eliakim avant mise en production réelle du recouvrement.
- [ ] TYPE_CHOICES de Notification étendu avec 3 nouvelles valeurs
      (relance_notification_interne, relance_escalade_direction,
      relance_alerte_contentieux) — migration pilotage à appliquer.

## Sous-module : Calendrier de relances intelligent — TERMINÉ (20/07/2026)

Modèles EtapeRelance/Relance, seed des 6 étapes par défaut, commande
executer_relances (garde-fou anti-doublon), notifications internes branchées
sur pilotage.Notification, écran de configuration (édition inline, Direction/
Cadre uniquement).

## Sous-module : Prévisions de trésorerie — TERMINÉ (20/07/2026)

Calcul dérivé (pas de modèle stocké) : encaissements attendus semaine/mois/
trimestre pondérés par ancienneté du retard, vieillissement des créances par
tranche (0-30/31-60/61-90/90+).

### Manques restants, reportés en connaissance de cause
- [ ] Pondération par ancienneté = estimation statistique grossière et
      provisoire (PONDERATION_PAR_RETARD dans previsions.py), en l'absence
      du sous-module "Promesses de paiement". À remplacer par une prévision
      basée sur les promesses déclarées dès que ce sous-module existe.
- [ ] Pas de courbe d'évolution des encaissements/impayés dans le temps —
      nécessiterait des snapshots réguliers (aucun historique de ce type
      stocké actuellement). Ce sous-module ne montre qu'une photo instantanée.
- [ ] Calcul agrégé en Python sur liste matérialisée (même pattern que
      liste_creances) — à repasser en SQL si le volume grossit.
- [ ] Pas de "Top 10 des débiteurs" ni de graphique — appartient plutôt au
      Dashboard exécutif (sous-module non démarré), pas dupliqué ici.

### Retrofit — Prévisions de trésorerie : TERMINÉ (20/07/2026)
- [x] Export CSV/Excel (photo actuelle : encaissements attendus + vieillissement)
- [x] Journal d'audit branché (consultation, export)
- [x] Graphiques ajoutés (Chart.js, via cdnjs déjà autorisé dans le projet) —
      2 histogrammes : encaissements attendus par période, vieillissement
      des créances. Comble en partie le manque "graphiques" du doc de
      vision original, MAIS reste une photo instantanée, pas une courbe
      dans le temps (voir manque ci-dessous, inchangé).

### Décisions actées (exclusions volontaires)
- [x] Pas de Kanban/calendrier/NoteInterne/archivage — pas d'entités
      individuelles sur cette vue agrégée, ces capacités n'ont pas de sens ici.
- [x] Pas de filtre par client — vue volontairement macro ; la décomposition
      par client existe déjà via KPI "clients à risque".

### Manque non tranché — décision métier à prendre
- [ ] Droits d'accès : vue exposant l'exposition financière globale du
      cabinet, actuellement ouverte à tout collaborateur du sous-module —
      à restreindre Direction/Cadre ou non ? Non tranché unilatéralement.

---

## Sous-module : Automatisations — TERMINÉ (20/07/2026)

### Décision actée
- [x] Pas de reconstruction : 3 des 4 règles du doc de vision étaient déjà
      couvertes par les sous-modules précédents sans être nommées
      "Automatisations" — inventaire fait plutôt que dupliquer :
      - Paiement reçu → clôture auto : Facture.enregistrer_paiement()
      - Retard >60j → informer Direction : executer_relances (étapes J+45/J+60)
      - Facture en retard (bascule statut) : marquer_factures_en_retard

### Bloqué (dépendance externe au recouvrement)
- [ ] "Facture >30j → créer tâche" : commande verifier_automatisations créée
      mais NE CRÉE RIEN — signale seulement en sortie console (log cron).
      Bloqué sur l'absence du module Tâches (jamais démarré, cf. mémoire
      projet : "Module Tâches complet — choisi explicitement, jamais repris").
      Point d'accroche laissé en commentaire TODO dans le fichier, prêt à
      activer dès que le module Tâches existe.
- [ ] Décision volontairement écartée : ne PAS détourner pilotage.Notification
      pour simuler une tâche (notification = éphémère/lue, tâche = cycle de
      vie propre avec assignation/échéance/clôture — les mélanger créerait
      de la dette technique).

---

## Sous-module : KPI — TERMINÉ (20/07/2026)

Délai moyen de paiement (12 mois glissants), taux d'impayés, taux de
recouvrement, créances par ancienneté (réutilise previsions.py), clients à
risque, encaissements mensuels.

### Manques restants
- [ ] clients_a_risque() groupe par client_nom (texte) — même limitation
      déjà documentée (Compensation, Affectation des recouvreurs) : pas de
      FK Facture → Client.
- [ ] Pas de graphiques (courbes/histogrammes) — les KPI restent tabulaires
      ici ; les graphiques seront centralisés au Dashboard exécutif pour
      éviter de fragmenter la lib de charts sur plusieurs sous-modules.
- [ ] delai_moyen_paiement() ignore les factures soldées uniquement par avoir/
      compensation (pas de ligne Paiement associée) — délai non calculable
      dans ce cas, choix assumé plutôt qu'une approximation trompeuse.

### Point transversal consolidé (concerne plusieurs sous-modules)
- [ ] Plusieurs calculs (liste_creances, previsions, kpi) itèrent en Python
      sur des querysets plutôt que d'agréger en SQL — acceptable au volume
      actuel. À surveiller globalement si le nombre de factures grossit
      significativement, plutôt qu'à corriger sous-module par sous-module.

---

# DÉPENSES

## Sous-module : Fournisseurs — TERMINÉ (20/07/2026)

Fournisseur (base référentielle) + ContratFournisseur. CRUD complet
(liste/recherche, création, modification, détail).

### Décision actée
- [x] Construit dans l'app `devis` (pas de nouvelle app) — cohérent avec la
      dette déjà connue ("devis = container Recouvrement + Dépenses"), à
      nettoyer en polissage plus tard, pas pendant le build.
- [x] "Tableau de bord Dépenses" volontairement PAS fait en premier — même
      raisonnement que pour Recouvrement (dashboard sans données réelles pas
      utile en premier). Fournisseurs choisi comme premier sous-module car
      c'est une dépendance du sous-module suivant (Dépenses).

### Manques dépendant d'un autre sous-module
- [ ] Historique achats / total acheté / factures liées : pas encore
      calculable, aucune Dépense n'existe encore en base. Propriétés à
      ajouter sur Fournisseur (@property, pas de champ stocké dupliqué) dès
      que le sous-module "Dépenses" (le suivant) est construit.

---

## Sous-module : Dépenses — EN COURS (20/07/2026)

Dépenses fournisseurs : liste, création, détail de dépense, documents et
paiements associés. Le modèle `Depense` est en place, avec catégories,
statuts, montant HT/TVA, échéance automatique et historique de statut.

### Ce qui est déjà construit
- [x] Liste des dépenses filtrable par statut et fournisseur.
- [x] Création de dépense avec calcul de date d'échéance selon le délai
      fournisseur.
- [x] Détail de dépense avec chargement des documents, paiements et
      historique de statuts.
- [x] Enregistrement de paiements de dépense, mise à jour automatique du
      statut `PAYEE` / `PARTIELLEMENT_PAYEE`.

### Manques restants
- [ ] Tableaux de bord dépenses / budget vs réel.
- [ ] Gestion des catégories de dépense (CRUD interne) plus complète.
- [ ] Workflow de validation interne / approbation des achats.
- [ ] Intégration des dépenses récurrentes dans un calendrier de trésorerie.

---

## Sous-module suivant : Dashboard exécutif (DERNIER du module Recouvrement)
(pas encore démarré — agrège les KPI, prévisions, ancienneté déjà construits
+ graphiques. Décision déjà actée avec Eliakim : délibérément repoussé en
dernier, un dashboard sans données réelles n'étant pas utile à construire
en premier.)

### Manques restants, reportés en connaissance de cause
- [ ] _generer_lettre_pdf() toujours un placeholder — dépend du gabarit PDF
      et du logo configurable (Paramètres, 🔴).
- [ ] pilotage.Notification sans champ destinataire — notifications visibles
      par tous, pas ciblées Direction. Décision à prendre avant mise en
      production réelle (voir détail dans l'entrée précédente du fichier).
- [ ] Pas encore branché sur un cron dédié — à ajouter à côté de
      marquer_factures_en_retard.
- [ ] Écran de config n'permet pas d'ajouter de nouvelles étapes (extra=0,
      volontaire pour l'instant) — seulement éditer les 6 étapes standard.
- [ ] Lien "Configuration des relances" visible dans la sidebar même pour les
      collaborateurs sans les droits (PermissionDenied bloque l'accès mais
      pas l'affichage du lien) — cohérent avec la limite connue "sécurité
      actuelle = affichage seulement", pas un bug propre à ce sous-module.
- [x] Rattachement recouvreur / affectation des recouvreurs démarré.

---

## Sous-module suivant : Litiges
(pas encore démarré)
- [ ] Sécurité : restriction Direction/Cadre sur les transitions sensibles
      appliquée seulement côté formulaire + validation dans clean_nouveau_statut().
- [ ] Recherche de facture de compensation basée sur nom client, pas sur une FK.
- [ ] Aucun workflow d'annulation ou d'ajustement des avoirs/compensations déjà enregistrés.

### Manques restants, reportés en connaissance de cause
- [ ] CONTESTEE/EN_LITIGE : pas de dossier structuré (pièces jointes dédiées)
      → sous-module "Litiges".
- [ ] Pas de rattachement recouvreur/portefeuille → sous-module "Affectation
      des recouvreurs".
- [ ] Pas de relance automatique (J+3...J+60) → sous-module "Calendrier de
      relances intelligent". La commande marquer_factures_en_retard ne fait
      que changer le statut, aucune notification/email n'est envoyé.
- [ ] Totaux du tableau liste calculés en Python (sum() sur liste matérialisée)
      — à repasser en agrégation SQL si le volume de créances grossit.
- [ ] Sécurité : restriction Direction/Cadre sur les transitions sensibles
      appliquée seulement côté formulaire (choix affichés) + validation dans
      clean_nouveau_statut(). Cohérent avec le niveau de sécurité actuel du
      projet (affichage uniquement, pas de vraie barrière serveur par URL) —
      à revoir en même temps que le chantier Sécurité niveau 2.

---

## Sous-modules pas encore démarrés
(seront listés ici avec leurs propres manques au fur et à mesure)
- Paiements
- Calendrier de relances intelligent
- Gestion des promesses de paiement
- Litiges
- Affectation des recouvreurs
- Prévisions de trésorerie
- Automatisations
- Dashboard exécutif

# CAPACITÉS TRANSVERSALES ERP (13 points) — retrofit en cours (20/07/2026)

Décision d'Eliakim : application locale à chaque sous-module, en rouvrant
les sous-modules déjà clos. Fondations construites une seule fois (app
`core`), puis branchées sous-module par sous-module.

## Fondations — TERMINÉ
- [x] JournalAudit (générique, qui/quand/depuis où) — app core
- [x] NoteInterne (générique, remplace la duplication future) — app core.
      CommentaireLitige laissé tel quel pour l'instant, pas migré.
- [x] Export CSV/Excel générique (core/exports.py)
- [x] Notification email générique (core/notifications.py)

## Décisions actées
- [x] Pas de middleware d'audit global — trop bruyant. Journalisation
      explicite (journaliser()) dans chaque vue sur les actions notables.
- [x] Pas d'export PDF générique — réutilise le moteur Weasyprint existant
      (déjà utilisé côté Paie), construit au cas par cas par sous-module
      pour garder une mise en page propre.
- [x] WhatsApp notifications : bloqué, dépend de l'inscription WhatsApp
      Business Meta (statut inconnu, démarche à lancer par Eliakim).

## À faire — retrofit sous-module par sous-module (dans l'ordre de
construction initial) :
- [x] Créances — recherche/export/archivage/Kanban/notes internes/journalisation ajouté(e)
- [ ] Paiements (avoirs/remb./compensation)
- [ ] Calendrier de relances
- [ ] Litiges
- [ ] Affectation des recouvreurs
- [ ] Prévisions de trésorerie
- [ ] KPI
- [ ] Automatisations
- [ ] Fournisseurs
- [ ] Dépenses

Pour chacun, checklist appliquée (seulement ce qui est pertinent) :
dashboard+KPI+graphique / recherche+filtres avancés / vues multiples
(Kanban, calendrier si pertinent) / journal d'audit branché / notes
internes génériques / notifications email / exports / droits par rôle
affinés / archivage.

## Restent bloqués/hors-scope, non concernés par ce retrofit
- [ ] API REST (DRF) — chantier à part entière, pas un ajout ponctuel par
      sous-module. À planifier séparément une fois plusieurs modules
      métier stabilisés.
- [ ] Droits par rôle "complets" — dépend du chantier Direction/Pôles déjà
      identifié comme prochain grand chantier. Ici on ne fera que des
      restrictions locales (Direction/Cadre), pas le système complet.
