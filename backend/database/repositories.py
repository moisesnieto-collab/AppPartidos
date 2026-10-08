import json
import itertools
from typing import List, Optional
from backend.database.connection import conectar_bd
from backend.models.jugador import Jugador
from backend.models.grupo import Grupo
from backend.models.partido import Partido
from backend.models.usuario import UsuarioAdmin
from config.constants import DATOS_INICIALES


class UsuarioRepository:
    @staticmethod
    def obtener_todos() -> List[UsuarioAdmin]:
        conn = conectar_bd()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, rut, nombre_contacto, equipo_asignado, es_superadmin FROM usuarios_admin ORDER BY es_superadmin DESC, nombre_contacto ASC"
            )
            filas = cursor.fetchall()
            return [UsuarioAdmin.from_tuple(r) for r in filas]
        finally:
            conn.close()

    @staticmethod
    def obtener_por_rut(rut: str) -> Optional[UsuarioAdmin]:
        rut_limpio = rut.replace(".", "").replace("-", "").strip()
        if not rut_limpio:
            return None
        conn = conectar_bd()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, rut, nombre_contacto, equipo_asignado, es_superadmin FROM usuarios_admin WHERE rut = ?",
                (rut_limpio,),
            )
            fila = cursor.fetchone()
            return UsuarioAdmin.from_tuple(fila) if fila else None
        finally:
            conn.close()

    @staticmethod
    def autenticar_por_rut(rut: str) -> Optional[UsuarioAdmin]:
        return UsuarioRepository.obtener_por_rut(rut)

    @staticmethod
    def crear_o_actualizar(rut: str, nombre_contacto: str, equipo_asignado: str, es_superadmin: bool = False) -> bool:
        rut_limpio = rut.replace(".", "").replace("-", "").strip()
        if not rut_limpio:
            return False
        conn = conectar_bd()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM usuarios_admin WHERE rut = ?", (rut_limpio,))
            existe = cursor.fetchone()
            if existe:
                cursor.execute(
                    "UPDATE usuarios_admin SET nombre_contacto = ?, equipo_asignado = ?, es_superadmin = ? WHERE rut = ?",
                    (nombre_contacto, equipo_asignado, 1 if es_superadmin else 0, rut_limpio),
                )
            else:
                cursor.execute(
                    "INSERT INTO usuarios_admin (rut, nombre_contacto, equipo_asignado, es_superadmin) VALUES (?, ?, ?, ?)",
                    (rut_limpio, nombre_contacto, equipo_asignado, 1 if es_superadmin else 0),
                )
            conn.commit()
            return True
        except Exception:
            return False
        finally:
            conn.close()

    @staticmethod
    def eliminar(rut: str) -> bool:
        rut_limpio = rut.replace(".", "").replace("-", "").strip()
        conn = conectar_bd()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM usuarios_admin WHERE rut = ?", (rut_limpio,))
            conn.commit()
            return True
        except Exception:
            return False
        finally:
            conn.close()


class JugadorRepository:
    @staticmethod
    def obtener_todos(equipo: Optional[str] = None, fecha: Optional[str] = None) -> List[Jugador]:
        conn = conectar_bd()
        try:
            cursor = conn.cursor()
            if equipo and fecha:
                cursor.execute(
                    "SELECT id, numero, nombre, puesto, equipo, fecha FROM jugadores WHERE equipo = ? AND fecha = ? ORDER BY CAST(numero AS INTEGER) ASC",
                    (equipo, fecha),
                )
                filas = cursor.fetchall()
                if filas:
                    return [Jugador.from_tuple(r) for r in filas]
                # Si no hay jugadores para esa fecha exacta, buscar en el historial más reciente
                return JugadorRepository.obtener_ultimo_plantel_historico(equipo, fecha)
            elif equipo:
                cursor.execute(
                    "SELECT id, numero, nombre, puesto, equipo, fecha FROM jugadores WHERE equipo = ? ORDER BY CAST(numero AS INTEGER) ASC",
                    (equipo,),
                )
                filas = cursor.fetchall()
                return [Jugador.from_tuple(r) for r in filas]
            else:
                cursor.execute(
                    "SELECT id, numero, nombre, puesto, equipo, fecha FROM jugadores ORDER BY CAST(numero AS INTEGER) ASC"
                )
                filas = cursor.fetchall()
                return [Jugador.from_tuple(r) for r in filas]
        finally:
            conn.close()

    @staticmethod
    def obtener_ultimo_plantel_historico(equipo: str, fecha_referencia: Optional[str] = None) -> List[Jugador]:
        conn = conectar_bd()
        try:
            cursor = conn.cursor()
            if fecha_referencia:
                cursor.execute(
                    "SELECT DISTINCT fecha FROM jugadores WHERE equipo = ? AND fecha < ? AND fecha != '' ORDER BY fecha DESC LIMIT 1",
                    (equipo, fecha_referencia),
                )
            else:
                cursor.execute(
                    "SELECT DISTINCT fecha FROM jugadores WHERE equipo = ? AND fecha != '' ORDER BY fecha DESC LIMIT 1",
                    (equipo,),
                )
            res = cursor.fetchone()
            if res and res[0]:
                fecha_ant = res[0]
                cursor.execute(
                    "SELECT id, numero, nombre, puesto, equipo, fecha FROM jugadores WHERE equipo = ? AND fecha = ? ORDER BY CAST(numero AS INTEGER) ASC",
                    (equipo, fecha_ant),
                )
                filas = cursor.fetchall()
                return [Jugador.from_tuple(r) for r in filas]

            # Si no hay fecha previa específica pero hay jugadores sin fecha para ese equipo
            cursor.execute(
                "SELECT id, numero, nombre, puesto, equipo, fecha FROM jugadores WHERE equipo = ? ORDER BY CAST(numero AS INTEGER) ASC",
                (equipo,),
            )
            filas = cursor.fetchall()
            if filas:
                return [Jugador.from_tuple(r) for r in filas]

            return []
        finally:
            conn.close()

    @staticmethod
    def agregar(numero: str, nombre: str, puesto: str, equipo: str = "Real Dunalastair", fecha: str = "") -> bool:
        conn = conectar_bd()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO jugadores (numero, nombre, puesto, equipo, fecha) VALUES (?, ?, ?, ?, ?)",
                (str(numero), nombre, puesto, equipo, fecha),
            )
            conn.commit()
            return True
        except Exception:
            return False
        finally:
            conn.close()

    @staticmethod
    def eliminar(nombre: str, equipo: Optional[str] = None, fecha: Optional[str] = None) -> bool:
        conn = conectar_bd()
        try:
            cursor = conn.cursor()
            if equipo and fecha:
                cursor.execute(
                    "DELETE FROM jugadores WHERE nombre = ? AND equipo = ? AND fecha = ?",
                    (nombre, equipo, fecha),
                )
            elif equipo:
                cursor.execute("DELETE FROM jugadores WHERE nombre = ? AND equipo = ?", (nombre, equipo))
            else:
                cursor.execute("DELETE FROM jugadores WHERE nombre = ?", (nombre,))
            conn.commit()
            return True
        except Exception:
            return False
        finally:
            conn.close()

    @staticmethod
    def importar_masivo(jugadores: List[dict], equipo: str = "Real Dunalastair", fecha: str = "", reemplazar: bool = False) -> tuple:
        """
        Inserta o actualiza una lista de jugadores para un equipo y fecha dados.
        Si reemplazar=True, borra los jugadores existentes previamente para ese equipo y fecha.
        Retorna (insertados, actualizados).
        """
        conn = conectar_bd()
        try:
            cursor = conn.cursor()
            if reemplazar:
                if fecha:
                    cursor.execute("DELETE FROM jugadores WHERE equipo = ? AND fecha = ?", (equipo, fecha))
                else:
                    cursor.execute("DELETE FROM jugadores WHERE equipo = ?", (equipo,))

            insertados = 0
            actualizados = 0
            for j in jugadores:
                nom = j.get("nombre", "").strip()
                num = str(j.get("numero", "0")).strip()
                puesto = j.get("puesto", "Jugador").strip() or "Jugador"
                if not nom:
                    continue

                if fecha:
                    cursor.execute(
                        "SELECT id FROM jugadores WHERE nombre = ? AND equipo = ? AND fecha = ?",
                        (nom, equipo, fecha),
                    )
                else:
                    cursor.execute(
                        "SELECT id FROM jugadores WHERE nombre = ? AND equipo = ?",
                        (nom, equipo),
                    )
                existe = cursor.fetchone()
                if existe:
                    cursor.execute(
                        "UPDATE jugadores SET numero = ?, puesto = ? WHERE id = ?",
                        (num, puesto, existe[0]),
                    )
                    actualizados += 1
                else:
                    cursor.execute(
                        "INSERT INTO jugadores (numero, nombre, puesto, equipo, fecha) VALUES (?, ?, ?, ?, ?)",
                        (num, nom, puesto, equipo, fecha),
                    )
                    insertados += 1

            conn.commit()
            return (insertados, actualizados)
        except Exception:
            conn.rollback()
            return (0, 0)
        finally:
            conn.close()

    @staticmethod
    def contar(equipo: Optional[str] = None, fecha: Optional[str] = None) -> int:
        conn = conectar_bd()
        try:
            cursor = conn.cursor()
            if equipo and fecha:
                cursor.execute("SELECT COUNT(*) FROM jugadores WHERE equipo = ? AND fecha = ?", (equipo, fecha))
            elif equipo:
                cursor.execute("SELECT COUNT(*) FROM jugadores WHERE equipo = ?", (equipo,))
            else:
                cursor.execute("SELECT COUNT(*) FROM jugadores")
            return cursor.fetchone()[0]
        finally:
            conn.close()


class GrupoRepository:
    @staticmethod
    def obtener_fechas_con_datos() -> List[str]:
        conn = conectar_bd()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT fecha FROM grupos WHERE fecha IS NOT NULL AND fecha != '' ORDER BY fecha DESC")
            rows = cursor.fetchall()
            return [r[0] for r in rows if r[0]]
        finally:
            conn.close()

    @staticmethod
    def obtener_todos_por_fecha(fecha: str) -> List[Grupo]:
        conn = conectar_bd()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, nombre, fecha, equipo_principal, equipos_json, es_principal FROM grupos WHERE fecha = ? ORDER BY es_principal DESC, id ASC",
                (fecha,)
            )
            rows = cursor.fetchall()
            return [Grupo.from_tuple(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def obtener_por_fecha(fecha: str) -> Optional[Grupo]:
        conn = conectar_bd()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, nombre, fecha, equipo_principal, equipos_json, es_principal FROM grupos WHERE fecha = ? ORDER BY es_principal DESC, id ASC LIMIT 1",
                (fecha,)
            )
            row = cursor.fetchone()
            if row:
                return Grupo.from_tuple(row)
            return None
        finally:
            conn.close()

    @staticmethod
    def obtener_por_id(grupo_id: int) -> Optional[Grupo]:
        conn = conectar_bd()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, nombre, fecha, equipo_principal, equipos_json, es_principal FROM grupos WHERE id = ?",
                (grupo_id,)
            )
            row = cursor.fetchone()
            if row:
                return Grupo.from_tuple(row)
            return None
        finally:
            conn.close()

    @staticmethod
    def crear(nombre: str, fecha: str, equipo_principal: str, equipos: List[str], es_principal: bool = True) -> int:
        conn = conectar_bd()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO grupos (nombre, fecha, equipo_principal, equipos_json, es_principal) VALUES (?, ?, ?, ?, ?)",
                (nombre, fecha, equipo_principal, json.dumps(equipos, ensure_ascii=False), 1 if es_principal else 0),
            )
            grupo_id = cursor.lastrowid
            conn.commit()
            return grupo_id
        finally:
            conn.close()

    @staticmethod
    def eliminar_por_id(grupo_id: int) -> bool:
        conn = conectar_bd()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM partidos WHERE grupo_id = ?", (grupo_id,))
            cursor.execute("DELETE FROM grupos WHERE id = ?", (grupo_id,))
            conn.commit()
            return True
        finally:
            conn.close()

    @staticmethod
    def eliminar_por_fecha(fecha: str) -> bool:
        conn = conectar_bd()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM grupos WHERE fecha = ?", (fecha,))
            conn.commit()
            return True
        finally:
            conn.close()


class TorneoConfigRepository:
    @staticmethod
    def obtener_por_fecha(fecha: str) -> dict:
        conn = conectar_bd()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT fecha, partido_definicion FROM torneo_config WHERE fecha = ?",
                (fecha,)
            )
            row = cursor.fetchone()
            if row:
                return {
                    "fecha": row[0],
                    "partido_definicion": bool(row[1]),
                }
            return {
                "fecha": fecha,
                "partido_definicion": False,
            }
        finally:
            conn.close()

    @staticmethod
    def guardar_opcion_definicion(fecha: str, partido_definicion: bool) -> bool:
        conn = conectar_bd()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO torneo_config (fecha, partido_definicion)
                VALUES (?, ?)
                ON CONFLICT(fecha) DO UPDATE SET partido_definicion=excluded.partido_definicion
                """,
                (fecha, 1 if partido_definicion else 0),
            )
            conn.commit()
            return True
        except Exception:
            # Fallback for older SQLite versions without ON CONFLICT DO UPDATE
            try:
                cursor.execute("DELETE FROM torneo_config WHERE fecha = ?", (fecha,))
                cursor.execute(
                    "INSERT INTO torneo_config (fecha, partido_definicion) VALUES (?, ?)",
                    (fecha, 1 if partido_definicion else 0),
                )
                conn.commit()
                return True
            except Exception:
                return False
        finally:
            conn.close()

    @staticmethod
    def eliminar_por_fecha(fecha: str) -> bool:
        conn = conectar_bd()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM torneo_config WHERE fecha = ?", (fecha,))
            conn.commit()
            return True
        finally:
            conn.close()


class PartidoRepository:
    @staticmethod
    def obtener_por_id(partido_id: int) -> Optional[Partido]:
        conn = conectar_bd()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, grupo_id, fecha, equipo_local, equipo_visita, es_principal,
                       tiempos_por_partido, minutos_por_tiempo, jugadores_en_cancha,
                       goles_local, goles_visita, segundos, segundos_acumulados,
                       hora_inicio, titulares, eventos, minutos_partido, finalizado, jugado, es_definicion
                FROM partidos WHERE id=?
                """,
                (partido_id,),
            )
            row = cursor.fetchone()
            return Partido.from_tuple(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def obtener_por_grupo(grupo_id: int) -> List[Partido]:
        conn = conectar_bd()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, grupo_id, fecha, equipo_local, equipo_visita, es_principal,
                       tiempos_por_partido, minutos_por_tiempo, jugadores_en_cancha,
                       goles_local, goles_visita, segundos, segundos_acumulados,
                       hora_inicio, titulares, eventos, minutos_partido, finalizado, jugado, es_definicion
                FROM partidos WHERE grupo_id=? ORDER BY id ASC
                """,
                (grupo_id,),
            )
            rows = cursor.fetchall()
            return [Partido.from_tuple(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def obtener_por_fecha(fecha: str) -> List[Partido]:
        conn = conectar_bd()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, grupo_id, fecha, equipo_local, equipo_visita, es_principal,
                       tiempos_por_partido, minutos_por_tiempo, jugadores_en_cancha,
                       goles_local, goles_visita, segundos, segundos_acumulados,
                       hora_inicio, titulares, eventos, minutos_partido, finalizado, jugado, es_definicion
                FROM partidos WHERE fecha=? ORDER BY id ASC
                """,
                (fecha,),
            )
            rows = cursor.fetchall()
            return [Partido.from_tuple(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def obtener_partido_definicion(fecha: str) -> Optional[Partido]:
        conn = conectar_bd()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, grupo_id, fecha, equipo_local, equipo_visita, es_principal,
                       tiempos_por_partido, minutos_por_tiempo, jugadores_en_cancha,
                       goles_local, goles_visita, segundos, segundos_acumulados,
                       hora_inicio, titulares, eventos, minutos_partido, finalizado, jugado, es_definicion
                FROM partidos WHERE fecha=? AND es_definicion=1 ORDER BY id DESC LIMIT 1
                """,
                (fecha,),
            )
            row = cursor.fetchone()
            return Partido.from_tuple(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def crear_partido_definicion(
        fecha: str,
        equipo_local: str,
        equipo_visita: str,
        tiempos_por_partido: int = 2,
        minutos_por_tiempo: int = 10,
        jugadores_en_cancha: int = 7,
    ) -> int:
        conn = conectar_bd()
        try:
            cursor = conn.cursor()
            # Eliminar partido de definición previo para esta fecha si existe
            cursor.execute("DELETE FROM partidos WHERE fecha=? AND es_definicion=1", (fecha,))
            cursor.execute(
                """
                INSERT INTO partidos (grupo_id, fecha, equipo_local, equipo_visita, equipo_rival, es_principal, tiempos_por_partido, minutos_por_tiempo, jugadores_en_cancha, es_definicion)
                VALUES (NULL, ?, ?, ?, ?, 0, ?, ?, ?, 1)
                """,
                (fecha, equipo_local, equipo_visita, equipo_visita, tiempos_por_partido, minutos_por_tiempo, jugadores_en_cancha),
            )
            partido_id = cursor.lastrowid
            conn.commit()
            return partido_id
        finally:
            conn.close()

    @staticmethod
    def eliminar_partido_definicion(fecha: str) -> bool:
        conn = conectar_bd()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM partidos WHERE fecha=? AND es_definicion=1", (fecha,))
            conn.commit()
            return True
        finally:
            conn.close()

    @staticmethod
    def crear(
        grupo_id: int,
        fecha: str,
        equipo_local: str,
        equipo_visita: str,
        equipo_rival: str,
        es_principal: bool,
        tiempos_por_partido: int = 2,
        minutos_por_tiempo: int = 10,
        jugadores_en_cancha: int = 7,
        es_definicion: bool = False,
    ) -> int:
        conn = conectar_bd()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO partidos (grupo_id, fecha, equipo_local, equipo_visita, equipo_rival, es_principal, tiempos_por_partido, minutos_por_tiempo, jugadores_en_cancha, es_definicion)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (grupo_id, fecha, equipo_local, equipo_visita, equipo_rival, 1 if es_principal else 0, tiempos_por_partido, minutos_por_tiempo, jugadores_en_cancha, 1 if es_definicion else 0),
            )
            partido_id = cursor.lastrowid
            conn.commit()
            return partido_id
        finally:
            conn.close()

    @staticmethod
    def actualizar(partido: Partido) -> bool:
        conn = conectar_bd()
        try:
            cursor = conn.cursor()
            
            paquete_eventos = {
                "lista": partido.eventos,
                "alerta_custom": partido.alerta_custom,
            }
            
            cursor.execute(
                """
                UPDATE partidos
                SET goles_local=?, goles_visita=?, segundos=?, segundos_acumulados=?, hora_inicio=?,
                    titulares=?, eventos=?, minutos_partido=?, finalizado=?, jugado=?
                WHERE id=?
                """,
                (
                    partido.goles_local,
                    partido.goles_visita,
                    partido.segundos,
                    partido.segundos_acumulados,
                    partido.hora_inicio,
                    json.dumps(partido.titulares, ensure_ascii=False),
                    json.dumps(paquete_eventos, ensure_ascii=False),
                    json.dumps(partido.minutos_partido, ensure_ascii=False),
                    1 if partido.finalizado else 0,
                    1 if partido.jugado else 0,
                    partido.id,
                ),
            )
            conn.commit()
            return True
        except Exception:
            return False
        finally:
            conn.close()

    @staticmethod
    def actualizar_marcador(partido_id: int, goles_local: int, goles_visita: int) -> bool:
        conn = conectar_bd()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE partidos
                SET goles_local=?, goles_visita=?, jugado=1
                WHERE id=?
                """,
                (goles_local, goles_visita, partido_id),
            )
            conn.commit()
            return True
        except Exception:
            return False
        finally:
            conn.close()

    @staticmethod
    def eliminar_por_fecha(fecha: str) -> bool:
        conn = conectar_bd()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM partidos WHERE fecha = ?", (fecha,))
            conn.commit()
            return True
        finally:
            conn.close()

    @staticmethod
    def obtener_minutos_por_fecha(fecha: str, excluir_partido_id: Optional[int] = None) -> dict:
        conn = conectar_bd()
        try:
            cursor = conn.cursor()
            if excluir_partido_id is not None:
                cursor.execute(
                    "SELECT id, minutos_partido FROM partidos WHERE fecha = ? AND id != ?",
                    (fecha, excluir_partido_id),
                )
            else:
                cursor.execute(
                    "SELECT id, minutos_partido FROM partidos WHERE fecha = ?",
                    (fecha,),
                )
            filas = cursor.fetchall()
            
            minutos_totales = {}
            for row in filas:
                try:
                    min_dict = json.loads(row[1]) if row[1] else {}
                except Exception:
                    min_dict = {}
                
                for jugador, segs in min_dict.items():
                    minutos_totales[jugador] = minutos_totales.get(jugador, 0) + segs
            
            return minutos_totales
        finally:
            conn.close()

    @staticmethod
    def obtener_minutos_todos() -> dict:
        conn = conectar_bd()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, minutos_partido FROM partidos")
            filas = cursor.fetchall()
            
            minutos_totales = {}
            for row in filas:
                try:
                    min_dict = json.loads(row[1]) if row[1] else {}
                except Exception:
                    min_dict = {}
                
                for jugador, segs in min_dict.items():
                    minutos_totales[jugador] = minutos_totales.get(jugador, 0) + segs
            
            return minutos_totales
        finally:
            conn.close()


class DatabaseInitializer:
    @staticmethod
    def inicializar():
        conn = conectar_bd()
        try:
            cursor = conn.cursor()

            # Tabla jugadores
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS jugadores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    numero TEXT NOT NULL,
                    nombre TEXT NOT NULL,
                    puesto TEXT NOT NULL,
                    equipo TEXT DEFAULT 'Real Dunalastair',
                    fecha TEXT DEFAULT ''
                )
            """)

            # Migración para remover UNIQUE(nombre) antiguo si existiese
            try:
                cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='jugadores'")
                sql_act = cursor.fetchone()
                if sql_act and "nombre TEXT NOT NULL UNIQUE" in sql_act[0]:
                    cursor.execute("""
                        CREATE TABLE jugadores_temp (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            numero TEXT NOT NULL,
                            nombre TEXT NOT NULL,
                            puesto TEXT NOT NULL,
                            equipo TEXT DEFAULT 'Real Dunalastair',
                            fecha TEXT DEFAULT ''
                        )
                    """)
                    cursor.execute("""
                        INSERT INTO jugadores_temp (id, numero, nombre, puesto, equipo, fecha)
                        SELECT id, numero, nombre, puesto, COALESCE(equipo, 'Real Dunalastair'), COALESCE(fecha, '')
                        FROM jugadores
                    """)
                    cursor.execute("DROP TABLE jugadores")
                    cursor.execute("ALTER TABLE jugadores_temp RENAME TO jugadores")
            except Exception:
                pass

            # Tabla grupos
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS grupos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL,
                    fecha TEXT NOT NULL,
                    equipo_principal TEXT NOT NULL,
                    equipos_json TEXT NOT NULL,
                    es_principal INTEGER DEFAULT 1
                )
            """)

            # Tabla torneo_config
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS torneo_config (
                    fecha TEXT PRIMARY KEY,
                    partido_definicion INTEGER DEFAULT 0
                )
            """)

            # Tabla partidos
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS partidos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    grupo_id INTEGER,
                    fecha TEXT NOT NULL,
                    equipo_local TEXT NOT NULL,
                    equipo_visita TEXT NOT NULL,
                    equipo_rival TEXT DEFAULT '',
                    es_principal INTEGER DEFAULT 0,
                    tiempos_por_partido INTEGER DEFAULT 2,
                    minutos_por_tiempo INTEGER DEFAULT 10,
                    jugadores_en_cancha INTEGER DEFAULT 7,
                    goles_local INTEGER DEFAULT 0,
                    goles_visita INTEGER DEFAULT 0,
                    segundos INTEGER DEFAULT 0,
                    segundos_acumulados INTEGER DEFAULT 0,
                    hora_inicio TEXT DEFAULT NULL,
                    updated_at TEXT DEFAULT NULL,
                    titulares TEXT DEFAULT '[]',
                    eventos TEXT DEFAULT '[]',
                    minutos_partido TEXT DEFAULT '{}',
                    finalizado INTEGER DEFAULT 0,
                    jugado INTEGER DEFAULT 0,
                    es_definicion INTEGER DEFAULT 0
                )
            """)

            # Tabla usuarios_admin
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS usuarios_admin (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rut TEXT NOT NULL UNIQUE,
                    nombre_contacto TEXT NOT NULL,
                    equipo_asignado TEXT NOT NULL,
                    es_superadmin INTEGER DEFAULT 0
                )
            """)

            # Asegurar columnas en jugadores (migración)
            try:
                cursor.execute("ALTER TABLE jugadores ADD COLUMN equipo TEXT DEFAULT 'Real Dunalastair'")
            except Exception:
                pass
            try:
                cursor.execute("ALTER TABLE jugadores ADD COLUMN fecha TEXT DEFAULT ''")
            except Exception:
                pass

            # Asegurar columnas en grupos
            try:
                cursor.execute("ALTER TABLE grupos ADD COLUMN es_principal INTEGER DEFAULT 1")
            except Exception:
                pass

            # Asegurar columnas requeridas en partidos (migración)
            columnas_requeridas = [
                ("grupo_id", "INTEGER"),
                ("fecha", "TEXT DEFAULT ''"),
                ("equipo_local", "TEXT DEFAULT ''"),
                ("equipo_visita", "TEXT DEFAULT ''"),
                ("equipo_rival", "TEXT DEFAULT ''"),
                ("es_principal", "INTEGER DEFAULT 0"),
                ("tiempos_por_partido", "INTEGER DEFAULT 2"),
                ("minutos_por_tiempo", "INTEGER DEFAULT 10"),
                ("jugadores_en_cancha", "INTEGER DEFAULT 7"),
                ("goles_local", "INTEGER DEFAULT 0"),
                ("goles_visita", "INTEGER DEFAULT 0"),
                ("segundos", "INTEGER DEFAULT 0"),
                ("segundos_acumulados", "INTEGER DEFAULT 0"),
                ("hora_inicio", "TEXT DEFAULT NULL"),
                ("updated_at", "TEXT DEFAULT NULL"),
                ("titulares", "TEXT DEFAULT '[]'"),
                ("eventos", "TEXT DEFAULT '[]'"),
                ("minutos_partido", "TEXT DEFAULT '{}'"),
                ("finalizado", "INTEGER DEFAULT 0"),
                ("jugado", "INTEGER DEFAULT 0"),
                ("es_definicion", "INTEGER DEFAULT 0"),
            ]

            for col_nombre, col_tipo in columnas_requeridas:
                try:
                    cursor.execute(f"ALTER TABLE partidos ADD COLUMN {col_nombre} {col_tipo}")
                except Exception:
                    pass

            # Crear índices para acelerar búsquedas
            try:
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_grupos_fecha ON grupos(fecha)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_partidos_fecha ON partidos(fecha)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_jugadores_equipo_fecha ON jugadores(equipo, fecha)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_usuarios_rut ON usuarios_admin(rut)")
            except Exception:
                pass

            # Insertar SuperAdmin inicial por defecto si no existe
            try:
                cursor.execute("SELECT COUNT(*) FROM usuarios_admin WHERE rut = '11165045'")
                if cursor.fetchone()[0] == 0:
                    cursor.execute(
                        "INSERT INTO usuarios_admin (rut, nombre_contacto, equipo_asignado, es_superadmin) VALUES (?, ?, ?, ?)",
                        ("11165045", "Super Administrador", "Real Dunalastair", 1)
                    )
            except Exception:
                pass

            # Insertar datos iniciales si la tabla está vacía
            if JugadorRepository.contar() == 0:
                for j in DATOS_INICIALES:
                    cursor.execute(
                        "INSERT INTO jugadores (numero, nombre, puesto, equipo, fecha) VALUES (?, ?, ?, ?, ?)",
                        (str(j["numero"]), j["nombre"], j["puesto"], "Real Dunalastair", ""),
                    )

            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def reiniciar():
        conn = conectar_bd()
        try:
            cursor = conn.cursor()
            cursor.execute("DROP TABLE IF EXISTS partidos")
            cursor.execute("DROP TABLE IF EXISTS grupos")
            cursor.execute("DROP TABLE IF EXISTS jugadores")
            cursor.execute("DROP TABLE IF EXISTS usuarios_admin")
            conn.commit()
        finally:
            conn.close()
        
        DatabaseInitializer.inicializar()
