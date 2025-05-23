# Commandes de Gestion d'Environnements

Cette section détaille toutes les commandes GestVenv liées à la création, l'activation, la modification et la suppression d'environnements virtuels Python.

## create

Crée un nouvel environnement virtuel Python.

### Syntaxe

```
gestvenv create <nom> [options]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `<nom>`  | Nom de l'environnement à créer |

### Options

| Option | Description |
|--------|-------------|
| `--python <version>` | Version Python à utiliser (ex: python3.9) |
| `--packages <liste>` | Liste de packages à installer, séparés par des virgules |
| `--requirements <fichier>` | Chemin vers un fichier requirements.txt |
| `--path <chemin>` | Chemin personnalisé pour l'environnement |
| `--minimal` | Crée un environnement minimal (sans pip) |
| `--system-site` | Permet l'accès aux packages du système |
| `--prompt <texte>` | Personnalise le texte du prompt quand l'environnement est actif |
| `--description <texte>` | Ajoute une description à l'environnement |
| `--no-pip` | Ne pas installer pip dans le nouvel environnement |
| `--symlinks` | Utilise des symlinks au lieu de copies de fichiers (Unix) |
| `--copies` | Utilise des copies de fichiers au lieu de symlinks (Windows) |
| `--clear` | Supprime l'environnement existant si le répertoire existe déjà |

### Exemples

```bash
# Création simple
gestvenv create mon_projet

# Avec une version Python spécifique
gestvenv create mon_projet --python python3.9

# Avec des packages initiaux
gestvenv create mon_projet --packages "flask,pytest,gunicorn"

# Depuis un fichier requirements.txt
gestvenv create mon_projet --requirements ./requirements.txt

# Avec un chemin personnalisé
gestvenv create mon_projet --path "/chemin/personnalise/venvs/mon_projet"

# Avec une description
gestvenv create mon_projet --description "Environnement pour application web Flask"
```

## activate

Affiche les commandes pour activer un environnement virtuel.

### Syntaxe

```
gestvenv activate <nom> [options]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `<nom>`  | Nom de l'environnement à activer |

### Options

| Option | Description |
|--------|-------------|
| `--shell <shell>` | Spécifie le shell (bash, zsh, fish, cmd, powershell) |
| `--copy` | Copie la commande dans le presse-papiers |
| `--direct` | Tente d'activer directement (si shell-init est configuré) |

### Exemples

```bash
# Afficher les commandes d'activation
gestvenv activate mon_projet

# Spécifier le shell
gestvenv activate mon_projet --shell zsh

# Copier la commande d'activation
gestvenv activate mon_projet --copy
```

## deactivate

Affiche les commandes pour désactiver l'environnement virtuel actif.

### Syntaxe

```
gestvenv deactivate [options]
```

### Options

| Option | Description |
|--------|-------------|
| `--shell <shell>` | Spécifie le shell (bash, zsh, fish, cmd, powershell) |
| `--copy` | Copie la commande dans le presse-papiers |
| `--direct` | Tente de désactiver directement (si shell-init est configuré) |

### Exemples

```bash
# Afficher la commande de désactivation
gestvenv deactivate

# Spécifier le shell
gestvenv deactivate --shell powershell
```

## list

Liste tous les environnements virtuels gérés par GestVenv.

### Syntaxe

```
gestvenv list [options]
```

### Options

| Option | Description |
|--------|-------------|
| `--format <format>` | Format de sortie (text, json, table) |
| `--sort <critère>` | Trie par nom, date, python (défaut: nom) |
| `--filter <motif>` | Filtre les environnements par nom |
| `--path` | Inclut les chemins des environnements |
| `--date` | Inclut les dates de création |

### Exemples

```bash
# Liste simple
gestvenv list

# Format JSON
gestvenv list --format json

# Avec chemins et dates, triés par date
gestvenv list --path --date --sort date

# Filtrer par nom
gestvenv list --filter "projet*"
```

## info

Affiche des informations détaillées sur un environnement spécifique.

### Syntaxe

```
gestvenv info <nom> [options]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `<nom>`  | Nom de l'environnement |

### Options

| Option | Description |
|--------|-------------|
| `--format <format>` | Format de sortie (text, json, table) |
| `--packages` | Inclut la liste des packages installés |
| `--deps` | Inclut l'arbre de dépendances |
| `--path` | Affiche uniquement le chemin de l'environnement |

### Exemples

```bash
# Informations complètes
gestvenv info mon_projet

# Avec liste de packages
gestvenv info mon_projet --packages

# Format JSON avec dépendances
gestvenv info mon_projet --deps --format json

# Obtenir uniquement le chemin
gestvenv info mon_projet --path
```

## rename

Renomme un environnement existant.

### Syntaxe

```
gestvenv rename <ancien_nom> <nouveau_nom> [options]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `<ancien_nom>` | Nom actuel de l'environnement |
| `<nouveau_nom>` | Nouveau nom à donner à l'environnement |

### Options

| Option | Description |
|--------|-------------|
| `--force` | Remplace un environnement existant avec le nouveau nom |

### Exemples

```bash
# Renommer un environnement
gestvenv rename mon_projet mon_nouveau_projet

# Forcer le renommage même si le nouveau nom existe
gestvenv rename mon_projet mon_nouveau_projet --force
```

## clone

Crée une copie d'un environnement existant.

### Syntaxe

```
gestvenv clone <source> <destination> [options]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `<source>` | Nom de l'environnement source |
| `<destination>` | Nom du nouvel environnement |

### Options

| Option | Description |
|--------|-------------|
| `--python <version>` | Utilise une version Python différente pour la destination |
| `--packages <liste>` | Liste de packages supplémentaires à installer |
| `--exclude <liste>` | Liste de packages à ne pas inclure dans la copie |
| `--path <chemin>` | Chemin personnalisé pour le nouvel environnement |
| `--clear` | Supprime l'environnement de destination s'il existe |

### Exemples

```bash
# Cloner un environnement
gestvenv clone mon_projet mon_projet_test

# Cloner avec une version Python différente
gestvenv clone mon_projet mon_projet_3_10 --python python3.10

# Cloner en excluant certains packages
gestvenv clone mon_projet mon_projet_minimal --exclude "pytest,black,mypy"

# Cloner en ajoutant des packages
gestvenv clone mon_projet mon_projet_plus --packages "django,djangorestframework"
```

## remove

Supprime un environnement virtuel.

### Syntaxe

```
gestvenv remove <nom> [options]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `<nom>`  | Nom de l'environnement à supprimer |

### Options

| Option | Description |
|--------|-------------|
| `--force` | Supprime sans demander de confirmation |
| `--keep-config` | Conserve les informations de configuration |
| `--export <fichier>` | Exporte la configuration avant la suppression |

### Exemples

```bash
# Suppression avec confirmation
gestvenv remove mon_projet

# Suppression forcée
gestvenv remove mon_projet --force

# Exporter avant suppression
gestvenv remove mon_projet --export mon_projet_backup.json
```

## snapshot

Crée un instantané d'un environnement qui peut être restauré ultérieurement.

### Syntaxe

```
gestvenv snapshot <action> <nom> [options]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `<action>` | Action à effectuer (create, list, restore, delete) |
| `<nom>`    | Nom de l'environnement ou du snapshot |

### Options

| Option | Description |
|--------|-------------|
| `--name <nom>` | Nom du snapshot (pour create) |
| `--description <texte>` | Description du snapshot |
| `--force` | Écrase un snapshot existant ou restaure sans confirmation |

### Exemples

```bash
# Créer un snapshot
gestvenv snapshot create mon_projet --name "avant-mise-a-jour"

# Lister les snapshots
gestvenv snapshot list mon_projet

# Restaurer un snapshot
gestvenv snapshot restore mon_projet --name "avant-mise-a-jour"

# Supprimer un snapshot
gestvenv snapshot delete mon_projet --name "avant-mise-a-jour"
```

## pyversions

Liste les versions Python disponibles sur le système.

### Syntaxe

```
gestvenv pyversions [options]
```

### Options

| Option | Description |
|--------|-------------|
| `--format <format>` | Format de sortie (text, json, table) |
| `--path` | Inclut les chemins des exécutables Python |
| `--details` | Inclut des détails supplémentaires (version complète, etc.) |

### Exemples

```bash
# Liste simple
gestvenv pyversions

# Avec chemins et détails
gestvenv pyversions --path --details

# Format JSON
gestvenv pyversions --format json
```

## locate

Localise le répertoire d'un environnement virtuel.

### Syntaxe

```
gestvenv locate <nom> [options]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `<nom>`  | Nom de l'environnement à localiser |

### Options

| Option | Description |
|--------|-------------|
| `--bin` | Retourne le chemin du répertoire bin/Scripts |
| `--python` | Retourne le chemin de l'exécutable Python |
| `--pip` | Retourne le chemin de l'exécutable pip |

### Exemples

```bash
# Obtenir le chemin de l'environnement
gestvenv locate mon_projet

# Obtenir le chemin de l'exécutable Python
gestvenv locate mon_projet --python

# Obtenir le chemin de pip
gestvenv locate mon_projet --pip
```

## Utilisation combinée

Les commandes de gestion d'environnements peuvent être combinées dans des flux de travail complexes :

```bash
# Créer, installer des packages, puis exporter
gestvenv create nouveau_projet --python python3.9
gestvenv install "flask,pytest" --env nouveau_projet
gestvenv export nouveau_projet --output nouveau_projet.json

# Cloner un environnement et comparer les packages
gestvenv clone mon_projet mon_projet_test
gestvenv list-packages --env mon_projet > packages_original.txt
gestvenv list-packages --env mon_projet_test > packages_clone.txt
diff packages_original.txt packages_clone.txt
```

Ces commandes constituent la base de la gestion des environnements avec GestVenv. Pour plus d'informations sur les commandes liées aux packages, consultez la section [Commandes de Gestion de Packages](package-commands.md).