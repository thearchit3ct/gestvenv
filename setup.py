
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
import os
import re

# Lire la version depuis le fichier __init__.py
with open('gestvenv/__init__.py', 'r', encoding='utf-8') as f:
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", f.read(), re.M)
    if version_match:
        version = version_match.group(1)
    else:
        version = '1.0.0'  # Par défaut si non trouvée

# Lire le contenu du README
with open('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()

# Assurer que les répertoires requis existent
for directory in ['gestvenv/core', 'gestvenv/utils', 'gestvenv/templates', 'gestvenv/tests']:
    os.makedirs(directory, exist_ok=True)
    # Créer les fichiers __init__.py s'ils n'existent pas
    init_file = os.path.join(directory, '__init__.py')
    if not os.path.exists(init_file):
        with open(init_file, 'w') as f:
            f.write('"""GestVenv package."""')

setup(
    name="gestvenv",
    version=version,
    author="Votre nom",
    author_email="votre.email@exemple.com",
    description="Gestionnaire d'Environnements Virtuels Python",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/votrenom/gestvenv",
    project_urls={
        "Bug Tracker": "https://github.com/votrenom/gestvenv/issues",
        "Documentation": "https://github.com/votrenom/gestvenv/wiki",
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Utilities",
    ],
    packages=find_packages(),
    package_data={
        "gestvenv.templates": ["*.json"],
    },
    include_package_data=True,
    python_requires=">=3.7",
    install_requires=[
        "argparse",
    ],
    entry_points={
        "console_scripts": [
            "gestvenv=gestvenv.cli:main",
        ],
    },
    license="MIT",
    keywords=["virtual environment", "python", "venv", "environment manager"],
    # Options setup.py
    setup_requires=['wheel'],
    zip_safe=False,
)
