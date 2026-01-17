#!/bin/bash
# Script d'installation des commandes gestvenv et gv

echo "Installation de GestVenv avec les commandes 'gestvenv' et 'gv'..."

# Installation en mode développement
pip install -e .

# Vérification
echo ""
echo "Vérification de l'installation..."
which gestvenv && echo "✓ Commande 'gestvenv' installée"
which gv && echo "✓ Commande 'gv' installée"

echo ""
echo "Test des commandes..."
echo "1. Test de 'gestvenv --version':"
gestvenv --version 2>/dev/null || echo "Erreur avec gestvenv"

echo ""
echo "2. Test de 'gv --version':"
gv --version 2>/dev/null || echo "Erreur avec gv"

echo ""
echo "Installation terminée !"
echo "Vous pouvez maintenant utiliser 'gestvenv' ou 'gv' pour gérer vos environnements Python."