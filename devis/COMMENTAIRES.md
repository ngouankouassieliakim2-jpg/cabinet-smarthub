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

### Wave — rappel opérationnel pour la mise en production
- [ ] Si la signature des requêtes est activée sur la clé API Wave, l'IP du
      serveur Hetzner de production devra être ajoutée à la liste blanche
      du portail Wave Business (section Développeur) — sinon les requêtes
      seront rejetées (403 ip-not-allowed). Configuration entièrement côté
      portail Wave, rien à coder ici.
- [ ] wave_signing_secret n'est affiché QU'UNE SEULE FOIS par Wave à la
      création de la clé — si perdu, il faut révoquer et recréer la clé,
      pas de récupération possible.

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

## Sous-module : Promesses de paiement — TERMINÉ (20/07/2026)

Pondération des créances avec promesse active pour les prévisions de trésorerie.
- [x] Modèle `PromessePaiement` ajouté, une seule promesse active par facture.
- [x] Formulaire de promesse ajouté sur la fiche facture.
- [x] Commande `devis:verifier_promesses` créée pour valider TENUE/ROMPUE
      automatiquement à la date promise.
- [ ] À noter : aucun envoi de notification sur promesse rompue/tenue pour l'instant.

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

## Sous-module : Dashboard exécutif — TERMINÉ (20/07/2026)

Réunit Recouvrement + Dépenses : total créances, échu/non échu, encaissé
aujourd'hui, litiges, promesses, taux recouvrement/impayés, DSO, ancienneté,
top clients à risque, encaissements mensuels, dépenses du mois, situation
budgétaire, validation dépenses, évolution annuelle et cash prévisionnel
pondéré.

### Décision actée
- [x] Accès restreint Direction/Cadre uniquement — cohérent avec le profil
      sensible des données affichées.
- [x] Aucune duplication : le fichier `dashboard.py` contient uniquement les
      indicateurs nouveaux qui n'existaient pas dans `kpi.py`, `kpi_depenses.py`
      ou `previsions.py`.
- [x] Le reste du dashboard réutilise les fonctions existantes du module
      `devis` plutôt que de recoder des KPI déjà définis.

---

## Sous-module : Automatisations — TERMINÉ (20/07/2026)

### Décision actée
- [x] Pas de reconstruction : 3 des 4 règles du doc de vision étaient déjà
      couvertes par les sous-modules précédents sans être nommées
      "Automatisations" — inventaire fait plutôt que dupliquer :
      - Paiement reçu → clôture auto : Facture.enregistrer_paiement()
      - Retard >60j → informer Direction : executer_relances (étapes J+45/J+60)
      - Facture en retard (bascule statut) : marquer_factures_en_retard
- [x] Journal des automatisations aligné sur le modèle réel
      `JournalExecutionCommande` : la vue et le template utilisent désormais
      les champs `commande`, `etat`, `resume` et `date_debut` (au lieu des
      anciens noms de champs supposés en amont), avec filtres et exports CSV/Excel.

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

### Correction (20/07/2026) — bug silencieux notifier_email
- [x] parametres.emails.envoyer_email attend une LISTE de destinataires, mais
      était importé directement sous l'alias notifier_email et appelé avec
      une simple chaîne (facture.client_email) dans detail_creance,
      detail_depense, valider_ou_rejeter_depense. Risque : email non envoyé
      silencieusement, ou tentative d'envoi caractère par caractère selon
      l'implémentation interne. Corrigé par un wrapper local dans
      devis/views.py qui transforme la chaîne en liste — aucun des 3 appels
      existants n'a eu besoin d'être modifié.
- [x] Créations de notifications devis mises à jour avec destinataire
      pertinent : dépense rejetée → soumise_par ; relance avec recouvreur
      affecté → recouvreur (reste générale si pas affecté). Alertes budget/
      contrat fournisseur restent générales (pas de destinataire évident).
- [ ] Point de vigilance pour la suite : bien vérifier la signature exacte
      d'une fonction partagée avant de l'aliaser directement — un alias
      masque les incompatibilités de signature jusqu'à l'exécution réelle.

## Sous-module : Gestion des promesses de paiement — TERMINÉ (20/07/2026)

PromessePaiement (une seule active à la fois par facture), vérification
automatique (verifier_promesses), intégrée à detail_creance et à la
pondération des prévisions de trésorerie.

### Résolu (dépendance levée, 3 endroits)
- [x] Créances : reporté depuis le début, résolu.
- [x] Calendrier de relances : pas d'intégration directe pour l'instant —
      une promesse active pourrait suspendre les relances automatiques,
      non fait ici (décision à prendre si jugé utile).
- [x] Prévisions de trésorerie : pondération 0.85 pour toute facture avec
      promesse active, au lieu de la seule pondération statistique par
      ancienneté. Valeur choisie par bon sens, pas mesurée — à ajuster une
      fois un historique de promesses tenues/rompues disponible pour
      calculer un vrai taux de fiabilité.

### Manques restants
- [ ] Pas de suspension des relances automatiques quand une promesse est
      active (une facture avec promesse continue de recevoir emails/
      notifications de relance comme si de rien n'était).
- [ ] Pas de notification quand une promesse est rompue — pourrait alerter
      le responsable ou la Direction (réutiliser pilotage.Notification avec
      destinataire=promesse.responsable, maintenant que ça existe).

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

## Sous-module : Dépenses — TERMINÉ (20/07/2026)

Corrigé le 20/07 : le statut "EN COURS" ne reflétait plus la réalité du
code — archivage, Kanban, recherche, export CSV/Excel, notes internes et
journal d'audit sont tous en place dans liste_depenses/detail_depense.

Dépenses fournisseurs : liste, création, détail de dépense, documents et
paiements associés. Le modèle `Depense` est en place, avec catégories,
statuts, montant HT/TVA, échéance automatique et historique de statut.

## Sous-module : KPI Dépenses — TERMINÉ (20/07/2026), ERP intégré dès la construction

7 indicateurs du doc de vision : par catégorie, par fournisseur, par
service, par collaborateur, évolution annuelle, dépassements budgétaires
(réutilise Budget), top fournisseurs. Filtre année, export CSV/Excel,
audit, 3 graphiques Chart.js.

### Décision actée — mapping "service"
- [x] "Dépenses par service" n'a pas de champ dédié sur Depense — mappé sur
      le pôle du collaborateur créateur (cree_par.profil.pole), réutilisant
      le module Direction déjà construit plutôt que d'ajouter un champ
      redondant. Dépenses sans créateur identifié ou sans pôle assigné
      groupées sous "Non renseigné". Approximation à valider avec Eliakim
      si un vrai champ "service" distinct s'avère nécessaire.

### Amélioration technique par rapport au pattern précédent
- [x] Toutes les agrégations utilisent values().annotate(Sum()) — vrai SQL,
      pas de boucle Python — possible ici car montant_ht est un champ
      stocké (pas une @property), contrairement à plusieurs KPI Recouvrement
      qui bouclaient en Python sur montant_ttc (property). Meilleure
      performance, même volume de données futures mieux supporté.

### Manque
- [x] Accès restreint Direction/Cadre uniquement, sans zone grise laissée
      ouverte cette fois (contrairement à Prévisions/KPI Recouvrement où la
      question était restée en suspens) — tranché directement car données
      encore plus sensibles ici (salaires indirects via dépenses par
      collaborateur).

### Ce qui est déjà construit
- [x] Liste des dépenses filtrable par statut et fournisseur.
- [x] Création de dépense avec calcul de date d'échéance selon le délai
      fournisseur.
- [x] Détail de dépense avec chargement des documents, paiements et
      historique de statuts.
- [x] Enregistrement de paiements de dépense, mise à jour automatique du
      statut `PAYEE` / `PARTIELLEMENT_PAYEE`.

### Résolu (dépendance levée)
- [x] 20/07/2026 — Seed de catégories de dépenses créé via la commande
      `seed_categories_depense`. La commande crée 14 catégories de base,
      avec sous-catégories pour certaines familles, et est instrumentée via
      `tracer_execution` comme les autres commandes d'automatisation.
      ⚠️ La catégorie "Salaires & Charges sociales" est présente avec une
      réserve métier : elle ne doit servir qu'à des cas exceptionnels hors
      circuit paie standard, afin d'éviter toute confusion ou double comptage.
      À confirmer avec Eliakim si elle doit rester en base ou être retirée.

### Manques restants
- [ ] Tableaux de bord dépenses / budget vs réel.
- [ ] Gestion des catégories de dépense (CRUD interne) plus complète.
- [ ] Workflow de validation interne / approbation des achats.
- [ ] Intégration des dépenses récurrentes dans un calendrier de trésorerie.

---

## Audit de cohérence code réel vs COMMENTAIRES.md (20/07/2026)

Ce fichier avait pris du retard sur plusieurs sous-modules déjà retrofités
en pratique mais encore marqués incomplets/non cochés. Relecture complète
du code (models.py, views.py, urls.py, forms.py, tous les fichiers
management/commands) faite ce jour — voir corrections ci-dessus.

### Manques réels confirmés par cet audit (à traiter)
- [ ] **Notes de frais** — retrofit ERP jamais fait (voir section dédiée
      plus haut). Priorité immédiate.
- [ ] **config_seuils_approbation** — toujours en lecture seule.
      SeuilApprobationForm existe (devis/forms.py) mais n'est utilisé nulle
      part dans la vue. Impossible de modifier les seuils sans passer par
      l'admin Django.
- [ ] **file_attente_validation** (Dépenses) — pas d'export CSV/Excel, pas
      de journaliser() sur la consultation de la file d'attente.
- [ ] **kanban_litiges** — n'appelle pas journaliser() sur la consultation,
      contrairement à liste_litiges qui le fait. Incohérence mineure à
      trancher : faut-il journaliser la consultation des vues Kanban en
      général (kanban_creances et kanban_depenses ont la même absence) ?
      Décision à prendre une fois pour toutes plutôt que sous-module par
      sous-module.
- [ ] **liste_creances** — calcule est_en_retard_affichage en boucle Python
      ALORS QUE _factures_avec_soldes() annote déjà en_retard via Case/When
      en SQL (ajout ultérieur non nettoyé). Redondant, pas un bug, mais à
      simplifier un jour (utiliser l'annotation SQL, retirer la boucle).

### Bugs corrigés lors de cet audit
- [x] journal_automatisations : vue et template réalignés sur le modèle
      réel JournalExecutionCommande (commande/etat/resume), qui avait
      divergé de la proposition initiale de Claude.
- [x] notifier_email : wrapper ajouté dans devis/views.py pour corriger
      l'incompatibilité de signature avec parametres.emails.envoyer_email
      (qui attend une liste, pas une chaîne) — voir entrée dédiée plus haut.

### Bonnes surprises confirmées (pas de action requise)
- [x] Le piège de template `{% if x in "A,B,C" %}` signalé à plusieurs
      reprises pendant la construction a bien été évité partout dans le
      code réel (peut_ouvrir_litige calculé en Python dans la vue, pas
      dans le template).
- [x] Budget.budget_disponible_pour() et Depense.save() gèrent en plus les
      dates passées en chaîne (isinstance(a_date, str)) — robustesse
      ajoutée au-delà de ce qui avait été demandé.
- [x] Des tests unitaires existent (devis/tests.py) couvrant validation de
      dépense, blocage de paiement avant validation, seed des seuils,
      génération de dépense récurrente (garde-fou anti-doublon), agrégation
      SQL des KPI dépenses, cycle de vie complet d'une note de frais — non
      demandés explicitement mais bonne pratique consolidée.

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

---

### Retrofit — Fournisseurs : TERMINÉ (20/07/2026)
- [x] Recherche (nom/NCC) + filtre notation + toggle actifs/inactifs +
      export CSV/Excel
- [x] Journal d'audit branché (ajout contrat, note, bascule actif, consultation)
- [x] Notes internes génériques (NoteInterne) — remplace l'usage du champ
      `notes` (TextField unique, écrasé à chaque modification) qui perdait
      l'historique. Le champ `notes` original reste en base pour
      compatibilité mais n'est plus la voie recommandée.
- [x] Alerte automatique contrats arrivant à échéance (30 jours) — nouvelle
      commande verifier_contrats_fournisseurs, réutilise pilotage.Notification
      (même limitation de diffusion large déjà documentée).

### Résolu (dépendance levée, deuxième fois)
- [x] Placeholder "historique achats disponible dès que Dépenses existe" —
      remplacé par les vraies valeurs total_achete/nombre_factures dans le
      template (la donnée existait déjà côté modèle depuis le retrofit
      Dépenses, seul le template n'avait pas été mis à jour).

### Décisions actées (exclusions volontaires)
- [x] Pas de nouveau champ `archive` — réutilise `actif` déjà existant
      (même rôle, pas de redondance).
- [x] Pas de Kanban/calendrier — pas de cycle de statuts sur un fournisseur.

---

### Prochain retrofit : Dépenses (entité centrale)
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
- [x] Créances — recherche/export/archivage/Kanban/notes internes/journalisation
- [x] Paiements (avoirs/remb./compensation) — journal_paiements : recherche,
      filtre type, export CSV/Excel, totaux, audit sur les 3 actions
- [x] Calendrier de relances — journal_relances + calendrier_relances :
      filtres, export, taux de succès
- [x] Litiges — liste_litiges + detail_litige : recherche, filtre statut,
      export, audit sur les actions (⚠️ kanban_litiges n'appelle pas
      journaliser() sur la consultation — voir manque ci-dessous)
- [x] Affectation des recouvreurs — journal_actions_recouvrement +
      affectation_masse : recherche, filtre, export
- [x] Prévisions de trésorerie — export, audit, graphiques Chart.js
- [x] KPI — tableau_kpi : export, audit, filtre année (graphiques
      volontairement renvoyés au Dashboard exécutif, décision actée)
- [x] Automatisations — journal_automatisations : filtres, export,
      aligné sur le modèle réel JournalExecutionCommande
- [x] Fournisseurs — recherche, filtre notation, export, notes, audit
- [x] Dépenses — liste_depenses + detail_depense : archive, Kanban,
      recherche, export, notes, audit (⚠️ statut à corriger de "EN COURS"
      à "TERMINÉ" plus bas dans ce fichier)

## Retrofit non fait — vrai manque identifié le 20/07/2026
- [ ] **Notes de frais** — AUCUNE des 13 capacités appliquée : pas de
      journaliser(), pas d'export CSV/Excel, pas de NoteInterne, aucune
      recherche/filtre sur liste_notes_de_frais/creer_note_de_frais/
      detail_note_de_frais. Construit après la discussion sur les 13
      capacités mais jamais retrofité — à faire en priorité.

## Restent bloqués/hors-scope, non concernés par ce retrofit
- [ ] API REST (DRF) — chantier à part entière, pas un ajout ponctuel par
      sous-module. À planifier séparément une fois plusieurs modules
      métier stabilisés.
- [ ] Droits par rôle "complets" — dépend du chantier Direction/Pôles déjà
      identifié comme prochain grand chantier. Ici on ne fera que des
      restrictions locales (Direction/Cadre), pas le système complet.
