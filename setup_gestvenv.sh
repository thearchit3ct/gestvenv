#!/bin/bash
# Script d'installation de GestVenv v2.0

echo "🚀 Installation de GestVenv v2.0"
echo "================================"
echo ""

# Vérifier Python
echo "1. Vérification de Python..."
python_version=$(python3 --version 2>&1)
echo "   ✓ $python_version"

# Installation en mode développement
echo ""
echo "2. Installation de GestVenv..."
pip install -e . --quiet

# Vérification de l'installation
echo ""
echo "3. Vérification de l'installation..."
echo ""

# Test direct Python
echo "   Test import Python:"
python3 -c "from gestvenv import __version__; print(f'   ✓ Version: {__version__}')" 2>/dev/null || echo "   ✗ Erreur d'import"

# Test commande gv
echo ""
echo "   Test commande 'gv':"
if command -v gv &> /dev/null; then
    gv_version=$(gv --version 2>&1 | head -n1)
    echo "   ✓ Commande 'gv' disponible"
    echo "   ✓ $gv_version"
else
    echo "   ✗ Commande 'gv' non trouvée"
    echo "   💡 Essayez: pip install -e ."
fi

# Test commande gestvenv
echo ""
echo "   Test commande 'gestvenv':"
if command -v gestvenv &> /dev/null; then
    echo "   ✓ Commande 'gestvenv' disponible"
else
    echo "   ✗ Commande 'gestvenv' non trouvée"
fi

echo ""
echo "================================"
echo "✅ Installation terminée!"
echo ""
echo "📖 Utilisation:"
echo "   gv create myproject      # Créer un environnement"
echo "   gv install django        # Installer un package"
echo "   gv list                  # Lister les environnements"
echo "   gv --help               # Aide complète"
echo ""
echo "🆕 Nouvelles fonctionnalités v2.0:"
echo "   gv ephemeral create test # Environnement temporaire"
echo "   Extension VS Code dans extensions/vscode/"
echo "   Interface web dans web/"
echo ""