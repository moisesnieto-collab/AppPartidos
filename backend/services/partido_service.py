from typing import Optional, Dict, List, Tuple
from backend.models.partido import Partido
from backend.database.repositories import PartidoRepository
from utils.time_utils import ordenar_eventos, obtener_segundos_actuales


class PartidoService:
    @staticmethod
    def _extraer_minuto_int(minuto_str: str) -> int:
        try:
            limpio = str(minuto_str).replace("'", "").replace('"', '').strip()
            if ":" in limpio:
                return int(limpio.split(":")[0])
            return int(limpio)
        except (ValueError, TypeError):
            return 0

    @staticmethod
    def _es_gol_generico(jugador_desc: str) -> bool:
        """
        Detecta si un evento de gol es genérico (ej. "Gol Rival", "Gol de Rival FC", etc.)
        o si tiene un nombre de jugador específico (ej. "Gol de Juan Pérez (Rival FC)").
        """
        d = jugador_desc.strip()
        if "Gol Rival" in d or "Equipo Rival" in d or "⚡" in d:
            return True
        if d.startswith("Gol de ") and "(" not in d:
            return True
        return False

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
    def agregar_evento_partido(
        partido_id: int,
        tipo_evento: str,
        jugador: str,
        minuto: str,
        equipo: str,
        es_superadmin: bool = False,
        equipo_usuario: Optional[str] = None,
    ) -> Tuple[bool, str, Optional[Partido]]:
        """
        Registra un evento según la Alternativa 1 (Suma descentralizada de goles propios):
        - SuperAdmin: puede registrar eventos para cualquier equipo.
        - DT Delegado: registra eventos y goles exclusivamente para su propio equipo/plantel.
        """
        partido = PartidoRepository.obtener_por_id(partido_id)
        if not partido:
            return False, "Partido no encontrado", None

        # Validación de permisos
        if not es_superadmin:
            if not equipo_usuario or (partido.equipo_local != equipo_usuario and partido.equipo_visita != equipo_usuario):
                return False, "No tienes permisos para registrar eventos en este partido", None
            
            # Alternativa 1: Cada administrador registra eventos exclusivamente para su propio equipo
            if equipo != equipo_usuario:
                return False, f"Solo puedes registrar eventos para tu propio equipo ({equipo_usuario})", None

            # Validar que si registra evento para su equipo, debe haber seleccionado titulares previamente
            titulares_data = partido.titulares
            if isinstance(titulares_data, dict):
                tits = titulares_data.get(equipo_usuario, [])
            else:
                from backend.services.jugador_service import JugadorService
                jugadores_eq = [
                    j["nombre"]
                    for j in JugadorService.obtener_todos_ordenados(equipo=equipo_usuario, fecha=partido.fecha)
                ]
                tits = [nom for nom in (titulares_data or []) if nom in jugadores_eq]

            if not tits:
                return False, f"Debes seleccionar los titulares de tu equipo ({equipo_usuario}) en la pestaña Plantel antes de registrar eventos.", None

        minuto_formateado = minuto if minuto.endswith("'") else f"{minuto}'"
        minuto_num = PartidoService._extraer_minuto_int(minuto)

        # Lógica de deduplicación y registro de Goles
        if tipo_evento == "Gol":
            es_generico_nuevo = PartidoService._es_gol_generico(jugador)
            
            # Buscar goles existentes para el mismo equipo en ventana de tiempo (+- 1 minuto)
            gol_existente_idx = None
            for idx, ev in enumerate(partido.eventos):
                if ev.get("evento") == "Gol" and ev.get("equipo") == equipo:
                    m_ev = PartidoService._extraer_minuto_int(ev.get("minuto", "0"))
                    if abs(m_ev - minuto_num) <= 1:
                        gol_existente_idx = idx
                        break

            if gol_existente_idx is not None:
                ev_existente = partido.eventos[gol_existente_idx]
                es_generico_existente = PartidoService._es_gol_generico(ev_existente.get("jugador", ""))

                if es_generico_existente and not es_generico_nuevo:
                    # Enriquecimiento: Había un "Gol Rival" genérico y ahora entra el gol con nombre de jugador
                    # Reemplazamos el detalle sin duplicar el conteo de goles
                    ev_existente["jugador"] = jugador
                    ev_existente["minuto"] = minuto_formateado
                    partido.eventos = ordenar_eventos(partido.eventos)
                    partido.jugado = True
                    exito = PartidoRepository.actualizar(partido)
                    return exito, f"⚽ Gol actualizado con el autor real: {jugador}", partido

                elif not es_generico_existente and es_generico_nuevo:
                    # Ya existía un gol con nombre y se intenta marcar "Gol Rival" genérico
                    autor_existente = ev_existente.get("jugador", "")
                    return True, f"ℹ️ El gol ya fue registrado por el DT rival ({autor_existente})", partido

                else:
                    # Ambos genéricos o ambos con nombre en el mismo minuto -> evitar doble clic accidental
                    if ev_existente.get("jugador") == jugador or abs(PartidoService._extraer_minuto_int(ev_existente.get("minuto", "0")) - minuto_num) == 0:
                        return True, "ℹ️ Este gol ya fue registrado previamente.", partido

            # Sumar gol al casillero correspondiente del equipo autor
            if equipo == partido.equipo_local:
                partido.goles_local += 1
            elif equipo == partido.equipo_visita:
                partido.goles_visita += 1
            else:
                if equipo_usuario == partido.equipo_visita:
                    partido.goles_visita += 1
                else:
                    partido.goles_local += 1

        nuevo_evento = {
            "minuto": minuto_formateado,
            "evento": tipo_evento,
            "jugador": jugador,
            "equipo": equipo,
        }

        partido.eventos.append(nuevo_evento)
        partido.eventos = ordenar_eventos(partido.eventos)
        partido.jugado = True

        exito = PartidoRepository.actualizar(partido)
        return exito, "Evento registrado con éxito" if exito else "Error al guardar evento", partido

    @staticmethod
    def eliminar_evento_partido(
        partido_id: int,
        indice_evento: int,
        es_superadmin: bool = False,
        equipo_usuario: Optional[str] = None,
    ) -> Tuple[bool, str, Optional[Partido]]:
        """
        Elimina un evento según la autoridad del usuario.
        - SuperAdmin: puede eliminar cualquier evento.
        - DT Delegado: puede eliminar eventos de su propio club o goles genéricos en su partido.
        """
        partido = PartidoRepository.obtener_por_id(partido_id)
        if not partido:
            return False, "Partido no encontrado", None

        if indice_evento < 0 or indice_evento >= len(partido.eventos):
            return False, "Índice de evento inválido", None

        evento = partido.eventos[indice_evento]
        eq_evento = evento.get("equipo")
        jug_evento = evento.get("jugador", "")

        if not es_superadmin:
            if not equipo_usuario or (partido.equipo_local != equipo_usuario and partido.equipo_visita != equipo_usuario):
                return False, "No tienes permisos para modificar eventos en este partido", None
            es_de_su_equipo = (eq_evento == equipo_usuario or (not eq_evento and equipo_usuario in jug_evento))
            if not es_de_su_equipo:
                return False, "Solo puedes eliminar eventos registrados por tu propio equipo", None

        ev_eliminado = partido.eventos.pop(indice_evento)

        # Si era gol, decrementar marcador
        if ev_eliminado.get("evento") == "Gol":
            if eq_evento == partido.equipo_local:
                partido.goles_local = max(0, partido.goles_local - 1)
            elif eq_evento == partido.equipo_visita:
                partido.goles_visita = max(0, partido.goles_visita - 1)
            else:
                if equipo_usuario == partido.equipo_visita:
                    partido.goles_visita = max(0, partido.goles_visita - 1)
                else:
                    partido.goles_local = max(0, partido.goles_local - 1)

        exito = PartidoRepository.actualizar(partido)
        return exito, "Evento eliminado con éxito" if exito else "Error al actualizar partido", partido

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

        # Solo se considera iniciado si se inició el reloj (o ya finalizó / fue marcado como jugado)
        ha_iniciado_reloj = bool(
            partido.hora_inicio is not None
            or partido.segundos > 0
            or partido.segundos_acumulados > 0
            or partido.finalizado
            or partido.jugado
        )
        partido.jugado = ha_iniciado_reloj
        
        return PartidoRepository.actualizar(partido)

    @staticmethod
    def guardar_marcador_rival(
        partido_id: int,
        goles_local: int,
        goles_visita: int,
        es_superadmin: bool = False,
        es_invitado: bool = False,
    ) -> Tuple[bool, str]:
        """
        Permiso exclusivo:
        Solo el usuario con rol SuperAdmin puede ingresar o modificar marcadores
        de los partidos de rivales (combinatoria de rivales que no usan la app).
        """
        if es_invitado:
            return False, "Los usuarios invitados no pueden modificar marcadores."

        if not es_superadmin:
            return False, "Solo el rol SuperAdmin puede guardar marcadores de partidos de rivales."

        partido = PartidoRepository.obtener_por_id(partido_id)
        if not partido:
            return False, "Partido no encontrado."

        ok = PartidoRepository.actualizar_marcador(partido_id, max(0, goles_local), max(0, goles_visita))
        if ok:
            return True, "Marcador guardado exitosamente (SuperAdmin)"
        return False, "Error al guardar el marcador en la base de datos."

    @staticmethod
    def sincronizar_desde_bd(
        grupo_id: int,
        partido_activo_id: int,
        estado_actual: Dict,
        equipo_principal: str,
    ) -> tuple[bool, List[dict]]:
        """
        Sincroniza el estado desde la base de datos para multi-dispositivo.
        Actualiza el diccionario de estado in-place.
        Retorna (hubo_cambio, lista_partidos_actualizada)
        """
        partidos_bd = PartidoRepository.obtener_por_grupo(grupo_id)
        nuevos_partidos = [p.to_dict() for p in partidos_bd]
        
        hubo_cambio = False
        
        for p_dict in nuevos_partidos:
            if p_dict["id"] == partido_activo_id:
                es_local = p_dict["equipo_local"] == equipo_principal
                
                goles_loc_esperados = p_dict["goles_local"] if es_local else p_dict["goles_visita"]
                goles_riv_esperados = p_dict["goles_visita"] if es_local else p_dict["goles_local"]
                
                titulares_bd = p_dict.get("titulares", [])
                if isinstance(titulares_bd, dict):
                    titulares_mi_equipo = list(titulares_bd.get(equipo_principal, []))
                else:
                    from backend.services.jugador_service import JugadorService
                    jugadores_eq = [
                        j["nombre"]
                        for j in JugadorService.obtener_todos_ordenados(
                            equipo=equipo_principal,
                            fecha=p_dict.get("fecha", "")
                        )
                    ]
                    titulares_mi_equipo = [nom for nom in titulares_bd if nom in jugadores_eq]

                if (
                    estado_actual.get("goles_local") != goles_loc_esperados or
                    estado_actual.get("goles_rival") != goles_riv_esperados or
                    estado_actual.get("hora_inicio") != p_dict["hora_inicio"] or
                    estado_actual.get("segundos_acumulados") != p_dict["segundos_acumulados"] or
                    estado_actual.get("finalizado") != p_dict["finalizado"] or
                    estado_actual.get("eventos_registrados") != p_dict["eventos"] or
                    estado_actual.get("titulares_seleccionados") != titulares_mi_equipo or
                    estado_actual.get("alerta_custom") != p_dict.get("alerta_custom")
                ):
                    hubo_cambio = True
                    estado_actual["goles_local"] = goles_loc_esperados
                    estado_actual["goles_rival"] = goles_riv_esperados
                    estado_actual["hora_inicio"] = p_dict["hora_inicio"]
                    estado_actual["corriendo"] = p_dict["hora_inicio"] is not None
                    estado_actual["segundos_acumulados"] = p_dict["segundos_acumulados"]
                    estado_actual["segs_al_iniciar"] = p_dict["segundos_acumulados"]
                    estado_actual["titulares_seleccionados"] = titulares_mi_equipo
                    estado_actual["eventos_registrados"] = list(p_dict["eventos"])
                    estado_actual["alerta_custom"] = p_dict.get("alerta_custom")
                    estado_actual["minutos_partido_actual"] = dict(p_dict["minutos_partido"])
                    estado_actual["finalizado"] = p_dict["finalizado"]
                    estado_actual["segundos"] = obtener_segundos_actuales(estado_actual)
        
        return hubo_cambio, nuevos_partidos
