# COMPTA-LIASSE — ARCHITECTURE & PLAN DE RÉALISATION
### Automatisation du remplissage des liasses fiscales DGI (module Comptabilité — Cabinet Smart-Hub)

> Document de référence. À recoller en début de session pour remettre une nouvelle instance à niveau.
> Régime cible de la 1re version : **NO (Système Normal)**. Les 6 autres régimes viennent après (données uniquement).

---

## 0. Objectif

Remplir automatiquement la liasse fiscale d'une entreprise à partir de sa **balance comptable**, avec toute la **logique comptable SYSCOHADA révisé**, pour que l'utilisateur fournisse **beaucoup moins d'effort qu'avec les fichiers Excel**. La cible finale est le dépôt sur **e-impôts** (DGI Côte d'Ivoire).

Principe non négociable : **chaque montant des états de synthèse doit être justifié par sa note annexe.**

---

## 1. État de l'existant (app `comptabilite`)

L'ossature est **déjà en place** et bien conçue. Ce chantier = compléter + une correction de fond, pas reconstruire.

**Modèles présents :**
- `Balance` (client, exercice, `regime_liasse` — NO, MT, BA, SGI, MF, AV, AN) + `LigneBalance` (compte, libellé, `solde_initial` N-1, `mouvement_debit`, `mouvement_credit`, `solde_final` N) → la **balance importée**.
- `CompteSyscohada` : plan comptable référentiel — **peuplé complet : 1398 comptes** (2 ch. : 84, 3 ch. : 427, 4 ch. : 873, 5 ch. : 14).
- `NoteAnnexeDefinition` : table maître des notes officielles — **77 pour le régime NO** (5 états financiers, 9 identification, 51 notes SYSCOHADA, 12 suppléments DGI). Les 6 autres régimes = vides.
- `LigneNote` : la **table de correspondance** compte → ligne de note (avec `ref_dgi` et `cellule_dgi`). Schéma : `regime_liasse, code_note, libelle_ligne, ref_dgi, cellule_dgi, prefixe_comptes, source, ordre`.
- `AjustementNote` : corrections manuelles **résiduelles**, appliquées PAR-DESSUS le calcul automatique (fait pour ce que la balance ne contient pas).
- `LigneImmobilisation` : fiches d'immo individuelles (alimentent SUPPL4, affinent NOTE 3A/3C/3D).

**Code présent :**
- `moteur.py` : rattachement compte → racine → note par **préfixe le plus long**, agrégation dans `cellule_dgi`, ajustements résiduels, prorata NOTE 3C, détection des comptes inconnus, génération de la liasse.
- `export_liasse.py` : écrit les valeurs dans une **copie du .xlsm officiel DGI** (sans toucher aux cellules-formules). C'est la bonne stratégie : on réutilise le **générateur XML** du fichier officiel (voir §12).
- Migrations qui peuplent : plan (0002), notes maître (0003/0005), lignenote **pilotes** (0006), comp-charges (0008).

**Ce qui MANQUE (le travail réel) :**
- **Couverture** : seuls **5 onglets sur 77** sont mappés (COMP-CHARGES, NOTE 3A, NOTE 3C, NOTE 4, NOTE 5). Le **BILAN, l'ACTIF, le PASSIF, le RESULTAT, le TFT ont zéro mapping.**
- **Signes** : `LigneNote` n'a ni `signe` ni `sens` → le bilan est impossible à remplir correctement (voir §3-§4).
- **Câblage** : `views.py` et `admin.py` sont vides → aucun écran (import, génération, contrôles, archivage).
- **Importateur de balance** : pas de parseur (une seule balance test de 5 lignes en base).

---

## 2. Structure de la liasse officielle (.xlsm, régime NO)

- **85 feuilles.** Machinerie XML (`Referentiels`, `Export XML`, `champs fixes`, `champs variables`) + couverture/recevabilité + états (BILAN, ACTIF, PASSIF, RESULTAT, TFT) + FICHE R1-R4 + NOTE 1 à 39 + suppléments DGI.
- **ACTIF / PASSIF sont en lecture seule** : ils recopient l'onglet **BILAN**. Le BILAN est la feuille de saisie.
- **Le BILAN fait les sous-totaux et totaux (formules), mais PAS l'agrégation compte → poste.** L'utilisateur tape aujourd'hui les montants agrégés à la main. **C'est exactement ce travail que le système automatise.**
- Codes de poste stables : actif `AD…BZ`, passif `CA…DZ`. L'actif a **3 colonnes** : Brut (F), Amort/Dépréc. (G), Net (H = F−G, formule).
- La colonne NOTE du bilan porte le **renvoi de chaque poste vers sa note** (AD→3, BB→6, BI→7, DJ→17, DK→18…). L'articulation est dans le format DGI.
- `champs fixes` = dictionnaire **cellule → code champ DGI** (`NO_ACTIF_…`, etc.) : **4291 champs** (ACTIF 120, PASSIF 56, RESULTAT 84, TFT 52 + toutes les notes). C'est la spec du XML e-impôts.
- La **RECEVABILITÉ** liste les notes applicables (A / N/A) par entité.

---

## 3. Principe fondateur : articulation notes ↔ synthèse

**Chaque poste des états de synthèse EST le total net de sa note annexe.** Confirmé par le guide d'application :
- NOTE 6 STOCKS → « TOTAL NET DE DÉPRÉCIATION » → poste **BB Stocks**.
- NOTE 7 CLIENTS → « TOTAL NET » → poste **BI Clients**.

**Conséquence de conception → on construit NOTE-FIRST :**
`compte → ligne de note → total de note → poste de synthèse`. Ainsi chaque montant du bilan/CR est justifié **par construction**.

**Cascade du compte de résultat** : les soldes intermédiaires (Marge, **Valeur Ajoutée**, EBE, Résultat d'exploitation, Résultat financier, RAO, RHAO, Résultat net) sont **calculés** à partir de comptes précis, pas recopiés.

---

## 4. La logique de calcul (moteur) — VALIDÉE sur une vraie balance

Testé sur la **Pharmacie de Tiémélékro** (balance Sage réelle) : reconstruction à **Actif net = Passif = 22 259 676** et **Résultat = −465 068**, au franc près.

**Règles du moteur :**
1. **Solde signé par compte** : débit = +, crédit = −. C'est la convention interne (l'importateur normalise vers ça).
2. **Rattachement compte → ligne** par **préfixe le plus long**, MAIS filtré par `sens` **dès la sélection** (pas après). Sinon les comptes à **double sens** tombent dans le vide — c'est le bug qu'on a attrapé sur le découvert bancaire (52 créditeur qui matchait « trésorerie-actif » puis était rejeté).
3. **Application du `signe`** : **+1 côté actif** (présentation débit-positif), **−1 côté passif** (présentation crédit-positif). Le **± du report à nouveau et du résultat émerge tout seul** (131 bénéfice → +, 139 perte → −). C'est la réponse à l'exemple du 129/139.
4. **Colonne Amort/Dépréc. (G)** : comptes 28/29/39/49/59, `sens=créditeur`, `signe=−1` pour les rendre positifs (le Net H = F−G est une formule du fichier).
5. **Résultat CALCULÉ** = − (somme des soldes signés classe 6/7/8). Pas lu d'un compte 13.
6. **Ajustements résiduels** (`AjustementNote`) appliqués par-dessus.

**Cas concrets validés (Pharmacie) :**

| Poste | Comptes | Sens | Signe | Montant |
|---|---|---|---|---|
| CA Capital | 101 | * | −1 | 5 000 000 |
| CJ Résultat (perte) | classe 6/7/8 (calculé) | — | — | −465 068 |
| DJ Fournisseurs | 401 | créditeur | −1 | 10 760 829 |
| DR Trésorerie-passif (découvert) | 52 | créditeur | −1 | 20 242 |
| AI brut (col F) | 22/23/24 | débiteur | +1 | 2 462 000 |
| AI amort (col G) | 28 | créditeur | −1 | 615 500 |
| BI Clients | 411 | débiteur | +1 | 4 803 486 |
| BB Stocks | 31 | débiteur | +1 | 14 973 380 |

---

## 5. Les deux champs à ajouter à `LigneNote`

- **`signe`** : `+1` (actif) / `−1` (passif).
- **`sens`** : `les_deux` / `debiteur` / `crediteur`.

**Migration non destructive** : défauts `signe=+1`, `sens=les_deux` → reproduit le comportement actuel, les 5 notes déjà mappées ne cassent pas.

⚠️ Point de vigilance : une fois la convention « solde signé » posée, vérifier que les lignes pilotes existantes qui lisent des comptes créditeurs (ex. amort. de NOTE 3C) reçoivent bien `signe=−1`. À traiter en même temps que le patch moteur.

---

## 6. Une note = deux sources de données

- **Part que la balance donne** : les totaux par groupe de comptes → via `LigneNote`.
- **Part que la balance NE donne PAS** : ventilation par échéance (NOTE 7), réévaluations (NOTE 3E), détail des dépréciations, fiches d'immo, notes en texte libre (NOTE 1, 34, 35, engagements) → via `AjustementNote` (résiduel) et `LigneImmobilisation`.

---

## 7. Report N/N-1 & continuité (persistance des liasses)

**Nouveau modèle : une liasse persistante par exercice** (entreprise + année + régime), avec un **statut** et un **lien vers la liasse de l'année précédente**.

**Le N-1 a trois sources :**
1. **Reporté automatiquement** (continuité) : liasse 2023 validée → son N devient le N-1 de 2024, sans ressaisie.
2. **Pré-rempli depuis le solde initial** : le solde initial d'une balance = la clôture de l'année précédente = le **bilan N-1**. Donc **même en cas de trou**, le bilan N-1 se remplit tout seul.
3. **Saisi à la main** : en cas de **trou** (ex. on fait 2025 sans avoir 2024) ou de **première année dans le système**, le **compte de résultat N-1 et le détail des notes N-1** sont saisis manuellement (les comptes de gestion repartent de zéro, la balance ne les reporte pas).

**Contrôle de cohérence** : en continuité, le solde initial N doit coïncider avec le bilan N validé de l'année précédente (à-nouveaux = clôture N-1), sinon on signale une erreur d'à-nouveaux.

---

## 8. Infos entité — automatiser les FICHE R1/R2/R3

La liasse réclame : NCC, NTD, RCCM + greffe + IDU, N° caisse sociale (CNPS), forme juridique (code), régime fiscal (code), activité (désignation + code nomenclature note 36), pays du siège, nombre d'établissements, exercice du/au + durée, professionnel signataire (codes ZA…ZQ, ZX…ZZ4).

**Le modèle `Client` a déjà** : nom/raison sociale, NCC, téléphone, email, ville/commune/quartier, logo, slogan, utilisateur principal, gestionnaire.

**À AJOUTER au `Client`** : NTD, RCCM + greffe + IDU, N° caisse sociale, forme juridique (code), régime fiscal (code), désignation + code d'activité (note 36), pays du siège, nombre d'établissements, boîte postale, adresse géographique complète.

**Vient d'ailleurs, sans ressaisie** : exercice (dates/durée) ← modèle `Exercice`/`Balance` ; identité cabinet + expert-comptable ← futur module **Paramètres « Infos cabinet »**.

→ Ces infos stables se saisissent **une fois par client**, puis se réinjectent chaque année.

---

## 9. Experts-comptables & certification

- **Registre des professionnels** enregistré une fois (nom, adresse, N° OEC…) et réutilisé.
- **Par liasse** : on choisit **le professionnel + son type d'intervention** :
  - **Attestation de visa** (expert-comptable), ou
  - **Commissariat aux comptes** (CAC).
- Ce choix commande la **page d'attestation/certification** et les **mentions du professionnel** dans les fiches d'identification (N° OEC, etc.). Les mentions diffèrent entre visa et CAC.

---

## 10. Archivage (SOUS-MODULE À PART ENTIÈRE)

Sous « États financiers », organisé par **entreprise → exercice**. Chaque exercice archivé contient **DEUX pièces** :
- **Version Excel générée** par le système (le .xlsm rempli) — le **document de travail** — déposée **automatiquement** à la génération.
- **Version définitive e-impôts** — la **preuve officielle** — **uploadée à la main** après validation en ligne de l'expert + transmission DGI.

**Stockage en base** (portabilité au déploiement, comme l'archivage Paie), avec **règle de gel par année** : une fois la définitive déposée, l'exercice est **verrouillé** et rendu tel quel.

Lien **1-à-1** avec la liasse persistante : la liasse porte les **données** (les valeurs calculées qui servent au report N/N-1), l'archive porte les **fichiers**. (Option : garder aussi le XML transmis pour la traçabilité complète.)

**Cycle de vie d'une liasse :**
`Brouillon → Générée → Transmise (validée + envoyée DGI) → Archivée (définitive déposée, exercice verrouillé)`

C'est un exercice **Archivé** qui fait foi comme N-1 de référence.

---

## 11. Contrôles (écran rouge/vert AVANT génération)

Tant que tout n'est pas vert, on ne génère pas :
- **Actif = Passif**
- **Résultat bilan = Résultat CR**
- **Chaque poste = total de sa note** (articulation)
- **À-nouveaux N = clôture N-1** (continuité)
- **Balance équilibrée**
- **Arrondi FCFA** géré (arrondi à l'unité + gestion du franc d'écart)

---

## 12. Qualité de la balance à l'import

Contrôles dès l'import (cause n°1 d'un bilan déséquilibré) :
- **Balance équilibrée** (débit = crédit).
- **Comptes de fonctionnement TVA non soldés** (4431/4452…) : doivent être soldés à la clôture, sinon des montants disparaissent en silence. Constaté sur la Pharmacie (avec le fournisseur d'investissement 481).
- **Compte 13 mouvementé ?** → balance **après affectation** du résultat : ne PAS recompter le résultat depuis la classe 6/7/8. Détecter avant/après affectation.
- **Comptes inconnus non mappés** : affichés en évidence (le moteur les détecte déjà).
- **Checksum** : la somme lue doit égaler les **totaux imprimés** de la balance (attrape les erreurs de parsing : entêtes répétés, lignes « à reporter »…).

**Format de balance (Sage 100 constaté)** : colonnes `[à-nouveaux Déb/Créd] [mouvements Déb/Créd] [soldes cumulés Déb/Créd]`. L'importateur lit ces paires débit/crédit et calcule `solde_initial` et `solde_final` **signés**. Prévoir un import **tolérant avec écran d'aperçu** (les logiciels varient selon les clients).

---

## 13. La cible : XML e-impôts

- **v1 (retenue)** : on remplit le **.xlsm officiel** et on réutilise **son propre bouton « Générer le XML »** (les 4291 champs y sont déjà cartographiés). `export_liasse.py` fait déjà le remplissage.
- **v2 (bien plus tard)** : générer le XML **directement** via le dictionnaire `champs fixes`. Gros chantier — **ne pas le faire maintenant.**

---

## 14. Les écrans

1. **États financiers — liste des entreprises** : celles ayant déjà des liasses + **« Créer une entreprise »** (complète la fiche entité — §8) + **« Experts-comptables »** (registre — §9). *(À concevoir « conscient des droits » : Direction voit tout ; un collaborateur du pôle Compta/Fiscalité ne voit que ses dossiers — même sans coder les droits maintenant.)*
2. **Fiche entreprise** : liste des exercices (avec statut) + **« Exercice suivant »** (crée N+1, propose le report).
3. **Écran des infos (après import de la balance)** : identité entité si incomplète ; choix **expert + type (visa / CAC)** ; extras des notes (échéances, réévaluations… via `AjustementNote`) ; **N-1** (reporté si continuité, bilan N-1 pré-rempli depuis le solde initial, CR + notes N-1 à saisir si trou/1re année).
4. **Écran des contrôles** (§11) — rouge/vert avant génération.
5. **Brouillon éditable** : tableau poste + sa note + sa valeur, ajustable via `AjustementNote`, PUIS génération (pas de boîte noire).
6. **Archives** (§10) : entreprise → exercice → les deux pièces (consulter/télécharger).

---

## 15. Suggestions retenues (backlog)

**Fiabilité / temps gagné (prioritaire, solo) :**
- **Charger le mapping poste↔comptes depuis un Excel** (référentiel maintenu dans un classeur, avalé par le système) plutôt qu'en migrations — des centaines de lignes × 39 notes × 7 régimes, ingérable en migrations, et corrigeable sans redéployer.
- **Mémoriser la résolution des comptes inconnus, par client** : un sous-compte « maison » résolu une fois est déjà connu l'année suivante.
- **Garder les vraies liasses (Pharmacie + autre entreprise) comme cas de test de non-régression** : les rejouer à chaque enrichissement du mapping, vérifier qu'elles bouclent toujours (22 259 676).

**Justesse d'usage :**
- **Matrice des notes applicables (A / N/A)** par entité (comme la RECEVABILITÉ) — la Pharmacie n'a que 5-6 notes sur 39.
- **Gabarits réutilisables** pour les notes en texte libre (NOTE 1, 34, 35, engagements) — un modèle par client, repris chaque année.
- **TFT traité à part** (le plus piégeux) : se déduit des variations bilan N/N-1 + résultat + mouvements précis ; contrôle dédié (trésorerie finale TFT = trésorerie bilan) ; à placer après bilan et CR, avec un peu de saisie manuelle.
- **Revue analytique N/N-1** : mettre en évidence les gros écarts (%) — attrape les erreurs, c'est la revue de l'expert.

**Robustesse / long terme :**
- **Journal de traçabilité** (comme `MouvementPersonnel` en Paie) : qui a importé/validé/archivé, chaque ajustement manuel **justifié par un motif**.
- **Millésimer le référentiel** (par année/version DGI) : un vieil exercice se régénère avec les règles de son époque.
- **Backup/export des archives** (tout est en SQLite) — cohérent avec la portabilité au déploiement.

---

## 16. Séquence de réalisation (le plan de code)

**Méthode : une tranche verticale complète sur le régime NO, de bout en bout, avant de toucher aux 6 autres.**

1. **Migration** : `signe` + `sens` sur `LigneNote` (non destructive).
2. **Patch moteur** : solde signé + `sens` intégré à la sélection + `signe` + résultat calculé (+ corriger le `signe` des lignes pilotes créditrices).
3. **Mapping BILAN** (actif + passif) → **valider Actif = Passif = 22 259 676** sur la Pharmacie.
4. **Mapping RESULTAT** → valider Résultat = −465 068 **et** = résultat bilan.
5. **Mapping TFT** (avec son contrôle dédié).
6. **Notes une à une** (compte→note), avec `AjustementNote` pour les extras.
7. **Couche de contrôles d'articulation** (§11).
8. **Modèle `Client` étendu** (§8) → auto-remplissage FICHE R1/R2/R3.
9. **Persistance des liasses + report N/N-1** (§7) + registre experts + choix visa/CAC (§9).
10. **Sous-module Archives** (§10).
11. **Câblage écrans** (§14) + **importateur de balance** tolérant (§12).
12. **Les 6 autres régimes** = migrations de données uniquement, moteur inchangé.

**Prochaine action : étapes 1-2-3 d'un bloc** (migration + moteur patché + mapping BILAN), prêtes à tester sur la Pharmacie.

---

*Fin du document. Contraintes de travail : pas de pièces jointes fiables → code fourni en texte, fichiers complets. Django (`config`), SQLite, Tailwind CDN. Édition via Copilot, diagnostics/architecture via Claude.*
