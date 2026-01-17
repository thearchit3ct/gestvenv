#!/bin/bash
# Réinstallation de GestVenv avec la nouvelle version

echo "🔄 Réinstallation de GestVenv v2.0.0..."
echo ""

# Désinstaller l'ancienne version
echo "1. Désinstallation de l'ancienne version..."
pip uninstall -y gestvenv 2>/dev/null || true

# Nettoyer les fichiers build
echo "2. Nettoyage des fichiers build..."
rm -rf build/ dist/ *.egg-info 2>/dev/null || true

# Réinstaller
echo "3. Installation de la nouvelle version..."
pip install -e . --quiet

echo ""
echo "✅ Installation terminée!"
echo ""
echo "Test de la version:"
echo "==================="

# Test Python direct
echo -n "Import Python: "
python -c "from gestvenv import __version__; print(__version__)" 2>/dev/null || echo "Erreur"

# Test CLI module
echo -n "Module CLI: "
python -m gestvenv.cli --version 2>/dev/null || echo "Erreur"

# Test commande gv
echo -n "Commande gv: "
gv --version 2>/dev/null || echo "Non disponible"

echo ""
echo "Si la version n'est pas 2.0.0, exécutez:"
echo "  export PATH=\"$HOME/.local/bin:$PATH\""
echo "  source ~/.bashrc  # ou ~/.zshrc"