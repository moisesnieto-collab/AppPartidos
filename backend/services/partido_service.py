from typing import Optional, Dict, List
from backend.models.partido import Partido
from backend.database.repositories import PartidoRepository
from utils.time_utils import ordenar_eventos


class PartidoService:
    @staticmethod
    def obtener_minutos_totales(
        partido_activo_id: Optional[int] = None,
        minutos_actuales: Optional[Dict] = None,
        fecha: Optional[str] = None,
    ) -> Dict:
        if not fecha:
            return {}
        
        # Minutos guardados en BD para la fecha indicada (excluyendo el partido activo si se indica)
        minutos_totales = PartidoRepository.obtener_minutos_por_fecha(
            fecha,
            excluir_partido_id=partido_activo_id
        )
        
        # Sumar los minutos en memoria del partido activo actual
        if minutos_actuales:
            for jugador, segs in minutos_actuales.items():
                minutos_totales[jugador] = minutos_totales.get(jugador, 0) + segs
        
        return minutos_totales

    @staticmethod
    def obtener_partido_por_id(partido_id: int) -> Optional[Partido]:
        return PartidoRepository.obtener_por_id(partido_id)

    @staticmethod
    def actualizar_eventos_y_marcador(
        partido_id: int,
        eventos: List[dict],
        goles_local: int,
        goles_visita: int,
        finalizado: Optional[bool] = None,
    ) -> bool:
        partido = PartidoRepository.obtener_por_id(partido_id)
        if not partido:
            return False
        
        partido.eventos = ordenar_eventos(eventos)
        partido.goles_local = max(0, goles_local)
        partido.goles_visita = max(0, goles_visita)
        if finalizado is not None:
            partido.finalizado = finalizado
        partido.jugado = True
        
        return PartidoRepository.actualizar(partido)

    @staticmethod
    def guardar_estado_partido(
        partido: Partido,
        goles_local: int,
        goles_rival: int,
        equipo_principal: str,
    ) -> bool:
        partido.eventos = ordenar_eventos(partido.eventos)
        # Determinar goles correctos según si es local o visita
        if partido.equipo_local == equipo_principal:
            partido.goles_local = goles_local
            partido.goles_visita = goles_rival
        else:
            partido.goles_local = goles_rival
            partido.goles_visita = goles_local
        
        return PartidoRepository.actualizar(partido)

    @staticmethod
    def guardar_marcador_rival(
        partido_id: int,
        goles_local: int,
        goles_visita: int,
    ) -> bool:
        return PartidoRepository.actualizar_marcador(partido_id, goles_local, goles_visita)

    @staticmethod
    def sincronizar_desde_bd(
        grupo_id: int,
        partido_activo_id: int,
        estado_actual: Dict,
        equipo_principal: str,
    ) -> tuple[bool, List[dict]]:
        """
        Sincroniza el estado desde la base de datos para multi-dispositivo.
        Retorna (hubo_cambio, lista_partidos_actualizada)
        """
        partidos_bd = PartidoRepository.obtener_por_grupo(grupo_id)
        nuevos_partidos = [p.to_dict() for p in partidos_bd]
        
        hubo_cambio = False
        estado_actualizado = estado_actual.copy()
        
        for p_dict in nuevos_partidos:
            if p_dict["id"] == partido_activo_id:
                es_local = p_dict["equipo_local"] == equipo_principal
                
                goles_loc_esperados = p_dict["goles_local"] if es_local else p_dict["goles_visita"]
                goles_riv_esperados = p_dict["goles_visita"] if es_local else p_dict["goles_local"]
                
                if (
                    estado_actual.get("goles_local") != goles_loc_esperados or
                    estado_actual.get("goles_rival") != goles_riv_esperados or
                    estado_actual.get("hora_inicio") != p_dict["hora_inicio"] or
                    estado_actual.get("segundos_acumulados") != p_dict["segundos_acumulados"] or
                    estado_actual.get("finalizado") != p_dict["finalizado"] or
                    estado_actual.get("eventos_registrados") != p_dict["eventos"] or
                    estado_actual.get("titulares_seleccionados") != p_dict["titulares"] or
                    estado_actual.get("alerta_custom") != p_dict.get("alerta_custom")
                ):
                    hubo_cambio = True
                    estado_actualizado["goles_local"] = goles_loc_esperados
                    estado_actualizado["goles_rival"] = goles_riv_esperados
                    estado_actualizado["hora_inicio"] = p_dict["hora_inicio"]
                    estado_actualizado["corriendo"] = p_dict["hora_inicio"] is not None
                    estado_actualizado["segundos_acumulados"] = p_dict["segundos_acumulados"]
                    estado_actualizado["titulares_seleccionados"] = list(p_dict["titulares"])
                    estado_actualizado["eventos_registrados"] = list(p_dict["eventos"])
                    estado_actualizado["alerta_custom"] = p_dict.get("alerta_custom")
                    estado_actualizado["minutos_partido_actual"] = dict(p_dict["minutos_partido"])
                    estado_actualizado["finalizado"] = p_dict["finalizado"]
        
        return hubo_cambio, nuevos_partidos
