"""
Module d'importation simplifiée pour les environnements éphémères
"""

def ephemeral(*args, **kwargs):
    """Import lazy des environnements éphémères"""
    from gestvenv.core.ephemeral import ephemeral as _ephemeral
    return _ephemeral(*args, **kwargs)

def ephemeral_sync(*args, **kwargs):
    """Import lazy de la version synchrone"""
    from gestvenv.core.ephemeral import ephemeral_sync as _ephemeral_sync
    return _ephemeral_sync(*args, **kwargs)

# Exports pour compatibilité
__all__ = ['ephemeral', 'ephemeral_sync']