from dataclasses import dataclass
from typing import Optional, List, Dict
import json


@dataclass
class Partido:
    id: Optional[int] = None
    grupo_id: Optional[int] = None
    fecha: str = ""
    equipo_local: str = ""
    equipo_visita: str = ""
    equipo_rival: str = ""
    es_principal: bool = False
    tiempos_por_partido: int = 2
    minutos_por_tiempo: int = 10
    jugadores_en_cancha: int = 7
    goles_local: int = 0
    goles_visita: int = 0
    segundos: int = 0
    segundos_acumulados: int = 0
    hora_inicio: Optional[str] = None
    titulares: List[str] = None
    eventos: List = None
    minutos_partido: Dict = None
    finalizado: bool = False
    jugado: bool = False
    alerta_custom: Optional[str] = None

    def __post_init__(self):
        if self.titulares is None:
            self.titulares = []
        if self.eventos is None:
            self.eventos = []
        if self.minutos_partido is None:
            self.minutos_partido = {}

    def to_dict(self):
        return {
            "id": self.id,
            "grupo_id": self.grupo_id,
            "fecha": self.fecha,
            "equipo_local": self.equipo_local,
            "equipo_visita": self.equipo_visita,
            "equipo_rival": self.equipo_rival,
            "es_principal": self.es_principal,
            "tiempos_por_partido": self.tiempos_por_partido,
            "minutos_por_tiempo": self.minutos_por_tiempo,
            "jugadores_en_cancha": self.jugadores_en_cancha,
            "goles_local": self.goles_local,
            "goles_visita": self.goles_visita,
            "segundos": self.segundos,
            "segundos_acumulados": self.segundos_acumulados,
            "hora_inicio": self.hora_inicio,
            "titulares": self.titulares,
            "eventos": self.eventos,
            "minutos_partido": self.minutos_partido,
            "finalizado": self.finalizado,
            "jugado": self.jugado,
            "alerta_custom": self.alerta_custom,
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            id=data.get("id"),
            grupo_id=data.get("grupo_id"),
            fecha=data.get("fecha", ""),
            equipo_local=data.get("equipo_local", ""),
            equipo_visita=data.get("equipo_visita", ""),
            equipo_rival=data.get("equipo_rival", ""),
            es_principal=data.get("es_principal", False),
            tiempos_por_partido=data.get("tiempos_por_partido", 2),
            minutos_por_tiempo=data.get("minutos_por_tiempo", 10),
            jugadores_en_cancha=data.get("jugadores_en_cancha", 7),
            goles_local=data.get("goles_local", 0),
            goles_visita=data.get("goles_visita", 0),
            segundos=data.get("segundos", 0),
            segundos_acumulados=data.get("segundos_acumulados", 0),
            hora_inicio=data.get("hora_inicio"),
            titulares=data.get("titulares", []),
            eventos=data.get("eventos", []),
            minutos_partido=data.get("minutos_partido", {}),
            finalizado=data.get("finalizado", False),
            jugado=data.get("jugado", False),
            alerta_custom=data.get("alerta_custom"),
        )

    @classmethod
    def from_tuple(cls, tupla: tuple):
        # Procesar titulares
        titulares_json = tupla[14] if len(tupla) > 14 else "[]"
        try:
            titulares = json.loads(titulares_json)
        except:
            titulares = []

        # Procesar eventos
        eventos_json = tupla[15] if len(tupla) > 15 else "[]"
        alerta_persistida = None
        try:
            evs = json.loads(eventos_json)
            if isinstance(evs, dict):
                alerta_persistida = evs.get("alerta_custom")
                evs = evs.get("lista", [])
            else:
                evs = evs if isinstance(evs, list) else []
        except:
            evs = []

        # Procesar minutos_partido
        minutos_json = tupla[16] if len(tupla) > 16 else "{}"
        try:
            minutos_partido = json.loads(minutos_json)
        except:
            minutos_partido = {}

        return cls(
            id=tupla[0] if len(tupla) > 0 else None,
            grupo_id=tupla[1] if len(tupla) > 1 else None,
            fecha=tupla[2] if len(tupla) > 2 else "",
            equipo_local=tupla[3] if len(tupla) > 3 else "",
            equipo_visita=tupla[4] if len(tupla) > 4 else "",
            es_principal=bool(tupla[5]) if len(tupla) > 5 else False,
            tiempos_por_partido=tupla[6] if len(tupla) > 6 else 2,
            minutos_por_tiempo=tupla[7] if len(tupla) > 7 else 10,
            jugadores_en_cancha=tupla[8] if len(tupla) > 8 else 7,
            goles_local=tupla[9] if len(tupla) > 9 else 0,
            goles_visita=tupla[10] if len(tupla) > 10 else 0,
            segundos=tupla[11] if len(tupla) > 11 else 0,
            segundos_acumulados=tupla[12] if len(tupla) > 12 else 0,
            hora_inicio=tupla[13] if len(tupla) > 13 else None,
            titulares=titulares,
            eventos=evs,
            minutos_partido=minutos_partido,
            finalizado=bool(tupla[17]) if len(tupla) > 17 else False,
            jugado=bool(tupla[18]) if len(tupla) > 18 else False,
            alerta_custom=alerta_persistida,
        )
