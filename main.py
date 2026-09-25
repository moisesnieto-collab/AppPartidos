import asyncio
from datetime import datetime, timezone
import itertools
import json
import os
import flet as ft
import libsql_experimental as sqlite3
import pandas as pd

# --- PALETA DE COLORES MODERNA (CELESTE Y PLOMO SLATE) ---
COLOR_FONDO = "#0F172A"
COLOR_TARJETA = "#1E293B"
COLOR_BORDE = "#334155"
COLOR_CELESTE = "#38BDF8"
COLOR_CELESTE_BOTON = "#0284C7"
COLOR_TEXTO = "#F8FAFC"
COLOR_SUBTEXTO = "#94A3B8"
COLOR_VERDE = "#4ADE80"
COLOR_ROJO = "#F87171"
COLOR_AMBAR = "#FBBF24"

# --- CONFIGURACIÓN DE BASE DE DATOS TURSO ---
TURSO_URL = os.environ.get(
    "TURSO_URL", "libsql://apppartidos-mnieto.aws-us-east-2.turso.io"
)
TURSO_TOKEN = os.environ.get(
    "TURSO_TOKEN",
    "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3OTAzNzYzNDUsImlkIjoiMDFhMGQ4NzctNzEwMS03NjMyLThiOWYtY2ExOWMzYmI1NDc3Iiwia2lkIjoiTDl6UGpCZkwtX2JXbzVlZWl3RElTcUZ2TFIwNms2c2Z2RGRDRTV3Q20wUSIsInJpZCI6IjUwMzI1MGM2LWFlNzgtNGZkMC1iZTg2LWY1YzkxOGE4NDFjNCJ9.UyizRZgwWnWUqqjb0rfP5logT8KAvTok0cobUkBfRwTRJywZiQowjyJ4B1SZzRUtE5XFrUxC8mMw9gA5w3gOCg",
)


def conectar_bd():
    return sqlite3.connect(TURSO_URL, auth_token=TURSO_TOKEN)


ORDEN_PUESTOS = {
    "Arquero": 1,
    "Defensa": 2,
    "Medio": 3,
    "Delantero": 4,
}

DATOS_INICIALES = [
    {"numero": 1, "nombre": "Santiago Muñoz - Santiago", "puesto": "Arquero"},
    {"numero": 2, "nombre": "ignacio Navarrete - Nacho", "puesto": "Defensa"},
    {"numero": 3, "nombre": "Santi espinoza - Santi", "puesto": "Defensa"},
    {"numero": 4, "nombre": "Tomi Villena", "puesto": "Defensa"},
    {"numero": 5, "nombre": "Benjamin Nieto - Benja", "puesto": "Delantero"},
    {"numero": 6, "nombre": "Tommy Lioret - Tommy", "puesto": "Delantero"},
    {"numero": 7, "nombre": "Renato. Rena", "puesto": "Delantero"},
    {"numero": 8, "nombre": "Tomi castillo - Tomás C -", "puesto": "Medio"},
    {"numero": 9, "nombre": "Gaspar Roblero - Gaspy", "puesto": "Medio"},
    {"numero": 10, "nombre": "Joaquin Caceres", "puesto": "Defensa"},
    {"numero": 11, "nombre": "Laura Navarrete", "puesto": "Medio"},
    {"numero": 12, "nombre": "Igna", "puesto": "Medio"},
]

EVENTOS_DEFECTO = [
    "Gol",
    "Asistencia",
    "Tarjeta Amarilla",
    "Tarjeta Roja",
    "Cambio",
]


def inicializar_bd():
    conn = conectar_bd()
    try:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jugadores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero TEXT NOT NULL,
                nombre TEXT NOT NULL UNIQUE,
                puesto TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS grupos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                fecha TEXT NOT NULL,
                equipo_principal TEXT NOT NULL,
                equipos_json TEXT NOT NULL
            )
        """)

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

        cursor.execute("SELECT COUNT(*) FROM jugadores")
        if cursor.fetchone()[0] == 0:
            for j in DATOS_INICIALES:
                cursor.execute(
                    "INSERT INTO jugadores (numero, nombre, puesto) VALUES (?, ?, ?)",
                    (str(j["numero"]), j["nombre"], j["puesto"]),
                )

        conn.commit()
    finally:
        conn.close()


def obtener_segundos_actuales(p_estado):
    segs = p_estado.get("segundos_acumulados", 0)
    hora_inicio_str = p_estado.get("hora_inicio")
    if p_estado.get("corriendo") and hora_inicio_str:
        try:
            hora_inicio = datetime.fromisoformat(hora_inicio_str)
            ahora = datetime.now(timezone.utc)
            delta = int((ahora - hora_inicio).total_seconds())
            if delta > 0:
                segs += delta
        except Exception:
            pass
    return segs


def main(page: ft.Page):
    inicializar_bd()

    page.title = "Real Dunalastair FC - Control de Torneo"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    page.bgcolor = COLOR_FONDO

    estado = {
        "segundos": 0,
        "segundos_acumulados": 0,
        "segs_al_iniciar": 0,
        "ultimo_segundo_procesado": 0,
        "hora_inicio": None,
        "corriendo": False,
        "finalizado": False,
        "alerta_custom": None,
        "pestana_activa": 0,
        "goles_local": 0,
        "goles_rival": 0,
        "partidos_grupo": [],
        "grupo_activo": None,
        "partido_activo_id": None,
        "minutos_partido_actual": {},
        "titulares_seleccionados": [],
        "eventos_registrados": [],
        "es_invitado": True,  # Por defecto arranca en invitado hasta que se valide
        "config": {
            "equipo_principal": "Real Dunalastair",
            "equipo_rival": "Rival FC",
            "tiempos_por_partido": 2,
            "minutos_por_tiempo": 10,
            "jugadores_en_cancha": 7,
            "fecha": datetime.now().strftime("%Y-%m-%d"),
        },
    }

    texto_reloj = ft.Text(
        "00:00", size=50, weight=ft.FontWeight.BOLD, color=COLOR_CELESTE
    )
    texto_alerta_cambio = ft.Text(
        "Partido listo", weight=ft.FontWeight.W_600, color=COLOR_SUBTEXTO
    )

    def actualizar_glosa():
        if estado["finalizado"]:
            texto_alerta_cambio.value = "🔒 PARTIDO FINALIZADO (Solo Lectura)"
            texto_alerta_cambio.color = COLOR_ROJO
        elif estado.get("alerta_custom"):
            texto_alerta_cambio.value = estado["alerta_custom"]
            texto_alerta_cambio.color = COLOR_AMBAR
        elif estado["corriendo"]:
            texto_alerta_cambio.value = "⏱️ Partido en marcha"
            texto_alerta_cambio.color = COLOR_VERDE
        elif estado["segundos"] > 0:
            texto_alerta_cambio.value = "⏸️ Partido pausado"
            texto_alerta_cambio.color = COLOR_AMBAR
        else:
            texto_alerta_cambio.value = "Partido listo"
            texto_alerta_cambio.color = COLOR_SUBTEXTO

    def formatear_tiempo(segs):
        return f"{segs // 60:02d}:{segs % 60:02d}"

    def actualizar_minutos_jugadores(seg_actual=None):
        if not estado["corriendo"] or estado["finalizado"]:
            return
        if seg_actual is None:
            seg_actual = obtener_segundos_actuales(estado)
        ultimo = estado.get("ultimo_segundo_procesado", seg_actual)
        delta = seg_actual - ultimo
        if delta > 0:
            for jugador in estado["titulares_seleccionados"]:
                estado["minutos_partido_actual"][jugador] = (
                        estado["minutos_partido_actual"].get(jugador, 0) + delta
                )
            estado["ultimo_segundo_procesado"] = seg_actual

    # --- CONSULTAS BD Y OPERACIONES ---
    def obtener_jugadores_bd():
        conn = conectar_bd()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT numero, nombre, puesto FROM jugadores")
            filas = cursor.fetchall()
        finally:
            conn.close()

        lista = [
            {"numero": r[0], "nombre": r[1], "puesto": r[2]} for r in filas
        ]

        def clave_orden_puesto(j):
            puesto = j["puesto"].strip()
            prioridad = 99
            for key, val in ORDEN_PUESTOS.items():
                if key.lower() in puesto.lower():
                    prioridad = val
                    break
            try:
                num = int(j["numero"])
            except ValueError:
                num = 999
            return (prioridad, num)

        return sorted(lista, key=clave_orden_puesto)

    def agregar_jugador_bd(num, nom, puesto):
        if estado["es_invitado"]:
            return False
        conn = conectar_bd()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO jugadores (numero, nombre, puesto) VALUES (?, ?, ?)",
                (str(num), nom, puesto),
            )
            conn.commit()
            return True
        except Exception:
            return False
        finally:
            conn.close()

    def eliminar_jugador_bd(nombre):
        if estado["es_invitado"]:
            return
        conn = conectar_bd()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM jugadores WHERE nombre=?", (nombre,))
            conn.commit()
        finally:
            conn.close()

        if nombre in estado["titulares_seleccionados"]:
            estado["titulares_seleccionados"].remove(nombre)
        if nombre in estado["minutos_partido_actual"]:
            del estado["minutos_partido_actual"][nombre]

        guardar_estado_partido_activo()

    def cargar_datos_grupo():
        conn = conectar_bd()
        try:
            cursor = conn.cursor()

            cursor.execute(
                "SELECT id, nombre, fecha, equipo_principal, equipos_json FROM grupos ORDER BY id DESC LIMIT 1"
            )
            row_grupo = cursor.fetchone()

            if row_grupo:
                estado["grupo_activo"] = {
                    "id": row_grupo[0],
                    "nombre": row_grupo[1],
                    "fecha": row_grupo[2],
                    "equipo_principal": row_grupo[3],
                    "equipos": json.loads(row_grupo[4]),
                }

                cursor.execute(
                    """
                    SELECT id, grupo_id, fecha, equipo_local, equipo_visita, es_principal,
                           tiempos_por_partido, minutos_por_tiempo, jugadores_en_cancha,
                           goles_local, goles_visita, segundos, segundos_acumulados,
                           hora_inicio, titulares, eventos, minutos_partido, finalizado, jugado
                    FROM partidos WHERE grupo_id=? ORDER BY id ASC
                """,
                    (row_grupo[0],),
                )
                rows_partidos = cursor.fetchall()

                lista_partidos = []
                for r in rows_partidos:
                    evs = json.loads(r[15] or '[]')
                    alerta_persistida = None
                    if isinstance(evs, dict):
                        alerta_persistida = evs.get("alerta_custom")
                        evs = evs.get("lista", [])

                    lista_partidos.append({
                        "id": r[0],
                        "grupo_id": r[1],
                        "fecha": r[2],
                        "equipo_local": r[3],
                        "equipo_visita": r[4],
                        "es_principal": bool(r[5]),
                        "tiempos_por_partido": r[6],
                        "minutos_por_tiempo": r[7],
                        "jugadores_en_cancha": r[8],
                        "goles_local": r[9],
                        "goles_visita": r[10],
                        "segundos": r[11],
                        "segundos_acumulados": r[12],
                        "hora_inicio": r[13],
                        "titulares": json.loads(r[14] or '[]'),
                        "eventos": evs,
                        "alerta_custom": alerta_persistida,
                        "minutos_partido": json.loads(r[16] or '{}'),
                        "finalizado": bool(r[17]),
                        "jugado": bool(r[18]),
                    })
                estado["partidos_grupo"] = lista_partidos

                if estado["partido_activo_id"] is None:
                    partidos_principales = [
                        p for p in lista_partidos if p["es_principal"]
                    ]
                    if partidos_principales:
                        activar_partido_memoria(partidos_principales[0])
        finally:
            conn.close()

    def crear_nuevo_grupo(
            nombre_grupo, fecha, equipo_principal, lista_equipos
    ):
        if estado["es_invitado"]:
            return
        conn = conectar_bd()
        try:
            cursor = conn.cursor()

            cursor.execute(
                "INSERT INTO grupos (nombre, fecha, equipo_principal, equipos_json) VALUES (?, ?, ?, ?)",
                (
                    nombre_grupo,
                    fecha,
                    equipo_principal,
                    json.dumps(lista_equipos, ensure_ascii=False),
                ),
            )
            grupo_id = cursor.lastrowid

            parejas = list(itertools.combinations(lista_equipos, 2))
            for loc, vis in parejas:
                es_principal = 1 if (loc == equipo_principal or vis == equipo_principal) else 0
                rival_calculado = vis if loc == equipo_principal else loc
                cursor.execute(
                    """
                    INSERT INTO partidos (grupo_id, fecha, equipo_local, equipo_visita, equipo_rival, es_principal, tiempos_por_partido, minutos_por_tiempo, jugadores_en_cancha)
                    VALUES (?, ?, ?, ?, ?, ?, 2, 10, 7)
                """,
                    (grupo_id, fecha, loc, vis, rival_calculado, es_principal),
                )

            conn.commit()
        finally:
            conn.close()

        estado["partido_activo_id"] = None
        cargar_datos_grupo()

    def guardar_marcador_rival(partido_id, goles_loc, goles_vis):
        if estado["es_invitado"]:
            return
        conn = conectar_bd()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE partidos
                SET goles_local=?, goles_visita=?, jugado=1, updated_at=DATETIME('now')
                WHERE id=?
            """,
                (goles_loc, goles_vis, partido_id),
            )
            conn.commit()
        finally:
            conn.close()

        sincronizar_desde_bd()

    def guardar_estado_partido_activo():
        if estado["es_invitado"] or estado["partido_activo_id"] is None:
            return

        seg_actuales = obtener_segundos_actuales(estado)
        actualizar_minutos_jugadores(seg_actuales)

        p_act = next(
            (p for p in estado["partidos_grupo"] if p["id"] == estado["partido_activo_id"]),
            None,
        )
        if not p_act:
            return

        eq_principal = estado["config"]["equipo_principal"]
        if p_act["equipo_local"] == eq_principal:
            g_loc, g_vis = estado["goles_local"], estado["goles_rival"]
        else:
            g_loc, g_vis = estado["goles_rival"], estado["goles_local"]

        paquete_eventos = {
            "lista": estado["eventos_registrados"],
            "alerta_custom": estado["alerta_custom"],
        }

        conn = conectar_bd()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE partidos
                SET goles_local=?, goles_visita=?, segundos=?, segundos_acumulados=?, hora_inicio=?,
                    titulares=?, eventos=?, minutos_partido=?, finalizado=?, jugado=1, updated_at=DATETIME('now')
                WHERE id=?
            """,
                (
                    g_loc,
                    g_vis,
                    seg_actuales,
                    estado["segundos_acumulados"],
                    estado["hora_inicio"],
                    json.dumps(
                        estado["titulares_seleccionados"], ensure_ascii=False
                    ),
                    json.dumps(paquete_eventos, ensure_ascii=False),
                    json.dumps(
                        estado["minutos_partido_actual"], ensure_ascii=False
                    ),
                    1 if estado["finalizado"] else 0,
                    estado["partido_activo_id"],
                ),
            )
            conn.commit()
        finally:
            conn.close()

        for p in estado["partidos_grupo"]:
            if p["id"] == estado["partido_activo_id"]:
                p["goles_local"] = g_loc
                p["goles_visita"] = g_vis
                p["segundos"] = seg_actuales
                p["segundos_acumulados"] = estado["segundos_acumulados"]
                p["hora_inicio"] = estado["hora_inicio"]
                p["titulares"] = list(estado["titulares_seleccionados"])
                p["eventos"] = list(estado["eventos_registrados"])
                p["alerta_custom"] = estado["alerta_custom"]
                p["minutos_partido"] = dict(estado["minutos_partido_actual"])
                p["finalizado"] = estado["finalizado"]
                p["jugado"] = True
                break

    # --- FUNCIÓN DE SINCRONIZACIÓN DESDE BASE DE DATOS (MULTI-DISPOSITIVO) ---
    def sincronizar_desde_bd():
        if estado["grupo_activo"] is None or estado["partido_activo_id"] is None:
            return False

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
                (estado["grupo_activo"]["id"],),
            )
            rows = cursor.fetchall()
            if not rows:
                return False

            hubo_cambio = False
            nuevos_partidos = []

            for r in rows:
                p_id = r[0]
                evs = json.loads(r[15] or '[]')
                alerta_persistida = None
                if isinstance(evs, dict):
                    alerta_persistida = evs.get("alerta_custom")
                    evs = evs.get("lista", [])

                p_dict = {
                    "id": r[0],
                    "grupo_id": r[1],
                    "fecha": r[2],
                    "equipo_local": r[3],
                    "equipo_visita": r[4],
                    "es_principal": bool(r[5]),
                    "tiempos_por_partido": r[6],
                    "minutos_por_tiempo": r[7],
                    "jugadores_en_cancha": r[8],
                    "goles_local": r[9],
                    "goles_visita": r[10],
                    "segundos": r[11],
                    "segundos_acumulados": r[12],
                    "hora_inicio": r[13],
                    "titulares": json.loads(r[14] or '[]'),
                    "eventos": evs,
                    "alerta_custom": alerta_persistida,
                    "minutos_partido": json.loads(r[16] or '{}'),
                    "finalizado": bool(r[17]),
                    "jugado": bool(r[18]),
                }
                nuevos_partidos.append(p_dict)

                if p_id == estado["partido_activo_id"]:
                    eq_principal = estado["config"]["equipo_principal"]
                    es_local = p_dict["equipo_local"] == eq_principal

                    goles_loc_esperados = p_dict["goles_local"] if es_local else p_dict["goles_visita"]
                    goles_riv_esperados = p_dict["goles_visita"] if es_local else p_dict["goles_local"]

                    if (
                            estado["goles_local"] != goles_loc_esperados or
                            estado["goles_rival"] != goles_riv_esperados or
                            estado["hora_inicio"] != p_dict["hora_inicio"] or
                            estado["segundos_acumulados"] != p_dict["segundos_acumulados"] or
                            estado["finalizado"] != p_dict["finalizado"] or
                            estado["eventos_registrados"] != p_dict["eventos"] or
                            estado["titulares_seleccionados"] != p_dict["titulares"] or
                            estado["alerta_custom"] != p_dict["alerta_custom"]
                    ):
                        hubo_cambio = True
                        estado["goles_local"] = goles_loc_esperados
                        estado["goles_rival"] = goles_riv_esperados
                        estado["hora_inicio"] = p_dict["hora_inicio"]
                        estado["corriendo"] = p_dict["hora_inicio"] is not None
                        estado["segundos_acumulados"] = p_dict["segundos_acumulados"]
                        estado["titulares_seleccionados"] = list(p_dict["titulares"])
                        estado["eventos_registrados"] = list(p_dict["eventos"])
                        estado["alerta_custom"] = p_dict["alerta_custom"]
                        estado["minutos_partido_actual"] = dict(p_dict["minutos_partido"])
                        estado["finalizado"] = p_dict["finalizado"]
                        estado["segundos"] = obtener_segundos_actuales(estado)
                        estado["ultimo_segundo_procesado"] = estado["segundos"]
                        actualizar_glosa()

            if estado["partidos_grupo"] != nuevos_partidos:
                estado["partidos_grupo"] = nuevos_partidos
                hubo_cambio = True

            return hubo_cambio
        except Exception:
            return False
        finally:
            conn.close()

    def reiniciar_base_datos():
        if estado["es_invitado"]:
            return
        conn = conectar_bd()
        try:
            cursor = conn.cursor()
            cursor.execute("DROP TABLE IF EXISTS partidos")
            cursor.execute("DROP TABLE IF EXISTS grupos")
            cursor.execute("DROP TABLE IF EXISTS jugadores")
            conn.commit()
        finally:
            conn.close()

        inicializar_bd()

        estado["partido_activo_id"] = None
        estado["grupo_activo"] = None
        estado["partidos_grupo"] = []
        cargar_datos_grupo()

    def activar_partido_memoria(partido):
        eq_principal = (
            estado["grupo_activo"]["equipo_principal"]
            if estado["grupo_activo"]
            else "Real Dunalastair"
        )
        estado["config"]["equipo_principal"] = eq_principal

        es_local = partido["equipo_local"] == eq_principal
        rival = partido["equipo_visita"] if es_local else partido["equipo_local"]

        estado["partido_activo_id"] = partido["id"]
        estado["goles_local"] = partido["goles_local"] if es_local else partido["goles_visita"]
        estado["goles_rival"] = partido["goles_visita"] if es_local else partido["goles_local"]
        estado["segundos_acumulados"] = partido.get("segundos_acumulados", partido["segundos"])
        estado["segs_al_iniciar"] = estado["segundos_acumulados"]
        estado["hora_inicio"] = partido.get("hora_inicio")
        estado["corriendo"] = estado["hora_inicio"] is not None
        estado["segundos"] = obtener_segundos_actuales(estado)
        estado["ultimo_segundo_procesado"] = estado["segundos"]
        estado["titulares_seleccionados"] = list(partido["titulares"])
        estado["eventos_registrados"] = list(partido["eventos"])
        estado["alerta_custom"] = partido.get("alerta_custom")
        estado["minutos_partido_actual"] = dict(partido["minutos_partido"])
        estado["finalizado"] = bool(partido.get("finalizado", False))

        estado["config"].update({
            "equipo_rival": rival,
            "tiempos_por_partido": partido["tiempos_por_partido"],
            "minutos_por_tiempo": partido["minutos_por_tiempo"],
            "jugadores_en_cancha": partido["jugadores_en_cancha"],
            "fecha": partido["fecha"],
        })

        texto_reloj.value = formatear_tiempo(estado["segundos"])
        actualizar_glosa()

    def obtener_minutos_totales_bd():
        actualizar_minutos_jugadores()
        conn = conectar_bd()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, minutos_partido FROM partidos")
            filas = cursor.fetchall()
        finally:
            conn.close()

        minutos_totales = {}
        for row in filas:
            p_id = row[0]
            if p_id == estado["partido_activo_id"]:
                min_dict = estado["minutos_partido_actual"]
            else:
                try:
                    min_dict = json.loads(row[1]) if row[1] else {}
                except Exception:
                    min_dict = {}

            for jugador, segs in min_dict.items():
                minutos_totales[jugador] = minutos_totales.get(jugador, 0) + segs

        return minutos_totales

    cargar_datos_grupo()

    # --- LOOP DEL CRONÓMETRO Y POLLING MULTI-DISPOSITIVO ---
    async def loop_reloj():
        contador_sync = 0
        while True:
            await asyncio.sleep(1)

            seg = obtener_segundos_actuales(estado)
            estado["segundos"] = seg
            texto_reloj.value = formatear_tiempo(seg)

            duracion_tiempo_segs = estado["config"]["minutos_por_tiempo"] * 60
            duracion_total_partido = (
                    duracion_tiempo_segs * estado["config"]["tiempos_por_partido"]
            )

            # Solo el administrador actualiza localmente y guarda cambios automáticos de tiempo
            if not estado["es_invitado"]:
                if estado["corriendo"] and not estado["finalizado"]:
                    actualizar_minutos_jugadores(seg)

                    if seg >= duracion_total_partido:
                        actualizar_minutos_jugadores(duracion_total_partido)
                        estado["corriendo"] = False
                        estado["finalizado"] = True
                        estado["segundos_acumulados"] = duracion_total_partido
                        estado["segundos"] = duracion_total_partido
                        estado["hora_inicio"] = None
                        estado["alerta_custom"] = None
                        actualizar_glosa()
                        guardar_estado_partido_activo()
                        refrescar_vistas()

                    elif duracion_tiempo_segs > 0:
                        segs_inicio = estado.get("segs_al_iniciar", 0)
                        for t in range(1, estado["config"]["tiempos_por_partido"]):
                            limite_half = t * duracion_tiempo_segs
                            if seg >= limite_half and segs_inicio < limite_half:
                                actualizar_minutos_jugadores(limite_half)
                                estado["corriendo"] = False
                                estado["segundos_acumulados"] = limite_half
                                estado["segundos"] = limite_half
                                estado["hora_inicio"] = None
                                estado["alerta_custom"] = f"🏁 ¡FIN DEL TIEMPO {t}! Cronómetro pausado."
                                actualizar_glosa()
                                guardar_estado_partido_activo()
                                refrescar_vistas()
                                break

            contador_sync += 1
            intervalo_sync = 2 if estado["pestana_activa"] == 0 else 10

            if contador_sync >= intervalo_sync:
                if sincronizar_desde_bd():
                    refrescar_vistas()
                contador_sync = 0

            try:
                page.update()
            except Exception:
                pass

    page.run_task(loop_reloj)

    # --- PANTALLA 1: CONFIGURACIÓN & TABLA DE POSICIONES ---
    def view_configuracion():
        tf_nombre_grupo = ft.TextField(
            label="Nombre del Grupo/Torneo",
            value="Grupo A - Cuadrangular",
            expand=True,
            border_color=COLOR_BORDE,
            focused_border_color=COLOR_CELESTE,
            border_radius=10,
        )
        tf_fecha_grupo = ft.TextField(
            label="Fecha (AAAA-MM-DD)",
            value=datetime.now().strftime("%Y-%m-%d"),
            width=140,
            border_color=COLOR_BORDE,
            focused_border_color=COLOR_CELESTE,
            border_radius=10,
        )
        tf_equipo_principal = ft.TextField(
            label="Mi Equipo Principal",
            value="Real Dunalastair",
            expand=True,
            border_color=COLOR_BORDE,
            focused_border_color=COLOR_CELESTE,
            border_radius=10,
        )
        tf_equipos_rivales = ft.TextField(
            label="Equipos Rivales (Separados por coma)",
            value="Rival A, Rival B, Rival C",
            expand=True,
            border_color=COLOR_BORDE,
            focused_border_color=COLOR_CELESTE,
            border_radius=10,
        )
        texto_feedback_grupo = ft.Text("", size=12)

        def click_generar_grupo(e):
            if estado["es_invitado"]:
                return
            nom_g = tf_nombre_grupo.value.strip()
            f_g = tf_fecha_grupo.value.strip()
            eq_princ = tf_equipo_principal.value.strip()
            rivales_str = tf_equipos_rivales.value.strip()

            if not nom_g or not eq_princ or not rivales_str:
                texto_feedback_grupo.value = "⚠️ Completa todos los campos del grupo."
                texto_feedback_grupo.color = COLOR_ROJO
                page.update()
                return

            lista_rivales = [r.strip() for r in rivales_str.split(",") if r.strip()]
            if not lista_rivales:
                texto_feedback_grupo.value = "⚠️ Ingresa al menos un equipo rival."
                texto_feedback_grupo.color = COLOR_ROJO
                page.update()
                return

            todos_los_equipos = [eq_princ] + lista_rivales
            crear_nuevo_grupo(nom_g, f_g, eq_princ, todos_los_equipos)

            texto_feedback_grupo.value = f"✅ Grupo '{nom_g}' generado con {len(todos_los_equipos)} equipos y sus partidos combinados."
            texto_feedback_grupo.color = COLOR_VERDE
            refrescar_vistas()
            page.update()

        def confirmar_reset(e):
            if estado["es_invitado"]:
                return

            def cerrar_dlg(ev):
                dialogo_reset.open = False
                page.update()

            def procesar_reset(ev):
                reiniciar_base_datos()
                texto_feedback_grupo.value = "🔄 Base de datos restablecida."
                dialogo_reset.open = False
                refrescar_vistas()
                page.update()

            dialogo_reset = ft.AlertDialog(
                title=ft.Text("¿Borrar Base de Datos?", color=COLOR_TEXTO),
                content=ft.Text("Se eliminarán todos los grupos, partidos y estadísticas."),
                actions=[
                    ft.TextButton("Cancelar", on_click=cerrar_dlg),
                    ft.ElevatedButton(
                        "Borrar BD",
                        bgcolor=COLOR_ROJO,
                        color=COLOR_TEXTO,
                        on_click=procesar_reset,
                    ),
                ],
                bgcolor=COLOR_TARJETA,
            )
            page.overlay.append(dialogo_reset)
            dialogo_reset.open = True
            page.update()

        componente_tabla = ft.Container()
        if estado["grupo_activo"] and estado["partidos_grupo"]:
            grupo = estado["grupo_activo"]
            stats = {
                eq: {
                    "PJ": 0,
                    "PG": 0,
                    "PE": 0,
                    "PP": 0,
                    "GF": 0,
                    "GC": 0,
                    "DG": 0,
                    "Pts": 0,
                }
                for eq in grupo["equipos"]
            }

            for p in estado["partidos_grupo"]:
                if p["jugado"] or p["segundos"] > 0 or len(p["eventos"]) > 0:
                    loc, vis = p["equipo_local"], p["equipo_visita"]
                    g_loc, g_vis = p["goles_local"], p["goles_visita"]

                    if loc not in stats:
                        stats[loc] = {"PJ": 0, "PG": 0, "PE": 0, "PP": 0, "GF": 0, "GC": 0, "DG": 0, "Pts": 0}
                    if vis not in stats:
                        stats[vis] = {"PJ": 0, "PG": 0, "PE": 0, "PP": 0, "GF": 0, "GC": 0, "DG": 0, "Pts": 0}

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
                stats.items(),
                key=lambda x: (x[1]["Pts"], x[1]["DG"], x[1]["GF"]),
                reverse=True,
            )

            filas_tabla = []
            for pos, (nombre_eq, st) in enumerate(equipos_ordenados, start=1):
                es_mi_equipo = nombre_eq.lower() == grupo["equipo_principal"].lower()
                color_nombre = COLOR_CELESTE if es_mi_equipo else COLOR_TEXTO
                peso_nombre = ft.FontWeight.BOLD if es_mi_equipo else ft.FontWeight.NORMAL

                filas_tabla.append(
                    ft.DataRow(
                        cells=[
                            ft.DataCell(content=ft.Text(str(pos), color=COLOR_TEXTO)),
                            ft.DataCell(content=ft.Text(nombre_eq, weight=peso_nombre, color=color_nombre)),
                            ft.DataCell(content=ft.Text(str(st["PJ"]), color=COLOR_TEXTO)),
                            ft.DataCell(content=ft.Text(str(st["PG"]), color=COLOR_TEXTO)),
                            ft.DataCell(content=ft.Text(str(st["PE"]), color=COLOR_TEXTO)),
                            ft.DataCell(content=ft.Text(str(st["PP"]), color=COLOR_TEXTO)),
                            ft.DataCell(content=ft.Text(str(st["GF"]), color=COLOR_TEXTO)),
                            ft.DataCell(content=ft.Text(str(st["GC"]), color=COLOR_TEXTO)),
                            ft.DataCell(content=ft.Text(f"{st['DG']:+d}", color=COLOR_TEXTO)),
                            ft.DataCell(content=ft.Text(str(st["Pts"]), weight=ft.FontWeight.BOLD, color=COLOR_VERDE)),
                        ]
                    )
                )

            tabla_ui = ft.DataTable(
                columns=[
                    ft.DataColumn(label=ft.Text("Pos", weight=ft.FontWeight.BOLD, color=COLOR_SUBTEXTO)),
                    ft.DataColumn(label=ft.Text("Equipo", weight=ft.FontWeight.BOLD, color=COLOR_CELESTE)),
                    ft.DataColumn(label=ft.Text("PJ", weight=ft.FontWeight.BOLD, color=COLOR_SUBTEXTO)),
                    ft.DataColumn(label=ft.Text("PG", weight=ft.FontWeight.BOLD, color=COLOR_VERDE)),
                    ft.DataColumn(label=ft.Text("PE", weight=ft.FontWeight.BOLD, color=COLOR_AMBAR)),
                    ft.DataColumn(label=ft.Text("PP", weight=ft.FontWeight.BOLD, color=COLOR_ROJO)),
                    ft.DataColumn(label=ft.Text("GF", weight=ft.FontWeight.BOLD, color=COLOR_SUBTEXTO)),
                    ft.DataColumn(label=ft.Text("GC", weight=ft.FontWeight.BOLD, color=COLOR_SUBTEXTO)),
                    ft.DataColumn(label=ft.Text("DG", weight=ft.FontWeight.BOLD, color=COLOR_SUBTEXTO)),
                    ft.DataColumn(label=ft.Text("Pts", weight=ft.FontWeight.BOLD, color=COLOR_VERDE)),
                ],
                rows=filas_tabla,
                bgcolor=COLOR_FONDO,
                border=ft.border.all(1, COLOR_BORDE),
                border_radius=8,
                column_spacing=16,
                heading_row_height=38,
                data_row_min_height=38,
                data_row_max_height=38,
            )

            componente_tabla = ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Text(
                                    f"🏆 Tabla de Posiciones: {grupo['nombre']}",
                                    weight=ft.FontWeight.BOLD,
                                    color=COLOR_CELESTE,
                                    size=15,
                                ),
                                ft.Text(f"📅 {grupo['fecha']}", color=COLOR_SUBTEXTO, size=12),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        ft.Row([tabla_ui], scroll=ft.ScrollMode.ALWAYS),
                    ],
                    spacing=8,
                ),
                padding=12,
                bgcolor=COLOR_TARJETA,
                border_radius=12,
                border=ft.border.all(1, COLOR_CELESTE),
            )

        partidos_mi_equipo_ui = []
        partidos_rivales_ui = []

        if estado["partidos_grupo"]:
            for p in estado["partidos_grupo"]:
                es_activo = p["id"] == estado["partido_activo_id"]

                def crear_handler_select(partido_obj):
                    return lambda e: (
                        activar_partido_memoria(partido_obj),
                        guardar_estado_partido_activo(),
                        refrescar_vistas(),
                        page.update(),
                    )

                if p["es_principal"]:
                    rival_nombre = (
                        p["equipo_visita"]
                        if p["equipo_local"] == estado["config"]["equipo_principal"]
                        else p["equipo_local"]
                    )
                    card = ft.Container(
                        content=ft.Row(
                            [
                                ft.Column(
                                    [
                                        ft.Text(
                                            f"vs {rival_nombre}",
                                            weight=ft.FontWeight.BOLD,
                                            size=14,
                                            color=COLOR_TEXTO,
                                        ),
                                        ft.Text(
                                            f"Marcador: {p['goles_local']} - {p['goles_visita']}",
                                            color=COLOR_VERDE if p["jugado"] else COLOR_SUBTEXTO,
                                            size=12,
                                        ),
                                    ],
                                    spacing=2,
                                ),
                                ft.ElevatedButton(
                                    "Seleccionar" if not es_activo else "En Curso",
                                    icon=ft.Icons.PLAY_ARROW if not es_activo else ft.Icons.CHECK_CIRCLE,
                                    disabled=es_activo,
                                    bgcolor=COLOR_CELESTE_BOTON if not es_activo else COLOR_BORDE,
                                    color=COLOR_TEXTO,
                                    on_click=crear_handler_select(p),
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        padding=10,
                        bgcolor=COLOR_TARJETA,
                        border_radius=10,
                        border=ft.border.all(1.5, COLOR_CELESTE if es_activo else COLOR_BORDE),
                    )
                    partidos_mi_equipo_ui.append(card)
                else:
                    tf_g_loc = ft.TextField(
                        value=str(p["goles_local"]),
                        width=50,
                        border_color=COLOR_BORDE,
                        border_radius=8,
                        keyboard_type=ft.KeyboardType.NUMBER,
                        disabled=estado["es_invitado"],
                    )
                    tf_g_vis = ft.TextField(
                        value=str(p["goles_visita"]),
                        width=50,
                        border_color=COLOR_BORDE,
                        border_radius=8,
                        keyboard_type=ft.KeyboardType.NUMBER,
                        disabled=estado["es_invitado"],
                    )

                    def crear_handler_guardar_rival(p_id, input_l, input_v):
                        return lambda e: (
                            guardar_marcador_rival(
                                p_id,
                                int(input_l.value or 0),
                                int(input_v.value or 0),
                            ),
                            refrescar_vistas(),
                            page.update(),
                        )

                    card_rival = ft.Container(
                        content=ft.Row(
                            [
                                ft.Text(
                                    f"{p['equipo_local']}",
                                    weight=ft.FontWeight.BOLD,
                                    size=12,
                                    color=COLOR_TEXTO,
                                    expand=True,
                                ),
                                tf_g_loc,
                                ft.Text("-", color=COLOR_SUBTEXTO),
                                tf_g_vis,
                                ft.Text(
                                    f"{p['equipo_visita']}",
                                    weight=ft.FontWeight.BOLD,
                                    size=12,
                                    color=COLOR_TEXTO,
                                    expand=True,
                                    text_align=ft.TextAlign.RIGHT,
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.SAVE,
                                    icon_color=COLOR_CELESTE,
                                    disabled=estado["es_invitado"],
                                    on_click=crear_handler_guardar_rival(
                                        p["id"], tf_g_loc, tf_g_vis
                                    ),
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        padding=6,
                        bgcolor=COLOR_TARJETA,
                        border_radius=8,
                        border=ft.border.all(1, COLOR_BORDE),
                    )
                    partidos_rivales_ui.append(card_rival)

        elementos_columna = [
            ft.Text(
                "⚙️ Configuración del Grupo y Torneo",
                size=20,
                weight=ft.FontWeight.BOLD,
                color=COLOR_TEXTO,
            ),
            componente_tabla,
        ]

        # Si NO es invitado, se muestra la opción de definir nuevo grupo y resetear BD
        if not estado["es_invitado"]:
            elementos_columna.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(
                                "1. Definir Nuevo Grupo / Torneo",
                                weight=ft.FontWeight.BOLD,
                                color=COLOR_CELESTE,
                            ),
                            ft.Row([tf_nombre_grupo, tf_fecha_grupo]),
                            ft.Row([tf_equipo_principal, tf_equipos_rivales]),
                            ft.Row(
                                [
                                    ft.ElevatedButton(
                                        "Generar Grupo y Tabla",
                                        icon=ft.Icons.TABLE_CHART,
                                        bgcolor=COLOR_CELESTE_BOTON,
                                        color=COLOR_TEXTO,
                                        on_click=click_generar_grupo,
                                    ),
                                    ft.OutlinedButton(
                                        "Resetear BD",
                                        icon=ft.Icons.DELETE_FOREVER,
                                        icon_color=COLOR_ROJO,
                                        style=ft.ButtonStyle(
                                            color=COLOR_ROJO,
                                            side=ft.BorderSide(1, COLOR_ROJO),
                                        ),
                                        on_click=confirmar_reset,
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            texto_feedback_grupo,
                        ],
                        spacing=8,
                    ),
                    padding=14,
                    bgcolor=COLOR_TARJETA,
                    border_radius=14,
                    border=ft.border.all(1, COLOR_BORDE),
                )
            )

        elementos_columna.extend([
            ft.Text(
                f"Partidos de {estado['config']['equipo_principal']}",
                weight=ft.FontWeight.BOLD,
                color=COLOR_CELESTE,
            ),
            ft.Column(
                controls=partidos_mi_equipo_ui
                         or [ft.Text("Sin partidos asignados", color=COLOR_SUBTEXTO)],
                spacing=8,
            ),
            ft.Text(
                "Marcadores entre Rivales del Grupo (Combinatoria)",
                weight=ft.FontWeight.BOLD,
                color=COLOR_AMBAR,
            ),
            ft.Column(
                controls=partidos_rivales_ui
                         or [ft.Text("Sin partidos de rivales", color=COLOR_SUBTEXTO)],
                spacing=6,
            ),
        ])

        return ft.Column(
            elementos_columna,
            spacing=12,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

    # --- PANTALLA 2: PLANTEL DE JUGADORES ---
    def view_plantel():
        actualizar_minutos_jugadores()
        jugadores = obtener_jugadores_bd()
        max_titulares = estado["config"]["jugadores_en_cancha"]
        es_bloqueado = estado["finalizado"] or estado["es_invitado"]

        tf_nuevo_num = ft.TextField(
            label="N°",
            width=60,
            border_color=COLOR_BORDE,
            focused_border_color=COLOR_CELESTE,
            border_radius=10,
            disabled=es_bloqueado,
        )
        tf_nuevo_nom = ft.TextField(
            label="Nombre Jugador",
            expand=True,
            border_color=COLOR_BORDE,
            focused_border_color=COLOR_CELESTE,
            border_radius=10,
            disabled=es_bloqueado,
        )
        tf_nuevo_puesto = ft.TextField(
            label="Puesto",
            width=110,
            border_color=COLOR_BORDE,
            focused_border_color=COLOR_CELESTE,
            border_radius=10,
            disabled=es_bloqueado,
        )
        texto_status_jugador = ft.Text("", size=11)

        def click_agregar_jugador(e):
            if estado["es_invitado"]:
                return
            if tf_nuevo_nom.value and tf_nuevo_num.value:
                res = agregar_jugador_bd(
                    tf_nuevo_num.value.strip(),
                    tf_nuevo_nom.value.strip(),
                    tf_nuevo_puesto.value.strip() or "Jugador",
                )
                if res:
                    texto_status_jugador.value = "✅ Agregado a la BD."
                    texto_status_jugador.color = COLOR_VERDE
                    contenedor_plantel.content = view_plantel()
                else:
                    texto_status_jugador.value = "⚠️ Ya existe el jugador."
                    texto_status_jugador.color = COLOR_ROJO
                page.update()

        def pedir_confirmacion_borrado(nom_jugador):
            if estado["es_invitado"]:
                return
            minutos_totales = obtener_minutos_totales_bd()
            mins = minutos_totales.get(nom_jugador, 0) // 60

            def cerrar_dlg(ev):
                dlg_confirm.open = False
                page.update()

            def procesar_borrado(ev):
                eliminar_jugador_bd(nom_jugador)
                dlg_confirm.open = False
                contenedor_plantel.content = view_plantel()
                page.update()

            mensaje = f"¿Deseas borrar permanentemente a {nom_jugador}?"
            if mins > 0:
                mensaje += f"\n\n⚠️ ADVERTENCIA: Este jugador registra {mins} min jugados en el historial."

            dlg_confirm = ft.AlertDialog(
                title=ft.Text("Confirmar eliminación", color=COLOR_TEXTO),
                content=ft.Text(mensaje, color=COLOR_SUBTEXTO),
                actions=[
                    ft.TextButton("Cancelar", on_click=cerrar_dlg),
                    ft.ElevatedButton(
                        "Eliminar",
                        bgcolor=COLOR_ROJO,
                        color=COLOR_TEXTO,
                        on_click=procesar_borrado,
                    ),
                ],
                bgcolor=COLOR_TARJETA,
            )
            page.overlay.append(dlg_confirm)
            dlg_confirm.open = True
            page.update()

        titulares_ui, suplentes_ui = [], []

        for j in jugadores:
            nombre = j["nombre"]
            puesto = j["puesto"]
            num = j["numero"]

            es_titular = nombre in estado["titulares_seleccionados"]
            segs_hoy = estado["minutos_partido_actual"].get(nombre, 0)
            mins_hoy = segs_hoy // 60

            def crear_on_change(nom):
                def on_change(e):
                    if estado["es_invitado"]:
                        return
                    actualizar_minutos_jugadores()
                    limite = estado["config"]["jugadores_en_cancha"]
                    if e.control.value:
                        if len(estado["titulares_seleccionados"]) < limite:
                            if nom not in estado["titulares_seleccionados"]:
                                estado["titulares_seleccionados"].append(nom)
                        else:
                            e.control.value = False
                    else:
                        if nom in estado["titulares_seleccionados"]:
                            estado["titulares_seleccionados"].remove(nom)

                    guardar_estado_partido_activo()
                    contenedor_plantel.content = view_plantel()
                    page.update()

                return on_change

            def crear_handler_borrar(nom_del):
                return lambda e: pedir_confirmacion_borrado(nom_del)

            switch_titular = ft.Switch(
                value=es_titular,
                active_color=COLOR_CELESTE,
                disabled=es_bloqueado,
                on_change=crear_on_change(nombre),
            )

            icon_borrar = ft.IconButton(
                icon=ft.Icons.DELETE_OUTLINED,
                icon_color=COLOR_ROJO,
                icon_size=18,
                tooltip="Borrar jugador",
                disabled=estado["es_invitado"],
                on_click=crear_handler_borrar(nombre),
            )

            fila = ft.Container(
                content=ft.Row(
                    [
                        ft.Container(
                            content=ft.Text(
                                f"#{num}",
                                weight=ft.FontWeight.BOLD,
                                size=11,
                                color=COLOR_CELESTE,
                            ),
                            bgcolor=COLOR_BORDE,
                            padding=6,
                            border_radius=8,
                        ),
                        ft.Column(
                            [
                                ft.Text(
                                    nombre,
                                    weight=ft.FontWeight.BOLD,
                                    size=13,
                                    color=COLOR_TEXTO,
                                ),
                                ft.Text(
                                    f"{puesto} | {mins_hoy} min hoy",
                                    size=11,
                                    color=COLOR_SUBTEXTO,
                                ),
                            ],
                            expand=True,
                            spacing=1,
                        ),
                        switch_titular,
                        icon_borrar,
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                padding=4,
            )

            if es_titular:
                titulares_ui.append(fila)
            else:
                suplentes_ui.append(fila)

        elementos_plantel = [
            ft.Text(
                "📋 Plantel de Jugadores",
                size=20,
                weight=ft.FontWeight.BOLD,
                color=COLOR_TEXTO,
            ),
            ft.Container(
                content=ft.Row(
                    [
                        ft.Text("Titulares en cancha:", color=COLOR_TEXTO, weight=ft.FontWeight.W_500),
                        ft.Container(
                            content=ft.Text(
                                f"{len(estado['titulares_seleccionados'])} / {max_titulares}",
                                color=COLOR_TEXTO,
                                weight=ft.FontWeight.BOLD,
                            ),
                            bgcolor=COLOR_CELESTE_BOTON,
                            padding=ft.Padding(10, 4, 10, 4),
                            border_radius=12,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                padding=12,
                bgcolor=COLOR_TARJETA,
                border_radius=12,
                border=ft.border.all(1, COLOR_BORDE),
            ),
        ]

        # Si no es invitado, se muestra la sección para agregar nuevo jugador
        if not estado["es_invitado"]:
            elementos_plantel.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(
                                "Nuevo Jugador",
                                size=12,
                                weight=ft.FontWeight.BOLD,
                                color=COLOR_CELESTE,
                            ),
                            ft.Row([tf_nuevo_num, tf_nuevo_nom, tf_nuevo_puesto]),
                            ft.Row([
                                ft.ElevatedButton(
                                    "Agregar",
                                    icon=ft.Icons.PERSON_ADD,
                                    bgcolor=COLOR_CELESTE_BOTON,
                                    color=COLOR_TEXTO,
                                    disabled=es_bloqueado,
                                    on_click=click_agregar_jugador,
                                ),
                                texto_status_jugador,
                            ]),
                        ],
                        spacing=6,
                    ),
                    padding=12,
                    bgcolor=COLOR_TARJETA,
                    border_radius=12,
                    border=ft.border.all(1, COLOR_BORDE),
                )
            )

        elementos_plantel.extend([
            ft.Text(
                f"🟢 TITULARES EN CANCHA ({len(titulares_ui)})",
                weight=ft.FontWeight.BOLD,
                color=COLOR_VERDE,
                size=12,
            ),
            ft.Container(
                content=ft.Column(controls=titulares_ui or [ft.Text("Sin titulares", color=COLOR_SUBTEXTO)]),
                bgcolor=COLOR_TARJETA,
                padding=8,
                border_radius=12,
                border=ft.border.all(1, COLOR_VERDE),
            ),
            ft.Text(
                f"🟡 BANCA / SUPLENTES ({len(suplentes_ui)})",
                weight=ft.FontWeight.BOLD,
                color=COLOR_AMBAR,
                size=12,
            ),
            ft.Container(
                content=ft.Column(controls=suplentes_ui or [ft.Text("Sin suplentes", color=COLOR_SUBTEXTO)]),
                bgcolor=COLOR_TARJETA,
                padding=8,
                border_radius=12,
                border=ft.border.all(1, COLOR_BORDE),
            ),
        ])

        return ft.Column(
            elementos_plantel,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            spacing=8,
        )

    # --- PANTALLA 3: PARTIDO EN VIVO ---
    def view_partido():
        segs_actuales = obtener_segundos_actuales(estado)
        texto_reloj.value = formatear_tiempo(segs_actuales)
        actualizar_glosa()
        jugadores = obtener_jugadores_bd()

        nombre_principal = estado["config"]["equipo_principal"]
        nombre_rival = estado["config"]["equipo_rival"]
        fecha_partido = estado["config"].get("fecha", datetime.now().strftime("%Y-%m-%d"))
        es_fin = estado["finalizado"]

        marcador_ui = ft.Container(
            content=ft.Column(
                [
                    ft.Text(f"📅 {fecha_partido}", size=11, color=COLOR_SUBTEXTO),
                    ft.Row(
                        [
                            ft.Column(
                                [
                                    ft.Text(
                                        nombre_principal,
                                        weight=ft.FontWeight.BOLD,
                                        size=15,
                                        color=COLOR_TEXTO,
                                    ),
                                    ft.Text(
                                        f"{estado['goles_local']}",
                                        size=42,
                                        weight=ft.FontWeight.BOLD,
                                        color=COLOR_CELESTE,
                                    ),
                                ],
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                expand=True,
                            ),
                            ft.Text("VS", size=18, weight=ft.FontWeight.BOLD, color=COLOR_SUBTEXTO),
                            ft.Column(
                                [
                                    ft.Text(
                                        nombre_rival,
                                        weight=ft.FontWeight.BOLD,
                                        size=15,
                                        color=COLOR_TEXTO,
                                        overflow=ft.TextOverflow.ELLIPSIS,
                                    ),
                                    ft.Text(
                                        f"{estado['goles_rival']}",
                                        size=42,
                                        weight=ft.FontWeight.BOLD,
                                        color=COLOR_ROJO,
                                    ),
                                ],
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                expand=True,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=COLOR_TARJETA,
            padding=14,
            border_radius=14,
            border=ft.border.all(1, COLOR_BORDE),
        )

        def iniciar_reloj(e):
            if estado["es_invitado"] or estado["finalizado"]:
                return
            if not estado["corriendo"]:
                estado["corriendo"] = True
                estado["segs_al_iniciar"] = estado["segundos_acumulados"]
                estado["hora_inicio"] = datetime.now(timezone.utc).isoformat()
                estado["ultimo_segundo_procesado"] = estado["segundos_acumulados"]
                estado["alerta_custom"] = None
                actualizar_glosa()
                guardar_estado_partido_activo()
                refrescar_vistas()
                page.update()

        def pausar_reloj(e):
            if estado["es_invitado"] or estado["finalizado"]:
                return
            if estado["corriendo"]:
                segs = obtener_segundos_actuales(estado)
                actualizar_minutos_jugadores(segs)
                estado["segundos_acumulados"] = segs
                estado["segundos"] = segs
                estado["hora_inicio"] = None
                estado["corriendo"] = False
                estado["alerta_custom"] = None
                actualizar_glosa()
                guardar_estado_partido_activo()
                refrescar_vistas()
                page.update()

        def alternar_finalizacion(e):
            if estado["es_invitado"]:
                return
            if estado["corriendo"]:
                pausar_reloj(None)

            estado["finalizado"] = not estado["finalizado"]
            estado["alerta_custom"] = None
            actualizar_glosa()

            guardar_estado_partido_activo()
            refrescar_vistas()
            page.update()

        dd_evento = ft.Dropdown(
            label="Evento",
            options=[ft.dropdown.Option(ev) for ev in EVENTOS_DEFECTO],
            expand=True,
            border_color=COLOR_BORDE,
            focused_border_color=COLOR_CELESTE,
            border_radius=10,
            disabled=es_fin or estado["es_invitado"],
        )
        opciones_titulares = [
            ft.dropdown.Option(nom) for nom in estado["titulares_seleccionados"]
        ]
        dd_jugador_titular = ft.Dropdown(
            label="Jugador Titular",
            options=opciones_titulares,
            expand=True,
            border_color=COLOR_BORDE,
            focused_border_color=COLOR_CELESTE,
            border_radius=10,
            disabled=es_fin or estado["es_invitado"],
        )

        suplentes_actuales = [
            j["nombre"]
            for j in jugadores
            if j["nombre"] not in estado["titulares_seleccionados"]
        ]
        dd_suplente_entra = ft.Dropdown(
            label="Entra (Suplente)",
            options=[ft.dropdown.Option(nom) for nom in suplentes_actuales],
            expand=True,
            visible=False,
            border_color=COLOR_BORDE,
            focused_border_color=COLOR_CELESTE,
            border_radius=10,
            disabled=es_fin or estado["es_invitado"],
        )

        texto_status_evento = ft.Text("", color=COLOR_VERDE, size=12)

        def al_cambiar_dropdown_evento(e):
            if dd_evento.value == "Gol":
                dd_jugador_titular.label = "Autor del Gol"
                dd_jugador_titular.options = [
                                                 ft.dropdown.Option("⚡ Equipo Rival")
                                             ] + opciones_titulares
                dd_suplente_entra.visible = False
            elif dd_evento.value == "Cambio":
                dd_jugador_titular.label = "Sale (Titular)"
                dd_jugador_titular.options = opciones_titulares
                dd_suplente_entra.visible = True
            else:
                dd_jugador_titular.label = "Jugador Titular"
                dd_jugador_titular.options = opciones_titulares
                dd_suplente_entra.visible = False
            page.update()

        dd_evento.on_change = al_cambiar_dropdown_evento

        def registrar_evento_click(e):
            if estado["es_invitado"] or estado["finalizado"]:
                return

            tipo_evento = dd_evento.value
            jugador_sel = dd_jugador_titular.value

            if not tipo_evento or not jugador_sel:
                texto_status_evento.value = "⚠️ Selecciona evento y jugador."
                texto_status_evento.color = COLOR_ROJO
                page.update()
                return

            minuto_actual = f"{obtener_segundos_actuales(estado) // 60:02d}'"

            if tipo_evento == "Gol":
                if jugador_sel == "⚡ Equipo Rival":
                    estado["goles_rival"] += 1
                    desc_evento = f"Gol de {estado['config']['equipo_rival']}"
                else:
                    estado["goles_local"] += 1
                    desc_evento = f"Gol de {jugador_sel}"

                estado["eventos_registrados"].append({
                    "minuto": minuto_actual,
                    "evento": "Gol",
                    "jugador": desc_evento,
                })

            elif tipo_evento == "Cambio":
                jugador_entra = dd_suplente_entra.value
                if not jugador_entra:
                    texto_status_evento.value = "⚠️ Selecciona suplente que entra."
                    texto_status_evento.color = COLOR_ROJO
                    page.update()
                    return

                actualizar_minutos_jugadores()

                if jugador_sel in estado["titulares_seleccionados"]:
                    estado["titulares_seleccionados"].remove(jugador_sel)
                if jugador_entra not in estado["titulares_seleccionados"]:
                    estado["titulares_seleccionados"].append(jugador_entra)

                desc_evento = f"Sale {jugador_sel} ➔ Entra {jugador_entra}"
                estado["eventos_registrados"].append({
                    "minuto": minuto_actual,
                    "evento": "Cambio",
                    "jugador": desc_evento,
                })

            else:
                estado["eventos_registrados"].append({
                    "minuto": minuto_actual,
                    "evento": tipo_evento,
                    "jugador": jugador_sel,
                })

            guardar_estado_partido_activo()
            refrescar_vistas()
            page.update()

        def crear_handler_eliminar_evento(ev_obj):
            def handler(e):
                if estado["es_invitado"]:
                    return
                if ev_obj in estado["eventos_registrados"]:
                    estado["eventos_registrados"].remove(ev_obj)
                    if ev_obj.get("evento") == "Gol":
                        if "Equipo Rival" in ev_obj.get("jugador", "") or estado['config'][
                            'equipo_rival'] in ev_obj.get("jugador", ""):
                            estado["goles_rival"] = max(0, estado["goles_rival"] - 1)
                        else:
                            estado["goles_local"] = max(0, estado["goles_local"] - 1)
                    guardar_estado_partido_activo()
                    refrescar_vistas()
                    page.update()

            return handler

        eventos_ui = []
        if estado["eventos_registrados"]:
            for ev in reversed(estado["eventos_registrados"]):
                minuto = ev.get("minuto", "00'")
                tipo = ev.get("evento", "Evento")
                jug = ev.get("jugador", "")

                icono = ft.Icons.SPORTS_SOCCER if tipo == "Gol" else (
                    ft.Icons.SWAP_HORIZ if tipo == "Cambio" else (
                        ft.Icons.STYLE if "Tarjeta" in tipo else ft.Icons.CHECK_CIRCLE
                    )
                )
                color_ev = COLOR_VERDE if tipo == "Gol" else (
                    COLOR_CELESTE if tipo == "Cambio" else (
                        COLOR_AMBAR if "Amarilla" in tipo else COLOR_ROJO
                    )
                )

                card_ev = ft.Container(
                    content=ft.Row(
                        [
                            ft.Row(
                                [
                                    ft.Icon(icono, color=color_ev, size=18),
                                    ft.Text(f"[{minuto}]", weight=ft.FontWeight.BOLD, color=COLOR_CELESTE, size=12),
                                    ft.Text(f"{tipo}: {jug}", color=COLOR_TEXTO, size=13, weight=ft.FontWeight.W_500),
                                ],
                                spacing=8,
                            ),
                            ft.IconButton(
                                icon=ft.Icons.DELETE_OUTLINED,
                                icon_color=COLOR_ROJO,
                                icon_size=16,
                                disabled=es_fin or estado["es_invitado"],
                                tooltip="Eliminar evento",
                                on_click=crear_handler_eliminar_evento(ev)
                            )
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    padding=ft.Padding(8, 4, 8, 4),
                    bgcolor=COLOR_TARJETA,
                    border_radius=8,
                    border=ft.border.all(1, COLOR_BORDE),
                )
                eventos_ui.append(card_ev)
        else:
            eventos_ui.append(
                ft.Text("Aún no se registran eventos en este partido", color=COLOR_SUBTEXTO, size=12)
            )

        elementos_partido = [
            ft.Row(
                [
                    ft.Text(
                        "⏱️ Control del Partido",
                        size=18,
                        weight=ft.FontWeight.BOLD,
                        color=COLOR_TEXTO,
                    ),
                    ft.OutlinedButton(
                        "Reabrir Partido" if es_fin else "Finalizar Partido",
                        icon=ft.Icons.LOCK_OPEN if es_fin else ft.Icons.LOCK,
                        visible=not estado["es_invitado"],
                        style=ft.ButtonStyle(
                            color=COLOR_VERDE if es_fin else COLOR_ROJO,
                            side=ft.BorderSide(1, COLOR_VERDE if es_fin else COLOR_ROJO),
                        ),
                        on_click=alternar_finalizacion,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            marcador_ui,
            ft.Container(content=texto_reloj, alignment=ft.Alignment(0, 0)),
            ft.Container(content=texto_alerta_cambio, alignment=ft.Alignment(0, 0)),
        ]

        # Si no es invitado, se muestran los botones de control de reloj
        if not estado["es_invitado"]:
            elementos_partido.append(
                ft.Row(
                    [
                        ft.IconButton(
                            icon=ft.Icons.PLAY_ARROW_ROUNDED,
                            icon_size=36,
                            icon_color=COLOR_VERDE if not es_fin else COLOR_SUBTEXTO,
                            bgcolor=COLOR_BORDE,
                            disabled=es_fin,
                            on_click=iniciar_reloj,
                        ),
                        ft.IconButton(
                            icon=ft.Icons.PAUSE_ROUNDED,
                            icon_size=36,
                            icon_color=COLOR_AMBAR if not es_fin else COLOR_SUBTEXTO,
                            bgcolor=COLOR_BORDE,
                            disabled=es_fin,
                            on_click=pausar_reloj,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                )
            )

        elementos_partido.append(ft.Divider(height=5, color=COLOR_BORDE))

        # Si no es invitado, se muestran los controles para registrar eventos
        if not estado["es_invitado"]:
            elementos_partido.extend([
                ft.Text(
                    "📝 Registrar Evento",
                    weight=ft.FontWeight.BOLD,
                    color=COLOR_CELESTE,
                ),
                ft.Row([dd_evento, dd_jugador_titular]),
                dd_suplente_entra,
                ft.ElevatedButton(
                    "Registrar Evento",
                    icon=ft.Icons.ADD_TASK,
                    bgcolor=COLOR_CELESTE_BOTON,
                    color=COLOR_TEXTO,
                    disabled=es_fin,
                    on_click=registrar_evento_click,
                ),
                texto_status_evento,
                ft.Divider(height=5, color=COLOR_BORDE),
            ])

        elementos_partido.extend([
            ft.Text(
                "📜 Historial de Eventos del Partido",
                weight=ft.FontWeight.BOLD,
                color=COLOR_CELESTE,
            ),
            ft.Column(controls=eventos_ui, spacing=6),
        ])

        return ft.Column(
            elementos_partido,
            scroll=ft.ScrollMode.AUTO,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True,
            spacing=8,
        )

    # --- PANTALLA 4: RANKING DE MINUTOS ---
    def view_minutos():
        actualizar_minutos_jugadores()
        jugadores = obtener_jugadores_bd()
        minutos_acumulados_bd = obtener_minutos_totales_bd()
        stats_ui = []
        texto_export = ft.Text("", color=COLOR_VERDE)

        def click_exportar(e):
            try:
                datos_jugadores = []
                for j in jugadores:
                    nom = j["nombre"]
                    segs = minutos_acumulados_bd.get(nom, 0)
                    datos_jugadores.append({
                        "Número": j["numero"],
                        "Jugador": nom,
                        "Puesto": j["puesto"],
                        "Minutos Acumulados Totales": segs // 60,
                    })
                df = pd.DataFrame(datos_jugadores)
                df.to_excel("Reporte_Minutos_BD.xlsx", index=False)
                texto_export.value = "✅ 'Reporte_Minutos_BD.xlsx' guardado."
            except Exception as ex:
                texto_export.value = f"❌ Error exportando: {ex}"
            page.update()

        jugadores_ordenados = sorted(
            jugadores,
            key=lambda x: minutos_acumulados_bd.get(x["nombre"], 0),
            reverse=False,
        )

        for j in jugadores_ordenados:
            nombre = j["nombre"]
            puesto = j["puesto"]
            num = j["numero"]
            segs_totales = minutos_acumulados_bd.get(nombre, 0)
            mins_totales = segs_totales // 60

            tarjeta = ft.Container(
                content=ft.Row(
                    [
                        ft.Container(
                            content=ft.Text(
                                f"#{num}",
                                weight=ft.FontWeight.BOLD,
                                size=11,
                                color=COLOR_TEXTO,
                            ),
                            bgcolor=COLOR_CELESTE_BOTON,
                            padding=6,
                            border_radius=8,
                        ),
                        ft.Column(
                            [
                                ft.Text(
                                    nombre,
                                    weight=ft.FontWeight.BOLD,
                                    size=13,
                                    color=COLOR_TEXTO,
                                ),
                                ft.Text(
                                    f"Puesto: {puesto}",
                                    size=11,
                                    color=COLOR_SUBTEXTO,
                                ),
                            ],
                            expand=True,
                            spacing=1,
                        ),
                        ft.Text(
                            f"{mins_totales} min",
                            color=COLOR_CELESTE,
                            weight=ft.FontWeight.BOLD,
                            size=15,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                padding=10,
                bgcolor=COLOR_TARJETA,
                border_radius=10,
                border=ft.border.all(1, COLOR_BORDE),
            )
            stats_ui.append(tarjeta)

        return ft.Column(
            [
                ft.Text(
                    "📊 Ranking Acumulado de Minutos (Menor a Mayor)",
                    size=18,
                    weight=ft.FontWeight.BOLD,
                    color=COLOR_TEXTO,
                ),
                ft.ElevatedButton(
                    "Exportar a Excel",
                    icon=ft.Icons.EXPLICIT,
                    bgcolor=COLOR_CELESTE_BOTON,
                    color=COLOR_TEXTO,
                    on_click=click_exportar,
                ),
                texto_export,
                ft.Divider(height=10, color=COLOR_BORDE),
                ft.Column(
                    controls=stats_ui,
                    scroll=ft.ScrollMode.AUTO,
                    expand=True,
                    spacing=8,
                ),
            ],
            expand=True,
        )

    # --- CONTENEDORES PRINCIPALES ---
    contenedor_config = ft.Container(
        content=view_configuracion(), expand=True, padding=12, visible=True
    )
    contenedor_plantel = ft.Container(
        content=view_plantel(), expand=True, padding=12, visible=False
    )
    contenedor_partido = ft.Container(
        content=view_partido(), expand=True, padding=12, visible=False
    )
    contenedor_minutos = ft.Container(
        content=view_minutos(), expand=True, padding=12, visible=False
    )

    def refrescar_vistas():
        contenedor_config.content = view_configuracion()
        contenedor_plantel.content = view_plantel()
        contenedor_partido.content = view_partido()
        contenedor_minutos.content = view_minutos()

    def construir_barra_navegacion():
        destinos = [
            ft.NavigationBarDestination(icon=ft.Icons.SETTINGS, label="Config & Tabla"),
            ft.NavigationBarDestination(icon=ft.Icons.PEOPLE, label="Plantel"),
            ft.NavigationBarDestination(icon=ft.Icons.SPORTS_SOCCER, label="Partido"),
        ]
        if not estado["es_invitado"]:
            destinos.append(
                ft.NavigationBarDestination(icon=ft.Icons.BAR_CHART, label="Ranking")
            )
        return ft.NavigationBar(
            selected_index=0,
            bgcolor=COLOR_TARJETA,
            indicator_color=COLOR_CELESTE_BOTON,
            on_change=cambiar_pantalla,
            destinations=destinos,
        )

    def cambiar_pantalla(e):
        indice = e.control.selected_index
        estado["pestana_activa"] = indice

        # Si es invitado, solo hay 3 pestañas (0, 1, 2)
        if estado["es_invitado"]:
            contenedor_config.visible = indice == 0
            contenedor_plantel.visible = indice == 1
            contenedor_partido.visible = indice == 2
            contenedor_minutos.visible = False
        else:
            contenedor_config.visible = indice == 0
            contenedor_plantel.visible = indice == 1
            contenedor_partido.visible = indice == 2
            contenedor_minutos.visible = indice == 3

        if indice == 0:
            contenedor_config.content = view_configuracion()
        elif indice == 1:
            contenedor_plantel.content = view_plantel()
        elif indice == 2:
            contenedor_partido.content = view_partido()
        elif indice == 3 and not estado["es_invitado"]:
            contenedor_minutos.content = view_minutos()
        page.update()

    page.navigation_bar = construir_barra_navegacion()

    header_app = ft.Container(
        content=ft.Row(
            [
                ft.Row(
                    [
                        ft.Icon(ft.Icons.SPORTS_SOCCER, color=COLOR_CELESTE, size=22),
                        ft.Text(
                            "Real Dunalastair FC",
                            weight=ft.FontWeight.BOLD,
                            size=15,
                            color=COLOR_TEXTO,
                        ),
                    ],
                    spacing=6,
                ),
                ft.Row(
                    [
                        ft.Container(
                            content=ft.Text(
                                "👑 Administrador" if not estado["es_invitado"] else "👤 Invitado",
                                size=10,
                                weight=ft.FontWeight.BOLD,
                                color=COLOR_VERDE if not estado["es_invitado"] else COLOR_AMBAR,
                            ),
                            bgcolor=COLOR_BORDE,
                            padding=ft.Padding(8, 3, 8, 3),
                            border_radius=8,
                        ),
                        ft.IconButton(
                            icon=ft.Icons.LOGOUT,
                            icon_size=16,
                            icon_color=COLOR_ROJO,
                            tooltip="Cambiar de Rol",
                            on_click=lambda e: mostrar_dialogo_rol(),
                        )
                    ],
                    spacing=4,
                )
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        ),
        padding=ft.Padding(12, 10, 12, 10),
        bgcolor=COLOR_TARJETA,
    )

    app_layout = ft.Container(
        expand=True,
        bgcolor=COLOR_FONDO,
        content=ft.Column(
            controls=[
                header_app,
                ft.Stack(
                    controls=[
                        contenedor_config,
                        contenedor_plantel,
                        contenedor_partido,
                        contenedor_minutos,
                    ],
                    expand=True,
                ),
            ],
            expand=True,
            spacing=0,
        ),
    )

    def mostrar_dialogo_rol():
        tf_clave = ft.TextField(
            label="Ingrese su RUT (Clave Admin)",
            password=True,
            can_reveal_password=True,
            border_color=COLOR_BORDE,
            focused_border_color=COLOR_CELESTE,
            border_radius=10,
        )
        texto_error = ft.Text("", color=COLOR_ROJO, size=12)

        def seleccionar_invitado(e):
            estado["es_invitado"] = True
            dialogo_rol.open = False
            page.navigation_bar = construir_barra_navegacion()
            page.navigation_bar.selected_index = 0
            estado["pestana_activa"] = 0
            contenedor_config.visible = True
            contenedor_plantel.visible = False
            contenedor_partido.visible = False
            contenedor_minutos.visible = False
            refrescar_vistas()
            page.update()

        def verificar_admin(e):
            if tf_clave.value.strip() == "11165045":
                estado["es_invitado"] = False
                dialogo_rol.open = False
                page.navigation_bar = construir_barra_navegacion()
                page.navigation_bar.selected_index = 0
                estado["pestana_activa"] = 0
                contenedor_config.visible = True
                contenedor_plantel.visible = False
                contenedor_partido.visible = False
                contenedor_minutos.visible = False
                refrescar_vistas()
                page.update()
            else:
                texto_error.value = "❌ RUT incorrecto. Acceso denegado."
                page.update()

        dialogo_rol = ft.AlertDialog(
            title=ft.Text("Seleccione su Rol de Acceso", color=COLOR_TEXTO),
            content=ft.Column(
                [
                    ft.Text("Elija cómo desea ingresar a la aplicación:", color=COLOR_SUBTEXTO),
                    ft.ElevatedButton(
                        "Entrar como Invitado (Solo Consulta)",
                        icon=ft.Icons.VISIBILITY,
                        bgcolor=COLOR_AMBAR,
                        color=COLOR_FONDO,
                        on_click=seleccionar_invitado,
                    ),
                    ft.Divider(color=COLOR_BORDE),
                    ft.Text("Acceso Administrador:", weight=ft.FontWeight.BOLD, color=COLOR_CELESTE),
                    tf_clave,
                    ft.ElevatedButton(
                        "Entrar como Administrador",
                        icon=ft.Icons.LOCK_OPEN,
                        bgcolor=COLOR_CELESTE_BOTON,
                        color=COLOR_TEXTO,
                        on_click=verificar_admin,
                    ),
                    texto_error,
                ],
                tight=True,
                spacing=10,
            ),
            bgcolor=COLOR_TARJETA,
            modal=True,
        )
        page.overlay.append(dialogo_rol)
        dialogo_rol.open = True
        page.update()

    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.add(app_layout)

    # Mostrar el diálogo de selección de rol al arrancar
    mostrar_dialogo_rol()


if __name__ == "__main__":
    puerto = int(os.environ.get("PORT", 8080))
    ft.app(
        target=main, host="0.0.0.0", port=puerto, view=ft.AppView.WEB_BROWSER
    )