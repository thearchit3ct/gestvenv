# Gestion des Environnements

## Introduction

La gestion des environnements virtuels est l'une des fonctionnalités principales de GestVenv. Cette section vous guidera à travers toutes les opérations liées aux environnements virtuels Python, de la création à la suppression.

## Création d'un environnement

Pour créer un nouvel environnement virtuel, utilisez la commande `create` :

```bash
gestvenv create mon_projet
```

Cette commande crée un environnement avec la version Python par défaut et les packages essentiels.

### Options de création

Vous pouvez personnaliser votre environnement lors de sa création :

```bash
# Spécifier une version Python particulière
gestvenv create mon_projet --python python3.9

# Inclure des packages dès la création
gestvenv create mon_projet --packages "flask,pytest,gunicorn"

# Spécifier un emplacement personnalisé
gestvenv create mon_projet --path "/chemin/personnalise"

# Créer à partir d'un requirements.txt
gestvenv create mon_projet --requirements chemin/vers/requirements.txt
```

## Activation d'un environnement

Pour activer un environnement, utilisez la commande `activate` :

```bash
gestvenv activate mon_projet
```

GestVenv affichera les instructions spécifiques à votre système d'exploitation pour activer l'environnement. Sur la plupart des systèmes, cela ressemblera à :

```bash
# Sur Windows
source C:\chemin\vers\environnements\mon_projet\Scripts\activate

# Sur macOS/Linux
source /chemin/vers/environnements/mon_projet/bin/activate
```

> **Note :** GestVenv ne peut pas activer directement l'environnement en raison des limitations des shells, mais il vous fournit la commande exacte à exécuter.

## Désactivation d'un environnement

Pour désactiver l'environnement actuellement actif :

```bash
gestvenv deactivate
```

Comme pour l'activation, GestVenv affichera la commande à exécuter pour désactiver l'environnement actuel, généralement simplement `deactivate`.

## Liste des environnements

Pour voir tous les environnements gérés par GestVenv :

```bash
gestvenv list
```

Exemple de sortie :

```
Environnements disponibles :
* mon_projet (Python 3.9) - actif
  webapp (Python 3.8)
  data_analysis (Python 3.10)
```

L'astérisque indique l'environnement actuellement actif.

## Informations détaillées sur un environnement

Pour obtenir des informations détaillées sur un environnement spécifique :

```bash
gestvenv info mon_projet
```

Exemple de sortie :

```
Environnement : mon_projet
Python version : 3.9.6
Chemin : /chemin/vers/environnements/mon_projet
Créé le : 2025-05-18 14:30:00
Packages installés (3) :
  - flask==2.0.1
  - pytest==6.2.5
  - gunicorn==20.1.0
```

## Clonage d'un environnement

Pour créer une copie d'un environnement existant :

```bash
gestvenv clone mon_projet mon_projet_dev
```

Cette commande crée un nouvel environnement `mon_projet_dev` avec les mêmes packages et la même version Python que `mon_projet`.

## Suppression d'un environnement

Pour supprimer un environnement existant :

```bash
gestvenv remove mon_projet
```

GestVenv demandera confirmation avant de supprimer l'environnement. Pour supprimer sans confirmation :

```bash
gestvenv remove mon_projet --force
```

## Exécution de commandes dans un environnement

Pour exécuter une commande dans un environnement spécifique sans l'activer manuellement :

```bash
gestvenv run mon_projet python script.py
```

Cette commande exécute `python script.py` dans l'environnement `mon_projet` puis revient au shell normal.

## Bonnes pratiques

1. **Utilisez des noms descriptifs** pour vos environnements qui indiquent leur objectif.
2. **Créez des environnements dédiés** pour chaque projet plutôt que de réutiliser le même.
3. **Documentez les versions de Python** requises pour chaque projet.
4. **Vérifiez régulièrement** l'état de vos environnements avec `gestvenv list` et `gestvenv info`.
5. **Supprimez les environnements inutilisés** pour économiser de l'espace disque.

## Dépannage

Si vous rencontrez des problèmes avec la gestion des environnements :

- Vérifiez que vous avez les droits d'accès sur le répertoire où les environnements sont stockés.
- Assurez-vous que la version de Python spécifiée est installée sur votre système.
- Consultez les journaux d'erreur avec `gestvenv logs mon_projet`.
- Reconstruisez un environnement problématique en l'exportant, le supprimant puis en le recréant à partir de l'export.