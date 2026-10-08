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
            hora_inicio = datetime.fromisoformat(str(hora_inicio_str))
            if hora_inicio.tzinfo is None:
                hora_inicio = hora_inicio.replace(tzinfo=timezone.utc)
            ahora = datetime.now(timezone.utc)
            delta = int((ahora - hora_inicio).total_seconds())
            if delta > 0:
                segs += delta
        except Exception:
            pass
    
    return segs


def actualizar_minutos_jugadores(estado: dict, seg_actual: int = None) -> dict:
    """Actualiza los minutos jugados por cada jugador titular de los equipos participantes con titulares definidos"""
    if not estado.get("corriendo") or estado.get("finalizado"):
        return estado.get("minutos_partido_actual", {})
    
    if seg_actual is None:
        seg_actual = obtener_segundos_actuales(estado)
    
    ultimo = estado.get("ultimo_segundo_procesado", seg_actual)
    delta = seg_actual - ultimo
    
    if delta > 0:
        if "minutos_partido_actual" not in estado:
            estado["minutos_partido_actual"] = {}

        # 1. Obtener titulares del equipo del usuario actual
        jugadores_a_sumar = set(estado.get("titulares_seleccionados", []))

        # 2. Obtener titulares del partido activo para ambos equipos si están definidos
        partido_activo_id = estado.get("partido_activo_id")
        partidos = estado.get("partidos_grupo", [])
        p_act = next((p for p in partidos if p.get("id") == partido_activo_id), None)

        if p_act:
            tits = p_act.get("titulares", {})
            if isinstance(tits, dict):
                for eq, lista_tits in tits.items():
                    if lista_tits and isinstance(lista_tits, list):
                        for jug in lista_tits:
                            if jug:
                                jugadores_a_sumar.add(jug)
            elif isinstance(tits, list):
                for jug in tits:
                    if jug:
                        jugadores_a_sumar.add(jug)

        for jugador in jugadores_a_sumar:
            if jugador:
                estado["minutos_partido_actual"][jugador] = (
                    estado["minutos_partido_actual"].get(jugador, 0) + delta
                )
        estado["ultimo_segundo_procesado"] = seg_actual
    
    return estado["minutos_partido_actual"]
