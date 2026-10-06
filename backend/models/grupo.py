from dataclasses import dataclass
from typing import Optional, List
import json


@dataclass
class Grupo:
    id: Optional[int] = None
    nombre: str = ""
    fecha: str = ""
    equipo_principal: str = ""
    equipos: List[str] = None
    es_principal: bool = True

    def __post_init__(self):
        if self.equipos is None:
            self.equipos = []

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "fecha": self.fecha,
            "equipo_principal": self.equipo_principal,
            "equipos": self.equipos,
            "es_principal": self.es_principal,
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            id=data.get("id"),
            nombre=data.get("nombre", ""),
            fecha=data.get("fecha", ""),
            equipo_principal=data.get("equipo_principal", ""),
            equipos=data.get("equipos", []),
            es_principal=bool(data.get("es_principal", True)),
        )

    @classmethod
    def from_tuple(cls, tupla: tuple):
        equipos_json = tupla[4] if len(tupla) > 4 else "[]"
        try:
            equipos = json.loads(equipos_json)
        except:
            equipos = []
        
        es_principal = bool(tupla[5]) if len(tupla) > 5 else True
        
        return cls(
            id=tupla[0] if len(tupla) > 0 else None,
            nombre=tupla[1] if len(tupla) > 1 else "",
            fecha=tupla[2] if len(tupla) > 2 else "",
            equipo_principal=tupla[3] if len(tupla) > 3 else "",
            equipos=equipos,
            es_principal=es_principal,
        )
