from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class UsuarioAdmin:
    id: Optional[int] = None
    rut: str = ""
    nombre_contacto: str = ""
    equipo_asignado: str = ""
    es_superadmin: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "rut": self.rut,
            "nombre_contacto": self.nombre_contacto,
            "equipo_asignado": self.equipo_asignado,
            "es_superadmin": self.es_superadmin,
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            id=data.get("id"),
            rut=data.get("rut", ""),
            nombre_contacto=data.get("nombre_contacto", ""),
            equipo_asignado=data.get("equipo_asignado", ""),
            es_superadmin=bool(data.get("es_superadmin", False)),
        )

    @classmethod
    def from_tuple(cls, tupla: tuple):
        return cls(
            id=tupla[0] if len(tupla) > 0 else None,
            rut=tupla[1] if len(tupla) > 1 else "",
            nombre_contacto=tupla[2] if len(tupla) > 2 else "",
            equipo_asignado=tupla[3] if len(tupla) > 3 else "",
            es_superadmin=bool(tupla[4]) if len(tupla) > 4 else False,
        )
