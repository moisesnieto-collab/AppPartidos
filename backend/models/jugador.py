from dataclasses import dataclass
from typing import Optional


@dataclass
class Jugador:
    id: Optional[int] = None
    numero: str = ""
    nombre: str = ""
    puesto: str = ""
    equipo: str = "Real Dunalastair"
    fecha: str = ""

    def to_dict(self):
        return {
            "id": self.id,
            "numero": self.numero,
            "nombre": self.nombre,
            "puesto": self.puesto,
            "equipo": self.equipo,
            "fecha": self.fecha,
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            id=data.get("id"),
            numero=data.get("numero", ""),
            nombre=data.get("nombre", ""),
            puesto=data.get("puesto", ""),
            equipo=data.get("equipo", "Real Dunalastair"),
            fecha=data.get("fecha", ""),
        )

    @classmethod
    def from_tuple(cls, tupla: tuple):
        return cls(
            id=tupla[0] if len(tupla) > 0 else None,
            numero=tupla[1] if len(tupla) > 1 else "",
            nombre=tupla[2] if len(tupla) > 2 else "",
            puesto=tupla[3] if len(tupla) > 3 else "",
            equipo=tupla[4] if len(tupla) > 4 and tupla[4] else "Real Dunalastair",
            fecha=tupla[5] if len(tupla) > 5 and tupla[5] else "",
        )
