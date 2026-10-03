import json
import itertools
from typing import List, Optional
from backend.database.connection import conectar_bd
from backend.models.jugador import Jugador
from backend.models.grupo import Grupo
from backend.models.partido import Partido
from config.constants import DATOS_INICIALES


class JugadorRepository:
    @staticmethod
    def obtener_todos() -> List[Jugador]:
        conn = conectar_bd()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, numero, nombre, puesto FROM jugadores")
            filas = cursor.fetchall()
            return [Jugador.from_tuple((r[0], r[1], r[2], r[3])) for r in filas]
        finally:
            conn.close()

    @staticmethod
    def agregar(numero: str, nombre: str, puesto: str) -> bool:
        conn = conectar_bd()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO jugadores (numero, nombre, puesto) VALUES (?, ?, ?)",
                (str(numero), nombre, puesto),
            )
            conn.commit()
            return True
        except Exception:
            return False
        finally:
            conn.close()

    @staticmethod
    def eliminar(nombre: str) -> bool:
        conn = conectar_bd()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM jugadores WHERE nombre=?", (nombre,))
            conn.commit()
            return True
        except Exception:
            return False
        finally:
            conn.close()

    @staticmethod
    def contar() -> int:
        conn = conectar_bd()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM jugadores")
            return cursor.fetchone()[0]
        finally:
            conn.close()


class GrupoRepository:
    @staticmethod
    def obtener_por_fecha(fecha: str) -> Optional[Grupo]:
        conn = conectar_bd()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, nombre, fecha, equipo_principal, equipos_json FROM grupos WHERE fecha = ? ORDER BY id DESC LIMIT 1",
                (fecha,)
            )
            row = cursor.fetchone()
            if row:
                return Grupo.from_tuple(row)
            return None
        finally:
            conn.close()

    @staticmethod
    def crear(nombre: str, fecha: str, equipo_principal: str, equipos: List[str]) -> int:
        conn = conectar_bd()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO grupos (nombre, fecha, equipo_principal, equipos_json) VALUES (?, ?, ?, ?)",
                (nombre, fecha, equipo_principal, json.dumps(equipos, ensure_ascii=False)),
            )
            grupo_id = cursor.lastrowid
            conn.commit()
            return grupo_id
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
                       hora_inicio, titulares, eventos, minutos_partido, finalizado, jugado
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
                       hora_inicio, titulares, eventos, minutos_partido, finalizado, jugado
                FROM partidos WHERE grupo_id=? ORDER BY id ASC
                """,
                (grupo_id,),
            )
            rows = cursor.fetchall()
            return [Partido.from_tuple(r) for r in rows]
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
    ) -> int:
        conn = conectar_bd()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO partidos (grupo_id, fecha, equipo_local, equipo_visita, equipo_rival, es_principal, tiempos_por_partido, minutos_por_tiempo, jugadores_en_cancha)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (grupo_id, fecha, equipo_local, equipo_visita, equipo_rival, 1 if es_principal else 0, tiempos_por_partido, minutos_por_tiempo, jugadores_en_cancha),
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
                    titulares=?, eventos=?, minutos_partido=?, finalizado=?, jugado=1
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
                    nombre TEXT NOT NULL UNIQUE,
                    puesto TEXT NOT NULL
                )
            """)

            # Tabla grupos
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS grupos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL,
                    fecha TEXT NOT NULL,
                    equipo_principal TEXT NOT NULL,
                    equipos_json TEXT NOT NULL
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
                    jugado INTEGER DEFAULT 0
                )
            """)

            # Asegurar columnas requeridas (migración)
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
            ]

            for col_nombre, col_tipo in columnas_requeridas:
                try:
                    cursor.execute(f"ALTER TABLE partidos ADD COLUMN {col_nombre} {col_tipo}")
                except Exception:
                    pass

            # Insertar datos iniciales si la tabla está vacía
            if JugadorRepository.contar() == 0:
                for j in DATOS_INICIALES:
                    cursor.execute(
                        "INSERT INTO jugadores (numero, nombre, puesto) VALUES (?, ?, ?)",
                        (str(j["numero"]), j["nombre"], j["puesto"]),
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
            conn.commit()
        finally:
            conn.close()
        
        DatabaseInitializer.inicializar()
