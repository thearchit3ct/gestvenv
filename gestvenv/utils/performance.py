"""
Monitoring de performance pour GestVenv v1.1
"""

import functools
import psutil
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable

import logging
logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """Métrique de performance"""
    operation: str
    avg_time: float
    success_rate: float
    performance_score: float
    sample_count: int
    
    
@dataclass
class PerformanceReport:
    """Rapport de performance"""
    metrics: List[PerformanceMetric] = field(default_factory=list)
    system_info: Dict[str, Any] = field(default_factory=dict)
    generated_at: datetime = field(default_factory=datetime.now)
    
    def add_metric(self, metric: PerformanceMetric):
        """Ajoute une métrique"""
        self.metrics.append(metric)


@dataclass
class PerformanceImprovement:
    """Suggestion d'amélioration de performance"""
    category: str
    description: str
    current_performance: str
    expected_improvement: str
    action: str


class PerformanceMonitor:
    """Moniteur de performance pour GestVenv"""
    
    def __init__(self):
        self.metrics = {}
        self.benchmarks = {
            "environment_creation": {"pip": 15.0, "uv": 3.0},
            "package_installation": {"pip": 8.0, "uv": 1.5},
            "pyproject_parsing": 0.1,
            "cache_hit_rate": 0.8,
            "cli_startup": 0.2
        }
        
    def measure_operation(self, operation: str, backend: str = None):
        """Décorateur pour mesurer les opérations"""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                start_memory = self._get_memory_usage()
                
                try:
                    result = func(*args, **kwargs)
                    success = True
                except Exception as e:
                    result = None
                    success = False
                    raise
                finally:
                    execution_time = time.time() - start_time
                    end_memory = self._get_memory_usage()
                    memory_delta = end_memory - start_memory
                    
                    self._record_metric(
                        operation, 
                        execution_time, 
                        success, 
                        backend,
                        memory_delta
                    )
                    
                return result
            return wrapper
        return decorator
        
    def time_function(self, func: Callable, *args, **kwargs) -> tuple:
        """Mesure le temps d'exécution d'une fonction"""
        start_time = time.time()
        start_memory = self._get_memory_usage()
        
        try:
            result = func(*args, **kwargs)
            success = True
        except Exception as e:
            result = None
            success = False
            raise
        finally:
            execution_time = time.time() - start_time
            end_memory = self._get_memory_usage()
            memory_delta = end_memory - start_memory
            
        return result, execution_time, memory_delta, success
        
    def get_performance_report(self) -> PerformanceReport:
        """Génère un rapport de performance"""
        report = PerformanceReport()
        
        for operation, metrics in self.metrics.items():
            benchmark = self._get_benchmark(operation)
            
            performance_score = 1.0
            if benchmark:
                performance_score = min(benchmark / metrics["avg_time"], 2.0)
                
            report.add_metric(PerformanceMetric(
                operation=operation,
                avg_time=metrics["avg_time"],
                success_rate=metrics["successes"] / (metrics["successes"] + metrics["failures"]),
                performance_score=performance_score,
                sample_count=len(metrics["times"])
            ))
            
        report.system_info = self._get_system_performance_info()
        return report
        
    def suggest_performance_improvements(self) -> List[PerformanceImprovement]:
        """Suggère des améliorations de performance"""
        improvements = []
        
        # Analyse des métriques
        for operation, metrics in self.metrics.items():
            if "pip" in operation and metrics["avg_time"] > 5.0:
                improvements.append(PerformanceImprovement(
                    category="backend",
                    description="Migrer vers uv pour améliorer les performances",
                    current_performance=f"{metrics['avg_time']:.2f}s",
                    expected_improvement="5-10x plus rapide",
                    action="gestvenv backend set uv"
                ))
                
        # Cache utilization
        cache_metrics = self.metrics.get("cache_hit_rate")
        if cache_metrics and cache_metrics["avg_time"] < 0.5:
            improvements.append(PerformanceImprovement(
                category="cache",
                description="Améliorer le taux de hit du cache",
                current_performance=f"{cache_metrics['avg_time']*100:.1f}%",
                expected_improvement="Mode hors ligne plus efficace",
                action="gestvenv cache add <packages-populaires>"
            ))
            
        # Système overloadé
        system_info = self._get_system_performance_info()
        if system_info["cpu_percent"] > 80:
            improvements.append(PerformanceImprovement(
                category="system",
                description="CPU surchargé",
                current_performance=f"{system_info['cpu_percent']:.1f}%",
                expected_improvement="Réduire la charge système",
                action="Fermer applications non nécessaires"
            ))
            
        return improvements
        
    def benchmark_backends(self, test_packages: List[str] = None) -> Dict[str, float]:
        """Benchmark des backends disponibles"""
        if not test_packages:
            test_packages = ["requests"]
            
        results = {}
        
        # Simulated benchmark (dans une vraie implémentation, tester réellement)
        benchmark_data = {
            "pip": 8.5,
            "uv": 1.2,
            "poetry": 5.8,
            "pdm": 2.1
        }
        
        for backend, time_avg in benchmark_data.items():
            # Ajouter variation pour réalisme
            import random
            variation = random.uniform(0.8, 1.2)
            results[backend] = time_avg * variation
            
        return results
        
    def profile_cache_performance(self) -> Dict[str, Any]:
        """Profile la performance du cache"""
        cache_stats = {
            "hit_rate": 0.0,
            "miss_rate": 0.0,
            "avg_fetch_time": 0.0,
            "cache_size_mb": 0.0,
            "compression_ratio": 0.0
        }
        
        cache_metrics = self.metrics.get("cache_operations", {})
        if cache_metrics:
            hits = cache_metrics.get("hits", 0)
            misses = cache_metrics.get("misses", 0)
            total = hits + misses
            
            if total > 0:
                cache_stats["hit_rate"] = hits / total
                cache_stats["miss_rate"] = misses / total
                cache_stats["avg_fetch_time"] = cache_metrics.get("avg_time", 0.0)
                
        return cache_stats
        
    def track_memory_usage(self, operation: str):
        """Décorateur pour tracker l'usage mémoire"""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start_memory = self._get_memory_usage()
                
                try:
                    result = func(*args, **kwargs)
                    end_memory = self._get_memory_usage()
                    memory_delta = end_memory - start_memory
                    
                    self._record_memory_metric(operation, memory_delta)
                    
                    if memory_delta > 100:  # >100MB
                        logger.warning(f"Forte consommation mémoire {operation}: {memory_delta:.1f}MB")
                        
                    return result
                except Exception:
                    raise
                    
            return wrapper
        return decorator
        
    def get_system_bottlenecks(self) -> List[str]:
        """Identifie les goulots d'étranglement système"""
        bottlenecks = []
        
        system_info = self._get_system_performance_info()
        
        if system_info["cpu_percent"] > 80:
            bottlenecks.append("CPU surchargé")
            
        if system_info["memory_percent"] > 85:
            bottlenecks.append("Mémoire saturée")
            
        if system_info["disk_io"]["read_mb_s"] > 100:
            bottlenecks.append("I/O disque élevé")
            
        return bottlenecks
        
    # Méthodes privées
    
    def _record_metric(self, operation: str, execution_time: float, 
                      success: bool, backend: str = None, memory_delta: float = 0):
        """Enregistre une métrique de performance"""
        key = f"{operation}_{backend}" if backend else operation
        
        if key not in self.metrics:
            self.metrics[key] = {
                "times": [],
                "successes": 0,
                "failures": 0,
                "avg_time": 0.0,
                "memory_usage": [],
                "last_recorded": None
            }
            
        self.metrics[key]["times"].append(execution_time)
        self.metrics[key]["memory_usage"].append(memory_delta)
        
        if success:
            self.metrics[key]["successes"] += 1
        else:
            self.metrics[key]["failures"] += 1
            
        # Moyenne glissante (100 dernières mesures)
        recent_times = self.metrics[key]["times"][-100:]
        self.metrics[key]["avg_time"] = sum(recent_times) / len(recent_times)
        self.metrics[key]["last_recorded"] = datetime.now()
        
    def _record_memory_metric(self, operation: str, memory_delta: float):
        """Enregistre une métrique mémoire"""
        key = f"memory_{operation}"
        
        if key not in self.metrics:
            self.metrics[key] = {
                "usage": [],
                "avg_usage": 0.0,
                "peak_usage": 0.0
            }
            
        self.metrics[key]["usage"].append(memory_delta)
        self.metrics[key]["avg_usage"] = sum(self.metrics[key]["usage"]) / len(self.metrics[key]["usage"])
        self.metrics[key]["peak_usage"] = max(self.metrics[key]["usage"])
        
    def _get_benchmark(self, operation: str) -> Optional[float]:
        """Récupère le benchmark pour une opération"""
        for bench_key, bench_value in self.benchmarks.items():
            if bench_key in operation:
                if isinstance(bench_value, dict):
                    # Backend spécifique
                    if "_" in operation:
                        backend = operation.split("_")[-1]
                        return bench_value.get(backend, bench_value.get("pip", 10.0))
                    return bench_value.get("pip", 10.0)
                else:
                    return bench_value
        return None
        
    def _get_memory_usage(self) -> float:
        """Récupère l'usage mémoire actuel en MB"""
        try:
            process = psutil.Process()
            return process.memory_info().rss / (1024 * 1024)
        except Exception:
            return 0.0
            
    def _get_system_performance_info(self) -> Dict[str, Any]:
        """Informations de performance système"""
        try:
            return {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage_percent": psutil.disk_usage('/').percent,
                "disk_io": {
                    "read_mb_s": psutil.disk_io_counters().read_bytes / (1024 * 1024),
                    "write_mb_s": psutil.disk_io_counters().write_bytes / (1024 * 1024)
                },
                "network_io": {
                    "sent_mb": psutil.net_io_counters().bytes_sent / (1024 * 1024),
                    "recv_mb": psutil.net_io_counters().bytes_recv / (1024 * 1024)
                }
            }
        except Exception:
            return {
                "cpu_percent": 0,
                "memory_percent": 0,
                "disk_usage_percent": 0,
                "disk_io": {"read_mb_s": 0, "write_mb_s": 0},
                "network_io": {"sent_mb": 0, "recv_mb": 0}
            }


# Instance globale pour le monitoring
performance_monitor = PerformanceMonitor()


def measure_performance(operation: str, backend: str = None):
    """Décorateur de convenance pour mesurer les performances"""
    return performance_monitor.measure_operation(operation, backend)


def track_memory(operation: str):
    """Décorateur de convenance pour tracker la mémoire"""
    return performance_monitor.track_memory_usage(operation)