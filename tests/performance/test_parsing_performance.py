"""
Tests de performance pour le parsing de fichiers GestVenv v2.0
"""

import pytest
import time
import tempfile
from pathlib import Path

from gestvenv.utils.toml_handler import TomlHandler
from gestvenv.utils.requirements_parser import RequirementsParser


class TestParsingPerformance:
    """Tests de performance pour le parsing"""
    
    @pytest.fixture
    def temp_dir(self):
        """Cree un repertoire temporaire"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    def create_simple_toml(self, path: Path) -> Path:
        """Cree un fichier TOML simple"""
        content = '''
[project]
name = "test-project"
version = "1.0.0"

[project.dependencies]
requests = "^2.28.0"
click = ">=8.0"
'''
        toml_file = path / "pyproject.toml"
        toml_file.write_text(content)
        return toml_file
    
    def create_simple_requirements(self, path: Path) -> Path:
        """Cree un fichier requirements.txt simple"""
        content = '''requests==2.28.0
click>=8.0
pandas>=1.0.0
'''
        req_file = path / "requirements.txt"
        req_file.write_text(content)
        return req_file
    
    @pytest.mark.benchmark
    def test_toml_parsing_performance(self, temp_dir):
        """Test de performance basique pour le parsing TOML"""
        handler = TomlHandler()
        toml_file = self.create_simple_toml(temp_dir)
        
        # Mesurer le parsing
        start = time.perf_counter()
        data = handler.load(toml_file)
        duration = time.perf_counter() - start
        
        # Verifications
        assert data is not None
        assert "project" in data
        assert duration < 0.1, f"Parsing TOML trop lent: {duration}s"
    
    @pytest.mark.benchmark
    def test_requirements_parsing_performance(self, temp_dir):
        """Test de performance basique pour le parsing requirements"""
        parser = RequirementsParser()
        req_file = self.create_simple_requirements(temp_dir)
        
        # Mesurer le parsing
        start = time.perf_counter()
        deps = parser.parse_file(str(req_file))
        duration = time.perf_counter() - start
        
        # Verifications
        assert len(deps) == 3
        assert duration < 0.1, f"Parsing requirements trop lent: {duration}s"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])