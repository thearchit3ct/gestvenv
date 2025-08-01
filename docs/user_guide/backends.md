# Guide des Backends GestVenv v1.1

GestVenv v1.1 offre un syst�me de backends modulaire avec auto-d�tection intelligente pour optimiser les performances selon votre projet.

## <� Vue d'Ensemble des Backends

### Backends Support�s

| Backend | Performance | Lock Files | Groupes | Workspace | Auto-d�tection | Statut |
|---------|-------------|------------|---------|-----------|----------------|--------|
| **uv** | =%=%=% |  uv.lock |  |  |  | Recommand� |
| **PDM** | =%=%=% |  pdm.lock |  |  |  | Stable |
| **Poetry** | =%=% |  poetry.lock |  | L |  | Stable |
| **pip** | =% | L |  | L |  | Legacy |

### Scores de Performance

```bash
# Voir les performances en temps r�el
gestvenv backend list --detailed

# Exemple de sortie :
# Backend: uv        Score: 10/10  Temps moyen: 2.1s
# Backend: pdm       Score: 8/10   Temps moyen: 3.2s  
# Backend: poetry    Score: 6/10   Temps moyen: 5.8s
# Backend: pip       Score: 4/10   Temps moyen: 12.4s
```

## =� Backend UV (Recommand�)

### Description
UV est le backend le plus performant, d�velopp� par Astral (cr�ateurs de Ruff). Il offre des vitesses d'installation jusqu'� 10x sup�rieures � pip.

### Avantages
- **Performance exceptionnelle** : Installation et r�solution ultra-rapides
- **Compatibilit� totale** : Compatible avec l'�cosyst�me Python existant
- **Lock files** : G�n�ration de uv.lock pour la reproductibilit�
- **Installation parall�le** : Jusqu'� 8 jobs simultan�s
- **Cache optimis�** : R�utilisation intelligente des t�l�chargements

### Installation
```bash
# Installation automatique
pip install uv

# V�rification
gestvenv backend list
# UV devrait appara�tre comme disponible

# Configuration comme backend par d�faut
gestvenv backend set uv
```

### Utilisation
```bash
# Auto-d�tection (recommand�)
gestvenv create monapp --backend auto

# Sp�cifique
gestvenv create monapp --backend uv

# Avec lock file
gestvenv create-from-pyproject pyproject.toml monapp --backend uv
# G�n�re automatiquement uv.lock
```

### Fonctionnalit�s Avanc�es
```bash
# Installation parall�le maximale
gestvenv config set backend_configs.uv.max_parallel_jobs 8

# Cache personnalis�
export UV_CACHE_DIR=/custom/cache/path

# Mode verbose
gestvenv install numpy --backend uv --verbose
```

## =� Backend PDM

### Description
PDM (Python Dependency Manager) est un gestionnaire moderne qui suit les standards PEP 582 et PEP 621.

### Avantages
- **Standards modernes** : Conforme PEP 621 (pyproject.toml)
- **Groupes de d�pendances** : Support natif des dependency groups
- **Workspace** : Gestion de projets multi-packages
- **Lock files** : pdm.lock pour la reproductibilit�
- **Performance** : R�solution rapide des d�pendances

### Installation
```bash
pip install pdm

# Configuration
gestvenv backend set pdm
```

### Utilisation avec Groupes
```bash
# Cr�ation avec groupes
gestvenv create-from-pyproject pyproject.toml monapp --backend pdm

# Installation par groupes
gestvenv install --group dev --backend pdm --env monapp
gestvenv install --group test,lint --backend pdm --env monapp

# Synchronisation
gestvenv sync monapp  # Utilise PDM automatiquement si d�tect�
```

### Workspace et Multi-packages
```bash
# Projet avec workspace
gestvenv create monworkspace --backend pdm

# Structure typique :
# monworkspace/
#    pyproject.toml (workspace root)
#    packages/
#       core/
#          pyproject.toml
#       api/
#           pyproject.toml
#    pdm.lock
```

## <� Backend Poetry

### Description
Poetry est un gestionnaire de d�pendances Python populaire avec une interface �l�gante et des fonctionnalit�s compl�tes.

### Avantages
- **�cosyst�me mature** : Large adoption dans la communaut�
- **Interface intuitive** : Commandes simples et claires
- **Packaging int�gr�** : Build et publication simplifi�s
- **Lock files** : poetry.lock pour la reproductibilit�
- **Environnements virtuels** : Gestion automatique

### Auto-d�tection
GestVenv d�tecte automatiquement Poetry quand :
- `poetry.lock` existe
- `pyproject.toml` contient `[tool.poetry]`
- `build-backend = "poetry.core.masonry.api"`

### Utilisation
```bash
# Auto-d�tection depuis projet Poetry existant
gestvenv import ./mon-projet-poetry/pyproject.toml

# Cr�ation sp�cifique
gestvenv create monapp --backend poetry

# Migration depuis Poetry
cd mon-projet-poetry
gestvenv create-from-pyproject pyproject.toml mon-env
```

### Commandes �quivalentes

| Poetry | GestVenv | Description |
|--------|----------|-------------|
| `poetry install` | `gestvenv sync mon-env` | Installation des d�pendances |
| `poetry add requests` | `gestvenv install requests --env mon-env` | Ajouter une d�pendance |
| `poetry remove requests` | `gestvenv uninstall requests --env mon-env` | Supprimer une d�pendance |
| `poetry show` | `gestvenv list-packages --env mon-env` | Lister les packages |
| `poetry lock` | `gestvenv sync mon-env` | Mettre � jour le lock file |

## =� Backend pip (Legacy)

### Description
pip est le gestionnaire de packages par d�faut de Python. Bien que moins performant, il reste universellement compatible.

### Avantages
- **Universalit�** : Disponible partout o� Python est install�
- **Compatibilit�** : Fonctionne avec tous les packages PyPI
- **Simplicit�** : Interface famili�re
- **Stabilit�** : Mature et test�

### Limitations
- Performance plus lente
- Pas de lock files natifs
- R�solution de d�pendances basique
- Pas de workspace

### Utilisation
```bash
# Fallback automatique si aucun autre backend
gestvenv create monapp

# Sp�cifique
gestvenv create monapp --backend pip

# Avec requirements.txt
gestvenv cache add -r requirements.txt
gestvenv create monapp --backend pip
gestvenv install -r requirements.txt --env monapp
```

## <� Auto-d�tection Intelligente

### M�canisme de D�tection

GestVenv utilise plusieurs strat�gies pour choisir le backend optimal :

#### 1. D�tection par Fichiers Projet
```bash
# Recherche dans cet ordre :
# 1. uv.lock         � backend uv
# 2. poetry.lock     � backend poetry  
# 3. pdm.lock        � backend pdm
# 4. pyproject.toml  � analyse des sections [tool.*]
# 5. requirements.txt � backend pip
```

#### 2. Analyse pyproject.toml
```toml
# D�tection Poetry
[tool.poetry]
name = "mon-projet"

# D�tection PDM  
[tool.pdm]
name = "mon-projet"

# D�tection UV
[tool.uv]
name = "mon-projet"

# Build backend
[build-system]
build-backend = "poetry.core.masonry.api"  # � Poetry
build-backend = "pdm.backend"              # � PDM
```

#### 3. S�lection par Performance
Si aucun fichier sp�cifique n'est trouv� :
1. **uv** (si disponible) - Performance maximale
2. **pdm** (si disponible) - Standards modernes
3. **poetry** (si disponible) - �cosyst�me mature
4. **pip** (toujours disponible) - Fallback universel

### Configuration de l'Auto-d�tection

```bash
# Activer l'auto-d�tection (par d�faut)
gestvenv config set preferred_backend auto

# Voir les recommandations pour un projet
gestvenv backend info --project /chemin/vers/projet

# Exemple de sortie :
# Detected: poetry (poetry.lock found)
# Optimal: uv (best performance available)
# Alternatives: pdm, pip
# Recommendation: Use poetry for consistency, or uv for performance
```

## � Configuration Avanc�e

### Configuration Globale
```bash
# Backend par d�faut
gestvenv config set preferred_backend uv

# Configuration sp�cifique par backend
gestvenv config set backend_configs.uv.max_parallel_jobs 6
gestvenv config set backend_configs.poetry.create_virtualenv false
gestvenv config set backend_configs.pdm.use_venv true
```

### Configuration Locale
```bash
# Pour le projet actuel
gestvenv config set --local preferred_backend poetry

# Variables d'environnement
export GESTVENV_BACKEND=uv
export GESTVENV_PDM_USE_VENV=true
export GESTVENV_UV_PARALLEL_JOBS=8
```

### Validation de Compatibilit�
```bash
# V�rifier la compatibilit� backend/projet
gestvenv backend validate poetry /mon/projet

# Exemple de sortie :
#  Poetry available
#  pyproject.toml compatible  
# �  No poetry.lock found (will be created)
#  Compatible with dependency groups
```

## = Migration Entre Backends

### Depuis pip vers uv
```bash
# Projet existant avec requirements.txt
gestvenv convert-to-pyproject requirements.txt
gestvenv create-from-pyproject pyproject.toml monapp --backend uv
```

### Depuis Poetry vers PDM
```bash
# Projet Poetry existant
cd mon-projet-poetry
gestvenv create-from-pyproject pyproject.toml mon-env --backend pdm
# PDM utilisera le pyproject.toml existant et cr�era pdm.lock
```

### Depuis PDM vers UV
```bash
# Projet PDM existant
gestvenv create-from-pyproject pyproject.toml mon-env --backend uv
# UV respectera la structure pyproject.toml et cr�era uv.lock
```

## =� Benchmarks et Performance

### Tests de Performance Typiques

```bash
# Installation de 50 packages courants
# R�sultats moyens sur Python 3.11 :

Backend | Temps | T�l�chargement | Cache Hit
--------|-------|----------------|----------
uv      | 8s    | 2.1s          | 0.3s
pdm     | 12s   | 3.4s          | 1.1s  
poetry  | 24s   | 8.2s          | 2.8s
pip     | 45s   | 18.7s         | 7.2s
```

### Optimisations Recommand�es

```bash
# Cache partag� pour UV
export UV_CACHE_DIR=/shared/cache/uv

# Parall�lisation maximale
gestvenv config set backend_configs.uv.max_parallel_jobs 8

# Pr�-chargement du cache
gestvenv cache add -r requirements.txt --platforms linux_x86_64,macosx_11_0_arm64

# Mode offline pour CI/CD
gestvenv --offline install requirements.txt
```

## =' D�pannage

### Probl�mes Courants

#### Backend non d�tect�
```bash
# V�rifier la disponibilit�
gestvenv backend list

# Installer le backend manquant
pip install uv  # ou poetry, pdm

# Forcer un backend sp�cifique
gestvenv create monapp --backend pip
```

#### Conflits de lock files
```bash
# Multiple lock files d�tect�s
# Solution : sp�cifier explicitement
gestvenv create-from-pyproject pyproject.toml monapp --backend uv
# Ou supprimer les lock files non d�sir�s
rm poetry.lock  # Garder seulement uv.lock
```

#### Performance d�grad�e
```bash
# Diagnostic
gestvenv doctor --performance

# V�rifier le cache
gestvenv cache info

# Nettoyer si n�cessaire
gestvenv cache clean --size-limit 1GB
```

### Support et Compatibilit�

#### Versions Minimales
- **uv** : e0.1.0
- **PDM** : e2.0.0  
- **Poetry** : e1.2.0
- **pip** : e21.0 (inclus avec Python 3.8+)

#### Compatibilit� Syst�me
Tous les backends sont test�s sur :
- Linux x86_64 / ARM64
- macOS Intel / Apple Silicon  
- Windows x64
- Python 3.8, 3.9, 3.10, 3.11, 3.12

Ce guide couvre l'utilisation compl�te du syst�me de backends de GestVenv v1.1. L'auto-d�tection et la modularit� vous permettent de travailler efficacement avec n'importe quel type de projet Python.