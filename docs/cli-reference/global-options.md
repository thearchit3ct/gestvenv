# Options globales

GestVenv fournit plusieurs options globales qui peuvent être utilisées avec n'importe quelle commande. Ce document détaille ces options et leur utilisation.

## Syntaxe générale

```bash
gestvenv [OPTIONS_GLOBALES] COMMANDE [ARGUMENTS] [OPTIONS_COMMANDE]
```

Les options globales doivent être placées avant la commande, tandis que les options spécifiques à la commande doivent être placées après les arguments de la commande.

## Options d'aide

### `--help, -h`

Affiche l'aide générale ou l'aide pour une commande spécifique.

```bash
# Afficher l'aide générale
gestvenv --help

# Afficher l'aide pour une commande spécifique
gestvenv create --help
```

## Options de sortie

### `--quiet, -q`

Réduit la verbosité de la sortie, n'affichant que les informations essentielles et les erreurs.

```bash
gestvenv --quiet create mon_projet
```

### `--verbose, -v`

Augmente la verbosité de la sortie, affichant des informations détaillées sur l'exécution des commandes. Peut être répété pour augmenter davantage le niveau de détail (ex: -vv, -vvv).

```bash
# Sortie verbosité standard
gestvenv -v list

# Sortie très détaillée (debug)
gestvenv -vvv install flask
```

### `--json`

Force la sortie au format JSON pour faciliter l'intégration avec d'autres outils ou scripts.

```bash
gestvenv --json list > environments.json
```

### `--no-color`

Désactive la coloration syntaxique dans la sortie du terminal.

```bash
gestvenv --no-color list
```

## Options de configuration

### `--config FILE`

Spécifie un fichier de configuration alternatif à utiliser.

```bash
gestvenv --config /path/to/custom/config.json create mon_projet
```

### `--config-dir DIR`

Spécifie un répertoire de configuration alternatif à utiliser.

```bash
gestvenv --config-dir /path/to/custom/config/ list
```

### `--env-dir DIR`

Spécifie un répertoire par défaut pour les environnements virtuels.

```bash
gestvenv --env-dir /path/to/envs/ create mon_projet
```

## Options d'exécution

### `--dry-run`

Simule l'exécution de la commande sans effectuer les actions. Utile pour tester ce qu'une commande ferait.

```bash
gestvenv --dry-run create mon_projet --packages "flask,pytest"
```

### `--yes, -y`

Confirme automatiquement toutes les demandes de confirmation, permettant une exécution non interactive.

```bash
gestvenv -y delete vieux_projet
```

### `--force, -f`

Force l'exécution de la commande, en ignorant certaines vérifications ou avertissements.

```bash
gestvenv -f create mon_projet
```

## Options système

### `--python PATH`

Spécifie le chemin ou la commande Python à utiliser par défaut pour les nouvelles opérations.

```bash
gestvenv --python /usr/local/bin/python3.9 create mon_projet
```

### `--pip-options "OPTIONS"`

Passe des options supplémentaires à pip lors des opérations d'installation ou de mise à jour.

```bash
gestvenv --pip-options "--no-cache-dir --timeout 60" install tensorflow
```

### `--system-site-packages`

Permet aux environnements virtuels d'accéder aux packages installés au niveau du système.

```bash
gestvenv --system-site-packages create mon_projet
```

### `--no-pip-check`

Désactive la vérification des conflits de dépendance par pip après l'installation des packages.

```bash
gestvenv --no-pip-check install "pandas,matplotlib"
```

## Options de journalisation

### `--log-file FILE`

Spécifie un fichier où enregistrer les journaux d'exécution.

```bash
gestvenv --log-file /path/to/gestvenv.log create mon_projet
```

### `--log-level {debug,info,warning,error}`

Définit le niveau de détail des journaux.

```bash
gestvenv --log-level debug create mon_projet
```

## Exemples combinés

Les options globales peuvent être combinées pour personnaliser l'exécution selon vos besoins :

```bash
# Création non interactive avec journalisation détaillée
gestvenv --yes --verbose --log-file create.log create mon_projet

# Installation de packages en mode silencieux avec un fichier de configuration personnalisé
gestvenv --quiet --config custom_config.json install "flask,sqlalchemy" --env web_app

# Export au format JSON avec une simulation préalable
gestvenv --json --dry-run export mon_projet
```

## Définir des options par défaut

Vous pouvez définir des options globales par défaut dans votre fichier de configuration pour éviter de les spécifier à chaque commande :

```json
{
  "defaults": {
    "verbose": true,
    "env_dir": "/path/to/envs",
    "python": "python3.9"
  }
}
```

Pour modifier ces paramètres, utilisez la commande config :

```bash
gestvenv config set defaults.verbose true
gestvenv config set defaults.env_dir "/path/to/envs"
```

## Variables d'environnement

Certaines options globales peuvent également être définies à l'aide de variables d'environnement :

```bash
# Définir le répertoire des environnements
export GESTVENV_ENV_DIR="/path/to/envs"

# Définir le niveau de verbosité
export GESTVENV_VERBOSE=1

# Définir la version Python par défaut
export GESTVENV_PYTHON="python3.9"
```

Les options spécifiées en ligne de commande ont priorité sur les variables d'environnement, qui ont elles-mêmes priorité sur les valeurs du fichier de configuration.
