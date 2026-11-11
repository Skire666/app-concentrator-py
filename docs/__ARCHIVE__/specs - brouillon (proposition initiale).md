TODO : Langue, cliquer sur une liste
pas de JSON5, faire un toml.
1000 taches pour le benchmark, et 100 pré-régalge de réveil.
Chauqe taches, à un historique de 10 (surtout pour les ccyclique)
Langue apr défaut = FR-FR
toml est save lorqu'une tache set créer, MAJ, 

rajoute les couleurs la prochaine fois.
définir enum
Theme sombre, them clair.

Dans les options, rendre la taille de police confiugrable
faire une taille de base. Prévoir 4 styles : normal, petit, grand+, grand+++

La hauteur des boutons, la faire un peu plus grande que ceux proposé.
Cooldown aussi lorque l'on clique (100ms c'est bien, mais un petit 120ms je pense que ça serait parfait)
Si la save échoue, mettre un bouton manuel qui retry

Bug : un compteur temps réel en seconde, n'était pas actualisé dans l'IHM
car le garbage collector perdait le pointeur, dans le compteur n'était plus décrémneter visuellement dans l'IHM (mais en mémoire c'était toujours ok)

Dans les réglages, il m'avait mis l'événement molette sur tous les contrôles, meme lorsqu'il n'était pas focus (un simple survol suffisait à "capter" la souris).
Du coup, quand je faisais l'usage de la molette, ça descendé parfois la page, mais si j'avais le mahleur d'avoir un compteur ou une liste, ça changé la valeur du composant, et du coup le scroll ne descendait pas la page. Genre pas besoin de clique, juste le survol suffisé à attraper le scroll.
Donc dans l'idée, je lui ai dit ne plus focus le composant.
Par contre, difficile d'avoir une règle général : toujours scroll page ?.
Typiquement, le menu principale, y'a pas de scroll écran, juste le tableau à l'intérieur. J'ai donc envie que le focus ce fasse sur le tableau, et on sur la page.

-------

Demander a claude d'économiser des tokens ?
NOTE PCO : en vrai, compliqué.
Si c'est planifié dès le début, c'est mieux.
Les tools pour aider (et ainsi gagner des tokens) :
- Lui dire de faire des skills en mode 'make-phase 1' et '/review-phase 1'
- faire des scripts aussi, comme le run des tests, comme ça il écrit moins de commande
- penser à rediriger toutes les sorties vers des fichiers et n'afficher que les problèmes (un ruiff, un coverage de test, c'est verbeux)

Dans chaque skill, définir des rôles et quel modèle fait quoi.
Quel modèle pour quelle phase, sur un projet Python :
- Haiku : formatage, docstrings, annotations de type, renommages, README/CHANGELOG, code répétitif, lancer et résumer les tests.
- Sonnet : implémenter une phase bien décrite, écrire les tests, refactor local.
- Opus : choix d’architecture, bug difficile qui touche plusieurs modules, phase encore floue.
- Si une phase confiée à Haiku échoue deux fois, refais-la avec Sonnet : les essais répétés coûtent plus que ce que tu économises.

# Ce que claude me propose :

L’idée est de dépenser le modèle cher une seule fois, au moment d’écrire le plan, puis de rédiger chaque phase assez précisément pour qu’un modèle moins cher puisse l’exécuter sans rien décider. Une phase vague confiée à Haiku finit en essais ratés et coûte plus cher que si tu l’avais donnée à Sonnet. Plus la phase est précise, moins le modèle qui l’exécute a besoin d’être fort.

## 1. Planifier avec Opus, une seule fois

Écris ou fais écrire le plan avec Opus en mode plan (opusplan le fait automatiquement), avec un effort high. C’est là que se prennent les décisions d’architecture, de découpage en modules et d’interfaces. Demande-lui aussi d’attribuer un modèle à chaque phase en justifiant son choix.

## 2. Séparer la décision de l’exécution

C’est le point le plus important. Ne découpe pas seulement par fonctionnalité, découpe aussi par difficulté. Une grosse phase « module de facturation » devient par exemple :

3a : concevoir les classes et les signatures (Opus, courte) ;
3b : implémenter selon ces signatures (Sonnet) ;
3c : docstrings, annotations de type, README (Haiku).

Le travail difficile reste ainsi petit et bien délimité, et la plus grosse partie du code est écrite par les modèles moins chers.

## 3. Rédiger chaque phase pour qu’elle se suffise à elle-même

Une phase ne doit pas dépendre de l’historique de la conversation. Elle doit pouvoir tourner dans un contexte vide. Voici un modèle de phase :

```
## Phase 4 — Export CSV des rapports
Modèle : sonnet · Effort : medium · Dépend de : phase 3

**Objectif** : exporter une liste de rapports en CSV.
**À lire d'abord** : src/rapports/models.py
**Périmètre** : créer src/rapports/export.py et tests/test_export.py. Ne rien modifier d'autre.
**Interface imposée** :
    def exporter_csv(rapports: list[Rapport], chemin: Path) -> int
**Terminé quand** :
- `pytest tests/test_export.py` passe
- `ruff check src/rapports` et `mypy src/rapports` ne signalent aucune erreur
**Si bloqué** : s'arrêter et expliquer, ne pas changer l'interface.
```

Trois éléments de ce modèle font la différence avec un modèle moins cher :

le périmètre explicite, qui empêche de toucher à d’autres fichiers ;
l’interface imposée, qui ne laisse aucune décision au modèle ;
des critères de fin vérifiables par une commande. Le modèle sait quand il a fini, et ton subagent testeur peut le vérifier.

La ligne « si bloqué » évite qu’un modèle moins capable improvise une décision d’architecture.

## 4. Choisir le modèle avec trois questions
Reste-t-il une décision à prendre dans cette phase ? Si oui, mets-la dans une phase Opus à part.
La phase dit-elle exactement quoi écrire et où ? Si oui, Sonnet suffit.
Est-ce une transformation mécanique, vérifiable par une commande ? Si oui, Haiku.

## 5. Écrire les tests tôt

Quand c’est possible, fais écrire les tests d’une phase dans la phase de conception (avec Sonnet ou Opus), avant l’implémentation. Les tests deviennent alors la spécification. Le modèle qui implémente, même moins cher, avance en les faisant passer, avec un critère de réussite clair.

## 6. Pendant l’exécution

/clear entre chaque phase. C’est l’économie la plus simple. Une longue conversation est renvoyée au modèle à chaque message, alors qu’une phase qui se suffit à elle-même n’a besoin d’aucun historique.
Un CLAUDE.md court avec ce qui ne change pas : les commandes (pytest, ruff, mypy), les conventions et l’arborescence. Les phases n’ont pas à le répéter. Il est chargé à chaque échange, donc garde-le concis.
Une règle d’escalade écrite dans le CLAUDE.md : après deux échecs, on passe au modèle du dessus. Si une phase révèle une décision qui n’était pas prévue, on s’arrête et on revient au plan.

Concrètement, ça donne : une session Opus pour produire PHASES.md selon ce modèle, puis pour chaque phase /clear suivi de /phase N (ou /phase-simple N), et le subagent testeur pour valider.

Si tu veux, je peux te préparer une commande /planifier (en model: opus) qui génère tes phases directement dans ce format, avec le modèle de chaque phase déjà choisi.

-------




Aide moi à planifier un futur projet que je veux développer.

Objectif :
- Développe la partie fonctionnelle ainsi que l'IHM.
- Challenger les propositions techniques et me dire les mauvais choix ou des alternatives meilleures.
- Rédiger le fichier AGENTS.md, tout en anglais, de moins de 850 lignes (ou moins de 45 000 caractères).
- Rédiger les spécifications, phase par phase
- Faire en plusieurs phase. Review entre chaque phase.
- Commencer par le minuteur, puis terminer pas le TODO list.

Pièce jointe :
- Il faut adapter les règles de "layer-violation" dans 'furryp.json' avec ce qui va suivre. Le fichier est issue d'un ancien projet (pour l'exemple), donc il faut l'adapter avec les nouvelles informations et refaire intégralement la règle.
- Je te donne aussi le fichier '.toml' à compléter.

Pour le dossier du projet : il est vide pour l'instant.
Indique moi l'étape minimale à suivre pour mettre en place le début.
Ensuite, Claude Code se chargera de coder le projet.

-------------------------------------------------
Objectif :
-------------------------------------------------

Faire une application, sur Windows 11.
Est codé en python 3.14, avec pyside6.
Pas de terminal. Tout en local.

Le projet est intégralement anglais, son code, ainsi que sa documentation.

-------------------------------------------------
But de l'application :
-------------------------------------------------

Lancement :
- Sans option au démarrage.
- La 1ère fois, cherche le fichier JSON5 de l'utilisateur, ou propose d'en créer 1 dans l'emplacement désiré (proposer aussi un défaut).
- Une seule instance de l’application. Pas de 2ème ouverture.

L'application est en 1 fenêtre :
- Une barre de module à gauche, de 100 pixels de large, contient les boutons vers les modules principaux. Occupe de haut en bas.
- En bas, pour tous les menus : une barre d'état d'1 ligne, indique la dernière sauvegarde. Un bouton pour changer de langue (FRA <-> ENG).
- Il y a 3 menus pour la zone principale :
--> Menu A) La zone 1 et 2, en un seul écran (soit 2 zones distinctes dans la même fenêtre)
--> Menu B) Journalisation (affiche le logging complet de l'application)
--> Menu C) Menu pour le réglage et les options disponibles

---------------------------
Menu A)
---------------------------

# Zone 1 :
-------------

La partie gauche de l'application (soit 70% de largeur environ) contiennent un gestionnaire de TODO list.

De haut en bas :

- En haut, il contient des onglets et qui servent à mettre des listes : Priorité + Nom + Description
- Dans une liste, il est possible de créer/modifier/supprimer une ou plusieurs tâches.
- Une tache est constituée d'un texte éditable, date d'échéance ponctuelle, récurrent (tous/toutes les semaines/mois/jours/ans, jour de la semaine, fin jamais/le/après X occurences), nombre d'occurences, historique des actions.
- Il est possible de manipuler les tâches sans les éditer : modifier l'état : terminer, archiver.
- Comportement particulier : Dans une tâche, il est possible de cliquer sur un chemin de dossier ou sur une URL, ce qui l'ouvre directement.
- Affichage par tableau, filtrage, recherche, etc...

# Zone 2 :
-------------

La partie de droite (soit 30%) de l'application contient un minuteur et des actions.

De haut en bas :

Un minuteur et ses boutons :
- Le minuteur est en heure, minute, seconde.
- La taille des caractères est de 64 pixels (ils sont grands)
- le minuteur démarre en un clic, sonne à zéro.
- Lorsque le minuteur est inactif ou stoppé : il y a 3 boutons -> "edit timer (actif)" + "reset (actif)", "start (actif)
- Lorsque le minuteur est lancé : il y a 3 boutons -> "edit timer (actif)", "reset (actif)", "paused (actif)"
- Lorsqu'il est terminé : il y a 3 boutons : "restart (actif)", "oK (actif)", "relancer dans 5min".
- éditer le minuteur permets : de choisir le son, le volume, et durée avant l'arrêt automatique, et s'il doit se relancer.
- pour l'alarme : il est possible de lire des mp3 de n'importe quelle taille, en boucle, X fois.
- Une alerte qui se déclenche même quand l'onglet est en arrière-plan (un son, une notification et le bouton qui clignote dans la barre des tâches).

Sous le minuteur :
Une liste de TODO rapide permet d'ajouter des actions à faire (TODO list temporaire, à piocher dans les TODO existant).
Cette TODO liste peut être alimenté par un bouton "spéciale" disponible sur chaque tâche.
Une fois la tache terminée (l'utilisateur change d'état), alors l'action est historisé. 

Sous la liste du TODO rapide :
- il y a une liste de favoris avec des minuteurs pré-réglé (15, 30, 45)
- Des options spécials permettent : de sonner toutes les heures

---------------------------
Menu B) 
---------------------------

Affiche le journal de tous les actions.
Possiblité de filtrer selon le niveau de log : info, warning, error, etc...

---------------------------
Menu C)
---------------------------

Option et réglage :
les champs sont éditables.

-------------------------------------------------
Organisation du dossier :
-------------------------------------------------

Dossier root : 'app-concentrator-py'

- Dossier 'concentrator' qui contient le code source
- Dossier 'tests' pour les tests unitaires
- Dossier 'scripts' pour lancer des scripts basiques (comme le nettoyage du projet, le build, etc...)
- Dossier 'docs' pour la documentation
- Dossier 'assets' (contient l'icone de l'apps, des fichiers mp3 pour les alarmes)
- Fichier 'AGENTS.md'
- Fichier 'CLAUDE.md'
- Fichier 'CONTRIBUTING.md'
- Fichier 'README.md'
- Fichier 'USAGE.md'
- Fichier 'LICENSE'
- Fichier 'pyproject.toml'

-------------------------------------------------
Outils et dépandances utilisés :
-------------------------------------------------

- uv
- ruff
- linter personnalisé qui se nomme 'furryp' et qui fonctionne comme ruff (exemple : 'furryp check .').
- python 3.14
- pyside6 (>=6.11)
- pydantic
- basedpyright en mode 'strict'
- pytest

Penser à ajouter :
- la capacité de lire un son mp3 (choisir un composant python populaire)
- lire/écrire des fichiers JSON5 (uniquement pour stocker les réglages utlisateurs)

-------------------------------------------------
Architecture :
-------------------------------------------------

- Prendre l'architecture hexagonale
- Stockage des fichiers : JSON5 pour le fonctionnel (utilisateur)
- Sépare bien le 'domain' des 'Use case' des adapteurs
- La view doit être en 3 partie :
--> 1) window (assemble les panels et les relie entre eux, sans logique propre)
--> 2) panel (compose des widgets et expose des signaux)
--> 3) widget (petit élément réutilisable, qu’on peut retrouver dans plusieurs panels)
- Pas de Qt dans 'domain/' ni 'application/', pense aux adaptateur UI

-------------------------------------------------
Développement
-------------------------------------------------

# Couvrir les généralités

- Description du projet.
- Structure et dossier
- Architecture
- layer, responsibility, rules
- Dependency Map : Importing layer, May import from, Must NEVER import from

# Environnement

- Environment & Installation (Windows 11, VS Code, uv)
- Build le projet (avec 'onedir' en options notamment)
- Nettoyer le projet

# Localisation

Possibilité de switch l'application entre FRA et ENG.
Gère l'internationalisation entre ses 2 langues.
Le changement de langue doit être temps réel.
Utilise des JSON normaux pour stocker la langue (pas d'élément compilé)

# Conception

Backend :
- Pour les données : Séparer les opérations d'écriture de la lecture (éviter de multiplier les responsabilités)
- Disposer d'opération comme : 'exist', 'create', 'read item', 'all items', 'update', 'find', 'delete', 'cp business = copie duppliquée', 'cp technical = copie exacte '
- Les entités métier doivent posséder un ID, date de création, date de modification
- Les données métiers doivent être validés par des '*Rules' pour valider si l'objet est conforme.
- La structure et la syntaxe par pydantic : L’adaptateur JSON5 attrape l’exception de pydantic tout de suite et la transforme en code d’erreur. NOTE : Pydantic doit être appliqué après la transformation de JSON5 en JSON.
- Une opération ne doit pas renvoyer une entité métier directement mais une classe 'DataResult' avec dedans un 'data' qui contient le résultat ainsi qu'un 'ValidationResult' qui contient le succès ou l'erreur. La 'ValidationResult' est tout le temps alimentée, même si 'data' est en erreur.
- la gestion des erreurs dans le backend doit remonter proprement avec un code d'erreur (éviter les exceptions et les string). Utiliser 'ValidationResult' ou 'DataResult' lorsqu'applicable.
- Pas d'exception sous silence (les attraper et les convertirs en code d'erreur si nécessaire).

Frontend :
- Threads : Privilégier les services synchrones. La fenêtre ne se fige pas.
- Côté IHM : garde les widgets « bêtes » et ainsi pouvoir tester la logique d’affichage sans ouvrir de fenêtre.
- Dans les formulaires des IHM, un état  'is_dirty' doit être disponible pour déterminer si l'utilisateur a modifié la donnée du formulaire.
- Toutes les actions qui recalcul l'IHM doivent se faire en 1 fois, et éviter de spam le rafraichissement. Il faut 1 point d'entrée clair et identifié.
- Toutes les actions, ou les cliques sur un bouton ont un cooldown de 100ms minimum. Et le bouton reste grisé tant que l'opération n'est pas terminée (cela évite les spamming des boutons).
- snapshot : objet qui décrit tout ce que la vue doit montrer à un instant donné. La vue ne lit pas directement le modèle ou la base de données : on lui donne un snapshot, et elle s’affiche à partir de lui.
- Chaque clique sur une bouton déclenchant une opération de plus de 200ms est loggué dans le logging à titre informatif.
- La validation des formulaires doit être en temps réel et proposer des erreurs inlines.
- Les réglages de l'utilisateur dans l'UX/UI, les tableaux, la largeur, les tries par défaut sont persisté d'une session à une autre.

# sauvegarder les donnés

Sauvegardes des données de l'utilisateur :
- Le minuteur, les TODO list de l'utilisateur, et ses réglages personnels, sont à sauvgarder dans un fichier JSON5, en oneshot.
- La sauvegarde se fait via un processu sécurisé : faire un temporaire vide, le finaliser (écriture en oneshot), renommer l'ancien et le backup, renommer le nouveau. Si crash, permettre la reprise du dernier fichier ou du dernier temporaire (si valide).
- Caractéristiques du fichier JSON5 (ne s'applique pas JSON) : Les retours à la ligne sont possibles (donc faire des tableau de lignes). Pouvoir stocker des chemins vers des dossiers windows (C:/…, D:/…, E:/…) ou bien des URLS (https://…). Les chemins sont toujours sur 1 seule ligne. A noter qu'ils sont écrient en clair dans l'IHM, puis transformé en JSON5 au niveu backend. L'objectif est d'avoir des chemins à plat, sans échappement (pour les chemins ou les URLs, remplacer les '\' par '/'), le tout dans un fichier JSON5. NOTE : JSON5 est lent et est seulement utilisé pour ce fichier, les autres JSON ne sont pas impactés (comme la langue FRA/ENG)
- Les éléments propres à QT uniquement (comme la position ou la taille de la fenêtre) doivent passer par QSettings avec un fichier '.ini'.

# Divers :
- les écritures passent par un seul thread de travail (pour éviter les problèmes de concurrence)
- Tous les Enums sont des 'int'. Tous les enums posséder à minima un état 'unset' (0) et 'unknown' (-1) en plus des autres valeurs
- Les règles métiers sont à ranger dans la couche métier. Les règles métiers sont des classes '*Rules' qui renvoient un 'ValidationResult'.
- Ajouter un 'ValidationResult' qui retourne le bilan de la vérification lorsque demandée. Il contient le bilan, la liste des 'ErrorCode' (si plusieurs erreurs par exemple) et des opérations pour savoir la liste, le niveau de severity ("critical, error, warning, success, skipped"), si c'est un succès avec warning, etc.
- Collections et tables : Lorqu'il est néccessaire d'avoir un tableau d'entité (exemple : client), alors il faut disposer d'une classe qui encapsule le tableau des entités (exemple : ClientsCollection). Ainsi, chaque entité possède son propre objet de collection dédié. Cela permet d'encapsuler la logique métier propre à ces groupes au même endroit.

# exemple pour la gestion des erreurs

- pydantic lève un ValidationError (contient la ou les erreurs).
- L’adaptateur l’attrape et écrit le détail technique dans le log.
- Il renvoie un 'DataResult' en échec : un élément par champ fautif, avec le code et le champ concerné
- L’utilisateur lit un message traduit, par exemple : « Le fichier de données est endommagé : titre invalide. Restaurer la dernière sauvegarde ? »

# journalisation

Logging : utiliser le module standard de `logging`

# chemin et valeurs par défaut.

Pour éviter les constantes codées en dur dans le code : il faut privilégier l'utilisation de constante issue du fichier '.ini' de l'application.
Le but étant de faciliter les problèmes de maintenance et éviter de redéployer systématiquement juste pour un chemin qui change.
Ne concerne que les variables système ou applicative et qui sont en dehors du périmètre fonctionnelle.

-------------------------------------------------
Règle de codage
-------------------------------------------------

- Respecter les conventions de nommages pour les fichiers
- Style général : **PEP 8** + **Docstrings** avec **Google style**
- Imposer l'odre des imports : tous les mettre en haut du fichier, avec standard lib, third party, puis first-party
- Interfaces avec le 'Protocol' Pattern
- Tous les enums sont suffixés '*Enum' et '*_enum.py'
- Principe SOLID
- Respecté l'orienté objet et l'encapsulation

# Vérification avant commit

```bash
uv run ruff format
uv run ruff check
uv run basedpyright
furryp check concentrator
uv run python -m unittest discover -s tests -t .
```

-------------------------------------------------
Tests
-------------------------------------------------

Produire les tests dans le dossier 'tests'
- Coverage thresholds: domain ≥ 90 %, application ≥ 85 %, presentation ≥ 80 %, overall ≥ 75 %.
