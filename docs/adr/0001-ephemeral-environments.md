# ADR 0001: Environnements Éphémères

## Statut
Accepté

## Contexte
GestVenv nécessite un mécanisme pour créer des environnements Python temporaires qui:
- Se nettoient automatiquement après utilisation
- Peuvent être isolés du système hôte
- Supportent des limites de ressources (mémoire, CPU)
- Permettent des tests et expérimentations rapides

## Décision
Nous implémentons un système d'environnements éphémères avec les caractéristiques suivantes:

### Architecture
```
gestvenv/core/ephemeral/
├── __init__.py
├── manager.py      # Gestionnaire principal
├── lifecycle.py    # Contrôleur de cycle de vie
├── monitoring.py   # Monitoring des ressources
├── cgroups.py      # Isolation via cgroups v2
└── models.py       # Modèles de données
```

### Niveaux d'isolation
1. **NONE**: Pas d'isolation, environnement standard
2. **BASIC**: Isolation via virtualenv uniquement
3. **NAMESPACE**: Isolation via namespaces Linux (si disponible)
4. **CGROUP**: Isolation complète avec limites de ressources

### Cycle de vie
```
PENDING → CREATING → READY → ACTIVE → CLEANUP → DELETED
                         ↓
                      ERROR
```

### Limites de ressources (cgroups v2)
- Mémoire maximale
- CPU (pourcentage)
- Nombre de processus
- I/O (bytes/seconde)

## Conséquences

### Positives
- Tests isolés et reproductibles
- Nettoyage automatique des ressources
- Protection contre les fuites de ressources
- Expérimentation sécurisée

### Négatives
- Complexité accrue du code
- Dépendance à cgroups v2 (Linux uniquement) pour l'isolation complète
- Overhead de performance pour la gestion du cycle de vie

### Neutres
- Nécessite des permissions root pour cgroups sur certains systèmes
- Fallback gracieux sur les systèmes sans cgroups

## Notes d'implémentation
- Utiliser asyncio pour les opérations de cycle de vie
- Implémenter un timeout par défaut (30 minutes)
- Logger toutes les opérations pour le debugging
- Exporter des métriques Prometheus pour le monitoring
