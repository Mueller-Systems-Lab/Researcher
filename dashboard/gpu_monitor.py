# =============================================================================
# Dashboard — GPU Monitor
# =============================================================================
# Sammelt GPU-Daten via nvidia-smi.
# Liefert: GPU-Auslastung (%), VRAM used/total, Temperatur, Prozesse.
#
# Nutzung:
#   monitor = GPUMonitor()
#   data = monitor.collect()
# =============================================================================

import json
import logging
import os
import re
import subprocess
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# VRAM-Warngrenze (90 % von 8 GB = 7.2 GB → 7372 MiB)
VRAM_WARN_MIB = 7372
VRAM_CRITICAL_MIB = 7680
VRAM_TOTAL_MIB = 8192


@dataclass
class GPUData:
    """Aktuelle GPU-Daten eines Durchlaufs."""

    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    gpu_index: int = 0
    gpu_name: str = ""
    gpu_utilization: float = 0.0  # Prozent
    memory_used_mib: int = 0
    memory_total_mib: int = VRAM_TOTAL_MIB
    memory_utilization: float = 0.0  # Prozent
    temperature_c: float = 0.0
    processes: list[dict] = field(default_factory=list)
    error: str = ""


class GPUMonitor:
    """Sammelt GPU-Daten via nvidia-smi."""

    def __init__(self, warn_mib: int = VRAM_WARN_MIB):
        self.warn_mib = warn_mib

    def collect(self) -> GPUData:
        """Sammelt aktuelle GPU-Daten.

        Returns:
            GPUData-Objekt mit aktuellen Werten.
            Bei Fehler: GPUData mit error-String.
        """
        try:
            # JSON-Ausgabe von nvidia-smi parsen
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=index,name,utilization.gpu,"
                    "memory.used,memory.total,"
                    "utilization.memory,temperature.gpu",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                return GPUData(error=f"nvidia-smi Fehler: {result.stderr.strip()}")

            lines = result.stdout.strip().split("\n")
            if not lines or not lines[0].strip():
                return GPUData(error="Keine GPU-Daten")

            parts = [p.strip() for p in lines[0].split(",")]
            if len(parts) < 7:
                return GPUData(error=f"Unerwartetes nvidia-smi Format: {parts}")

            memory_used = int(parts[3]) if parts[3] else 0

            data = GPUData(
                gpu_index=int(parts[0]) if parts[0] else 0,
                gpu_name=parts[1],
                gpu_utilization=float(parts[2]) if parts[2] else 0.0,
                memory_used_mib=memory_used,
                memory_total_mib=int(parts[4]) if parts[4] else VRAM_TOTAL_MIB,
                memory_utilization=float(parts[5]) if parts[5] else 0.0,
                temperature_c=float(parts[6]) if parts[6] else 0.0,
            )

            # Prozesse abrufen
            data.processes = self._get_processes()

            return data

        except FileNotFoundError:
            return GPUData(error="nvidia-smi nicht gefunden — keine NVIDIA-GPU?")
        except subprocess.TimeoutExpired:
            return GPUData(error="nvidia-smi timeout (10s)")
        except Exception as e:
            logger.exception(f"GPU-Monitor-Fehler: {e}")
            return GPUData(error=str(e))

    @staticmethod
    def _get_processes() -> list[dict]:
        """Holt laufende GPU-Prozesse."""
        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-compute-apps=pid,process_name,used_memory",
                    "--format=csv,noheader",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                return []

            processes = []
            for line in result.stdout.strip().split("\n"):
                line = line.strip()
                if not line:
                    continue
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 3:
                    processes.append(
                        {
                            "pid": parts[0],
                            "name": os.path.basename(parts[1])
                            if "/" in parts[1]
                            else parts[1],
                            "memory_mib": int(parts[2]) if parts[2] else 0,
                        }
                    )
            return processes
        except Exception:
            return []

    def collect_dict(self) -> dict:
        """Sammelt Daten und gibt Dict zurück (für SSE/JSON)."""
        data = self.collect()
        result = asdict(data)

        # Warnungen
        warnings = []
        if data.memory_used_mib >= VRAM_CRITICAL_MIB:
            warnings.append("critical")
        elif data.memory_used_mib >= self.warn_mib:
            warnings.append("warning")

        result["warning_level"] = warnings[0] if warnings else "ok"
        result["memory_percent"] = round(
            data.memory_used_mib / max(1, data.memory_total_mib) * 100, 1
        )
        return result

    @staticmethod
    def is_available() -> bool:
        """Prüft, ob nvidia-smi verfügbar ist."""
        try:
            result = subprocess.run(
                ["which", "nvidia-smi"],
                capture_output=True,
                timeout=3,
            )
            return result.returncode == 0
        except Exception:
            logger.debug("GPU-Monitor: is_available Prüfung fehlgeschlagen", exc_info=True)
            return False
