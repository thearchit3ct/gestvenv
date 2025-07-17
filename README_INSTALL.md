# Installation de GestVenv v2.0

## Installation rapide

```bash
# 1. Cloner le projet (si pas déjà fait)
git clone https://github.com/gestvenv/gestvenv
cd gestvenv

# 2. Installer en mode développement
pip install -e .

# 3. Vérifier l'installation
gv --version
```

## Résolution des problèmes

### Erreur "gv: command not found"

Si la commande `gv` n'est pas trouvée après l'installation :

1. **Vérifier le PATH** :
   ```bash
   echo $PATH
   # Assurez-vous que le dossier Scripts/bin de Python est dans le PATH
   ```

2. **Réinstaller** :
   ```bash
   pip uninstall gestvenv
   pip install -e .
   ```

3. **Utiliser la commande longue** :
   ```bash
   gestvenv --version
   ```

### Erreur d'import

Si vous avez des erreurs d'import :

1. **Vérifier Python** :
   ```bash
   python --version  # Doit être 3.9+
   ```

2. **Nettoyer et réinstaller** :
   ```bash
   rm -rf build/ dist/ *.egg-info
   pip install -e .
   ```

### Script d'installation automatique

Un script d'installation est fourni :

```bash
chmod +x setup_gestvenv.sh
./setup_gestvenv.sh
```

## Utilisation

Une fois installé, vous pouvez utiliser :

```bash
# Commande courte (recommandée)
gv create myproject
gv install django
gv list

# Ou commande longue
gestvenv create myproject
```

## Nouvelles fonctionnalités v2.0

- **Environnements éphémères** : `gv ephemeral create test`
- **Extension VS Code** : Dans `extensions/vscode/`
- **Interface Web** : Dans `web/`

Pour plus d'informations, consultez le [README principal](README.md).