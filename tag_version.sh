#!/bin/bash
# Script pour créer le tag de version 2.0.0

echo "🏷️  Création du tag v2.0.0 pour GestVenv"
echo "========================================"
echo ""

# Vérifier si nous sommes dans un repo git
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "❌ Erreur: Ce n'est pas un repository Git"
    exit 1
fi

# Vérifier s'il y a des changements non commités
if ! git diff-index --quiet HEAD --; then
    echo "⚠️  Attention: Il y a des changements non commités"
    echo ""
    echo "Voulez-vous continuer? (y/n)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo "Annulé."
        exit 0
    fi
fi

# Vérifier si le tag existe déjà
if git rev-parse v2.0.0 >/dev/null 2>&1; then
    echo "⚠️  Le tag v2.0.0 existe déjà"
    echo ""
    echo "Voulez-vous le remplacer? (y/n)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        git tag -d v2.0.0
        echo "✓ Ancien tag supprimé"
    else
        echo "Annulé."
        exit 0
    fi
fi

# Créer le tag
echo ""
echo "Création du tag v2.0.0..."
git tag -a v2.0.0 -m "Release v2.0.0 - Environnements éphémères, Extension VS Code, API Web"

echo "✅ Tag créé avec succès!"
echo ""
echo "Pour vérifier:"
echo "  git tag -l v2.0.0"
echo "  git describe --tags"
echo ""
echo "Pour pousser le tag:"
echo "  git push origin v2.0.0"
echo ""

# Réinstaller pour mettre à jour la version
echo "Réinstallation de GestVenv..."
pip install -e . --quiet

echo ""
echo "✅ Terminé! Testez avec: gv --version"