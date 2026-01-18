# Problèmes courants et solutions

## Installation

### Erreur: "pip not found" ou "uv not found"

**Symptôme**: Le backend demandé n'est pas installé.

**Solution**:
```bash
# Installer pip (généralement inclus avec Python)
python -m ensurepip --upgrade

# Installer uv
curl -LsSf https://astral.sh/uv/install.sh | sh
# ou
pip install uv
```

### Erreur: "Permission denied" lors de la création d'environnement

**Symptôme**: Impossible de créer un environnement dans le répertoire spécifié.

**Solution**:
```bash
# Vérifier les permissions
ls -la ~/.gestvenv/

# Corriger les permissions
chmod -R u+rwX ~/.gestvenv/

# Ou utiliser un chemin différent
gv config set environments_path ~/my-envs
```

## Cache

### Erreur: "list index out of range" lors de `cache add`

**Symptôme**: Erreur lors de l'ajout de packages au cache.

**Cause**: Problème d'encodage sur Windows (cp1252) ou méthode manquante.

**Solution**: Mettre à jour vers la dernière version de GestVenv qui corrige ce bug.

### Cache trop volumineux

**Symptôme**: Le cache occupe trop d'espace disque.

**Solution**:
```bash
# Voir la taille du cache
gv cache info

# Nettoyer les packages anciens (> 30 jours)
gv cache clean --older-than 30

# Définir une limite de taille
gv cache clean --size-limit 500MB
```

## Environnements

### Environnement corrompu

**Symptôme**: L'environnement ne s'active pas ou pip ne fonctionne pas.

**Solution**:
```bash
# Diagnostiquer
gv doctor myenv --verbose

# Réparer
gv doctor myenv --fix

# Si irréparable, recréer
gv delete myenv --force
gv create myenv -r requirements.txt
```

### Conflits de dépendances

**Symptôme**: Erreur "package X requires Y, but you have Z".

**Solution**:
```bash
# Vérifier les conflits
gv deps check myenv

# Synchroniser avec le fichier requirements
gv sync myenv

# Ou forcer la réinstallation
gv install package --force
```

## Performance

### Création d'environnement lente

**Symptôme**: La création prend plusieurs minutes.

**Solution**:
```bash
# Utiliser uv (10-100x plus rapide)
gv create myenv --backend uv

# Activer le cache
gv config set cache.enabled true

# Pré-charger les packages fréquents
gv cache add requests numpy pandas
```

### Installation de packages lente

**Symptôme**: L'installation est plus lente qu'attendu.

**Solution**:
```bash
# Vérifier le hit ratio du cache
gv cache info

# Utiliser le mode parallèle
gv install pkg1 pkg2 pkg3 --parallel

# Utiliser un miroir PyPI local
export PIP_INDEX_URL=http://local-pypi:8080/simple
```

## Réseau

### Erreur: "Connection refused" ou "Timeout"

**Symptôme**: Impossible de télécharger les packages.

**Solution**:
```bash
# Vérifier la connectivité
ping pypi.org

# Utiliser le mode offline si le cache est rempli
gv config set cache.offline_mode true

# Configurer un proxy
export HTTPS_PROXY=http://proxy:8080
```

### Erreur SSL/TLS

**Symptôme**: "SSL: CERTIFICATE_VERIFY_FAILED"

**Solution**:
```bash
# Mettre à jour les certificats
pip install --upgrade certifi

# Ou ignorer (non recommandé en production)
export PIP_TRUSTED_HOST=pypi.org
```

## Environnements éphémères

### Erreur: "cgroups not available"

**Symptôme**: Impossible d'utiliser l'isolation cgroups.

**Cause**: cgroups v2 non disponible ou permissions insuffisantes.

**Solution**:
```bash
# Vérifier si cgroups v2 est disponible
mount | grep cgroup2

# Utiliser un niveau d'isolation inférieur
gv ephemeral create --isolation basic

# Ou avec sudo pour les permissions cgroups
sudo gv ephemeral create --isolation cgroup
```

### Environnement éphémère non nettoyé

**Symptôme**: Les environnements éphémères persistent après utilisation.

**Solution**:
```bash
# Lister les environnements éphémères
gv ephemeral list

# Nettoyer manuellement
gv ephemeral cleanup --all

# Vérifier le processus de monitoring
gv ephemeral status
```

## Diagnostic

### Comment obtenir des informations de debug

```bash
# Mode debug complet
gv --debug create myenv

# Trace de performance
gv --trace-performance install numpy

# Afficher la configuration
gv config show

# Diagnostic système
gv doctor --verbose --profile
```

### Générer un rapport de bug

```bash
# Collecter les informations système
gv doctor --report > bug-report.txt

# Inclure les logs
cat ~/.gestvenv/logs/gestvenv.log >> bug-report.txt

# Ouvrir une issue sur GitHub
# https://github.com/thearchit3ct/gestvenv/issues
```
