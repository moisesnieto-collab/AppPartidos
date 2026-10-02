from datetime import datetime, timezone


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
