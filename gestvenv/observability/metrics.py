"""
Métriques Prometheus pour GestVenv

Collecte et export de métriques au format Prometheus:
- Compteurs d'opérations
- Histogrammes de durée
- Gauges d'état
"""

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from functools import wraps
from threading import Lock
from datetime import datetime


@dataclass
class Counter:
    """Compteur Prometheus"""
    name: str
    help: str
    labels: Dict[str, str] = field(default_factory=dict)
    value: float = 0.0
    _lock: Lock = field(default_factory=Lock, repr=False)

    def inc(self, amount: float = 1.0):
        """Incrémente le compteur"""
        with self._lock:
            self.value += amount

    def get(self) -> float:
        return self.value


@dataclass
class Gauge:
    """Gauge Prometheus"""
    name: str
    help: str
    labels: Dict[str, str] = field(default_factory=dict)
    value: float = 0.0
    _lock: Lock = field(default_factory=Lock, repr=False)

    def set(self, value: float):
        """Définit la valeur"""
        with self._lock:
            self.value = value

    def inc(self, amount: float = 1.0):
        """Incrémente"""
        with self._lock:
            self.value += amount

    def dec(self, amount: float = 1.0):
        """Décrémente"""
        with self._lock:
            self.value -= amount

    def get(self) -> float:
        return self.value


@dataclass
class Histogram:
    """Histogramme Prometheus"""
    name: str
    help: str
    buckets: List[float] = field(default_factory=lambda: [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0])
    labels: Dict[str, str] = field(default_factory=dict)
    _observations: List[float] = field(default_factory=list, repr=False)
    _sum: float = 0.0
    _count: int = 0
    _lock: Lock = field(default_factory=Lock, repr=False)

    def observe(self, value: float):
        """Enregistre une observation"""
        with self._lock:
            self._observations.append(value)
            self._sum += value
            self._count += 1

    def get_bucket_counts(self) -> Dict[float, int]:
        """Retourne les comptages par bucket"""
        counts = {b: 0 for b in self.buckets}
        counts[float('inf')] = 0

        for obs in self._observations:
            for bucket in self.buckets:
                if obs <= bucket:
                    counts[bucket] += 1
            counts[float('inf')] += 1

        return counts

    @property
    def sum(self) -> float:
        return self._sum

    @property
    def count(self) -> int:
        return self._count


class MetricsCollector:
    """Collecteur central de métriques"""

    def __init__(self):
        self._counters: Dict[str, Counter] = {}
        self._gauges: Dict[str, Gauge] = {}
        self._histograms: Dict[str, Histogram] = {}
        self._lock = Lock()

        # Métriques prédéfinies pour GestVenv
        self._init_default_metrics()

    def _init_default_metrics(self):
        """Initialise les métriques par défaut"""
        # Compteurs
        self.register_counter(
            "gestvenv_environment_created_total",
            "Total des environnements créés"
        )
        self.register_counter(
            "gestvenv_environment_deleted_total",
            "Total des environnements supprimés"
        )
        self.register_counter(
            "gestvenv_package_installed_total",
            "Total des packages installés"
        )
        self.register_counter(
            "gestvenv_cache_hits_total",
            "Total des hits de cache"
        )
        self.register_counter(
            "gestvenv_cache_misses_total",
            "Total des misses de cache"
        )
        self.register_counter(
            "gestvenv_backend_errors_total",
            "Total des erreurs backend"
        )

        # Gauges
        self.register_gauge(
            "gestvenv_active_environments",
            "Nombre d'environnements actifs"
        )
        self.register_gauge(
            "gestvenv_cache_size_bytes",
            "Taille du cache en bytes"
        )

        # Histogrammes
        self.register_histogram(
            "gestvenv_environment_creation_seconds",
            "Durée de création d'environnement",
            buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0]
        )
        self.register_histogram(
            "gestvenv_package_install_seconds",
            "Durée d'installation de package",
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
        )
        self.register_histogram(
            "gestvenv_sync_seconds",
            "Durée de synchronisation",
            buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
        )

    def register_counter(self, name: str, help: str, labels: Optional[Dict[str, str]] = None) -> Counter:
        """Enregistre un nouveau compteur"""
        with self._lock:
            if name not in self._counters:
                self._counters[name] = Counter(name=name, help=help, labels=labels or {})
            return self._counters[name]

    def register_gauge(self, name: str, help: str, labels: Optional[Dict[str, str]] = None) -> Gauge:
        """Enregistre un nouveau gauge"""
        with self._lock:
            if name not in self._gauges:
                self._gauges[name] = Gauge(name=name, help=help, labels=labels or {})
            return self._gauges[name]

    def register_histogram(self, name: str, help: str, buckets: Optional[List[float]] = None,
                          labels: Optional[Dict[str, str]] = None) -> Histogram:
        """Enregistre un nouvel histogramme"""
        with self._lock:
            if name not in self._histograms:
                self._histograms[name] = Histogram(
                    name=name,
                    help=help,
                    buckets=buckets or [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
                    labels=labels or {}
                )
            return self._histograms[name]

    def counter(self, name: str) -> Optional[Counter]:
        """Récupère un compteur"""
        return self._counters.get(name)

    def gauge(self, name: str) -> Optional[Gauge]:
        """Récupère un gauge"""
        return self._gauges.get(name)

    def histogram(self, name: str) -> Optional[Histogram]:
        """Récupère un histogramme"""
        return self._histograms.get(name)

    def inc_counter(self, name: str, amount: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """Incrémente un compteur"""
        counter = self._counters.get(name)
        if counter:
            counter.inc(amount)

    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Définit la valeur d'un gauge"""
        gauge = self._gauges.get(name)
        if gauge:
            gauge.set(value)

    def observe_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Enregistre une observation dans un histogramme"""
        histogram = self._histograms.get(name)
        if histogram:
            histogram.observe(value)

    def time_histogram(self, name: str):
        """Décorateur pour mesurer le temps d'exécution"""
        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start = time.time()
                try:
                    return func(*args, **kwargs)
                finally:
                    duration = time.time() - start
                    self.observe_histogram(name, duration)
            return wrapper
        return decorator

    def export_prometheus(self) -> str:
        """Exporte les métriques au format Prometheus"""
        lines = []
        timestamp = int(datetime.now().timestamp() * 1000)

        # Compteurs
        for name, counter in self._counters.items():
            lines.append(f"# HELP {name} {counter.help}")
            lines.append(f"# TYPE {name} counter")
            labels_str = self._format_labels(counter.labels)
            lines.append(f"{name}{labels_str} {counter.value}")

        # Gauges
        for name, gauge in self._gauges.items():
            lines.append(f"# HELP {name} {gauge.help}")
            lines.append(f"# TYPE {name} gauge")
            labels_str = self._format_labels(gauge.labels)
            lines.append(f"{name}{labels_str} {gauge.value}")

        # Histogrammes
        for name, histogram in self._histograms.items():
            lines.append(f"# HELP {name} {histogram.help}")
            lines.append(f"# TYPE {name} histogram")

            bucket_counts = histogram.get_bucket_counts()
            cumulative = 0
            for bucket in histogram.buckets:
                cumulative += bucket_counts.get(bucket, 0)
                lines.append(f'{name}_bucket{{le="{bucket}"}} {cumulative}')
            lines.append(f'{name}_bucket{{le="+Inf"}} {histogram.count}')
            lines.append(f"{name}_sum {histogram.sum}")
            lines.append(f"{name}_count {histogram.count}")

        return "\n".join(lines)

    def _format_labels(self, labels: Dict[str, str]) -> str:
        """Formate les labels pour Prometheus"""
        if not labels:
            return ""
        label_pairs = [f'{k}="{v}"' for k, v in labels.items()]
        return "{" + ",".join(label_pairs) + "}"

    def get_summary(self) -> Dict:
        """Retourne un résumé des métriques"""
        return {
            "counters": {name: c.value for name, c in self._counters.items()},
            "gauges": {name: g.value for name, g in self._gauges.items()},
            "histograms": {
                name: {"count": h.count, "sum": h.sum}
                for name, h in self._histograms.items()
            }
        }


# Instance globale
metrics = MetricsCollector()


# Fonctions utilitaires
def env_created():
    """Marque la création d'un environnement"""
    metrics.inc_counter("gestvenv_environment_created_total")


def env_deleted():
    """Marque la suppression d'un environnement"""
    metrics.inc_counter("gestvenv_environment_deleted_total")


def package_installed(count: int = 1):
    """Marque l'installation de packages"""
    metrics.inc_counter("gestvenv_package_installed_total", count)


def cache_hit():
    """Marque un hit de cache"""
    metrics.inc_counter("gestvenv_cache_hits_total")


def cache_miss():
    """Marque un miss de cache"""
    metrics.inc_counter("gestvenv_cache_misses_total")


def backend_error(backend: str = "unknown"):
    """Marque une erreur backend"""
    metrics.inc_counter("gestvenv_backend_errors_total")


def record_creation_time(seconds: float):
    """Enregistre le temps de création"""
    metrics.observe_histogram("gestvenv_environment_creation_seconds", seconds)


def record_install_time(seconds: float):
    """Enregistre le temps d'installation"""
    metrics.observe_histogram("gestvenv_package_install_seconds", seconds)


def record_sync_time(seconds: float):
    """Enregistre le temps de synchronisation"""
    metrics.observe_histogram("gestvenv_sync_seconds", seconds)
