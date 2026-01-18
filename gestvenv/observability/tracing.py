"""
Tracing des opérations pour GestVenv

Fournit des outils pour tracer les opérations et mesurer les performances.
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any
from contextlib import contextmanager
from functools import wraps
from datetime import datetime
import threading
import json


@dataclass
class Span:
    """Représente une opération tracée"""
    name: str
    trace_id: str
    span_id: str
    parent_id: Optional[str] = None
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    status: str = "running"
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict] = field(default_factory=list)

    def finish(self, status: str = "ok"):
        """Termine le span"""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.status = status

    def add_event(self, name: str, **attributes):
        """Ajoute un événement au span"""
        self.events.append({
            "name": name,
            "timestamp": time.time(),
            "attributes": attributes
        })

    def set_attribute(self, key: str, value: Any):
        """Définit un attribut"""
        self.attributes[key] = value

    def to_dict(self) -> Dict:
        """Convertit en dictionnaire"""
        return {
            "name": self.name,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_id": self.parent_id,
            "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
            "end_time": datetime.fromtimestamp(self.end_time).isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "attributes": self.attributes,
            "events": self.events
        }


@dataclass
class PerformanceTrace:
    """Trace de performance avec étapes détaillées"""
    name: str
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    steps: List[Dict] = field(default_factory=list)
    current_step: Optional[str] = None
    step_start: Optional[float] = None

    def start_step(self, step_name: str):
        """Démarre une étape"""
        if self.current_step:
            self.end_step()
        self.current_step = step_name
        self.step_start = time.time()

    def end_step(self, status: str = "ok"):
        """Termine l'étape courante"""
        if self.current_step and self.step_start:
            duration = (time.time() - self.step_start) * 1000
            self.steps.append({
                "name": self.current_step,
                "duration_ms": duration,
                "status": status
            })
            self.current_step = None
            self.step_start = None

    def finish(self):
        """Termine la trace"""
        if self.current_step:
            self.end_step()
        self.end_time = time.time()

    def __enter__(self):
        """Support context manager"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Termine la trace à la sortie du context"""
        self.finish()
        return False

    @property
    def total_duration_ms(self) -> float:
        """Durée totale en millisecondes"""
        if self.end_time:
            return (self.end_time - self.start_time) * 1000
        return (time.time() - self.start_time) * 1000

    def format_report(self, show_bar: bool = True, bar_width: int = 30) -> str:
        """Formate un rapport de performance"""
        lines = []
        lines.append(f"┌{'─' * 58}┐")
        lines.append(f"│ {'Performance Trace: ' + self.name:<56} │")
        lines.append(f"├{'─' * 58}┤")

        if not self.steps:
            lines.append(f"│ {'Aucune étape enregistrée':<56} │")
        else:
            total = self.total_duration_ms
            max_name_len = max(len(s['name']) for s in self.steps)

            for step in self.steps:
                name = step['name']
                duration = step['duration_ms']
                pct = (duration / total * 100) if total > 0 else 0

                # Formater la durée
                if duration < 1000:
                    dur_str = f"{duration:.0f}ms"
                else:
                    dur_str = f"{duration/1000:.2f}s"

                # Barre de progression
                if show_bar:
                    bar_filled = int(pct / 100 * bar_width)
                    bar = "█" * bar_filled + "░" * (bar_width - bar_filled)
                    lines.append(f"│ {name:<20} │ {dur_str:>8} │ {bar} │")
                else:
                    lines.append(f"│ {name:<30} │ {dur_str:>10} │ {pct:>5.1f}% │")

        lines.append(f"├{'─' * 58}┤")

        total_str = f"{self.total_duration_ms/1000:.2f}s" if self.total_duration_ms >= 1000 else f"{self.total_duration_ms:.0f}ms"
        lines.append(f"│ {'Total':<30} │ {total_str:>10} │       │")
        lines.append(f"└{'─' * 58}┘")

        return "\n".join(lines)

    def to_dict(self) -> Dict:
        """Convertit en dictionnaire"""
        return {
            "name": self.name,
            "total_duration_ms": self.total_duration_ms,
            "steps": self.steps
        }


class Tracer:
    """Gestionnaire de traces"""

    def __init__(self):
        self._traces: Dict[str, List[Span]] = {}
        self._current_span = threading.local()
        self._lock = threading.Lock()

    def _generate_id(self) -> str:
        """Génère un ID unique"""
        return str(uuid.uuid4())[:16]

    def start_trace(self, name: str) -> str:
        """Démarre une nouvelle trace"""
        trace_id = self._generate_id()
        with self._lock:
            self._traces[trace_id] = []
        return trace_id

    def start_span(self, name: str, trace_id: Optional[str] = None,
                   parent_id: Optional[str] = None) -> Span:
        """Démarre un nouveau span"""
        if trace_id is None:
            trace_id = self.start_trace(name)

        span = Span(
            name=name,
            trace_id=trace_id,
            span_id=self._generate_id(),
            parent_id=parent_id
        )

        with self._lock:
            if trace_id in self._traces:
                self._traces[trace_id].append(span)

        # Stocker le span courant
        self._current_span.span = span
        return span

    def current_span(self) -> Optional[Span]:
        """Récupère le span courant"""
        return getattr(self._current_span, 'span', None)

    def end_span(self, span: Span, status: str = "ok"):
        """Termine un span"""
        span.finish(status)
        if hasattr(self._current_span, 'span') and self._current_span.span == span:
            self._current_span.span = None

    @contextmanager
    def span(self, name: str, trace_id: Optional[str] = None, **attributes):
        """Context manager pour créer un span"""
        current = self.current_span()
        parent_id = current.span_id if current else None

        span = self.start_span(name, trace_id or (current.trace_id if current else None), parent_id)
        for key, value in attributes.items():
            span.set_attribute(key, value)

        try:
            yield span
            self.end_span(span, "ok")
        except Exception as e:
            span.set_attribute("error", str(e))
            span.set_attribute("error_type", type(e).__name__)
            self.end_span(span, "error")
            raise

    def get_trace(self, trace_id: str) -> List[Span]:
        """Récupère tous les spans d'une trace"""
        with self._lock:
            return self._traces.get(trace_id, [])

    def export_trace(self, trace_id: str) -> str:
        """Exporte une trace en JSON"""
        spans = self.get_trace(trace_id)
        return json.dumps([s.to_dict() for s in spans], indent=2)

    def clear_trace(self, trace_id: str):
        """Supprime une trace"""
        with self._lock:
            if trace_id in self._traces:
                del self._traces[trace_id]


# Instance globale
_tracer = Tracer()


def trace_operation(name: str):
    """
    Décorateur pour tracer une opération.

    Usage:
        @trace_operation("create_environment")
        def create_env(name):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with _tracer.span(name) as span:
                span.set_attribute("function", func.__name__)
                span.set_attribute("args_count", len(args))
                result = func(*args, **kwargs)
                return result
        return wrapper
    return decorator


@contextmanager
def performance_trace(name: str):
    """
    Context manager pour créer une trace de performance.

    Usage:
        with performance_trace("install_packages") as trace:
            trace.start_step("resolve_dependencies")
            # ...
            trace.start_step("download")
            # ...
        print(trace.format_report())
    """
    trace = PerformanceTrace(name=name)
    try:
        yield trace
    finally:
        trace.finish()


def get_tracer() -> Tracer:
    """Récupère le tracer global"""
    return _tracer
