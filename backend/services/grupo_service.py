import itertools
from typing import List, Optional, Dict, Any
from backend.models.grupo import Grupo
from backend.models.partido import Partido
from backend.database.repositories import GrupoRepository, PartidoRepository, TorneoConfigRepository


class GrupoService:
    @staticmethod
    def obtener_fechas_con_cuadrangulares() -> List[str]:
        """
        Retorna la lista de fechas únicas que tienen cuadrangulares/grupos registrados en la BD.
        """
        return GrupoRepository.obtener_fechas_con_datos()

    @staticmethod
    def calcular_tabla_grupo(partidos: List[Any], equipos: List[str]) -> List[Dict[str, Any]]:
        """
        Calcula la tabla de posiciones para una lista de partidos y equipos dados.
        Retorna una lista de diccionarios ordenada por Pts > DG > GF.
        """
        stats = {
            eq: {
                "equipo": eq,
                "PJ": 0,
                "PG": 0,
                "PE": 0,
                "PP": 0,
                "GF": 0,
                "GC": 0,
                "DG": 0,
                "Pts": 0,
            }
            for eq in equipos
        }

        for p in partidos:
            p_dict = p if isinstance(p, dict) else p.to_dict()
            # Ignorar partidos de definición final en la tabla de grupo
            if p_dict.get("es_definicion"):
                continue

            eventos = p_dict.get("eventos", [])
            segundos = p_dict.get("segundos", 0)
            jugado = p_dict.get("jugado", False)

            if jugado or segundos > 0 or len(eventos) > 0:
                loc = p_dict.get("equipo_local", "")
                vis = p_dict.get("equipo_visita", "")
                g_loc = int(p_dict.get("goles_local", 0))
                g_vis = int(p_dict.get("goles_visita", 0))

                if loc not in stats:
                    stats[loc] = {"equipo": loc, "PJ": 0, "PG": 0, "PE": 0, "PP": 0, "GF": 0, "GC": 0, "DG": 0, "Pts": 0}
                if vis not in stats:
                    stats[vis] = {"equipo": vis, "PJ": 0, "PG": 0, "PE": 0, "PP": 0, "GF": 0, "GC": 0, "DG": 0, "Pts": 0}

                stats[loc]["PJ"] += 1
                stats[vis]["PJ"] += 1
                stats[loc]["GF"] += g_loc
                stats[loc]["GC"] += g_vis
                stats[vis]["GF"] += g_vis
                stats[vis]["GC"] += g_loc

                if g_loc > g_vis:
                    stats[loc]["PG"] += 1
                    stats[loc]["Pts"] += 3
                    stats[vis]["PP"] += 1
                elif g_loc < g_vis:
                    stats[vis]["PG"] += 1
                    stats[vis]["Pts"] += 3
                    stats[loc]["PP"] += 1
                else:
                    stats[loc]["PE"] += 1
                    stats[loc]["Pts"] += 1
                    stats[vis]["PE"] += 1
                    stats[vis]["Pts"] += 1

        for eq in stats:
            stats[eq]["DG"] = stats[eq]["GF"] - stats[eq]["GC"]

        equipos_ordenados = sorted(
            stats.values(),
            key=lambda x: (x["Pts"], x["DG"], x["GF"]),
            reverse=True,
        )
        return equipos_ordenados

    @staticmethod
    def cargar_grupo_por_fecha(fecha: str) -> Optional[dict]:
        """
        Carga el grupo principal (o el primero) de la fecha seleccionada.
        """
        grupo = GrupoRepository.obtener_por_fecha(fecha)
        if grupo:
            partidos = PartidoRepository.obtener_por_grupo(grupo.id)
            return {
                "grupo": grupo.to_dict(),
                "partidos": [p.to_dict() for p in partidos],
            }
        return None

    @staticmethod
    def cargar_grupos_por_fecha(fecha: str) -> dict:
        """
        Carga todos los grupos del día, sus respectivos partidos, tablas de posiciones,
        configuración del torneo y partido de definición si existe.
        """
        grupos_db = GrupoRepository.obtener_todos_por_fecha(fecha)
        grupos_data = []

        for g in grupos_db:
            partidos = PartidoRepository.obtener_por_grupo(g.id)
            partidos_dict = [p.to_dict() for p in partidos]
            tabla = GrupoService.calcular_tabla_grupo(partidos_dict, g.equipos)
            grupos_data.append({
                "grupo": g.to_dict(),
                "partidos": partidos_dict,
                "tabla": tabla,
            })

        config_torneo = TorneoConfigRepository.obtener_por_fecha(fecha)
        partido_def = PartidoRepository.obtener_partido_definicion(fecha)

        return {
            "fecha": fecha,
            "grupos": grupos_data,
            "config_torneo": config_torneo,
            "partido_definicion": partido_def.to_dict() if partido_def else None,
        }

    @staticmethod
    def crear_grupo(
        nombre_grupo: str,
        fecha: str,
        equipo_principal: str,
        lista_equipos: List[str],
        es_invitado: bool = False,
    ) -> Optional[int]:
        """
        Crea el grupo principal de la fecha y genera sus 6 partidos.
        """
        if es_invitado:
            return None
        
        grupo_id = GrupoRepository.crear(nombre_grupo, fecha, equipo_principal, lista_equipos, es_principal=True)
        
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
                es_definicion=False,
            )
        
        return grupo_id

    @staticmethod
    def crear_grupo_adicional(
        nombre_grupo: str,
        fecha: str,
        lista_equipos: List[str],
        es_invitado: bool = False,
    ) -> Optional[int]:
        """
        Crea un grupo secundario/adicional para la fecha con 4 equipos rivales
        y genera automáticamente sus 6 partidos.
        """
        if es_invitado:
            return None

        # Para grupos secundarios no hay equipo principal local
        eq_primero = lista_equipos[0] if lista_equipos else ""
        grupo_id = GrupoRepository.crear(
            nombre=nombre_grupo,
            fecha=fecha,
            equipo_principal=eq_primero,
            equipos=lista_equipos,
            es_principal=False,
        )

        parejas = list(itertools.combinations(lista_equipos, 2))
        for loc, vis in parejas:
            PartidoRepository.crear(
                grupo_id=grupo_id,
                fecha=fecha,
                equipo_local=loc,
                equipo_visita=vis,
                equipo_rival=vis,
                es_principal=False,
                es_definicion=False,
            )

        return grupo_id

    @staticmethod
    def eliminar_grupo_por_id(grupo_id: int, es_invitado: bool = False) -> bool:
        if es_invitado or not grupo_id:
            return False
        return GrupoRepository.eliminar_por_id(grupo_id)

    @staticmethod
    def eliminar_grupo_por_fecha(fecha: str, es_invitado: bool = False) -> bool:
        if es_invitado or not fecha:
            return False
        PartidoRepository.eliminar_por_fecha(fecha)
        GrupoRepository.eliminar_por_fecha(fecha)
        TorneoConfigRepository.eliminar_por_fecha(fecha)
        return True

    @staticmethod
    def actualizar_opcion_definicion(fecha: str, partido_definicion: bool, es_invitado: bool = False) -> bool:
        if es_invitado or not fecha:
            return False
        ok = TorneoConfigRepository.guardar_opcion_definicion(fecha, partido_definicion)
        if not partido_definicion:
            PartidoRepository.eliminar_partido_definicion(fecha)
        return ok

    @staticmethod
    def sincronizar_partido_definicion(fecha: str, equipo_local: str, equipo_visita: str) -> Optional[dict]:
        """
        Crea o actualiza el partido de definición entre los 2 mejores equipos clasificados.
        """
        if not fecha or not equipo_local or not equipo_visita:
            return None

        partido_existente = PartidoRepository.obtener_partido_definicion(fecha)
        if partido_existente:
            # Si los equipos cambiaron y el partido no ha sido jugado, actualizar equipos
            if not partido_existente.jugado and (
                partido_existente.equipo_local != equipo_local or partido_existente.equipo_visita != equipo_visita
            ):
                partido_existente.equipo_local = equipo_local
                partido_existente.equipo_visita = equipo_visita
                partido_existente.equipo_rival = equipo_visita
                PartidoRepository.actualizar(partido_existente)
            return partido_existente.to_dict()
        else:
            partido_id = PartidoRepository.crear_partido_definicion(fecha, equipo_local, equipo_visita)
            partido = PartidoRepository.obtener_por_id(partido_id)
            return partido.to_dict() if partido else None

    @staticmethod
    def calcular_campeon_del_dia(
        grupos_data: List[dict],
        con_partido_definicion: bool = False,
        partido_definicion: Optional[dict] = None,
    ) -> Dict[str, Any]:
        """
        Determina al Campeón del Día:
        - Si no hay partido de definición: compara a los primeros lugares de cada grupo por Pts > DG > GF.
        - Si hay partido de definición: enfrenta a los 2 mejores líderes (o 1° y 2° de grupo único).
        """
        if not grupos_data:
            return {
                "campeon": None,
                "motivo": "No hay grupos creados para esta fecha.",
                "lideres": [],
                "finalistas": [],
                "partido_definicion": None,
                "con_partido_definicion": con_partido_definicion,
            }

        # Extraer punteros de cada grupo
        lideres = []
        for g_info in grupos_data:
            tabla = g_info.get("tabla", [])
            g_nombre = g_info.get("grupo", {}).get("nombre", "Grupo")
            if tabla:
                lider = dict(tabla[0])
                lider["nombre_grupo"] = g_nombre
                lider["es_principal"] = g_info.get("grupo", {}).get("es_principal", False)
                lideres.append(lider)

        # Si solo hay 1 grupo, los 2 mejores de ese grupo son los candidatos
        if len(grupos_data) == 1 and len(grupos_data[0].get("tabla", [])) >= 2:
            tabla_unica = grupos_data[0]["tabla"]
            ranking_lideres = [dict(t) for t in tabla_unica]
            for idx, r in enumerate(ranking_lideres):
                r["nombre_grupo"] = grupos_data[0]["grupo"].get("nombre", "Grupo Principal")
        else:
            ranking_lideres = sorted(
                lideres,
                key=lambda x: (x["Pts"], x["DG"], x["GF"]),
                reverse=True,
            )

        if not ranking_lideres:
            return {
                "campeon": None,
                "motivo": "No hay partidos registrados.",
                "lideres": [],
                "finalistas": [],
                "partido_definicion": None,
                "con_partido_definicion": con_partido_definicion,
            }

        finalistas = [ranking_lideres[0]["equipo"]]
        if len(ranking_lideres) > 1:
            finalistas.append(ranking_lideres[1]["equipo"])

        campeon = None
        motivo = ""

        if con_partido_definicion and len(finalistas) >= 2:
            if partido_definicion and (partido_definicion.get("jugado") or partido_definicion.get("finalizado")):
                g_loc = int(partido_definicion.get("goles_local", 0))
                g_vis = int(partido_definicion.get("goles_visita", 0))
                eq_loc = partido_definicion.get("equipo_local", finalistas[0])
                eq_vis = partido_definicion.get("equipo_visita", finalistas[1])

                if g_loc > g_vis:
                    campeon = eq_loc
                    motivo = f"Ganador del Partido de Definición ({g_loc} - {g_vis})"
                elif g_vis > g_loc:
                    campeon = eq_vis
                    motivo = f"Ganador del Partido de Definición ({g_vis} - {g_loc})"
                else:
                    campeon = None
                    motivo = f"Partido de Definición empatado ({g_loc} - {g_vis}). Requiere desempate."
            else:
                campeon = None
                motivo = f"Pendiente por definir en Gran Final: {finalistas[0]} vs {finalistas[1]}"
        else:
            mejor = ranking_lideres[0]
            if mejor["PJ"] > 0:
                campeon = mejor["equipo"]
                motivo = f"1° Lugar General ({mejor['Pts']} Pts, {mejor['DG']:+d} DG, {mejor['GF']} GF)"
            else:
                campeon = None
                motivo = "Torneo en curso (sin partidos completados)"

        return {
            "campeon": campeon,
            "motivo": motivo,
            "lideres": ranking_lideres,
            "finalistas": finalistas,
            "partido_definicion": partido_definicion,
            "con_partido_definicion": con_partido_definicion,
        }
