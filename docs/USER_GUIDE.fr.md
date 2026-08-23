# FreizeitManager 0.2.2 – Manuel

FreizeitManager vous aide à entretenir vos relations sans en faire une liste
de corvées. Il retient qui compte pour vous et à quel rythme vous souhaitez
garder le contact, et vous propose chaque jour une poignée de personnes tout
au plus.

Ce manuel est généré à partir de l'aide intégrée à l'application. Les mêmes
textes y sont accessibles à tout moment avec **F1**.

## Sommaire

- [Premiers pas](#premiers-pas)
- [Importer une liste](#importer-une-liste)
- [Le cockpit](#le-cockpit)
- [Contacts et rythme](#contacts-et-rythme)
- [Enregistrer un contact](#enregistrer-un-contact)
- [Fraîcheur et rotation](#fraicheur-et-rotation)
- [Anniversaires](#anniversaires)
- [Planifier des rendez-vous](#planifier-des-rendez-vous)
- [Mode simple et mode expert](#mode-simple-et-mode-expert)
- [Réglages, langue et sauvegarde](#reglages-langue-et-sauvegarde)

## Premiers pas

Le FreizeitManager répond à une seule question : **avec qui aurais-je envie de reprendre contact maintenant ?** Ce n'est ni un carnet d'adresses ni une liste de tâches. Rien ici ne crée de dette.

Le démarrage le plus rapide : créer des contacts ou importer une liste existante. Pour chaque personne, vous définissez son importance et le rythme de contact souhaité. Tout le reste découle de ce que vous saisissez réellement.

Ensuite, le cockpit suffit. Il affiche au plus trois suggestions – l'expérience montre qu'au-delà, cela crée de la pression plutôt que de la clarté.

## Importer une liste

Via **Contacts → Importer**, vous reprenez une liste de personnes existante depuis un fichier CSV ou Excel (.xlsx). Les colonnes n'ont pas besoin d'un ordre fixe : l'import reconnaît lui-même des en-têtes comme nom, prénom, nom de famille, anniversaire, groupe, notes, e-mail et téléphone, en allemand comme en anglais.

Avant toute écriture, un **aperçu** s'affiche. Vous y décidez ligne par ligne de ce qui doit se passer. Les noms déjà présents sont sur « Ignorer » – pour eux, « Créer » n'est même pas proposé. Si vous choisissez « Compléter les champs vides », seul ce qui manque encore au contact existant est renseigné. Les données présentes ne sont jamais écrasées.

Les anniversaires sont repris même si le fichier ne contient pas d'année : le jour et le mois sont conservés, l'âge n'est alors simplement pas affiché. Les années à deux chiffres ne tombent jamais dans le futur – « 65 » devient 1965.

Les lignes sans nom sont ignorées et comptées dans le récapitulatif. Une cellule illisible ne fait jamais échouer tout l'import.

## Le cockpit

**Aujourd'hui** est l'écran d'accueil. Il ne répond pas à « où en est tout ? » mais à « qu'est-ce qui serait opportun maintenant ? ».

Les quatre tuiles indiquent combien de contacts conviendraient maintenant, seraient à prévoir cette semaine, sont déjà convenus et sont au repos. En dessous, vos prochaines étapes apparaissent sous forme de cartes avec des actions rapides : enregistrer, planifier, reporter ou marquer comme souhait.

**Autres suggestions** remplace les cartes sans reproposer aussitôt les mêmes personnes.

En haut, vous choisissez votre état d'énergie du jour : peu d'énergie, normal ou envie de voir du monde. Cela oriente les suggestions vers des contacts courts ou plus longs et ne vaut que pour ce jour.

Si rien n'est urgent, le cockpit le dit – au lieu d'afficher un tableau vide.

## Contacts et rythme

Chaque contact comporte deux indications distinctes, souvent confondues :

L'**importance** (A à E) indique la proximité de la personne. **Contact tous les … jours** indique la fréquence souhaitée. Les deux sont liées sans se déterminer : un proche que vous voyez deux fois par an reste un proche.

La **tolérance** est la marge autour de ce rythme. Ce n'est qu'au-delà qu'un contact est considéré en retard.

Le **niveau de relation** est un modèle : si vous en choisissez un, les nouveaux contacts héritent de son importance et de son rythme.

Le **statut** pilote la rotation : « Actif » et « Moins de contact en ce moment » y participent, « Pas dans la rotation » reste enregistré mais n'est jamais suggéré, « En pause » suspend jusqu'à une date, « Archivé » disparaît du quotidien.

Sous **Quel contact est bienvenu ?** et **Quand cela convient-il le plus souvent ?**, vous notez ce qui convient à la personne – les suggestions s'y conforment.

## Enregistrer un contact

Un contact s'enregistre en un clic : sur la carte du cockpit ou via **Enregistrer** dans la liste des contacts. Vous n'êtes sollicité que si vous souhaitez préciser davantage.

Le **type** va de la longue rencontre à la brève réaction. Il détermine la durée de l'effet : une longue soirée porte plus loin qu'un pouce levé sous une photo.

La **qualité** (court, normal, intense) renforce ou atténue cet effet ; la **durée** est facultative.

Chaque contact enregistré met fin à un report. Il n'y a volontairement pas de champ « dernière rencontre » : l'historique naît de ce que vous saisissez, et c'est la seule base pour calculer la fraîcheur.

## Fraîcheur et rotation

Des contacts enregistrés découle pour chaque personne une **fraîcheur** : tout va bien, bientôt à revoir, bon moment maintenant, silence depuis longtemps. C'est ce classement – et non un score – qui pilote les suggestions.

Les suggestions sont retenues lorsqu'une raison s'y oppose : contact tout juste eu (repos après contact), un rendez-vous est déjà planifié, le contact est en pause ou reporté, ou votre capacité sociale de la semaine est atteinte. Le cockpit nomme ces raisons en clair.

La **capacité sociale** dans les réglages limite le nombre de jours sociaux suggérés par semaine. C'est une protection contre la surcharge, pas un objectif.

La rubrique **Rotation** montre l'évaluation complète de tous les contacts, justification comprise. Le quotidien n'en a pas besoin – elle rend compréhensible pourquoi quelque chose est suggéré. Vous la trouvez en mode expert.

## Anniversaires

Les contacts peuvent avoir un anniversaire. Le cockpit affiche les anniversaires des 30 prochains jours ; celui du jour est mis en évidence.

Si l'**année est inconnue**, cochez la case correspondante dans le formulaire de contact. Le jour et le mois sont alors conservés, mais aucun âge n'est affiché et aucune année n'est inventée.

Un anniversaire le 29 février est affiché le 28 février les années ordinaires, afin qu'il reste en février.

Les contacts archivés n'apparaissent pas ici.

## Planifier des rendez-vous

Via **Planifier** sur une carte de suggestion, vous fixez un rendez-vous en y incluant directement la personne proposée. Plusieurs participants sont possibles.

Les rendez-vous planifiés des deux prochaines semaines figurent dans le cockpit sous **Planifié**. Tant qu'un rendez-vous tient, la personne n'est plus suggérée.

Une fois le rendez-vous passé, il devient un véritable contact enregistré pour tous les participants – vous n'avez pas à le saisir deux fois.

## Mode simple et mode expert

Le FreizeitManager démarre en **mode simple** : cockpit, contacts et réglages. Cela suffit au quotidien.

Le **mode expert** affiche en plus la rotation et montre les chiffres derrière les classements dans les cartes et les listes. Vous basculez en bas de la barre latérale ou avec **Ctrl+E**.

Autres raccourcis : **Ctrl+N** crée un contact, **F1** ouvre cette aide.

## Réglages, langue et sauvegarde

Sous **Réglages**, vous définissez le nombre de suggestions du cockpit, la durée du repos après un contact et le nombre de jours sociaux par semaine qui vous convient.

La **langue** s'applique immédiatement, sans redémarrage – allemand, anglais et français.

Sous **Apparence**, vous choisissez un profil de design et la taille de police. Si le FreizeitManager tourne dans le LifePlanner, il peut reprendre le profil défini de façon centrale.

**Créer une sauvegarde** dépose une copie de la base de données. Le dossier de données est indiqué sur la même page.

Si le FreizeitManager est connecté au LifePlanner, il ne transmet sur demande que des compteurs et les prochaines étapes – jamais les notes.

Les prochaines étapes apparaissent alors aussi sur la page d'aperçu du LifePlanner, à côté des messages des autres programmes – trois au maximum, comme dans le cockpit. Seule la ligne finie est transmise : qui serait à contacter et ce qui conviendrait. Une amitié devenue silencieuse n'y est délibérément jamais marquée comme urgente ; aucune montagne de dettes ne doit se former dans le LifePlanner non plus. Qui vous avez contacté aujourd'hui disparaît de la liste de lui-même.

---

Généré à partir de l'aide de l'application avec `tools/build_handbook.py`. Les modifications vont dans `freizeitmanager/i18n/fr.json` sous `help.topics`.
