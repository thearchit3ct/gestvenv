"""Tests pour le module utils.format_utils."""

import pytest
from datetime import datetime
from pytest import MonkeyPatch
import time

from gestvenv.utils.format_utils import (
    format_timestamp, truncate_string, format_list_as_table,
    get_color_for_terminal, format_size, format_duration
)

class TestFormatUtils:
    """Tests pour les fonctions utilitaires de formatage."""
    
    def test_format_timestamp(self) -> None:
        """Teste le formatage des timestamps."""
        # Timestamp sous forme de float (timestamp UNIX)
        ts_float = time.time()
        formatted = format_timestamp(ts_float)
        assert isinstance(formatted, str)
        assert ":" in formatted  # Format standard avec heures:minutes:secondes
        
        # Timestamp sous forme de str (ISO)
        ts_str = datetime.now().isoformat()
        formatted = format_timestamp(ts_str)
        assert isinstance(formatted, str)
        
        # Timestamp sous forme de datetime
        ts_dt = datetime.now()
        formatted = format_timestamp(ts_dt)
        assert isinstance(formatted, str)
        
        # Format personnalisé
        custom_format = "%Y-%m-%d"
        formatted = format_timestamp(ts_dt, format_str=custom_format)
        assert len(formatted) == 10  # YYYY-MM-DD = 10 caractères
        assert "-" in formatted
    
    def test_truncate_string(self) -> None:
        """Teste la troncature des chaînes."""
        # Chaîne courte (ne devrait pas être tronquée)
        short_str = "Short string"
        truncated = truncate_string(short_str, max_length=20)
        assert truncated == short_str
        
        # Chaîne longue (devrait être tronquée)
        long_str = "This is a very long string that should be truncated"
        truncated = truncate_string(long_str, max_length=20)
        assert len(truncated) <= 20
        assert truncated.endswith("...")
        
        # Suffixe personnalisé
        truncated = truncate_string(long_str, max_length=20, suffix="[...]")
        assert truncated.endswith("[...]")
    
    def test_format_list_as_table(self) -> None:
        """Teste le formatage des listes en tableaux textuels."""
        # Liste de dictionnaires
        data = [
            {"name": "Item 1", "value": 100},
            {"name": "Item 2", "value": 200},
            {"name": "Item 3", "value": 300}
        ]
        
        # Formatage avec en-tête
        table = format_list_as_table(data)
        assert len(table) >= 3  # En-tête + séparateur + lignes de données
        
        # Vérifier que les colonnes sont alignées
        assert "name" in table[0]
        assert "value" in table[0]
        
        # Formatage sans en-tête
        table = format_list_as_table(data, header=False)
        assert len(table) == 3  # Juste les lignes de données
        
        # Colonnes spécifiques
        table = format_list_as_table(data, columns=["name"])
        assert "name" in table[0]
        assert "value" not in table[0]
        
        # Liste vide
        table = format_list_as_table([])
        assert table == []
    
    def test_get_color_for_terminal(self, monkeypatch: MonkeyPatch) -> None:
        """Teste la récupération des codes couleur pour le terminal."""
        # Simuler un terminal qui supporte les couleurs
        monkeypatch.setattr('gestvenv.utils.format_utils._supports_color', lambda: True)
        
        # Couleurs valides
        assert get_color_for_terminal("red") != ""
        assert get_color_for_terminal("green") != ""
        assert get_color_for_terminal("bold") != ""
        
        # Couleur invalide
        assert get_color_for_terminal("invalid_color") == ""
        
        # Terminal qui ne supporte pas les couleurs
        monkeypatch.setattr('gestvenv.utils.format_utils._supports_color', lambda: False)
        assert get_color_for_terminal("red") == ""
    
    def test_format_size(self) -> None:
        """Teste le formatage des tailles en octets."""
        # Octets
        assert "B" in format_size(500)
        
        # Kibioctets
        assert "KiB" in format_size(1500)
        
        # Mébioctets
        assert "MiB" in format_size(1500 * 1024)
        
        # Gibioctets
        assert "GiB" in format_size(1500 * 1024 * 1024)
        
        # Valeur négative (devrait lever une exception)
        with pytest.raises(ValueError):
            format_size(-100)
    
    def test_format_duration(self) -> None:
        """Teste le formatage des durées en secondes."""
        # Millisecondes
        assert "ms" in format_duration(0.5)
        
        # Secondes
        assert "s" in format_duration(5)
        
        # Minutes et secondes
        duration = format_duration(125)  # 2min 5sec
        assert "m" in duration
        assert "s" in duration
        
        # Heures, minutes et secondes
        duration = format_duration(3725)  # 1h 2min 5sec
        assert "h" in duration
        assert "m" in duration
        assert "s" in duration
        
        # Valeur négative (devrait lever une exception)
        with pytest.raises(ValueError):
            format_duration(-10)