from datetime import datetime, timezone
import re
from typing import List, Dict, Any


def parsear_minuto(minuto_val) -> float:
    """Extrae el valor numérico en minutos desde strings como '12'', '05'', '45+2'', '10:30', etc."""
    if isinstance(minuto_val, (int, float)):
        return float(minuto_val)
    if not minuto_val:
        return 0.0
    s = str(minuto_val).strip().replace("'", "").replace('"', '')
    if ":" in s:
        try:
            parts = s.split(":")
            return float(parts[0]) + float(parts[1]) / 60.0
        except Exception:
            pass
    if "+" in s:
        try:
            parts = s.split("+")
            return float(parts[0]) + float(parts[1])
        except Exception:
            pass
    match = re.search(r"(\d+(?:\.\d+)?)", s)
    if match:
        try:
            return float(match.group(1))
        except Exception:
            return 0.0
    return 0.0


def ordenar_eventos(eventos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Ordena una lista de eventos cronológicamente por sus minutos"""
    if not eventos:
        return []
    return sorted(eventos, key=lambda ev: parsear_minuto(ev.get("minuto", "00'")))


def formatear_tiempo(segs: int) -> str:
    """Formatea segundos a formato MM:SS"""
    return f"{segs // 60:02d}:{segs % 60:02d}"


def obtener_segundos_actuales(estado: dict) -> int:
    """Calcula los segundos actuales considerando si el cronómetro está corriendo"""
    segs = estado.get("segundos_acumulados", 0)
    hora_inicio_str = estado.get("hora_inicio")
    
    if estado.get("corriendo") and hora_inicio_str:
        try:
            hora_inicio = datetime.fromisoformat(hora_inicio_str)
            ahora = datetime.now(timezone.utc)
            delta = int((ahora - hora_inicio).total_seconds())
            if delta > 0:
                segs += delta
        except Exception:
            pass
    
    return segs


def actualizar_minutos_jugadores(estado: dict, seg_actual: int = None) -> dict:
    """Actualiza los minutos jugados por cada jugador titular"""
    if not estado["corriendo"] or estado["finalizado"]:
        return estado["minutos_partido_actual"]
    
    if seg_actual is None:
        seg_actual = obtener_segundos_actuales(estado)
    
    ultimo = estado.get("ultimo_segundo_procesado", seg_actual)
    delta = seg_actual - ultimo
    
    if delta > 0:
        for jugador in estado["titulares_seleccionados"]:
            estado["minutos_partido_actual"][jugador] = (
                estado["minutos_partido_actual"].get(jugador, 0) + delta
            )
        estado["ultimo_segundo_procesado"] = seg_actual
    
    return estado["minutos_partido_actual"]
