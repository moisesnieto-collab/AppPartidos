from dataclasses import dataclass
from typing import Optional


@dataclass
class Jugador:
    id: Optional[int] = None
    numero: str = ""
    nombre: str = ""
    puesto: str = ""

    def to_dict(self):
        return {
            "id": self.id,
            "numero": self.numero,
            "nombre": self.nombre,
            "puesto": self.puesto,
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            id=data.get("id"),
            numero=data.get("numero", ""),
            nombre=data.get("nombre", ""),
            puesto=data.get("puesto", ""),
        )

    @classmethod
    def from_tuple(cls, tupla: tuple):
        return cls(
            id=tupla[0] if len(tupla) > 0 else None,
            numero=tupla[1] if len(tupla) > 1 else "",
            nombre=tupla[2] if len(tupla) > 2 else "",
            puesto=tupla[3] if len(tupla) > 3 else "",
        )
