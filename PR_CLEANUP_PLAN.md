# Plan de nettoyage des PRs - GestVenv

## Date: Janvier 2026

## Contexte
Suite à la migration vers v2.0 (via branch `new_keko`), les PRs ouvertes #11, #12, #13 sont devenues obsolètes car basées sur l'ancienne architecture.

## Actions requises

### 1. Fermer les PRs obsolètes

```bash
# Via GitHub CLI
gh pr close 11 --comment "Obsolète: basée sur architecture pré-v2.0. Les fixes CI ont été refaits dans la nouvelle version."
gh pr close 12 --comment "Obsolète: basée sur architecture pré-v2.0. EnvironmentService a été restructuré."
gh pr close 13 --comment "Obsolète: basée sur architecture pré-v2.0. Fonctionnalités logging à ré-implémenter sur v2.0."
```

### 2. Nettoyer les branches obsolètes

```bash
# Supprimer les branches distantes obsolètes
git push origin --delete cicd
git push origin --delete phase1
git push origin --delete update_config

# Supprimer les branches locales
git branch -D cicd phase1
```

### 3. Fonctionnalités à ré-implémenter (optionnel)

#### Logging utilities (ex-PR #13)
- [ ] `gestvenv/utils/logging_utils.py` - Structured logging
- [ ] `gestvenv/utils/toml_utils.py` - TOML file handlers
- [ ] Amélioration diagnostic_service

#### CI/CD improvements (ex-PR #11)
- [ ] Vérifier que le workflow actuel couvre tous les cas
- [ ] Ajouter `safety check` si manquant

### 4. Vérification post-nettoyage

```bash
# Lister les branches restantes
git branch -a

# S'assurer que develop et main sont synchronisés
git checkout main
git merge develop --ff-only
git push origin main
```

## Branches à conserver
- `main` - Production
- `develop` - Développement actif
- `new_keko` - (peut être archivée après fusion complète)

## Branches à supprimer
- `cicd` ❌
- `phase1` ❌
- `update_config` ❌
- `update` ❌ (si plus utilisée)
