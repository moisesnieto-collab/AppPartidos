import itertools
from typing import List, Optional
from backend.models.grupo import Grupo
from backend.models.partido import Partido
from backend.database.repositories import GrupoRepository, PartidoRepository


class GrupoService:
    @staticmethod
    def cargar_grupo_por_fecha(fecha: str) -> Optional[dict]:
        grupo = GrupoRepository.obtener_por_fecha(fecha)
        if grupo:
            partidos = PartidoRepository.obtener_por_grupo(grupo.id)
            return {
                "grupo": grupo.to_dict(),
                "partidos": [p.to_dict() for p in partidos],
            }
        return None

    @staticmethod
    def crear_grupo(
        nombre_grupo: str,
        fecha: str,
        equipo_principal: str,
        lista_equipos: List[str],
        es_invitado: bool = False,
    ) -> Optional[int]:
        if es_invitado:
            return None
        
        grupo_id = GrupoRepository.crear(nombre_grupo, fecha, equipo_principal, lista_equipos)
        
        # Crear partidos para todas las combinaciones
        parejas = list(itertools.combinations(lista_equipos, 2))
        for loc, vis in parejas:
            es_principal = loc == equipo_principal or vis == equipo_principal
            rival_calculado = vis if loc == equipo_principal else loc
            PartidoRepository.crear(
                grupo_id=grupo_id,
                fecha=fecha,
                equipo_local=loc,
                equipo_visita=vis,
                equipo_rival=rival_calculado,
                es_principal=es_principal,
            )
        
        return grupo_id

    @staticmethod
    def eliminar_grupo_por_fecha(fecha: str, es_invitado: bool = False) -> bool:
        if es_invitado or not fecha:
            return False
        PartidoRepository.eliminar_por_fecha(fecha)
        GrupoRepository.eliminar_por_fecha(fecha)
        return True
