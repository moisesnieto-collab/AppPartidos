import asyncio
from datetime import datetime
import json
import os
import sqlite3
import flet as ft
import pandas as pd

# --- CONFIGURACIÓN DE BASE DE DATOS SQLITE ---
DB_PATH = "partidos_dunalastair.db"

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
    {"numero": 10, "nombre": "Joaquin Caceres", "puesto": "Medio"},
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
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Tabla de Jugadores (Plantel)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jugadores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT NOT NULL,
            nombre TEXT NOT NULL UNIQUE,
            puesto TEXT NOT NULL
        )
    """)

    # Tabla de Partidos
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
            minutos_partido TEXT DEFAULT '{}'
        )
    """)

    # Si la tabla de jugadores está vacía, insertamos la plantilla inicial
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

    page.title = "Dunalastair - Control de Cambios BD Total"
    page.window_width = 400
    page.window_height = 800
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0

    # --- ESTADO DE LA APLICACIÓN ---
    estado = {
        "segundos": 0,
        "corriendo": False,
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

    # --- CONSULTAS Y OPERACIONES EN BASE DE DATOS ---

    def obtener_jugadores_bd():
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT numero, nombre, puesto FROM jugadores ORDER BY id ASC")
        filas = cursor.fetchall()
        conn.close()
        return [{"numero": r[0], "nombre": r[1], "puesto": r[2]} for r in filas]

    def agregar_jugador_bd(num, nom, puesto):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO jugadores (numero, nombre, puesto) VALUES (?, ?, ?)",
                (str(num), nom, puesto),
            )
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            return False

    def cargar_partidos_bd():
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, fecha, equipo_rival, tiempos_por_partido, minutos_por_tiempo, jugadores_en_cancha, goles_local, goles_rival, segundos, titulares, eventos, minutos_partido FROM partidos ORDER BY fecha DESC, id DESC"
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
        conn = sqlite3.connect(DB_PATH)
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

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE partidos
            SET goles_local=?, goles_rival=?, segundos=?, titulares=?, eventos=?, minutos_partido=?
            WHERE id=?
        """,
            (
                estado["goles_local"],
                estado["goles_rival"],
                estado["segundos"],
                json.dumps(estado["titulares_seleccionados"], ensure_ascii=False),
                json.dumps(estado["eventos_registrados"], ensure_ascii=False),
                json.dumps(estado["minutos_partido_actual"], ensure_ascii=False),
                estado["partido_activo_id"],
            ),
        )
        conn.commit()
        conn.close()

    def eliminar_partido_bd(partido_id):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM partidos WHERE id=?", (partido_id,))
        conn.commit()
        conn.close()

    def reiniciar_base_datos():
        conn = sqlite3.connect(DB_PATH)
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
        """Calcula el acumulado global de segundos por jugador directamente leyendo la BD."""
        conn = sqlite3.connect(DB_PATH)
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
        estado["titulares_seleccionados"] = partido["titulares"]
        estado["eventos_registrados"] = partido["eventos"]
        estado["minutos_partido_actual"] = partido["minutos_partido"]
        estado["config"] = {
            "equipo_rival": partido["equipo_rival"],
            "tiempos_por_partido": partido["tiempos_por_partido"],
            "minutos_por_tiempo": partido["minutos_por_tiempo"],
            "jugadores_en_cancha": partido["jugadores_en_cancha"],
            "fecha": partido["fecha"],
        }

    # Cargar datos desde SQLite al arrancar
    cargar_partidos_bd()

    # --- COMPONENTES VISUALES Y BUCLE ---
    texto_reloj = ft.Text("00:00", size=55, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_200)
    texto_alerta_cambio = ft.Text("Partido listo", weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_400)

    def formatear_tiempo(segs):
        return f"{segs // 60:02d}:{segs % 60:02d}"

    async def loop_reloj():
        contador_guardado = 0
        while True:
            await asyncio.sleep(1)
            if estado["corriendo"]:
                estado["segundos"] += 1
                seg = estado["segundos"]
                texto_reloj.value = formatear_tiempo(seg)

                duracion_tiempo_segs = estado["config"]["minutos_por_tiempo"] * 60

                if seg > 0 and seg % duracion_tiempo_segs == 0:
                    estado["corriendo"] = False
                    tiempo_terminado = seg // duracion_tiempo_segs
                    texto_alerta_cambio.value = f"🏁 ¡FIN DEL TIEMPO {tiempo_terminado}!"
                    texto_alerta_cambio.color = ft.Colors.AMBER_400

                # Sumar tiempo solo a los titulares seleccionados en cancha
                for jugador in estado["titulares_seleccionados"]:
                    estado["minutos_partido_actual"][jugador] = (
                        estado["minutos_partido_actual"].get(jugador, 0) + 1
                    )

                contador_guardado += 1
                if contador_guardado >= 5:  # Guardar en SQLite cada 5 segundos
                    guardar_estado_partido_activo()
                    contador_guardado = 0

                try:
                    page.update()
                except Exception:
                    pass

    page.run_task(loop_reloj)

    # --- PANTALLA 1: CONFIGURACIÓN Y HISTORIAL BD ---
    def view_configuracion():
        tf_fecha = ft.TextField(
            label="Fecha (AAAA-MM-DD)",
            value=datetime.now().strftime("%Y-%m-%d"),
            width=150,
        )
        tf_rival = ft.TextField(label="Equipo Rival", value="Rival FC", expand=True)
        tf_tiempos = ft.TextField(label="Tiempos", value="2", keyboard_type=ft.KeyboardType.NUMBER, width=90)
        tf_minutos_tiempo = ft.TextField(label="Min/Tiempo", value="10", keyboard_type=ft.KeyboardType.NUMBER, width=100)
        tf_jugadores_cancha = ft.TextField(label="Cancha", value="7", keyboard_type=ft.KeyboardType.NUMBER, width=90)

        texto_feedback = ft.Text("", color=ft.Colors.GREEN_400, size=12)

        def crear_partido_click(e):
            try:
                rival = tf_rival.value.strip()
                fecha_val = tf_fecha.value.strip()

                if not rival or not fecha_val:
                    texto_feedback.value = "⚠️ Ingresa fecha y nombre del rival."
                    texto_feedback.color = ft.Colors.RED_400
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

                texto_feedback.value = f"✅ Partido vs '{rival}' registrado en BD ({fecha_val})."
                texto_feedback.color = ft.Colors.GREEN_400
                contenedor_config.content = view_configuracion()
                page.update()
            except ValueError:
                texto_feedback.value = "❌ Ingresa números válidos."
                texto_feedback.color = ft.Colors.RED_400
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
                texto_feedback.value = "🔄 Toda la BD fue restablecida."
                dialogo_reset.open = False
                contenedor_config.content = view_configuracion()
                page.update()

            dialogo_reset = ft.AlertDialog(
                title=ft.Text("¿Borrar Base de Datos?"),
                content=ft.Text("Se eliminarán todos los partidos y estadísticas registradas."),
                actions=[
                    ft.TextButton("Cancelar", on_click=cerrar_dlg),
                    ft.ElevatedButton("Borrar BD", bgcolor=ft.Colors.RED_700, color=ft.Colors.WHITE, on_click=procesar_reset),
                ],
            )
            page.overlay.append(dialogo_reset)
            dialogo_reset.open = True
            page.update()

        # Agrupar partidos por fecha
        partidos_por_fecha = {}
        for p in estado["partidos"]:
            f = p["fecha"]
            partidos_por_fecha.setdefault(f, []).append(p)

        partidos_ui_grupos = []
        for fecha_grupo, partidos_lista in partidos_por_fecha.items():
            partidos_ui_grupos.append(
                ft.Text(f"📅 {fecha_grupo}", weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER_400, size=13)
            )
            for p in partidos_lista:
                es_activo = p["id"] == estado["partido_activo_id"]

                def crear_handler_select(partido_obj):
                    return lambda e: seleccionar_partido(partido_obj)

                def crear_handler_delete(partido_id_val):
                    return lambda e: eliminar_partido(partido_id_val)

                tarjeta = ft.Container(
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Text(f"vs {p['equipo_rival']}", weight=ft.FontWeight.BOLD, size=15),
                                    ft.Text(f"Goles: {p['goles_local']} - {p['goles_rival']}", color=ft.Colors.GREEN_300, weight=ft.FontWeight.BOLD),
                                    ft.Container(
                                        content=ft.Text("ACTIVO", size=10, weight=ft.FontWeight.BOLD),
                                        bgcolor=ft.Colors.GREEN_700,
                                        padding=ft.Padding(5, 2, 5, 2),
                                        border_radius=5,
                                    ) if es_activo else ft.Container(),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            ft.Text(
                                f"{p['tiempos_por_partido']} Tiempos | {p['minutos_por_tiempo']} min/tiempo | Max {p['jugadores_en_cancha']} en cancha",
                                size=11, color=ft.Colors.GREY_400,
                            ),
                            ft.Row(
                                [
                                    ft.ElevatedButton(
                                        "Seleccionar" if not es_activo else "En Juego",
                                        icon=ft.Icons.CHECK_CIRCLE if es_activo else ft.Icons.PLAY_ARROW,
                                        disabled=es_activo,
                                        on_click=crear_handler_select(p),
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.DELETE,
                                        icon_color=ft.Colors.RED_400,
                                        on_click=crear_handler_delete(p["id"]),
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                        ],
                        spacing=4,
                    ),
                    padding=10,
                    bgcolor=ft.Colors.GREY_900,
                    border_radius=8,
                    border=ft.border.all(1, ft.Colors.GREEN_400) if es_activo else None,
                )
                partidos_ui_grupos.append(tarjeta)

        return ft.Column(
            [
                ft.Row([
                    ft.Text("⚙️ Configuración", size=20, weight=ft.FontWeight.BOLD),
                    ft.Container(
                        content=ft.Text("BD SQLite Conectada", size=10, color=ft.Colors.WHITE),
                        bgcolor=ft.Colors.BLUE_800, padding=ft.Padding(6, 3, 6, 3), border_radius=8
                    )
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(height=5),
                ft.Text("1. Nuevo Partido", weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_200),
                ft.Row([tf_fecha, tf_rival]),
                ft.Row([tf_tiempos, tf_minutos_tiempo, tf_jugadores_cancha]),
                ft.Row([
                    ft.ElevatedButton("Guardar en BD", icon=ft.Icons.SAVE, on_click=crear_partido_click),
                    ft.OutlinedButton("Resetear BD", icon=ft.Icons.DELETE_FOREVER, icon_color=ft.Colors.RED_400, on_click=confirmar_reset),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                texto_feedback,
                ft.Divider(height=10),
                ft.Text("2. Historial de Partidos en BD", weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_200),
                ft.Column(controls=partidos_ui_grupos, spacing=8, scroll=ft.ScrollMode.AUTO),
            ],
            spacing=8, scroll=ft.ScrollMode.AUTO, expand=True,
        )

    # --- PANTALLA 2: PLANTEL Y JUGADORES ---
    def view_plantel():
        jugadores = obtener_jugadores_bd()
        max_titulares = estado["config"]["jugadores_en_cancha"]

        tf_nuevo_num = ft.TextField(label="N°", width=60)
        tf_nuevo_nom = ft.TextField(label="Nombre Jugador", expand=True)
        tf_nuevo_puesto = ft.TextField(label="Puesto", width=110)
        texto_status_jugador = ft.Text("", size=11)

        def click_agregar_jugador(e):
            if tf_nuevo_nom.value and tf_nuevo_num.value:
                res = agregar_jugador_bd(
                    tf_nuevo_num.value.strip(),
                    tf_nuevo_nom.value.strip(),
                    tf_nuevo_puesto.value.strip() or "Jugador",
                )
                if res:
                    texto_status_jugador.value = "✅ Jugador agregado a la BD."
                    texto_status_jugador.color = ft.Colors.GREEN_400
                    contenedor_plantel.content = view_plantel()
                else:
                    texto_status_jugador.value = "⚠️ El jugador ya existe."
                    texto_status_jugador.color = ft.Colors.RED_400
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

            switch_titular = ft.Switch(value=es_titular, on_change=crear_on_change(nombre))

            fila = ft.Container(
                content=ft.Row(
                    [
                        ft.Container(
                            content=ft.Text(f"#{num}", weight=ft.FontWeight.BOLD, size=11, color=ft.Colors.BLUE_200),
                            bgcolor=ft.Colors.GREY_800, padding=6, border_radius=8,
                        ),
                        ft.Column(
                            [
                                ft.Text(nombre, weight=ft.FontWeight.BOLD, size=14),
                                ft.Text(f"{puesto} | {mins_hoy} min hoy", size=11, color=ft.Colors.GREY_400),
                            ],
                            expand=True, spacing=1,
                        ),
                        switch_titular,
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                padding=2,
            )

            if es_titular:
                titulares_ui.append(fila)
            else:
                suplentes_ui.append(fila)

        return ft.Column(
            [
                ft.Text("📋 Plantel (SQLite)", size=20, weight=ft.FontWeight.BOLD),
                ft.Text(
                    f"Titulares en cancha: {len(estado['titulares_seleccionados'])} / {max_titulares}",
                    color=ft.Colors.GREEN_400, weight=ft.FontWeight.BOLD,
                ),
                ft.Divider(height=5),
                ft.Text("Agregar Jugador a la BD", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_200),
                ft.Row([tf_nuevo_num, tf_nuevo_nom, tf_nuevo_puesto]),
                ft.Row([
                    ft.ElevatedButton("Agregar", icon=ft.Icons.PERSON_ADD, on_click=click_agregar_jugador),
                    texto_status_jugador
                ]),
                ft.Divider(height=10),
                ft.Text(f"🟢 TITULARES EN CANCHA ({len(titulares_ui)})", weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_400),
                ft.Container(content=ft.Column(controls=titulares_ui or [ft.Text("Sin titulares", color=ft.Colors.GREY_500)]), bgcolor=ft.Colors.GREY_900, padding=8, border_radius=8),
                ft.Text(f"🟡 BANCA / SUPLENTES ({len(suplentes_ui)})", weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER_400),
                ft.Container(content=ft.Column(controls=suplentes_ui or [ft.Text("Sin suplentes", color=ft.Colors.GREY_500)]), bgcolor=ft.Colors.GREY_900, padding=8, border_radius=8),
            ],
            scroll=ft.ScrollMode.AUTO, expand=True, spacing=6
        )

    # --- PANTALLA 3: PARTIDO EN VIVO Y EVENTOS ---
    def view_partido():
        texto_reloj.value = formatear_tiempo(estado["segundos"])
        jugadores = obtener_jugadores_bd()

        nombre_rival = estado["config"]["equipo_rival"]
        fecha_partido = estado["config"].get("fecha", datetime.now().strftime("%Y-%m-%d"))

        marcador_ui = ft.Container(
            content=ft.Column(
                [
                    ft.Text(f"📅 Partido: {fecha_partido}", size=12, color=ft.Colors.GREY_400),
                    ft.Row(
                        [
                            ft.Column(
                                [
                                    ft.Text("Dunalastair", weight=ft.FontWeight.BOLD, size=14),
                                    ft.Text(f"{estado['goles_local']}", size=36, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_400),
                                ],
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER, expand=True,
                            ),
                            ft.Text("-", size=30, weight=ft.FontWeight.BOLD),
                            ft.Column(
                                [
                                    ft.Text(nombre_rival, weight=ft.FontWeight.BOLD, size=14, overflow=ft.TextOverflow.ELLIPSIS),
                                    ft.Text(f"{estado['goles_rival']}", size=36, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_400),
                                ],
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER, expand=True,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=ft.Colors.GREY_900, padding=8, border_radius=10,
        )

        dd_evento = ft.Dropdown(label="Evento", options=[ft.dropdown.Option(ev) for ev in EVENTOS_DEFECTO], expand=True)
        opciones_titulares = [ft.dropdown.Option(nom) for nom in estado["titulares_seleccionados"]]
        dd_jugador_titular = ft.Dropdown(label="Jugador Titular", options=opciones_titulares, expand=True)

        suplentes_actuales = [j["nombre"] for j in jugadores if j["nombre"] not in estado["titulares_seleccionados"]]
        dd_suplente_entra = ft.Dropdown(label="Entra (Suplente)", options=[ft.dropdown.Option(nom) for nom in suplentes_actuales], expand=True, visible=False)

        lista_eventos_ui = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO)
        texto_status_evento = ft.Text("", color=ft.Colors.GREEN_400, size=12)

        for ev in reversed(estado["eventos_registrados"]):
            lista_eventos_ui.controls.append(
                ft.Text(f"• [{ev['minuto']}] {ev['evento']}: {ev['jugador']}", size=12, color=ft.Colors.GREY_300)
            )

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
            tipo_evento = dd_evento.value
            jugador_sel = dd_jugador_titular.value

            if not tipo_evento or not jugador_sel:
                texto_status_evento.value = "⚠️ Selecciona evento y jugador."
                texto_status_evento.color = ft.Colors.RED_400
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
                    texto_status_evento.color = ft.Colors.RED_400
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

        return ft.Column(
            [
                ft.Text("⏱️ Cronómetro y Registro de Eventos", size=18, weight=ft.FontWeight.BOLD),
                marcador_ui,
                ft.Container(content=texto_reloj, alignment=ft.Alignment(0, 0)),
                ft.Container(content=texto_alerta_cambio, alignment=ft.Alignment(0, 0)),
                ft.Row(
                    [
                        ft.IconButton(icon=ft.Icons.PLAY_ARROW_ROUNDED, icon_size=40, icon_color=ft.Colors.GREEN, on_click=lambda e: setattr(estado, "corriendo", True)),
                        ft.IconButton(icon=ft.Icons.PAUSE_ROUNDED, icon_size=40, icon_color=ft.Colors.ORANGE, on_click=lambda e: (setattr(estado, "corriendo", False), guardar_estado_partido_activo())),
                        ft.IconButton(icon=ft.Icons.STOP_ROUNDED, icon_size=40, icon_color=ft.Colors.RED, on_click=lambda e: (setattr(estado, "corriendo", False), estado.update({"segundos": 0}), guardar_estado_partido_activo(), page.update())),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                ft.Divider(height=5),
                ft.Text("📝 Evento de Partido", weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_200),
                ft.Row([dd_evento, dd_jugador_titular]),
                dd_suplente_entra,
                ft.ElevatedButton("Registrar Evento", icon=ft.Icons.ADD_TASK, on_click=registrar_evento_click),
                texto_status_evento,
                ft.Text("Historial de Eventos (BD):", size=12, weight=ft.FontWeight.BOLD),
                ft.Container(content=lista_eventos_ui, bgcolor=ft.Colors.GREY_900, padding=8, border_radius=8, height=110),
            ],
            scroll=ft.ScrollMode.AUTO, horizontal_alignment=ft.CrossAxisAlignment.CENTER, expand=True, spacing=5,
        )

    # --- PANTALLA 4: ESTADÍSTICAS Y RANKING ACUMULADO ---
    def view_minutos():
        jugadores = obtener_jugadores_bd()
        minutos_acumulados_bd = obtener_minutos_totales_bd()
        stats_ui = []
        texto_export = ft.Text("", color=ft.Colors.GREEN_400)

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

        # Ordenar por minutos jugados acumulados en BD
        jugadores_ordenados = sorted(
            jugadores,
            key=lambda x: minutos_acumulados_bd.get(x["nombre"], 0),
            reverse=True,
        )

        for j in jugadores_ordenados:
            nombre = j["nombre"]
            puesto = j["puesto"]
            num = j["numero"]
            segs_totales = minutos_acumulados_bd.get(nombre, 0)
            mins_totales = segs_totales // 60

            tarjeta = ft.Card(
                content=ft.Container(
                    content=ft.Row(
                        [
                            ft.Container(
                                content=ft.Text(f"#{num}", weight=ft.FontWeight.BOLD, size=11, color=ft.Colors.BLUE_200),
                                bgcolor=ft.Colors.GREY_800, padding=6, border_radius=8,
                            ),
                            ft.Column(
                                [
                                    ft.Text(nombre, weight=ft.FontWeight.BOLD, size=14),
                                    ft.Text(f"Puesto: {puesto}", size=11, color=ft.Colors.GREY_400),
                                ],
                                expand=True, spacing=1,
                            ),
                            ft.Text(f"{mins_totales} min", color=ft.Colors.GREEN_400, weight=ft.FontWeight.BOLD, size=15),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    padding=10, bgcolor=ft.Colors.GREY_900, border_radius=8,
                )
            )
            stats_ui.append(tarjeta)

        return ft.Column(
            [
                ft.Text("📊 Ranking Acumulado (BD Total)", size=20, weight=ft.FontWeight.BOLD),
                ft.ElevatedButton("Exportar a Excel", icon=ft.Icons.EXPLICIT, on_click=click_exportar),
                texto_export,
                ft.Divider(height=10),
                ft.Column(controls=stats_ui, scroll=ft.ScrollMode.AUTO, expand=True),
            ],
            expand=True,
        )

    # --- CONTENEDORES PRINCIPALES ---
    contenedor_config = ft.Container(content=view_configuracion(), expand=True, padding=15, visible=True)
    contenedor_plantel = ft.Container(content=view_plantel(), expand=True, padding=15, visible=False)
    contenedor_partido = ft.Container(content=view_partido(), expand=True, padding=15, visible=False)
    contenedor_minutos = ft.Container(content=view_minutos(), expand=True, padding=15, visible=False)

    def cambiar_pantalla(e):
        # En el NavigationBar, el índice viene dentro del evento 'e'
        indice = e.control.selected_index

        contenedor_config.visible = (indice == 0)
        contenedor_plantel.visible = (indice == 1)
        contenedor_partido.visible = (indice == 2)
        contenedor_minutos.visible = (indice == 3)

        if indice == 0:
            contenedor_config.content = view_configuracion()
        elif indice == 1:
            contenedor_plantel.content = view_plantel()
        elif indice == 2:
            contenedor_partido.content = view_partido()
        elif indice == 3:
            contenedor_minutos.content = view_minutos()
        page.update()

    # 1. Usar la barra de navegación nativa (Siempre visible abajo)
    page.navigation_bar = ft.NavigationBar(
        selected_index=0,
        bgcolor=ft.Colors.GREY_900,
        on_change=cambiar_pantalla,
        destinations=[
            ft.NavigationDestination(icon=ft.Icons.SETTINGS, label="Config"),
            ft.NavigationDestination(icon=ft.Icons.PEOPLE, label="Plantel"),
            ft.NavigationDestination(icon=ft.Icons.SPORTS_SOCCER, label="Partido"),
            ft.NavigationDestination(icon=ft.Icons.BAR_CHART, label="Ranking"),
        ]
    )

    # 2. Quitar 'height=800' y usar 'expand=True'
    app_layout = ft.Container(
        width=400,
        expand=True,  # Esto permite que se adapte al alto exacto del celular
        bgcolor=ft.Colors.BLACK,
        content=ft.Stack(
            controls=[contenedor_config, contenedor_plantel, contenedor_partido, contenedor_minutos],
            expand=True,
        ),
    )

    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.bgcolor = ft.Colors.BLACK
    page.add(app_layout)


if __name__ == "__main__":
    puerto = int(os.environ.get("PORT", 8080))
    ft.app(target=main, host="0.0.0.0", port=puerto, view=ft.AppView.WEB_BROWSER)