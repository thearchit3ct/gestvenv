"""
GestVenv CLI Module

Ce module expose l'interface CLI de GestVenv.
Les commandes sont définies dans cli_main.py.
"""

def main():
    """Point d'entrée principal pour la CLI"""
    # Import différé pour éviter les imports circulaires
    from gestvenv.cli_main import main as _main
    return _main()

def get_cli():
    """Obtenir l'objet CLI click"""
    from gestvenv.cli_main import cli
    return cli

# Pour compatibilité, cli est accessible via get_cli()
# mais ne doit pas être importé directement au niveau module
__all__ = ['main', 'get_cli']
