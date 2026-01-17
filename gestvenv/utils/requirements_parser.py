"""
Parser de fichiers requirements.txt pour GestVenv v2.0
"""

import re
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass


@dataclass
class Requirement:
    """Représente une dépendance parsée"""
    name: str
    version_spec: Optional[str] = None
    extras: List[str] = None
    markers: Optional[str] = None
    editable: bool = False
    url: Optional[str] = None

    def __post_init__(self):
        if self.extras is None:
            self.extras = []

    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire"""
        return {
            "name": self.name,
            "version_spec": self.version_spec,
            "extras": self.extras,
            "markers": self.markers,
            "editable": self.editable,
            "url": self.url
        }


class RequirementsParser:
    """Parser pour fichiers requirements.txt"""

    # Pattern pour parser une ligne requirements.txt
    # Gère: package==1.0, package>=1.0, package[extra]>=1.0, -e git+url
    REQUIREMENT_PATTERN = re.compile(
        r'^'
        r'(?P<editable>-e\s+)?'  # -e pour editable
        r'(?P<name>[a-zA-Z0-9][-a-zA-Z0-9._]*)'  # nom du package
        r'(?:\[(?P<extras>[^\]]+)\])?'  # extras optionnels [extra1,extra2]
        r'(?P<version_spec>(?:[<>=!~]=?|@)[^;#\s]*)?'  # version spec
        r'(?:\s*;\s*(?P<markers>[^#]*))?'  # markers optionnels
        r'(?:\s*#.*)?'  # commentaires
        r'$'
    )

    URL_PATTERN = re.compile(
        r'^'
        r'(?P<editable>-e\s+)?'
        r'(?P<url>(?:git\+|hg\+|svn\+|bzr\+)?(?:https?|git|ssh)://[^\s#]+)'
        r'(?:#egg=(?P<name>[a-zA-Z0-9][-a-zA-Z0-9._]*))?'
        r'(?:\s*#.*)?'
        r'$'
    )

    def __init__(self):
        self.requirements: List[Requirement] = []

    def parse_file(self, file_path: str) -> List[Requirement]:
        """Parse un fichier requirements.txt

        Args:
            file_path: Chemin vers le fichier requirements.txt

        Returns:
            Liste des dépendances parsées
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Fichier non trouvé: {file_path}")

        content = path.read_text(encoding='utf-8')
        return self.parse_string(content)

    def parse_string(self, content: str) -> List[Requirement]:
        """Parse une chaîne au format requirements.txt

        Args:
            content: Contenu au format requirements.txt

        Returns:
            Liste des dépendances parsées
        """
        self.requirements = []

        for line in content.splitlines():
            line = line.strip()

            # Ignorer les lignes vides et commentaires
            if not line or line.startswith('#'):
                continue

            # Ignorer les options pip (-i, --index-url, etc.)
            if line.startswith('-') and not line.startswith('-e'):
                continue

            # Gérer les fichiers inclus (-r other.txt)
            if line.startswith('-r ') or line.startswith('--requirement '):
                continue

            req = self._parse_line(line)
            if req:
                self.requirements.append(req)

        return self.requirements

    def _parse_line(self, line: str) -> Optional[Requirement]:
        """Parse une ligne unique

        Args:
            line: Ligne à parser

        Returns:
            Requirement ou None si parsing échoue
        """
        # Essayer d'abord le pattern URL
        url_match = self.URL_PATTERN.match(line)
        if url_match:
            groups = url_match.groupdict()
            return Requirement(
                name=groups.get('name') or self._extract_name_from_url(groups['url']),
                url=groups['url'],
                editable=bool(groups.get('editable'))
            )

        # Essayer le pattern standard
        match = self.REQUIREMENT_PATTERN.match(line)
        if match:
            groups = match.groupdict()
            extras = []
            if groups.get('extras'):
                extras = [e.strip() for e in groups['extras'].split(',')]

            return Requirement(
                name=groups['name'],
                version_spec=groups.get('version_spec'),
                extras=extras,
                markers=groups.get('markers', '').strip() or None,
                editable=bool(groups.get('editable'))
            )

        return None

    def _extract_name_from_url(self, url: str) -> str:
        """Extrait le nom du package depuis une URL

        Args:
            url: URL du package

        Returns:
            Nom extrait ou 'unknown'
        """
        # Essayer d'extraire depuis le path
        if '/' in url:
            path_part = url.rstrip('/').split('/')[-1]
            # Enlever l'extension .git si présente
            if path_part.endswith('.git'):
                path_part = path_part[:-4]
            if path_part:
                return path_part
        return 'unknown'

    def to_dict_list(self) -> List[Dict[str, Any]]:
        """Convertit les requirements en liste de dictionnaires

        Returns:
            Liste de dictionnaires représentant les requirements
        """
        return [req.to_dict() for req in self.requirements]

    def get_package_names(self) -> List[str]:
        """Retourne la liste des noms de packages

        Returns:
            Liste des noms de packages
        """
        return [req.name for req in self.requirements]

    def to_pip_format(self) -> str:
        """Convertit les requirements en format pip

        Returns:
            Chaîne au format requirements.txt
        """
        lines = []
        for req in self.requirements:
            line = req.name
            if req.extras:
                line += f"[{','.join(req.extras)}]"
            if req.version_spec:
                line += req.version_spec
            if req.markers:
                line += f" ; {req.markers}"
            lines.append(line)
        return '\n'.join(lines)
