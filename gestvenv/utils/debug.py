"""
Outils de débogage pour GestVenv CLI

Fournit des utilitaires pour le debug et le profiling des commandes.
"""

import functools
import json
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
import subprocess
import platform


@dataclass
class DebugContext:
    """Contexte de débogage global"""
    enabled: bool = False
    trace_performance: bool = False
    log_level: str = "INFO"
    log_file: Optional[str] = None
    show_commands: bool = False
    json_output: bool = False


# Contexte global
_debug_context = DebugContext()


def set_debug_mode(enabled: bool):
    """Active/désactive le mode debug"""
    _debug_context.enabled = enabled


def set_trace_performance(enabled: bool):
    """Active/désactive le trace de performance"""
    _debug_context.trace_performance = enabled


def set_log_level(level: str):
    """Définit le niveau de log"""
    _debug_context.log_level = level


def set_log_file(path: str):
    """Définit le fichier de log"""
    _debug_context.log_file = path


def set_show_commands(enabled: bool):
    """Active/désactive l'affichage des commandes"""
    _debug_context.show_commands = enabled


def is_debug_enabled() -> bool:
    """Vérifie si le mode debug est actif"""
    return _debug_context.enabled


def is_trace_enabled() -> bool:
    """Vérifie si le trace est actif"""
    return _debug_context.trace_performance


def debug_print(message: str, **kwargs):
    """Affiche un message de debug"""
    if not _debug_context.enabled:
        return

    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    prefix = f"\033[36m[DEBUG {timestamp}]\033[0m"

    if kwargs:
        extras = " ".join(f"\033[33m{k}\033[0m={v}" for k, v in kwargs.items())
        print(f"{prefix} {message} | {extras}", file=sys.stderr)
    else:
        print(f"{prefix} {message}", file=sys.stderr)


def debug_command(cmd: List[str], cwd: Optional[str] = None):
    """Affiche une commande en mode debug"""
    if not _debug_context.enabled and not _debug_context.show_commands:
        return

    cmd_str = " ".join(cmd)
    timestamp = datetime.now().strftime("%H:%M:%S")
    cwd_str = f" (in {cwd})" if cwd else ""

    print(f"\033[35m[CMD {timestamp}]\033[0m {cmd_str}{cwd_str}", file=sys.stderr)


@dataclass
class PerformanceStep:
    """Étape de performance"""
    name: str
    start_time: float
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None

    def finish(self):
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000


@dataclass
class PerformanceTracker:
    """Tracker de performance pour les commandes"""
    command: str
    start_time: float = field(default_factory=time.time)
    steps: List[PerformanceStep] = field(default_factory=list)
    current_step: Optional[PerformanceStep] = None

    def start_step(self, name: str):
        """Démarre une nouvelle étape"""
        if self.current_step:
            self.current_step.finish()
            self.steps.append(self.current_step)

        self.current_step = PerformanceStep(name=name, start_time=time.time())

    def end_step(self):
        """Termine l'étape courante"""
        if self.current_step:
            self.current_step.finish()
            self.steps.append(self.current_step)
            self.current_step = None

    def finish(self) -> 'PerformanceTracker':
        """Termine le tracking"""
        self.end_step()
        return self

    @property
    def total_duration_ms(self) -> float:
        return (time.time() - self.start_time) * 1000

    def format_report(self) -> str:
        """Génère un rapport formaté"""
        lines = []
        lines.append("┌─────────────────────────────────────────┐")
        lines.append("│ Performance Trace                       │")
        lines.append("├─────────────────────────────────────────┤")

        total = self.total_duration_ms
        bar_width = 20

        for step in self.steps:
            name = step.name[:20].ljust(20)
            duration = step.duration_ms or 0

            # Formater la durée
            if duration >= 1000:
                dur_str = f"{duration/1000:.2f}s".rjust(8)
            else:
                dur_str = f"{duration:.0f}ms".rjust(8)

            # Barre de progression
            pct = duration / total if total > 0 else 0
            filled = int(pct * bar_width)
            bar = "█" * filled + "░" * (bar_width - filled)

            lines.append(f"│ {name} │{dur_str} │ {bar} │")

        lines.append("├─────────────────────────────────────────┤")

        # Total
        total_str = f"{total/1000:.2f}s" if total >= 1000 else f"{total:.0f}ms"
        lines.append(f"│ {'Total':<20} │{total_str.rjust(8)} │{' ' * 22}│")
        lines.append("└─────────────────────────────────────────┘")

        return "\n".join(lines)

    def to_json(self) -> str:
        """Exporte en JSON"""
        return json.dumps({
            "command": self.command,
            "total_duration_ms": self.total_duration_ms,
            "steps": [
                {"name": s.name, "duration_ms": s.duration_ms}
                for s in self.steps
            ]
        }, indent=2)


def with_performance_trace(func: Callable) -> Callable:
    """Décorateur pour tracer la performance d'une fonction"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if not _debug_context.trace_performance:
            return func(*args, **kwargs)

        tracker = PerformanceTracker(command=func.__name__)

        # Injecter le tracker si la fonction l'accepte
        if 'perf_tracker' in func.__code__.co_varnames:
            kwargs['perf_tracker'] = tracker

        try:
            result = func(*args, **kwargs)
            tracker.finish()

            # Afficher le rapport
            print("\n" + tracker.format_report(), file=sys.stderr)

            return result
        except Exception as e:
            tracker.finish()
            raise

    return wrapper


def get_system_info() -> Dict[str, Any]:
    """Récupère les informations système pour le debug"""
    info = {
        "platform": platform.system(),
        "platform_release": platform.release(),
        "platform_version": platform.version(),
        "architecture": platform.machine(),
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
    }

    # Informations supplémentaires
    try:
        info["hostname"] = platform.node()
        info["processor"] = platform.processor()
    except Exception:
        pass

    return info


def get_environment_info() -> Dict[str, str]:
    """Récupère les variables d'environnement pertinentes"""
    relevant_vars = [
        "PATH", "PYTHONPATH", "VIRTUAL_ENV", "CONDA_DEFAULT_ENV",
        "PIP_INDEX_URL", "PIP_TRUSTED_HOST", "UV_CACHE_DIR",
        "HOME", "USER", "SHELL"
    ]

    return {
        var: os.environ.get(var, "")
        for var in relevant_vars
        if os.environ.get(var)
    }


def format_config_display(config: Dict[str, Any]) -> str:
    """Formate l'affichage de la configuration"""
    lines = []
    lines.append("┌─────────────────────────────────────────────────────┐")
    lines.append("│ GestVenv Configuration                              │")
    lines.append("├─────────────────────────────────────────────────────┤")

    for key, value in config.items():
        # Tronquer les valeurs longues
        value_str = str(value)
        if len(value_str) > 35:
            value_str = value_str[:32] + "..."

        key_formatted = key.replace("_", " ").title()
        lines.append(f"│ {key_formatted:<20} │ {value_str:<28} │")

    lines.append("└─────────────────────────────────────────────────────┘")
    return "\n".join(lines)


def detect_backends() -> Dict[str, Dict[str, Any]]:
    """Détecte les backends disponibles et leurs versions"""
    backends = {}

    # pip
    try:
        result = subprocess.run(
            ["pip", "--version"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            backends["pip"] = {
                "available": True,
                "version": result.stdout.strip().split()[1] if result.stdout else "unknown"
            }
    except Exception:
        backends["pip"] = {"available": False, "version": None}

    # uv
    try:
        result = subprocess.run(
            ["uv", "--version"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            backends["uv"] = {
                "available": True,
                "version": result.stdout.strip().split()[-1] if result.stdout else "unknown"
            }
    except Exception:
        backends["uv"] = {"available": False, "version": None}

    # poetry
    try:
        result = subprocess.run(
            ["poetry", "--version"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            backends["poetry"] = {
                "available": True,
                "version": result.stdout.strip().split()[-1].strip("()") if result.stdout else "unknown"
            }
    except Exception:
        backends["poetry"] = {"available": False, "version": None}

    # pdm
    try:
        result = subprocess.run(
            ["pdm", "--version"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            backends["pdm"] = {
                "available": True,
                "version": result.stdout.strip().split()[-1] if result.stdout else "unknown"
            }
    except Exception:
        backends["pdm"] = {"available": False, "version": None}

    return backends


def format_backends_display(backends: Dict[str, Dict]) -> str:
    """Formate l'affichage des backends"""
    lines = []
    lines.append("┌─────────────────────────────────────────┐")
    lines.append("│ Available Backends                      │")
    lines.append("├─────────────────────────────────────────┤")

    for name, info in backends.items():
        status = "✓" if info["available"] else "✗"
        version = info["version"] or "not installed"
        color = "\033[32m" if info["available"] else "\033[31m"
        reset = "\033[0m"

        lines.append(f"│ {color}{status}{reset} {name:<10} │ {version:<22} │")

    lines.append("└─────────────────────────────────────────┘")
    return "\n".join(lines)


def run_diagnostic() -> Dict[str, Any]:
    """Exécute un diagnostic complet"""
    return {
        "timestamp": datetime.now().isoformat(),
        "system": get_system_info(),
        "environment": get_environment_info(),
        "backends": detect_backends(),
        "debug_context": {
            "debug_enabled": _debug_context.enabled,
            "trace_performance": _debug_context.trace_performance,
            "log_level": _debug_context.log_level,
        }
    }


def format_diagnostic_report(diagnostic: Dict[str, Any]) -> str:
    """Formate le rapport de diagnostic"""
    lines = []

    # Header
    lines.append("=" * 60)
    lines.append("GestVenv Diagnostic Report")
    lines.append(f"Generated: {diagnostic['timestamp']}")
    lines.append("=" * 60)

    # System
    lines.append("\n📊 System Information:")
    for key, value in diagnostic["system"].items():
        lines.append(f"  {key}: {value}")

    # Backends
    lines.append("\n🔧 Backends:")
    lines.append(format_backends_display(diagnostic["backends"]))

    # Environment
    lines.append("\n🌍 Environment Variables:")
    for key, value in diagnostic["environment"].items():
        # Tronquer PATH
        if key == "PATH" and len(value) > 50:
            value = value[:47] + "..."
        lines.append(f"  {key}: {value}")

    return "\n".join(lines)
