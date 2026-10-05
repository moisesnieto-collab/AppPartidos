from typing import List
from backend.models.jugador import Jugador
from backend.database.repositories import JugadorRepository
from config.constants import ORDEN_PUESTOS


class JugadorService:
    @staticmethod
    def obtener_todos_ordenados() -> List[dict]:
        jugadores = JugadorRepository.obtener_todos()
        
        def clave_orden_puesto(j: Jugador):
            puesto = j.puesto.strip()
            prioridad = 99
            for key, val in ORDEN_PUESTOS.items():
                if key.lower() in puesto.lower():
                    prioridad = val
                    break
            try:
                num = int(j.numero)
            except ValueError:
                num = 999
            return (prioridad, num)
        
        jugadores_ordenados = sorted(jugadores, key=clave_orden_puesto)
        return [j.to_dict() for j in jugadores_ordenados]

    @staticmethod
    def agregar(numero: str, nombre: str, puesto: str, es_invitado: bool = False) -> bool:
        if es_invitado:
            return False
        return JugadorRepository.agregar(numero, nombre, puesto)

    @staticmethod
    def eliminar(nombre: str, es_invitado: bool = False) -> bool:
        if es_invitado:
            return False
        return JugadorRepository.eliminar(nombre)

    @staticmethod
    def importar_plantel(jugadores: List[dict], reemplazar: bool = False, es_invitado: bool = False) -> tuple:
        if es_invitado or not jugadores:
            return (0, 0)
        return JugadorRepository.importar_masivo(jugadores, reemplazar=reemplazar)
