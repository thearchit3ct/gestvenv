"""
Exceptions pour le système d'environnements éphémères
"""

from ..exceptions import GestVenvError


class EphemeralException(GestVenvError):
    """Exception de base pour les environnements éphémères"""
    pass


class ResourceExhaustedException(EphemeralException):
    """Exception levée quand les ressources sont épuisées"""
    pass


class EnvironmentCreationException(EphemeralException):
    """Exception lors de la création d'environnement"""
    pass


class CleanupException(EphemeralException):
    """Exception lors du nettoyage d'environnement"""
    pass


class IsolationException(EphemeralException):
    """Exception lors de la configuration d'isolation"""
    pass


class SecurityException(EphemeralException):
    """Exception de sécurité"""
    pass


class TimeoutException(EphemeralException):
    """Exception de timeout"""
    pass


class EnvironmentNotFoundException(EphemeralException):
    """Exception quand un environnement n'est pas trouvé"""
    pass


class InvalidConfigurationException(EphemeralException):
    """Exception pour configuration invalide"""
    pass