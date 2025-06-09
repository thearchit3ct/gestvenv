"""
Utilitaires de formatage et d'affichage pour GestVenv v1.1.
Formatage des tailles, durées, tableaux, couleurs.
"""

import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class Colors:
    """Codes couleurs ANSI pour le terminal."""
    
    # Couleurs de base
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # Couleurs vives
    BRIGHT_BLACK = '\033[90m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'
    
    # Styles
    BOLD = '\033[1m'
    DIM = '\033[2m'
    ITALIC = '\033[3m'
    UNDERLINE = '\033[4m'
    BLINK = '\033[5m'
    REVERSE = '\033[7m'
    STRIKETHROUGH = '\033[9m'
    
    # Reset
    RESET = '\033[0m'
    END = '\033[0m'

class FormatUtils:
    """Utilitaires de formatage et d'affichage."""
    
    @staticmethod
    def format_size(size_bytes: int, decimal_places: int = 2) -> str:
        """
        Formate une taille en bytes dans une unité lisible.
        
        Args:
            size_bytes: Taille en bytes
            decimal_places: Nombre de décimales
            
        Returns:
            Taille formatée (ex: "1.5 GB")
        """
        if size_bytes < 0:
            return "0 B"
        
        units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
        size = float(size_bytes)
        unit_index = 0
        
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        
        if unit_index == 0:  # Bytes
            return f"{int(size)} {units[unit_index]}"
        else:
            return f"{size:.{decimal_places}f} {units[unit_index]}"
    
    @staticmethod
    def format_duration(seconds: float, precise: bool = False) -> str:
        """
        Formate une durée en secondes dans une unité lisible.
        
        Args:
            seconds: Durée en secondes
            precise: Affichage précis ou approximatif
            
        Returns:
            Durée formatée (ex: "2m 30s", "1.5 minutes")
        """
        if seconds < 0:
            return "0s"
        
        if seconds < 1:
            if precise:
                return f"{seconds*1000:.0f}ms"
            return "< 1s"
        
        if seconds < 60:
            return f"{seconds:.1f}s" if precise else f"{int(seconds)}s"
        
        minutes = int(seconds // 60)
        remaining_seconds = int(seconds % 60)
        
        if minutes < 60:
            if precise:
                return f"{minutes}m {remaining_seconds}s"
            return f"{minutes}m" if remaining_seconds < 30 else f"{minutes+1}m"
        
        hours = int(minutes // 60)
        remaining_minutes = int(minutes % 60)
        
        if hours < 24:
            if precise:
                return f"{hours}h {remaining_minutes}m"
            return f"{hours}h"
        
        days = int(hours // 24)
        remaining_hours = int(hours % 24)
        
        if precise:
            return f"{days}d {remaining_hours}h"
        return f"{days}d"
    
    @staticmethod
    def format_table(data: List[Dict[str, Any]], headers: Optional[List[str]] = None,
                     max_width: int = 80, show_index: bool = False) -> str:
        """
        Formate des données en tableau ASCII.
        
        Args:
            data: Données à afficher
            headers: En-têtes des colonnes (auto-détectés si None)
            max_width: Largeur maximale du tableau
            show_index: Afficher un index numérique
            
        Returns:
            Tableau formaté en chaîne
        """
        if not data:
            return "Aucune donnée à afficher"
        
        # Déterminer les en-têtes
        if headers is None:
            headers = list(data[0].keys())
        
        # Ajouter l'index si demandé
        if show_index:
            headers = ['#'] + headers
            for i, row in enumerate(data):
                row = {'#': str(i + 1), **row}
                data[i] = row
        
        # Calculer la largeur des colonnes
        col_widths = {}
        for header in headers:
            col_widths[header] = len(str(header))
        
        for row in data:
            for header in headers:
                value = str(row.get(header, ''))
                col_widths[header] = max(col_widths[header], len(value))
        
        # Ajuster les largeurs si nécessaire
        total_width = sum(col_widths.values()) + len(headers) * 3 + 1
        if total_width > max_width:
            # Réduire les colonnes proportionnellement
            reduction = (total_width - max_width) / len(headers)
            for header in headers:
                col_widths[header] = max(8, int(col_widths[header] - reduction))
        
        # Construire le tableau
        lines = []
        
        # Ligne d'en-tête
        header_line = '|'
        separator_line = '+'
        for header in headers:
            width = col_widths[header]
            header_line += f" {header:<{width}} |"
            separator_line += '-' * (width + 2) + '+'
        
        lines.append(separator_line)
        lines.append(header_line)
        lines.append(separator_line)
        
        # Lignes de données
        for row in data:
            data_line = '|'
            for header in headers:
                width = col_widths[header]
                value = str(row.get(header, ''))
                # Tronquer si trop long
                if len(value) > width:
                    value = value[:width-3] + '...'
                data_line += f" {value:<{width}} |"
            lines.append(data_line)
        
        lines.append(separator_line)
        
        return '\n'.join(lines)
    
    @staticmethod
    def colorize(text: str, color: str, bold: bool = False) -> str:
        """
        Ajoute des couleurs à un texte pour le terminal.
        
        Args:
            text: Texte à coloriser
            color: Couleur (nom ou code ANSI)
            bold: Texte en gras
            
        Returns:
            Texte colorisé
        """
        # Mapping des couleurs par nom
        color_map = {
            'black': Colors.BLACK,
            'red': Colors.RED,
            'green': Colors.GREEN,
            'yellow': Colors.YELLOW,
            'blue': Colors.BLUE,
            'magenta': Colors.MAGENTA,
            'cyan': Colors.CYAN,
            'white': Colors.WHITE,
            'bright_red': Colors.BRIGHT_RED,
            'bright_green': Colors.BRIGHT_GREEN,
            'bright_yellow': Colors.BRIGHT_YELLOW,
            'bright_blue': Colors.BRIGHT_BLUE,
            'bright_magenta': Colors.BRIGHT_MAGENTA,
            'bright_cyan': Colors.BRIGHT_CYAN,
        }
        
        # Récupérer le code couleur
        color_code = color_map.get(color.lower(), color)
        
        # Construire le texte colorisé
        result = color_code
        if bold:
            result += Colors.BOLD
        result += text + Colors.RESET
        
        return result
    
    @staticmethod
    def format_progress_bar(current: int, total: int, width: int = 50, 
                           filled_char: str = '█', empty_char: str = '░') -> str:
        """
        Crée une barre de progression ASCII.
        
        Args:
            current: Valeur actuelle
            total: Valeur totale
            width: Largeur de la barre
            filled_char: Caractère de remplissage
            empty_char: Caractère vide
            
        Returns:
            Barre de progression formatée
        """
        if total <= 0:
            return f"[{empty_char * width}] 0%"
        
        percentage = min(100, (current / total) * 100)
        filled_width = int((current / total) * width)
        empty_width = width - filled_width
        
        bar = filled_char * filled_width + empty_char * empty_width
        return f"[{bar}] {percentage:.1f}%"
    
    @staticmethod
    def format_list(items: List[str], style: str = "bullet", 
                   indent: int = 2, max_items: Optional[int] = None) -> str:
        """
        Formate une liste d'éléments.
        
        Args:
            items: Liste d'éléments
            style: Style de la liste ('bullet', 'number', 'dash')
            indent: Indentation en espaces
            max_items: Nombre maximum d'éléments à afficher
            
        Returns:
            Liste formatée
        """
        if not items:
            return "Aucun élément"
        
        # Limiter le nombre d'éléments si nécessaire
        display_items = items[:max_items] if max_items else items
        
        # Choisir le marqueur selon le style
        if style == "bullet":
            marker = "•"
        elif style == "number":
            marker = None  # Sera remplacé par le numéro
        elif style == "dash":
            marker = "-"
        else:
            marker = "•"
        
        # Construire la liste
        lines = []
        indent_str = " " * indent
        
        for i, item in enumerate(display_items):
            if style == "number":
                prefix = f"{i + 1}."
            else:
                prefix = marker
            
            lines.append(f"{indent_str}{prefix} {item}")
        
        # Ajouter un indicateur si des éléments sont tronqués
        if max_items and len(items) > max_items:
            remaining = len(items) - max_items
            lines.append(f"{indent_str}... et {remaining} élément(s) de plus")
        
        return '\n'.join(lines)
    
    @staticmethod
    def format_timestamp(timestamp: Optional[Union[datetime, float, int]] = None,
                        format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
        """
        Formate un timestamp en chaîne lisible.
        
        Args:
            timestamp: Timestamp à formater (datetime, timestamp Unix ou None pour maintenant)
            format_str: Format de sortie
            
        Returns:
            Timestamp formaté
        """
        if timestamp is None:
            dt = datetime.now()
        elif isinstance(timestamp, datetime):
            dt = timestamp
        elif isinstance(timestamp, (int, float)):
            dt = datetime.fromtimestamp(timestamp)
        else:
            return "Timestamp invalide"
        
        try:
            return dt.strftime(format_str)
        except Exception as e:
            logger.error(f"Erreur formatage timestamp: {e}")
            return str(dt)

# Fonctions utilitaires pour compatibilité
def format_size(size_bytes: int) -> str:
    """Fonction utilitaire pour formater une taille."""
    return FormatUtils.format_size(size_bytes)

def format_duration(seconds: float) -> str:
    """Fonction utilitaire pour formater une durée."""
    return FormatUtils.format_duration(seconds)

def format_table(data: List[Dict[str, Any]]) -> str:
    """Fonction utilitaire pour formater un tableau."""
    return FormatUtils.format_table(data)
