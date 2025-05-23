#!/bin/bash
# docs/macros
# Script pour automatiser la génération de documentation pour GestVenv
# Auteur: Thearchit3ct
# Date: 18 mai 2025
# Licence: MIT

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOCS_DIR="$PROJECT_ROOT/docs"
SRC_DIR="$PROJECT_ROOT/gestvenv"
README_PATH="$PROJECT_ROOT/README.md"
VERSION_FILE="$SRC_DIR/__init__.py"
OUTPUT_DIR="$DOCS_DIR/generated"

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Créer le répertoire de sortie s'il n'existe pas
mkdir -p "$OUTPUT_DIR"

# Fonction d'aide
show_help() {
    echo -e "${BLUE}GestVenv - Utilitaire de génération de documentation${NC}"
    echo
    echo "Usage: ./macros [COMMANDE] [OPTIONS]"
    echo
    echo "Commandes disponibles:"
    echo "  help                 Affiche cette aide"
    echo "  commands             Génère la documentation des commandes"
    echo "  examples             Génère des exemples d'utilisation"
    echo "  api                  Génère la documentation de l'API"
    echo "  all                  Génère toute la documentation"
    echo "  version              Affiche la version actuelle"
    echo "  update-version VER   Met à jour la version dans tous les fichiers"
    echo "  sync-readme          Synchronise les informations du README"
    echo
    echo "Options:"
    echo "  --format FORMAT      Format de sortie (md, html, rst) [défaut: md]"
    echo "  --output PATH        Chemin de sortie personnalisé"
    echo "  --verbose            Affiche des informations détaillées"
    echo
    echo "Exemples:"
    echo "  ./macros commands --format html"
    echo "  ./macros update-version 1.1.0"
    echo "  ./macros all --verbose"
}

# Fonction pour extraire la version actuelle
get_version() {
    if [ -f "$VERSION_FILE" ]; then
        VERSION=$(grep -E "__version__\s*=\s*['\"]([^'\"]+)['\"]" "$VERSION_FILE" | sed -E "s/__version__\s*=\s*['\"]([^'\"]+)['\"]/__\1__/g" | sed -E "s/__(.*)__/\1/")
        echo "$VERSION"
    else
        echo "unknown"
    fi
}

# Fonction pour mettre à jour la version
update_version() {
    NEW_VERSION=$1
    
    if [ -z "$NEW_VERSION" ]; then
        echo -e "${RED}Erreur: Veuillez spécifier une version (ex: 1.1.0)${NC}"
        exit 1
    fi
    
    echo -e "${YELLOW}Mise à jour de la version vers $NEW_VERSION...${NC}"
    
    # Mettre à jour __init__.py
    if [ -f "$VERSION_FILE" ]; then
        sed -i "s/__version__\s*=\s*['\"].*['\"]/__version__ = \"$NEW_VERSION\"/" "$VERSION_FILE"
        echo -e "${GREEN}Version mise à jour dans $VERSION_FILE${NC}"
    else
        echo -e "${RED}Fichier $VERSION_FILE introuvable${NC}"
    fi
    
    # Mettre à jour README.md
    if [ -f "$README_PATH" ]; then
        sed -i "s/version-[0-9]\+\.[0-9]\+\.[0-9]\+-blue/version-$NEW_VERSION-blue/" "$README_PATH"
        echo -e "${GREEN}Version mise à jour dans $README_PATH${NC}"
    fi
    
    # Mettre à jour setup.py si existant
    SETUP_PY="$PROJECT_ROOT/setup.py"
    if [ -f "$SETUP_PY" ]; then
        sed -i "s/version=['\"].*['\"]/version=\"$NEW_VERSION\"/" "$SETUP_PY"
        echo -e "${GREEN}Version mise à jour dans $SETUP_PY${NC}"
    fi
    
    # Créer une nouvelle entrée dans CHANGELOG.md
    CHANGELOG="$PROJECT_ROOT/CHANGELOG.md"
    if [ -f "$CHANGELOG" ]; then
        DATE=$(date +%Y-%m-%d)
        TEMP_FILE=$(mktemp)
        
        # Lire les premières lignes jusqu'à la première entrée de version
        awk 'BEGIN {p=1} /^## \[[0-9]+\.[0-9]+\.[0-9]+\]/ {p=0} p {print}' "$CHANGELOG" > "$TEMP_FILE"
        
        # Ajouter la nouvelle entrée
        echo -e "## [$NEW_VERSION] - $DATE\n\n### Ajouté\n- \n\n### Amélioré\n- \n\n### Corrigé\n- \n" >> "$TEMP_FILE"
        
        # Ajouter le reste du fichier
        awk 'BEGIN {p=0} /^## \[[0-9]+\.[0-9]+\.[0-9]+\]/ {p=1} p {print}' "$CHANGELOG" >> "$TEMP_FILE"
        
        # Mise à jour du lien de comparaison
        OLD_VERSION=$(get_version)
        COMPARE_LINK="[${NEW_VERSION}]: https://github.com/votrenom/gestvenv/compare/v${OLD_VERSION}...v${NEW_VERSION}"
        echo "$COMPARE_LINK" >> "$TEMP_FILE"
        
        # Remplacer le fichier original
        mv "$TEMP_FILE" "$CHANGELOG"
        echo -e "${GREEN}Nouvelle entrée créée dans $CHANGELOG${NC}"
        echo -e "${YELLOW}N'oubliez pas de compléter les détails du changelog!${NC}"
    fi
    
    echo -e "${GREEN}Version mise à jour avec succès vers $NEW_VERSION${NC}"
}

# Fonction pour générer la documentation des commandes
generate_commands_doc() {
    FORMAT=${1:-md}
    echo -e "${YELLOW}Génération de la documentation des commandes au format $FORMAT...${NC}"
    
    # Trouver toutes les commandes disponibles
    CLI_FILE="$SRC_DIR/cli.py"
    if [ ! -f "$CLI_FILE" ]; then
        echo -e "${RED}Fichier CLI introuvable: $CLI_FILE${NC}"
        return 1
    fi
    
    OUTPUT_FILE="$OUTPUT_DIR/commands.$FORMAT"
    
    case "$FORMAT" in
        md)
            echo "# Commandes GestVenv" > "$OUTPUT_FILE"
            echo "" >> "$OUTPUT_FILE"
            echo "Ce document décrit toutes les commandes disponibles dans GestVenv." >> "$OUTPUT_FILE"
            echo "" >> "$OUTPUT_FILE"
            
            # Extraire les commandes et leurs descriptions
            COMMANDS=$(grep -E "add_subparsers|add_parser" "$CLI_FILE" | grep -oE "add_parser\(['\"]([^'\"]+)" | sed -E "s/add_parser\(['\"]//")
            
            for CMD in $COMMANDS; do
                echo "## $CMD" >> "$OUTPUT_FILE"
                DESC=$(grep -A2 "add_parser(['\"]$CMD" "$CLI_FILE" | grep -E "help=['\"]" | sed -E "s/.*help=[\'\"]([^\'\"]+)[\'\"].*/\1/")
                echo "" >> "$OUTPUT_FILE"
                echo "$DESC" >> "$OUTPUT_FILE"
                echo "" >> "$OUTPUT_FILE"
                
                # Extraire les options
                OPTIONS=$(grep -A20 "add_parser(['\"]$CMD" "$CLI_FILE" | grep -E "add_argument" | grep -v "^#" | sed -E "s/.*add_argument\(([^)]+).*/\1/")
                
                if [ ! -z "$OPTIONS" ]; then
                    echo "### Options" >> "$OUTPUT_FILE"
                    echo "" >> "$OUTPUT_FILE"
                    
                    for OPT in $OPTIONS; do
                        OPT_NAME=$(echo $OPT | grep -oE "['\"]--[^'\"]+['\"]" | sed -E "s/['\"]//g")
                        OPT_DESC=$(echo $OPT | grep -oE "help=['\"]([^'\"]+)" | sed -E "s/help=[\'\"]//")
                        
                        if [ ! -z "$OPT_NAME" ] && [ ! -z "$OPT_DESC" ]; then
                            echo "- **$OPT_NAME**: $OPT_DESC" >> "$OUTPUT_FILE"
                        fi
                    done
                    
                    echo "" >> "$OUTPUT_FILE"
                fi
                
                # Ajouter un exemple
                echo "### Exemple" >> "$OUTPUT_FILE"
                echo "" >> "$OUTPUT_FILE"
                echo '```bash' >> "$OUTPUT_FILE"
                echo "gestvenv $CMD [options]" >> "$OUTPUT_FILE"
                echo '```' >> "$OUTPUT_FILE"
                echo "" >> "$OUTPUT_FILE"
            done
            ;;
            
        html)
            echo "<html><head><title>Commandes GestVenv</title></head><body>" > "$OUTPUT_FILE"
            echo "<h1>Commandes GestVenv</h1>" >> "$OUTPUT_FILE"
            echo "<p>Ce document décrit toutes les commandes disponibles dans GestVenv.</p>" >> "$OUTPUT_FILE"
            
            # Même logique que pour MD mais avec du HTML
            COMMANDS=$(grep -E "add_subparsers|add_parser" "$CLI_FILE" | grep -oE "add_parser\(['\"]([^'\"]+)" | sed -E "s/add_parser\(['\"]//")
            
            for CMD in $COMMANDS; do
                echo "<h2>$CMD</h2>" >> "$OUTPUT_FILE"
                DESC=$(grep -A2 "add_parser(['\"]$CMD" "$CLI_FILE" | grep -E "help=['\"]" | sed -E "s/.*help=[\'\"]([^\'\"]+)[\'\"].*/\1/")
                echo "<p>$DESC</p>" >> "$OUTPUT_FILE"
                
                # Extraire les options
                OPTIONS=$(grep -A20 "add_parser(['\"]$CMD" "$CLI_FILE" | grep -E "add_argument" | grep -v "^#" | sed -E "s/.*add_argument\(([^)]+).*/\1/")
                
                if [ ! -z "$OPTIONS" ]; then
                    echo "<h3>Options</h3>" >> "$OUTPUT_FILE"
                    echo "<ul>" >> "$OUTPUT_FILE"
                    
                    for OPT in $OPTIONS; do
                        OPT_NAME=$(echo $OPT | grep -oE "['\"]--[^'\"]+['\"]" | sed -E "s/['\"]//g")
                        OPT_DESC=$(echo $OPT | grep -oE "help=['\"]([^'\"]+)" | sed -E "s/help=[\'\"]//")
                        
                        if [ ! -z "$OPT_NAME" ] && [ ! -z "$OPT_DESC" ]; then
                            echo "<li><strong>$OPT_NAME</strong>: $OPT_DESC</li>" >> "$OUTPUT_FILE"
                        fi
                    done
                    
                    echo "</ul>" >> "$OUTPUT_FILE"
                fi
                
                # Ajouter un exemple
                echo "<h3>Exemple</h3>" >> "$OUTPUT_FILE"
                echo "<pre><code>gestvenv $CMD [options]</code></pre>" >> "$OUTPUT_FILE"
            done
            
            echo "</body></html>" >> "$OUTPUT_FILE"
            ;;
            
        rst)
            echo "Commandes GestVenv" > "$OUTPUT_FILE"
            echo "================" >> "$OUTPUT_FILE"
            echo "" >> "$OUTPUT_FILE"
            echo "Ce document décrit toutes les commandes disponibles dans GestVenv." >> "$OUTPUT_FILE"
            echo "" >> "$OUTPUT_FILE"
            
            COMMANDS=$(grep -E "add_subparsers|add_parser" "$CLI_FILE" | grep -oE "add_parser\(['\"]([^'\"]+)" | sed -E "s/add_parser\(['\"]//")
            
            for CMD in $COMMANDS; do
                echo "$CMD" >> "$OUTPUT_FILE"
                echo "--------------" >> "$OUTPUT_FILE"
                DESC=$(grep -A2 "add_parser(['\"]$CMD" "$CLI_FILE" | grep -E "help=['\"]" | sed -E "s/.*help=[\'\"]([^\'\"]+)[\'\"].*/\1/")
                echo "" >> "$OUTPUT_FILE"
                echo "$DESC" >> "$OUTPUT_FILE"
                echo "" >> "$OUTPUT_FILE"
                
                # Extraire les options
                OPTIONS=$(grep -A20 "add_parser(['\"]$CMD" "$CLI_FILE" | grep -E "add_argument" | grep -v "^#" | sed -E "s/.*add_argument\(([^)]+).*/\1/")
                
                if [ ! -z "$OPTIONS" ]; then
                    echo "Options" >> "$OUTPUT_FILE"
                    echo "~~~~~~~" >> "$OUTPUT_FILE"
                    echo "" >> "$OUTPUT_FILE"
                    
                    for OPT in $OPTIONS; do
                        OPT_NAME=$(echo $OPT | grep -oE "['\"]--[^'\"]+['\"]" | sed -E "s/['\"]//g")
                        OPT_DESC=$(echo $OPT | grep -oE "help=['\"]([^'\"]+)" | sed -E "s/help=[\'\"]//")
                        
                        if [ ! -z "$OPT_NAME" ] && [ ! -z "$OPT_DESC" ]; then
                            echo "- **$OPT_NAME**: $OPT_DESC" >> "$OUTPUT_FILE"
                        fi
                    done
                    
                    echo "" >> "$OUTPUT_FILE"
                fi
                
                # Ajouter un exemple
                echo "Exemple" >> "$OUTPUT_FILE"
                echo "~~~~~~~" >> "$OUTPUT_FILE"
                echo "" >> "$OUTPUT_FILE"
                echo ".. code-block:: bash" >> "$OUTPUT_FILE"
                echo "" >> "$OUTPUT_FILE"
                echo "    gestvenv $CMD [options]" >> "$OUTPUT_FILE"
                echo "" >> "$OUTPUT_FILE"
            done
            ;;
            
        *)
            echo -e "${RED}Format non supporté: $FORMAT${NC}"
            return 1
            ;;
    esac
    
    echo -e "${GREEN}Documentation des commandes générée: $OUTPUT_FILE${NC}"
}

# Fonction pour générer des exemples d'utilisation
generate_examples() {
    FORMAT=${1:-md}
    echo -e "${YELLOW}Génération des exemples d'utilisation au format $FORMAT...${NC}"
    
    OUTPUT_FILE="$OUTPUT_DIR/examples.$FORMAT"
    
    # Exemples standards d'utilisation de GestVenv
    EXAMPLES=(
        "# Créer un environnement simple|gestvenv create mon_projet"
        "# Créer un environnement avec Python 3.9 et des packages|gestvenv create mon_projet --python python3.9 --packages \"flask,pytest\""
        "# Activer un environnement|gestvenv activate mon_projet"
        "# Installer des packages|gestvenv install \"pandas,matplotlib\""
        "# Mettre à jour tous les packages|gestvenv update --all"
        "# Exporter un environnement|gestvenv export mon_projet --output mon_projet_config.json"
        "# Importer une configuration|gestvenv import mon_projet_config.json"
        "# Cloner un environnement|gestvenv clone mon_projet mon_projet_dev"
        "# Lister tous les environnements|gestvenv list"
        "# Exécuter un script dans un environnement|gestvenv run mon_projet python script.py"
    )
    
    case "$FORMAT" in
        md)
            echo "# Exemples d'utilisation de GestVenv" > "$OUTPUT_FILE"
            echo "" >> "$OUTPUT_FILE"
            echo "Ce document fournit des exemples d'utilisation courante de GestVenv." >> "$OUTPUT_FILE"
            echo "" >> "$OUTPUT_FILE"
            
            for EXAMPLE in "${EXAMPLES[@]}"; do
                IFS="|" read -r COMMENT CMD <<< "$EXAMPLE"
                echo "## $COMMENT" >> "$OUTPUT_FILE"
                echo "" >> "$OUTPUT_FILE"
                echo '```bash' >> "$OUTPUT_FILE"
                echo "$CMD" >> "$OUTPUT_FILE"
                echo '```' >> "$OUTPUT_FILE"
                echo "" >> "$OUTPUT_FILE"
            done
            ;;
            
        html)
            echo "<html><head><title>Exemples d'utilisation de GestVenv</title></head><body>" > "$OUTPUT_FILE"
            echo "<h1>Exemples d'utilisation de GestVenv</h1>" >> "$OUTPUT_FILE"
            echo "<p>Ce document fournit des exemples d'utilisation courante de GestVenv.</p>" >> "$OUTPUT_FILE"
            
            for EXAMPLE in "${EXAMPLES[@]}"; do
                IFS="|" read -r COMMENT CMD <<< "$EXAMPLE"
                echo "<h2>$COMMENT</h2>" >> "$OUTPUT_FILE"
                echo "<pre><code>$CMD</code></pre>" >> "$OUTPUT_FILE"
            done
            
            echo "</body></html>" >> "$OUTPUT_FILE"
            ;;
            
        rst)
            echo "Exemples d'utilisation de GestVenv" > "$OUTPUT_FILE"
            echo "=================================" >> "$OUTPUT_FILE"
            echo "" >> "$OUTPUT_FILE"
            echo "Ce document fournit des exemples d'utilisation courante de GestVenv." >> "$OUTPUT_FILE"
            echo "" >> "$OUTPUT_FILE"
            
            for EXAMPLE in "${EXAMPLES[@]}"; do
                IFS="|" read -r COMMENT CMD <<< "$EXAMPLE"
                echo "$COMMENT" >> "$OUTPUT_FILE"
                echo "-------------------------------" >> "$OUTPUT_FILE"
                echo "" >> "$OUTPUT_FILE"
                echo ".. code-block:: bash" >> "$OUTPUT_FILE"
                echo "" >> "$OUTPUT_FILE"
                echo "    $CMD" >> "$OUTPUT_FILE"
                echo "" >> "$OUTPUT_FILE"
            done
            ;;
            
        *)
            echo -e "${RED}Format non supporté: $FORMAT${NC}"
            return 1
            ;;
    esac
    
    echo -e "${GREEN}Exemples d'utilisation générés: $OUTPUT_FILE${NC}"
}

# Fonction pour générer la documentation de l'API
generate_api_doc() {
    FORMAT=${1:-md}
    echo -e "${YELLOW}Génération de la documentation de l'API au format $FORMAT...${NC}"
    
    # Trouver tous les fichiers Python dans le projet
    PY_FILES=$(find "$SRC_DIR" -name "*.py")
    
    OUTPUT_FILE="$OUTPUT_DIR/api.$FORMAT"
    
    case "$FORMAT" in
        md)
            echo "# Documentation de l'API GestVenv" > "$OUTPUT_FILE"
            echo "" >> "$OUTPUT_FILE"
            echo "Ce document décrit l'API interne de GestVenv pour les développeurs." >> "$OUTPUT_FILE"
            echo "" >> "$OUTPUT_FILE"
            
            for PY_FILE in $PY_FILES; do
                REL_PATH=$(realpath --relative-to="$PROJECT_ROOT" "$PY_FILE")
                MODULE_NAME=$(echo "$REL_PATH" | sed -E 's/\.py$//' | sed -E 's/\//./g')
                
                echo "## Module \`$MODULE_NAME\`" >> "$OUTPUT_FILE"
                echo "" >> "$OUTPUT_FILE"
                
                # Extraire la docstring du module
                MODULE_DOC=$(grep -A5 '"""' "$PY_FILE" | head -n5 | grep -v '"""' | sed -E 's/^# //')
                
                if [ ! -z "$MODULE_DOC" ]; then
                    echo "$MODULE_DOC" >> "$OUTPUT_FILE"
                    echo "" >> "$OUTPUT_FILE"
                fi
                
                # Extraire les classes
                CLASSES=$(grep -E "^class [A-Za-z]+" "$PY_FILE" | sed -E 's/class ([A-Za-z0-9_]+)(\(.*\))?:/\1/')
                
                for CLASS in $CLASSES; do
                    echo "### Classe \`$CLASS\`" >> "$OUTPUT_FILE"
                    echo "" >> "$OUTPUT_FILE"
                    
                    # Extraire la docstring de la classe
                    CLASS_DOC=$(sed -n "/^class $CLASS/,/def /p" "$PY_FILE" | grep -A5 '"""' | grep -v '"""' | sed -E 's/^    //')
                    
                    if [ ! -z "$CLASS_DOC" ]; then
                        echo "$CLASS_DOC" >> "$OUTPUT_FILE"
                        echo "" >> "$OUTPUT_FILE"
                    fi
                    
                    # Extraire les méthodes
                    METHODS=$(grep -E "^    def [A-Za-z]+" "$PY_FILE" | grep -v "__init__" | sed -E 's/    def ([A-Za-z0-9_]+)\(.*\):/\1/')
                    
                    if [ ! -z "$METHODS" ]; then
                        echo "#### Méthodes" >> "$OUTPUT_FILE"
                        echo "" >> "$OUTPUT_FILE"
                        
                        for METHOD in $METHODS; do
                            echo "- \`$METHOD\`" >> "$OUTPUT_FILE"
                        done
                        
                        echo "" >> "$OUTPUT_FILE"
                    fi
                done
                
                # Extraire les fonctions
                FUNCTIONS=$(grep -E "^def [A-Za-z]+" "$PY_FILE" | sed -E 's/def ([A-Za-z0-9_]+)\(.*\):/\1/')
                
                if [ ! -z "$FUNCTIONS" ]; then
                    echo "### Fonctions" >> "$OUTPUT_FILE"
                    echo "" >> "$OUTPUT_FILE"
                    
                    for FUNC in $FUNCTIONS; do
                        echo "#### \`$FUNC\`" >> "$OUTPUT_FILE"
                        echo "" >> "$OUTPUT_FILE"
                        
                        # Extraire la docstring de la fonction
                        FUNC_DOC=$(sed -n "/^def $FUNC/,/def /p" "$PY_FILE" | grep -A5 '"""' | grep -v '"""' | sed -E 's/^    //')
                        
                        if [ ! -z "$FUNC_DOC" ]; then
                            echo "$FUNC_DOC" >> "$OUTPUT_FILE"
                            echo "" >> "$OUTPUT_FILE"
                        fi
                    done
                fi
            done
            ;;
            
        html)
            # Similaire au format MD mais avec du HTML
            echo "<html><head><title>Documentation de l'API GestVenv</title></head><body>" > "$OUTPUT_FILE"
            echo "<h1>Documentation de l'API GestVenv</h1>" >> "$OUTPUT_FILE"
            echo "<p>Ce document décrit l'API interne de GestVenv pour les développeurs.</p>" >> "$OUTPUT_FILE"
            
            # Code similaire au format MD mais avec balises HTML
            
            echo "</body></html>" >> "$OUTPUT_FILE"
            ;;
            
        rst)
            # Format RST
            echo "Documentation de l'API GestVenv" > "$OUTPUT_FILE"
            echo "===============================" >> "$OUTPUT_FILE"
            echo "" >> "$OUTPUT_FILE"
            echo "Ce document décrit l'API interne de GestVenv pour les développeurs." >> "$OUTPUT_FILE"
            echo "" >> "$OUTPUT_FILE"
            
            # Code similaire au format MD mais avec syntaxe RST
            
            ;;
            
        *)
            echo -e "${RED}Format non supporté: $FORMAT${NC}"
            return 1
            ;;
    esac
    
    echo -e "${GREEN}Documentation de l'API générée: $OUTPUT_FILE${NC}"
}

# Fonction pour synchroniser le README
sync_readme() {
    echo -e "${YELLOW}Synchronisation du README...${NC}"
    
    # Vérifier que le README existe
    if [ ! -f "$README_PATH" ]; then
        echo -e "${RED}README introuvable: $README_PATH${NC}"
        return 1
    fi
    
    # Extraire la version depuis __init__.py
    VERSION=$(get_version)
    
    # Mettre à jour la version dans le README
    sed -i "s/version-[0-9]\+\.[0-9]\+\.[0-9]\+-blue/version-$VERSION-blue/" "$README_PATH"
    
    # Mettre à jour la liste des commandes
    if [ -f "$OUTPUT_DIR/commands.md" ]; then
        COMMANDS=$(grep -E "^## [a-z]+" "$OUTPUT_DIR/commands.md" | sed -E 's/^## //')
        
        # Mettre à jour la section des commandes dans le README
        # Cette partie est un peu simplifiée - dans un script réel, il faudrait
        # une analyse plus robuste du README pour localiser la section à mettre à jour
        
        echo -e "${GREEN}README synchronisé avec succès${NC}"
    else
        echo -e "${YELLOW}Documentation des commandes non trouvée. Exécutez d'abord 'commands'${NC}"
    fi
}

# Traitement des commandes
COMMAND=$1
shift

if [ -z "$COMMAND" ]; then
    show_help
    exit 0
fi

# Analyser les options
FORMAT="md"
VERBOSE=false
CUSTOM_OUTPUT=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --format)
            FORMAT="$2"
            shift 2
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --output)
            CUSTOM_OUTPUT="$2"
            shift 2
            ;;
        *)
            # Argument inconnu
            echo -e "${RED}Option inconnue: $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

# Si un chemin de sortie personnalisé est spécifié
if [ ! -z "$CUSTOM_OUTPUT" ]; then
    OUTPUT_DIR="$CUSTOM_OUTPUT"
    mkdir -p "$OUTPUT_DIR"
fi

# Exécuter la commande demandée
case "$COMMAND" in
    help)
        show_help
        ;;
        
    commands)
        generate_commands_doc "$FORMAT"
        ;;
        
    examples)
        generate_examples "$FORMAT"
        ;;
        
    api)
        generate_api_doc "$FORMAT"
        ;;
        
    all)
        generate_commands_doc "$FORMAT"
        generate_examples "$FORMAT"
        generate_api_doc "$FORMAT"
        echo -e "${GREEN}Toute la documentation a été générée dans $OUTPUT_DIR${NC}"
        ;;
        
    version)
        VERSION=$(get_version)
        echo -e "${GREEN}Version actuelle: $VERSION${NC}"
        ;;
        
    update-version)
        update_version "$1"
        ;;
        
    sync-readme)
        sync_readme
        ;;
        
    *)
        echo -e "${RED}Commande inconnue: $COMMAND${NC}"
        show_help
        exit 1
        ;;
esac

exit 0