import asyncio
from datetime import datetime
import json
import os
# Reemplazamos el sqlite3 nativo por el driver de Turso/LibSQL
import libsql_experimental as sqlite3
import flet as ft
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

# --- CONFIGURACIÓN DE BASE DE DATOS TURSO EN LA NUBE ---
# Reemplaza estos valores con tu URL y Token generados en Turso
TURSO_URL = os.environ.get("TURSO_URL", "libsql://apppartidos-mnieto.aws-us-east-2.turso.io")
TURSO_TOKEN = os.environ.get("TURSO_TOKEN", "tu-token-secreto-aqui")

def conectar_bd():
    """Genera la conexión a la base de datos remota de Turso"""
    return sqlite3.connect(TURSO_URL, auth_token="eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3OTAzMzgxNTcsImlkIjoiMDFhMGQ4NzctNzEwMS03NjMyLThiOWYtY2ExOWMzYmI1NDc3Iiwia2lkIjoiTDl6UGpCZkwtX2JXbzVlZWl3RElTcUZ2TFIwNms2c2Z2RGRDRTV3Q20wUSIsInJpZCI6IjUwMzI1MGM2LWFlNzgtNGZkMC1iZTg2LWY1YzkxOGE4NDFjNCJ9.NVAc4gJsI2qAz75C00A6nYrJLTzgOGgEynUB5Y4GBp5rJIEtmczZjwYHAoUMGvcfZKk4Y8qYfEioGthy86guCw")

ORDEN_PUESTOS = {
    "Arquero": 1,
    "Defensa": 2,
    "Medio": 3,
    "Delantero": 4
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
        CREATE TABLE IF NOT EXISTS partidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            equipo_rival TEXT NOT NULL,
            tiempos_por_partido INTEGER NOT NULL,
            minutos_por_tiempo INTEGER NOT NULL,
            jugadores_en_cancha INTEGER NOT NULL,
            goles_local INTEGER DEFAULT 0,
            goles_rival INTEGER DEFAULT 0,
            segundos INTEGER DEFAULT 0,
            titulares TEXT DEFAULT '[]',
            eventos TEXT DEFAULT '[]',
            minutos_partido TEXT DEFAULT '{}',
            finalizado INTEGER DEFAULT 0
        )
    """)

    try:
        cursor.execute("ALTER TABLE partidos ADD COLUMN finalizado INTEGER DEFAULT 0")
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
    conn.close()


def main(page: ft.Page):
    inicializar_bd()

    page.title = "Dunalastair FC - Control de Partidos"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    page.bgcolor = COLOR_FONDO

    # --- ESTADO DE LA APLICACIÓN ---
    estado = {
        "segundos": 0,
        "corriendo": False,
        "finalizado": False,
        "goles_local": 0,
        "goles_rival": 0,
        "partidos": [],
        "partido_activo_id": None,
        "minutos_partido_actual": {},
        "titulares_seleccionados": [],
        "eventos_registrados": [],
        "config": {
            "equipo_rival": "Rival FC",
            "tiempos_por_partido": 2,
            "minutos_por_tiempo": 10,
            "jugadores_en_cancha": 7,
            "fecha": datetime.now().strftime("%Y-%m-%d"),
        },
    }

    # --- CONSULTAS Y OPERACIONES BD ---
    def obtener_jugadores_bd():
        conn = conectar_bd()
        cursor = conn.cursor()
        cursor.execute("SELECT numero, nombre, puesto FROM jugadores")
        filas = cursor.fetchall()
        conn.close()

        lista = [{"numero": r[0], "nombre": r[1], "puesto": r[2]} for r in filas]

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
        try:
            conn = conectar_bd()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO jugadores (numero, nombre, puesto) VALUES (?, ?, ?)",
                (str(num), nom, puesto),
            )
            conn.commit()
            conn.close()
            return True
        except Exception:
            return False

    def eliminar_jugador_bd(nombre):
        conn = conectar_bd()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM jugadores WHERE nombre=?", (nombre,))
        conn.commit()
        conn.close()

        if nombre in estado["titulares_seleccionados"]:
            estado["titulares_seleccionados"].remove(nombre)
        if nombre in estado["minutos_partido_actual"]:
            del estado["minutos_partido_actual"][nombre]

        guardar_estado_partido_activo()

    def cargar_partidos_bd():
        conn = conectar_bd()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, fecha, equipo_rival, tiempos_por_partido, minutos_por_tiempo, jugadores_en_cancha, goles_local, goles_rival, segundos, titulares, eventos, minutos_partido, finalizado FROM partidos ORDER BY fecha DESC, id DESC"
        )
        filas = cursor.fetchall()
        conn.close()

        lista_partidos = []
        for row in filas:
            lista_partidos.append(
                {
                    "id": row[0],
                    "fecha": row[1],
                    "equipo_rival": row[2],
                    "tiempos_por_partido": row[3],
                    "minutos_por_tiempo": row[4],
                    "jugadores_en_cancha": row[5],
                    "goles_local": row[6],
                    "goles_rival": row[7],
                    "segundos": row[8],
                    "titulares": json.loads(row[9]),
                    "eventos": json.loads(row[10]),
                    "minutos_partido": json.loads(row[11]),
                    "finalizado": bool(row[12]) if len(row) > 12 else False,
                }
            )
        estado["partidos"] = lista_partidos

        if not lista_partidos:
            crear_partido_bd(
                datetime.now().strftime("%Y-%m-%d"), "Rival FC", 2, 10, 7
            )
            cargar_partidos_bd()
        elif estado["partido_activo_id"] is None:
            activar_partido_memoria(lista_partidos[0])

    def crear_partido_bd(fecha, rival, tiempos, minutos_tiempo, jugadores_cancha):
        conn = conectar_bd()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO partidos (fecha, equipo_rival, tiempos_por_partido, minutos_por_tiempo, jugadores_en_cancha)
            VALUES (?, ?, ?, ?, ?)
        """,
            (fecha, rival, tiempos, minutos_tiempo, jugadores_cancha),
        )
        nuevo_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return nuevo_id

    def guardar_estado_partido_activo():
        if estado["partido_activo_id"] is None:
            return

        conn = conectar_bd()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE partidos
            SET goles_local=?, goles_rival=?, segundos=?, titulares=?, eventos=?, minutos_partido=?, finalizado=?
            WHERE id=?
        """,
            (
                estado["goles_local"],
                estado["goles_rival"],
                estado["segundos"],
                json.dumps(estado["titulares_seleccionados"], ensure_ascii=False),
                json.dumps(estado["eventos_registrados"], ensure_ascii=False),
                json.dumps(estado["minutos_partido_actual"], ensure_ascii=False),
                1 if estado["finalizado"] else 0,
                estado["partido_activo_id"],
            ),
        )
        conn.commit()
        conn.close()

        for p in estado["partidos"]:
            if p["id"] == estado["partido_activo_id"]:
                p["goles_local"] = estado["goles_local"]
                p["goles_rival"] = estado["goles_rival"]
                p["segundos"] = estado["segundos"]
                p["titulares"] = list(estado["titulares_seleccionados"])
                p["eventos"] = list(estado["eventos_registrados"])
                p["minutos_partido"] = dict(estado["minutos_partido_actual"])
                p["finalizado"] = estado["finalizado"]
                break

    def eliminar_partido_bd(partido_id):
        conn = conectar_bd()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM partidos WHERE id=?", (partido_id,))
        conn.commit()
        conn.close()

    def reiniciar_base_datos():
        conn = conectar_bd()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM partidos")
        cursor.execute("DELETE FROM jugadores")
        for j in DATOS_INICIALES:
            cursor.execute(
                "INSERT INTO jugadores (numero, nombre, puesto) VALUES (?, ?, ?)",
                (str(j["numero"]), j["nombre"], j["puesto"]),
            )
        conn.commit()
        conn.close()
        estado["partido_activo_id"] = None
        cargar_partidos_bd()

    def obtener_minutos_totales_bd():
        conn = conectar_bd()
        cursor = conn.cursor()
        cursor.execute("SELECT minutos_partido FROM partidos")
        filas = cursor.fetchall()
        conn.close()

        minutos_totales = {}
        for row in filas:
            min_dict = json.loads(row[0])
            for jugador, segs in min_dict.items():
                minutos_totales[jugador] = minutos_totales.get(jugador, 0) + segs
        return minutos_totales

    def activar_partido_memoria(partido):
        estado["partido_activo_id"] = partido["id"]
        estado["goles_local"] = partido["goles_local"]
        estado["goles_rival"] = partido["goles_rival"]
        estado["segundos"] = partido["segundos"]
        estado["titulares_seleccionados"] = list(partido["titulares"])
        estado["eventos_registrados"] = list(partido["eventos"])
        estado["minutos_partido_actual"] = dict(partido["minutos_partido"])
        estado["finalizado"] = bool(partido.get("finalizado", False))
        estado["corriendo"] = False
        estado["config"] = {
            "equipo_rival": partido["equipo_rival"],
            "tiempos_por_partido": partido["tiempos_por_partido"],
            "minutos_por_tiempo": partido["minutos_por_tiempo"],
            "jugadores_en_cancha": partido["jugadores_en_cancha"],
            "fecha": partido["fecha"],
        }

    cargar_partidos_bd()

    # --- COMPONENTES VISUALES ---
    texto_reloj = ft.Text("00:00", size=50, weight=ft.FontWeight.BOLD, color=COLOR_CELESTE)
    texto_alerta_cambio = ft.Text("Partido listo", weight=ft.FontWeight.W_600, color=COLOR_SUBTEXTO)

    def formatear_tiempo(segs):
        return f"{segs // 60:02d}:{segs % 60:02d}"

    # --- LOOP DEL CRONÓMETRO ---
    async def loop_reloj():
        contador_guardado = 0
        while True:
            await asyncio.sleep(1)
            if estado["corriendo"] and not estado["finalizado"]:
                estado["segundos"] += 1
                seg = estado["segundos"]
                texto_reloj.value = formatear_tiempo(seg)

                duracion_tiempo_segs = estado["config"]["minutos_por_tiempo"] * 60
                duracion_total_partido = duracion_tiempo_segs * estado["config"]["tiempos_por_partido"]

                if seg >= duracion_total_partido:
                    estado["corriendo"] = False
                    estado["finalizado"] = True
                    texto_alerta_cambio.value = "🏁 ¡PARTIDO FINALIZADO!"
                    texto_alerta_cambio.color = COLOR_ROJO
                    guardar_estado_partido_activo()
                elif seg > 0 and seg % duracion_tiempo_segs == 0:
                    estado["corriendo"] = False
                    tiempo_terminado = seg // duracion_tiempo_segs
                    texto_alerta_cambio.value = f"🏁 ¡FIN DEL TIEMPO {tiempo_terminado}!"
                    texto_alerta_cambio.color = COLOR_AMBAR

                for jugador in estado["titulares_seleccionados"]:
                    estado["minutos_partido_actual"][jugador] = (
                        estado["minutos_partido_actual"].get(jugador, 0) + 1
                    )

                contador_guardado += 1
                if contador_guardado >= 5:
                    guardar_estado_partido_activo()
                    contador_guardado = 0

                try:
                    page.update()
                except Exception:
                    pass

    page.run_task(loop_reloj)

    # --- PANTALLA 1: CONFIGURACIÓN ---
    def view_configuracion():
        cargar_partidos_bd()

        tf_fecha = ft.TextField(
            label="Fecha (AAAA-MM-DD)",
            value=datetime.now().strftime("%Y-%m-%d"),
            width=150, border_color=COLOR_BORDE, focused_border_color=COLOR_CELESTE, border_radius=10
        )
        tf_rival = ft.TextField(label="Equipo Rival", value="Rival FC", expand=True, border_color=COLOR_BORDE, focused_border_color=COLOR_CELESTE, border_radius=10)
        tf_tiempos = ft.TextField(label="Tiempos", value="2", keyboard_type=ft.KeyboardType.NUMBER, width=90, border_color=COLOR_BORDE, focused_border_color=COLOR_CELESTE, border_radius=10)
        tf_minutos_tiempo = ft.TextField(label="Min/Tiempo", value="10", keyboard_type=ft.KeyboardType.NUMBER, width=100, border_color=COLOR_BORDE, focused_border_color=COLOR_CELESTE, border_radius=10)
        tf_jugadores_cancha = ft.TextField(label="Cancha", value="7", keyboard_type=ft.KeyboardType.NUMBER, width=90, border_color=COLOR_BORDE, focused_border_color=COLOR_CELESTE, border_radius=10)

        texto_feedback = ft.Text("", color=COLOR_VERDE, size=12)

        def crear_partido_click(e):
            try:
                rival = tf_rival.value.strip()
                fecha_val = tf_fecha.value.strip()

                if not rival or not fecha_val:
                    texto_feedback.value = "⚠️ Ingresa fecha y nombre del rival."
                    texto_feedback.color = COLOR_ROJO
                    page.update()
                    return

                nuevo_id = crear_partido_bd(
                    fecha_val,
                    rival,
                    int(tf_tiempos.value),
                    int(tf_minutos_tiempo.value),
                    int(tf_jugadores_cancha.value),
                )

                cargar_partidos_bd()
                for p in estado["partidos"]:
                    if p["id"] == nuevo_id:
                        activar_partido_memoria(p)
                        break

                texto_feedback.value = f"✅ Partido vs '{rival}' registrado en BD."
                texto_feedback.color = COLOR_VERDE
                contenedor_config.content = view_configuracion()
                page.update()
            except ValueError:
                texto_feedback.value = "❌ Ingresa números válidos."
                texto_feedback.color = COLOR_ROJO
                page.update()

        def seleccionar_partido(partido):
            activar_partido_memoria(partido)
            guardar_estado_partido_activo()
            contenedor_config.content = view_configuracion()
            page.update()

        def eliminar_partido(partido_id):
            eliminar_partido_bd(partido_id)
            cargar_partidos_bd()
            if estado["partidos"]:
                activar_partido_memoria(estado["partidos"][0])
            contenedor_config.content = view_configuracion()
            page.update()

        def confirmar_reset(e):
            def cerrar_dlg(ev):
                dialogo_reset.open = False
                page.update()

            def procesar_reset(ev):
                reiniciar_base_datos()
                texto_reloj.value = "00:00"
                texto_alerta_cambio.value = "BD Reiniciada"
                texto_feedback.value = "🔄 Base de datos restablecida."
                dialogo_reset.open = False
                contenedor_config.content = view_configuracion()
                page.update()

            dialogo_reset = ft.AlertDialog(
                title=ft.Text("¿Borrar Base de Datos?", color=COLOR_TEXTO),
                content=ft.Text("Se eliminarán todos los partidos y estadísticas."),
                actions=[
                    ft.TextButton("Cancelar", on_click=cerrar_dlg),
                    ft.ElevatedButton("Borrar BD", bgcolor=COLOR_ROJO, color=COLOR_TEXTO, on_click=procesar_reset),
                ],
                bgcolor=COLOR_TARJETA
            )
            page.overlay.append(dialogo_reset)
            dialogo_reset.open = True
            page.update()

        partidos_por_fecha = {}
        for p in estado["partidos"]:
            f = p["fecha"]
            partidos_por_fecha.setdefault(f, []).append(p)

        partidos_ui_grupos = []
        for fecha_grupo, partidos_lista in partidos_por_fecha.items():
            partidos_ui_grupos.append(
                ft.Text(f"📅 {fecha_grupo}", weight=ft.FontWeight.BOLD, color=COLOR_CELESTE, size=13)
            )
            for p in partidos_lista:
                es_activo = (p["id"] == estado["partido_activo_id"])
                es_fin = p.get("finalizado", False)

                def crear_handler_select(partido_obj):
                    return lambda e: seleccionar_partido(partido_obj)

                def crear_handler_delete(partido_id_val):
                    return lambda e: eliminar_partido(partido_id_val)

                badge_estado = ft.Container()
                if es_fin:
                    badge_estado = ft.Container(
                        content=ft.Text("FINALIZADO", size=9, weight=ft.FontWeight.BOLD, color=COLOR_TEXTO),
                        bgcolor=COLOR_ROJO, padding=ft.Padding(6, 2, 6, 2), border_radius=8,
                    )
                elif es_activo:
                    badge_estado = ft.Container(
                        content=ft.Text("EN JUEGO", size=9, weight=ft.FontWeight.BOLD, color=COLOR_TEXTO),
                        bgcolor=COLOR_CELESTE_BOTON, padding=ft.Padding(6, 2, 6, 2), border_radius=8,
                    )

                tarjeta = ft.Container(
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Text(f"vs {p['equipo_rival']}", weight=ft.FontWeight.BOLD, size=15, color=COLOR_TEXTO),
                                    badge_estado,
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            ft.Row(
                                [
                                    ft.Text("Marcador final:", size=12, color=COLOR_SUBTEXTO),
                                    ft.Text(f"{p['goles_local']} - {p['goles_rival']}", color=COLOR_VERDE, weight=ft.FontWeight.BOLD, size=16),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            ft.Text(
                                f"{p['tiempos_por_partido']} Tiempos | {p['minutos_por_tiempo']} min/tiempo | Max {p['jugadores_en_cancha']} en cancha",
                                size=11, color=COLOR_SUBTEXTO,
                            ),
                            ft.Row(
                                [
                                    ft.ElevatedButton(
                                        "Seleccionar" if not es_activo else "Activo",
                                        icon=ft.Icons.CHECK_CIRCLE if es_activo else ft.Icons.PLAY_ARROW,
                                        disabled=es_activo,
                                        bgcolor=COLOR_CELESTE_BOTON if not es_activo else COLOR_BORDE,
                                        color=COLOR_TEXTO,
                                        on_click=crear_handler_select(p),
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.DELETE_OUTLINED,
                                        icon_color=COLOR_ROJO,
                                        on_click=crear_handler_delete(p["id"]),
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                        ],
                        spacing=6,
                    ),
                    padding=12,
                    bgcolor=COLOR_TARJETA,
                    border_radius=12,
                    border=ft.border.all(1.5, COLOR_CELESTE if es_activo else COLOR_BORDE),
                )
                partidos_ui_grupos.append(tarjeta)

        return ft.Column(
            [
                ft.Text("⚙️ Configuración", size=20, weight=ft.FontWeight.BOLD, color=COLOR_TEXTO),
                ft.Container(
                    content=ft.Column([
                        ft.Text("1. Nuevo Partido", weight=ft.FontWeight.BOLD, color=COLOR_CELESTE),
                        ft.Row([tf_fecha, tf_rival]),
                        ft.Row([tf_tiempos, tf_minutos_tiempo, tf_jugadores_cancha]),
                        ft.Row([
                            ft.ElevatedButton("Guardar en BD", icon=ft.Icons.SAVE, bgcolor=COLOR_CELESTE_BOTON, color=COLOR_TEXTO, on_click=crear_partido_click),
                            ft.OutlinedButton(
                                "Resetear BD",
                                icon=ft.Icons.DELETE_FOREVER,
                                icon_color=COLOR_ROJO,
                                style=ft.ButtonStyle(color=COLOR_ROJO, side=ft.BorderSide(1, COLOR_ROJO)),
                                on_click=confirmar_reset,
                            ),
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        texto_feedback,
                    ], spacing=8),
                    padding=14, bgcolor=COLOR_TARJETA, border_radius=14, border=ft.border.all(1, COLOR_BORDE)
                ),
                ft.Divider(height=10, color=COLOR_BORDE),
                ft.Text("2. Historial de Partidos", weight=ft.FontWeight.BOLD, color=COLOR_CELESTE),
                ft.Column(controls=partidos_ui_grupos, spacing=10, scroll=ft.ScrollMode.AUTO),
            ],
            spacing=10, scroll=ft.ScrollMode.AUTO, expand=True,
        )

    # --- PANTALLA 2: PLANTEL ---
    def view_plantel():
        jugadores = obtener_jugadores_bd()
        max_titulares = estado["config"]["jugadores_en_cancha"]
        es_bloqueado = estado["finalizado"]

        tf_nuevo_num = ft.TextField(label="N°", width=60, border_color=COLOR_BORDE, focused_border_color=COLOR_CELESTE, border_radius=10, disabled=es_bloqueado)
        tf_nuevo_nom = ft.TextField(label="Nombre Jugador", expand=True, border_color=COLOR_BORDE, focused_border_color=COLOR_CELESTE, border_radius=10, disabled=es_bloqueado)
        tf_nuevo_puesto = ft.TextField(label="Puesto", width=110, border_color=COLOR_BORDE, focused_border_color=COLOR_CELESTE, border_radius=10, disabled=es_bloqueado)
        texto_status_jugador = ft.Text("", size=11)

        def click_agregar_jugador(e):
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
                    ft.ElevatedButton("Eliminar", bgcolor=COLOR_ROJO, color=COLOR_TEXTO, on_click=procesar_borrado),
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

            fila = ft.Container(
                content=ft.Row(
                    [
                        ft.Container(
                            content=ft.Text(f"#{num}", weight=ft.FontWeight.BOLD, size=11, color=COLOR_CELESTE),
                            bgcolor=COLOR_BORDE, padding=6, border_radius=8,
                        ),
                        ft.Column(
                            [
                                ft.Text(nombre, weight=ft.FontWeight.BOLD, size=13, color=COLOR_TEXTO),
                                ft.Text(f"{puesto} | {mins_hoy} min hoy", size=11, color=COLOR_SUBTEXTO),
                            ],
                            expand=True, spacing=1,
                        ),
                        switch_titular,
                        ft.IconButton(
                            icon=ft.Icons.DELETE_OUTLINED,
                            icon_color=COLOR_ROJO,
                            icon_size=18,
                            tooltip="Borrar jugador",
                            on_click=crear_handler_borrar(nombre),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                padding=4,
            )

            if es_titular:
                titulares_ui.append(fila)
            else:
                suplentes_ui.append(fila)

        alerta_bloqueo = (
            ft.Container(
                content=ft.Text("🔒 PARTIDO FINALIZADO - Para modificar la alineación debes reabrir el partido.", color=COLOR_AMBAR, size=11, weight=ft.FontWeight.BOLD),
                padding=8, bgcolor=COLOR_TARJETA, border_radius=8, border=ft.border.all(1, COLOR_AMBAR)
            ) if es_bloqueado else ft.Container()
        )

        return ft.Column(
            [
                ft.Text("📋 Plantel de Jugadores", size=20, weight=ft.FontWeight.BOLD, color=COLOR_TEXTO),
                alerta_bloqueo,
                ft.Container(
                    content=ft.Row([
                        ft.Text("Titulares en cancha:", color=COLOR_TEXTO, weight=ft.FontWeight.W_500),
                        ft.Container(
                            content=ft.Text(f"{len(estado['titulares_seleccionados'])} / {max_titulares}", color=COLOR_TEXTO, weight=ft.FontWeight.BOLD),
                            bgcolor=COLOR_CELESTE_BOTON, padding=ft.Padding(10, 4, 10, 4), border_radius=12
                        )
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    padding=12, bgcolor=COLOR_TARJETA, border_radius=12, border=ft.border.all(1, COLOR_BORDE)
                ),
                ft.Container(
                    content=ft.Column([
                        ft.Text("Nuevo Jugador", size=12, weight=ft.FontWeight.BOLD, color=COLOR_CELESTE),
                        ft.Row([tf_nuevo_num, tf_nuevo_nom, tf_nuevo_puesto]),
                        ft.Row([
                            ft.ElevatedButton("Agregar", icon=ft.Icons.PERSON_ADD, bgcolor=COLOR_CELESTE_BOTON, color=COLOR_TEXTO, disabled=es_bloqueado, on_click=click_agregar_jugador),
                            texto_status_jugador
                        ]),
                    ], spacing=6),
                    padding=12, bgcolor=COLOR_TARJETA, border_radius=12, border=ft.border.all(1, COLOR_BORDE)
                ),
                ft.Text(f"🟢 TITULARES EN CANCHA ({len(titulares_ui)})", weight=ft.FontWeight.BOLD, color=COLOR_VERDE, size=12),
                ft.Container(content=ft.Column(controls=titulares_ui or [ft.Text("Sin titulares", color=COLOR_SUBTEXTO)]), bgcolor=COLOR_TARJETA, padding=8, border_radius=12, border=ft.border.all(1, COLOR_VERDE)),
                ft.Text(f"🟡 BANCA / SUPLENTES ({len(suplentes_ui)})", weight=ft.FontWeight.BOLD, color=COLOR_AMBAR, size=12),
                ft.Container(content=ft.Column(controls=suplentes_ui or [ft.Text("Sin suplentes", color=COLOR_SUBTEXTO)]), bgcolor=COLOR_TARJETA, padding=8, border_radius=12, border=ft.border.all(1, COLOR_BORDE)),
            ],
            scroll=ft.ScrollMode.AUTO, expand=True, spacing=8
        )

    # --- PANTALLA 3: PARTIDO EN VIVO ---
    def view_partido():
        texto_reloj.value = formatear_tiempo(estado["segundos"])
        jugadores = obtener_jugadores_bd()

        nombre_rival = estado["config"]["equipo_rival"]
        fecha_partido = estado["config"].get("fecha", datetime.now().strftime("%Y-%m-%d"))
        es_fin = estado["finalizado"]

        if es_fin:
            texto_alerta_cambio.value = "🔒 PARTIDO FINALIZADO (Solo Lectura)"
            texto_alerta_cambio.color = COLOR_ROJO

        marcador_ui = ft.Container(
            content=ft.Column(
                [
                    ft.Text(f"📅 {fecha_partido}", size=11, color=COLOR_SUBTEXTO),
                    ft.Row(
                        [
                            ft.Column(
                                [
                                    ft.Text("Dunalastair", weight=ft.FontWeight.BOLD, size=15, color=COLOR_TEXTO),
                                    ft.Text(f"{estado['goles_local']}", size=42, weight=ft.FontWeight.BOLD, color=COLOR_CELESTE),
                                ],
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER, expand=True,
                            ),
                            ft.Text("VS", size=18, weight=ft.FontWeight.BOLD, color=COLOR_SUBTEXTO),
                            ft.Column(
                                [
                                    ft.Text(nombre_rival, weight=ft.FontWeight.BOLD, size=15, color=COLOR_TEXTO, overflow=ft.TextOverflow.ELLIPSIS),
                                    ft.Text(f"{estado['goles_rival']}", size=42, weight=ft.FontWeight.BOLD, color=COLOR_ROJO),
                                ],
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER, expand=True,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=COLOR_TARJETA, padding=14, border_radius=14, border=ft.border.all(1, COLOR_BORDE),
        )

        def iniciar_reloj(e):
            if estado["finalizado"]:
                return
            estado["corriendo"] = True
            texto_alerta_cambio.value = "⏱️ Partido en marcha"
            texto_alerta_cambio.color = COLOR_VERDE
            page.update()

        def pausar_reloj(e):
            if estado["finalizado"]:
                return
            estado["corriendo"] = False
            texto_alerta_cambio.value = "⏸️ Partido pausado"
            texto_alerta_cambio.color = COLOR_AMBAR
            guardar_estado_partido_activo()
            page.update()

        def detener_reloj(e):
            if estado["finalizado"]:
                return
            estado["corriendo"] = False
            estado["segundos"] = 0
            texto_reloj.value = "00:00"
            texto_alerta_cambio.value = "⏹️ Cronómetro reiniciado"
            texto_alerta_cambio.color = COLOR_SUBTEXTO
            guardar_estado_partido_activo()
            page.update()

        def alternar_finalizacion(e):
            estado["corriendo"] = False
            estado["finalizado"] = not estado["finalizado"]
            if estado["finalizado"]:
                texto_alerta_cambio.value = "🔒 PARTIDO FINALIZADO"
                texto_alerta_cambio.color = COLOR_ROJO
            else:
                texto_alerta_cambio.value = "🔓 Partido Reabierto para Edición"
                texto_alerta_cambio.color = COLOR_VERDE

            guardar_estado_partido_activo()
            contenedor_partido.content = view_partido()
            page.update()

        dd_evento = ft.Dropdown(label="Evento", options=[ft.dropdown.Option(ev) for ev in EVENTOS_DEFECTO], expand=True, border_color=COLOR_BORDE, focused_border_color=COLOR_CELESTE, border_radius=10, disabled=es_fin)
        opciones_titulares = [ft.dropdown.Option(nom) for nom in estado["titulares_seleccionados"]]
        dd_jugador_titular = ft.Dropdown(label="Jugador Titular", options=opciones_titulares, expand=True, border_color=COLOR_BORDE, focused_border_color=COLOR_CELESTE, border_radius=10, disabled=es_fin)

        suplentes_actuales = [j["nombre"] for j in jugadores if j["nombre"] not in estado["titulares_seleccionados"]]
        dd_suplente_entra = ft.Dropdown(label="Entra (Suplente)", options=[ft.dropdown.Option(nom) for nom in suplentes_actuales], expand=True, visible=False, border_color=COLOR_BORDE, focused_border_color=COLOR_CELESTE, border_radius=10, disabled=es_fin)

        texto_status_evento = ft.Text("", color=COLOR_VERDE, size=12)

        def al_cambiar_dropdown_evento(e):
            if dd_evento.value == "Gol":
                dd_jugador_titular.label = "Autor del Gol"
                dd_jugador_titular.options = [ft.dropdown.Option("⚡ Equipo Rival")] + opciones_titulares
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
            if estado["finalizado"]:
                return

            tipo_evento = dd_evento.value
            jugador_sel = dd_jugador_titular.value

            if not tipo_evento or not jugador_sel:
                texto_status_evento.value = "⚠️ Selecciona evento y jugador."
                texto_status_evento.color = COLOR_ROJO
                page.update()
                return

            minuto_actual = f"{estado['segundos'] // 60:02d}'"

            if tipo_evento == "Gol":
                if jugador_sel == "⚡ Equipo Rival":
                    estado["goles_rival"] += 1
                    desc_evento = f"Gol de {estado['config']['equipo_rival']}"
                else:
                    estado["goles_local"] += 1
                    desc_evento = f"Gol de {jugador_sel}"

                estado["eventos_registrados"].append({"minuto": minuto_actual, "evento": "Gol", "jugador": desc_evento})

            elif tipo_evento == "Cambio":
                jugador_entra = dd_suplente_entra.value
                if not jugador_entra:
                    texto_status_evento.value = "⚠️ Selecciona suplente que entra."
                    texto_status_evento.color = COLOR_ROJO
                    page.update()
                    return

                if jugador_sel in estado["titulares_seleccionados"]:
                    estado["titulares_seleccionados"].remove(jugador_sel)
                if jugador_entra not in estado["titulares_seleccionados"]:
                    estado["titulares_seleccionados"].append(jugador_entra)

                desc_evento = f"Sale {jugador_sel} ➔ Entra {jugador_entra}"
                estado["eventos_registrados"].append({"minuto": minuto_actual, "evento": "Cambio", "jugador": desc_evento})

            else:
                estado["eventos_registrados"].append({"minuto": minuto_actual, "evento": tipo_evento, "jugador": jugador_sel})

            guardar_estado_partido_activo()
            contenedor_partido.content = view_partido()
            page.update()

        def obtener_estilo_evento(tipo):
            if "Gol" in tipo:
                return ft.Icons.SPORTS_SOCCER, COLOR_VERDE
            elif "Tarjeta Amarilla" in tipo:
                return ft.Icons.STYLE, COLOR_AMBAR
            elif "Tarjeta Roja" in tipo:
                return ft.Icons.STYLE, COLOR_ROJO
            elif "Cambio" in tipo:
                return ft.Icons.SWAP_HORIZ, COLOR_CELESTE
            elif "Asistencia" in tipo:
                return ft.Icons.HANDSHAKE, COLOR_CELESTE
            return ft.Icons.INFO_OUTLINE, COLOR_SUBTEXTO

        def eliminar_evento(idx_real):
            if estado["finalizado"]:
                return
            ev_eliminado = estado["eventos_registrados"].pop(idx_real)
            if ev_eliminado.get("evento") == "Gol":
                if "Gol de " + estado['config']['equipo_rival'] in ev_eliminado.get("jugador", ""):
                    estado["goles_rival"] = max(0, estado["goles_rival"] - 1)
                else:
                    estado["goles_local"] = max(0, estado["goles_local"] - 1)

            guardar_estado_partido_activo()
            contenedor_partido.content = view_partido()
            page.update()

        lista_eventos_ui = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO)
        total_eventos = len(estado["eventos_registrados"])

        if total_eventos == 0:
            lista_eventos_ui.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(ft.Icons.HISTORY_TOGGLE_OFF, color=COLOR_SUBTEXTO, size=28),
                            ft.Text("Aún no hay eventos en este partido", color=COLOR_SUBTEXTO, size=12),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=4,
                    ),
                    padding=15,
                    alignment=ft.Alignment(0, 0),
                )
            )
        else:
            for idx_inverso, ev in enumerate(reversed(estado["eventos_registrados"])):
                idx_real = total_eventos - 1 - idx_inverso
                icono, color_evento = obtener_estilo_evento(ev["evento"])

                def crear_handler_eliminar(i):
                    return lambda e: eliminar_evento(i)

                tarjeta_ev = ft.Container(
                    content=ft.Row(
                        [
                            ft.Container(
                                content=ft.Text(f"{ev['minuto']}", size=11, weight=ft.FontWeight.BOLD, color=COLOR_TEXTO),
                                bgcolor=COLOR_CELESTE_BOTON,
                                padding=ft.Padding(6, 3, 6, 3),
                                border_radius=8,
                            ),
                            ft.Row(
                                [
                                    ft.Icon(icono, color=color_evento, size=18),
                                    ft.Column(
                                        [
                                            ft.Text(ev["jugador"], size=12, weight=ft.FontWeight.BOLD, color=COLOR_TEXTO, overflow=ft.TextOverflow.ELLIPSIS),
                                            ft.Text(ev["evento"], size=10, color=color_evento, weight=ft.FontWeight.W_500),
                                        ],
                                        spacing=1,
                                        expand=True,
                                    ),
                                ],
                                expand=True,
                                spacing=8,
                            ),
                            ft.IconButton(
                                icon=ft.Icons.CLOSE,
                                icon_size=14,
                                icon_color=COLOR_SUBTEXTO,
                                disabled=es_fin,
                                tooltip="Eliminar evento",
                                on_click=crear_handler_eliminar(idx_real),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    bgcolor=COLOR_FONDO,
                    padding=ft.Padding(8, 4, 4, 4),
                    border_radius=10,
                    border=ft.border.all(1, COLOR_BORDE),
                )
                lista_eventos_ui.controls.append(tarjeta_ev)

        return ft.Column(
            [
                ft.Row(
                    [
                        ft.Text("⏱️ Cronómetro y Registro", size=18, weight=ft.FontWeight.BOLD, color=COLOR_TEXTO),
                        ft.OutlinedButton(
                            "Reabrir Partido" if es_fin else "Finalizar Partido",
                            icon=ft.Icons.LOCK_OPEN if es_fin else ft.Icons.LOCK,
                            style=ft.ButtonStyle(
                                color=COLOR_VERDE if es_fin else COLOR_ROJO,
                                side=ft.BorderSide(1, COLOR_VERDE if es_fin else COLOR_ROJO)
                            ),
                            on_click=alternar_finalizacion,
                        )
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                marcador_ui,
                ft.Container(content=texto_reloj, alignment=ft.Alignment(0, 0)),
                ft.Container(content=texto_alerta_cambio, alignment=ft.Alignment(0, 0)),
                ft.Row(
                    [
                        ft.IconButton(icon=ft.Icons.PLAY_ARROW_ROUNDED, icon_size=36, icon_color=COLOR_VERDE if not es_fin else COLOR_SUBTEXTO, bgcolor=COLOR_BORDE, disabled=es_fin, on_click=iniciar_reloj),
                        ft.IconButton(icon=ft.Icons.PAUSE_ROUNDED, icon_size=36, icon_color=COLOR_AMBAR if not es_fin else COLOR_SUBTEXTO, bgcolor=COLOR_BORDE, disabled=es_fin, on_click=pausar_reloj),
                        ft.IconButton(icon=ft.Icons.STOP_ROUNDED, icon_size=36, icon_color=COLOR_ROJO if not es_fin else COLOR_SUBTEXTO, bgcolor=COLOR_BORDE, disabled=es_fin, on_click=detener_reloj),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                ft.Divider(height=5, color=COLOR_BORDE),
                ft.Text("📝 Nuevo Evento", weight=ft.FontWeight.BOLD, color=COLOR_CELESTE),
                ft.Row([dd_evento, dd_jugador_titular]),
                dd_suplente_entra,
                ft.ElevatedButton("Registrar Evento", icon=ft.Icons.ADD_TASK, bgcolor=COLOR_CELESTE_BOTON, color=COLOR_TEXTO, disabled=es_fin, on_click=registrar_evento_click),
                texto_status_evento,
                ft.Row(
                    [
                        ft.Text("Historial de Eventos", size=13, weight=ft.FontWeight.BOLD, color=COLOR_TEXTO),
                        ft.Text(f"{total_eventos} registrados", size=11, color=COLOR_SUBTEXTO),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Container(
                    content=lista_eventos_ui,
                    bgcolor=COLOR_TARJETA,
                    padding=8,
                    border_radius=12,
                    border=ft.border.all(1, COLOR_BORDE),
                    height=180,
                ),
            ],
            scroll=ft.ScrollMode.AUTO, horizontal_alignment=ft.CrossAxisAlignment.CENTER, expand=True, spacing=6,
        )

    # --- PANTALLA 4: RANKING ACUMULADO ---
    def view_minutos():
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
                    datos_jugadores.append(
                        {
                            "Número": j["numero"],
                            "Jugador": nom,
                            "Puesto": j["puesto"],
                            "Minutos Acumulados Totales": segs // 60,
                        }
                    )
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
                            content=ft.Text(f"#{num}", weight=ft.FontWeight.BOLD, size=11, color=COLOR_TEXTO),
                            bgcolor=COLOR_CELESTE_BOTON, padding=6, border_radius=8,
                        ),
                        ft.Column(
                            [
                                ft.Text(nombre, weight=ft.FontWeight.BOLD, size=13, color=COLOR_TEXTO),
                                ft.Text(f"Puesto: {puesto}", size=11, color=COLOR_SUBTEXTO),
                            ],
                            expand=True, spacing=1,
                        ),
                        ft.Text(f"{mins_totales} min", color=COLOR_CELESTE, weight=ft.FontWeight.BOLD, size=15),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                padding=10, bgcolor=COLOR_TARJETA, border_radius=10, border=ft.border.all(1, COLOR_BORDE)
            )
            stats_ui.append(tarjeta)

        return ft.Column(
            [
                ft.Text("📊 Ranking Acumulado (Menor a Mayor)", size=20, weight=ft.FontWeight.BOLD, color=COLOR_TEXTO),
                ft.ElevatedButton("Exportar a Excel", icon=ft.Icons.EXPLICIT, bgcolor=COLOR_CELESTE_BOTON, color=COLOR_TEXTO, on_click=click_exportar),
                texto_export,
                ft.Divider(height=10, color=COLOR_BORDE),
                ft.Column(controls=stats_ui, scroll=ft.ScrollMode.AUTO, expand=True, spacing=8),
            ],
            expand=True,
        )

    # --- PANTALLA 5: RESUMEN / TABLA DE POSICIONES DUNALASTAIR ---
    def view_resumen():
        cargar_partidos_bd()

        # Por defecto muestra TODO el historial, si se ingresa fecha filtra la jornada.
        fecha_filtro = ""
        tf_fecha_filtro = ft.TextField(
            label="Filtrar por fecha (Vacío = Todos los partidos)",
            value=fecha_filtro,
            expand=True,
            border_color=COLOR_BORDE,
            focused_border_color=COLOR_CELESTE,
            border_radius=10,
        )

        def al_cambiar_fecha(e):
            contenedor_resumen.content = view_resumen_contenido(tf_fecha_filtro.value.strip())
            page.update()

        tf_fecha_filtro.on_submit = al_cambiar_fecha

        btn_buscar = ft.IconButton(
            icon=ft.Icons.SEARCH,
            icon_color=COLOR_CELESTE,
            bgcolor=COLOR_TARJETA,
            on_click=al_cambiar_fecha,
        )

        return ft.Column(
            [
                ft.Text("🏆 Tabla de Posiciones de Equipo", size=20, weight=ft.FontWeight.BOLD, color=COLOR_TEXTO),
                ft.Row([tf_fecha_filtro, btn_buscar]),
                ft.Divider(height=5, color=COLOR_BORDE),
                view_resumen_contenido(fecha_filtro),
            ],
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )

    def view_resumen_contenido(fecha=""):
        if fecha:
            partidos_mostrar = [p for p in estado["partidos"] if p["fecha"] == fecha]
            titulo = f"📊 Tabla de Posiciones ({fecha})"
        else:
            partidos_mostrar = estado["partidos"]
            titulo = "📊 Tabla de Posiciones (Histórico Total)"

        if not partidos_mostrar:
            return ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(ft.Icons.EVENT_BUSY, size=40, color=COLOR_SUBTEXTO),
                        ft.Text("No hay partidos registrados", color=COLOR_SUBTEXTO, size=14),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=6,
                ),
                padding=20, alignment=ft.Alignment(0, 0)
            )

        total_partidos = len(partidos_mostrar)
        victorias = sum(1 for p in partidos_mostrar if p["goles_local"] > p["goles_rival"])
        empates = sum(1 for p in partidos_mostrar if p["goles_local"] == p["goles_rival"])
        derrotas = sum(1 for p in partidos_mostrar if p["goles_local"] < p["goles_rival"])
        goles_favor = sum(p["goles_local"] for p in partidos_mostrar)
        goles_contra = sum(p["goles_rival"] for p in partidos_mostrar)
        diferencia = goles_favor - goles_contra
        puntos = (victorias * 3) + (empates * 1)

        goleadores = {}
        for p in partidos_mostrar:
            for ev in p["eventos"]:
                if ev.get("evento") == "Gol":
                    txt = ev.get("jugador", "")
                    if "Gol de " in txt and "Rival" not in txt:
                        jug = txt.replace("Gol de ", "").strip()
                        goleadores[jug] = goleadores.get(jug, 0) + 1

        top_goleador_str = "Ninguno"
        if goleadores:
            max_goles = max(goleadores.values())
            mejores = [k for k, v in goleadores.items() if v == max_goles]
            top_goleador_str = f"{', '.join(mejores)} ({max_goles} goles)"

        tabla_posiciones = ft.DataTable(
            columns=[
                ft.DataColumn(label=ft.Text("Pos", weight=ft.FontWeight.BOLD, color=COLOR_SUBTEXTO)),
                ft.DataColumn(label=ft.Text("Equipo", weight=ft.FontWeight.BOLD, color=COLOR_CELESTE)),
                ft.DataColumn(label=ft.Text("PJ", weight=ft.FontWeight.BOLD, color=COLOR_SUBTEXTO)),
                ft.DataColumn(label=ft.Text("PG", weight=ft.FontWeight.BOLD, color=COLOR_VERDE)),
                ft.DataColumn(label=ft.Text("PE", weight=ft.FontWeight.BOLD, color=COLOR_AMBAR)),
                ft.DataColumn(label=ft.Text("PP", weight=ft.FontWeight.BOLD, color=COLOR_ROJO)),
                ft.DataColumn(label=ft.Text("GF", weight=ft.FontWeight.BOLD, color=COLOR_SUBTEXTO)),
                ft.DataColumn(label=ft.Text("GE", weight=ft.FontWeight.BOLD, color=COLOR_SUBTEXTO)),
                ft.DataColumn(label=ft.Text("DG", weight=ft.FontWeight.BOLD, color=COLOR_SUBTEXTO)),
                ft.DataColumn(label=ft.Text("Pts", weight=ft.FontWeight.BOLD, color=COLOR_CELESTE)),
            ],
            rows=[
                ft.DataRow(
                    cells=[
                        ft.DataCell(content=ft.Text("1", color=COLOR_TEXTO)),
                        ft.DataCell(content=ft.Text("Dunalastairs", weight=ft.FontWeight.BOLD, color=COLOR_TEXTO)),
                        ft.DataCell(content=ft.Text(str(total_partidos), color=COLOR_TEXTO)),
                        ft.DataCell(content=ft.Text(str(victorias), color=COLOR_TEXTO)),
                        ft.DataCell(content=ft.Text(str(empates), color=COLOR_TEXTO)),
                        ft.DataCell(content=ft.Text(str(derrotas), color=COLOR_TEXTO)),
                        ft.DataCell(content=ft.Text(str(goles_favor), color=COLOR_TEXTO)),
                        ft.DataCell(content=ft.Text(str(goles_contra), color=COLOR_TEXTO)),
                        ft.DataCell(content=ft.Text(f"{diferencia:+d}", color=COLOR_TEXTO)),
                        ft.DataCell(content=ft.Text(str(puntos), weight=ft.FontWeight.BOLD, color=COLOR_VERDE)),
                    ]
                )
            ],
            bgcolor=COLOR_FONDO,
            border=ft.border.all(1, COLOR_BORDE),
            border_radius=8,
            column_spacing=18,
            heading_row_height=40,
            data_row_min_height=40,
            data_row_max_height=40,
        )

        tarjeta_resumen_global = ft.Container(
            content=ft.Column(
                [
                    ft.Text(titulo, weight=ft.FontWeight.BOLD, color=COLOR_CELESTE, size=14),
                    # Scroll Horizontal por si la pantalla del móvil es pequeña
                    ft.Row([tabla_posiciones], scroll=ft.ScrollMode.ALWAYS),
                    ft.Text(f"⚽ Goleador(es): {top_goleador_str}", size=13, color=COLOR_AMBAR, weight=ft.FontWeight.BOLD),
                ],
                spacing=12,
            ),
            padding=14, bgcolor=COLOR_TARJETA, border_radius=14, border=ft.border.all(1, COLOR_CELESTE)
        )

        tarjetas_partidos = []
        for i, p in enumerate(partidos_mostrar, 1):
            eventos_goles = [ev for ev in p["eventos"] if ev.get("evento") == "Gol"]
            eventos_tarjetas = [ev for ev in p["eventos"] if "Tarjeta" in ev.get("evento", "")]

            resumen_evs = []
            if eventos_goles:
                resumen_evs.append(ft.Text("⚽ Goles: " + ", ".join([f"{g['jugador']} ({g['minuto']})" for g in eventos_goles]), size=11, color=COLOR_SUBTEXTO))
            if eventos_tarjetas:
                resumen_evs.append(ft.Text("🟨/🟥 Tarjetas: " + ", ".join([f"{t['jugador']} ({t['evento']})" for t in eventos_tarjetas]), size=11, color=COLOR_SUBTEXTO))

            if not resumen_evs:
                resumen_evs.append(ft.Text("Sin incidentes ni goles registrados.", size=11, color=COLOR_SUBTEXTO))

            card = ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Text(f"{p['fecha']} | vs {p['equipo_rival']}", weight=ft.FontWeight.BOLD, size=14, color=COLOR_TEXTO),
                                ft.Text(f"{p['goles_local']} - {p['goles_rival']}", weight=ft.FontWeight.BOLD, size=18, color=COLOR_CELESTE),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        ft.Text(f"Duración: {p['segundos'] // 60} min jugados | Titulares: {len(p['titulares'])}", size=11, color=COLOR_SUBTEXTO),
                        ft.Column(controls=resumen_evs, spacing=2),
                    ],
                    spacing=4,
                ),
                padding=12, bgcolor=COLOR_TARJETA, border_radius=12, border=ft.border.all(1, COLOR_BORDE)
            )
            tarjetas_partidos.append(card)

        return ft.Column([tarjeta_resumen_global] + tarjetas_partidos, spacing=10)

    # --- CONTENEDORES PRINCIPALES ---
    contenedor_config = ft.Container(content=view_configuracion(), expand=True, padding=12, visible=True)
    contenedor_plantel = ft.Container(content=view_plantel(), expand=True, padding=12, visible=False)
    contenedor_partido = ft.Container(content=view_partido(), expand=True, padding=12, visible=False)
    contenedor_minutos = ft.Container(content=view_minutos(), expand=True, padding=12, visible=False)
    contenedor_resumen = ft.Container(content=view_resumen(), expand=True, padding=12, visible=False)

    def cambiar_pantalla(e):
        indice = e.control.selected_index
        contenedor_config.visible = (indice == 0)
        contenedor_plantel.visible = (indice == 1)
        contenedor_partido.visible = (indice == 2)
        contenedor_minutos.visible = (indice == 3)
        contenedor_resumen.visible = (indice == 4)

        if indice == 0:
            contenedor_config.content = view_configuracion()
        elif indice == 1:
            contenedor_plantel.content = view_plantel()
        elif indice == 2:
            contenedor_partido.content = view_partido()
        elif indice == 3:
            contenedor_minutos.content = view_minutos()
        elif indice == 4:
            contenedor_resumen.content = view_resumen()
        page.update()

    page.navigation_bar = ft.NavigationBar(
        selected_index=0,
        bgcolor=COLOR_TARJETA,
        indicator_color=COLOR_CELESTE_BOTON,
        on_change=cambiar_pantalla,
        destinations=[
            ft.NavigationBarDestination(icon=ft.Icons.SETTINGS, label="Config"),
            ft.NavigationBarDestination(icon=ft.Icons.PEOPLE, label="Plantel"),
            ft.NavigationBarDestination(icon=ft.Icons.SPORTS_SOCCER, label="Partido"),
            ft.NavigationBarDestination(icon=ft.Icons.BAR_CHART, label="Ranking"),
            ft.NavigationBarDestination(icon=ft.Icons.SUMMARIZE, label="Resumen"),
        ]
    )

    header_app = ft.Container(
        content=ft.Row(
            [
                ft.Row([
                    ft.Icon(ft.Icons.SPORTS_SOCCER, color=COLOR_CELESTE, size=22),
                    ft.Text("DUNALASTAIR FC", weight=ft.FontWeight.BOLD, size=15, color=COLOR_TEXTO),
                ], spacing=6),
                ft.Container(
                    # Actualizado para indicar que ahora usas Turso
                    content=ft.Text("Turso BD", size=10, weight=ft.FontWeight.BOLD, color=COLOR_CELESTE),
                    bgcolor=COLOR_BORDE, padding=ft.Padding(8, 3, 8, 3), border_radius=8
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
                    controls=[contenedor_config, contenedor_plantel, contenedor_partido, contenedor_minutos, contenedor_resumen],
                    expand=True,
                ),
            ],
            expand=True,
            spacing=0,
        ),
    )

    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.add(app_layout)


if __name__ == "__main__":
    puerto = int(os.environ.get("PORT", 8080))
    ft.app(target=main, host="0.0.0.0", port=puerto, view=ft.AppView.WEB_BROWSER)