import flet as ft
from datetime import datetime
from config.constants import (
    COLOR_TARJETA, COLOR_BORDE, COLOR_CELESTE, COLOR_CELESTE_BOTON,
    COLOR_TEXTO, COLOR_SUBTEXTO, COLOR_VERDE, COLOR_ROJO, COLOR_AMBAR, COLOR_FONDO
)
from backend.services.grupo_service import GrupoService
from backend.services.partido_service import PartidoService
from frontend.screens.mantenedor_eventos import mostrar_dialogo_mantenedor_eventos


class ConfiguracionScreen:
    def __init__(self, estado, page, callbacks):
        self.estado = estado
        self.page = page
        self.callbacks = callbacks

    def build(self):
        tf_buscar_fecha = ft.TextField(
            label="Consultar Fecha (AAAA-MM-DD)",
            value=self.estado.get("fecha_filtro", datetime.now().strftime("%Y-%m-%d")),
            width=220,
            border_color=COLOR_BORDE,
            focused_border_color=COLOR_CELESTE,
            border_radius=10,
        )

        def click_buscar_fecha(e=None):
            self.estado["fecha_filtro"] = tf_buscar_fecha.value.strip()
            self.estado["partido_activo_id"] = None
            self.estado["minutos_partido_actual"] = {}
            self.estado["segundos"] = 0
            self.estado["segundos_acumulados"] = 0
            self.estado["segs_al_iniciar"] = 0
            self.estado["ultimo_segundo_procesado"] = 0
            self.estado["hora_inicio"] = None
            self.estado["corriendo"] = False
            self.estado["finalizado"] = False
            self.estado["alerta_custom"] = None
            self.estado["titulares_seleccionados"] = []
            self.estado["eventos_registrados"] = []
            self.estado["goles_local"] = 0
            self.estado["goles_rival"] = 0
            self.callbacks["cargar_grupo"]()
            self.callbacks["refrescar_vistas"]()
            self.page.update()

        def on_date_picked(e):
            if date_picker.value:
                fecha_str = date_picker.value.strftime("%Y-%m-%d") if isinstance(date_picker.value, datetime) else str(date_picker.value).split("T")[0].split(" ")[0]
                tf_buscar_fecha.value = fecha_str
                click_buscar_fecha()

        fecha_val_inicial = datetime.now()
        try:
            if self.estado.get("fecha_filtro"):
                fecha_val_inicial = datetime.strptime(self.estado["fecha_filtro"], "%Y-%m-%d")
        except Exception:
            pass

        date_picker = ft.DatePicker(
            value=fecha_val_inicial,
            first_date=datetime(2020, 1, 1),
            last_date=datetime(2035, 12, 31),
            on_change=on_date_picked,
        )

        def abrir_calendario(e):
            self.page.open(date_picker)

        row_filtro = ft.Row([
            tf_buscar_fecha,
            ft.IconButton(
                icon=ft.Icons.CALENDAR_MONTH,
                icon_color=COLOR_CELESTE,
                on_click=abrir_calendario,
                tooltip="Seleccionar Fecha"
            ),
            ft.IconButton(
                icon=ft.Icons.SEARCH,
                icon_color=COLOR_CELESTE,
                on_click=click_buscar_fecha,
                tooltip="Buscar Cuadrangular"
            )
        ])

        # Tabla de posiciones (código original)
        componente_tabla = ft.Container()
        if self.estado["grupo_activo"] and self.estado["partidos_grupo"]:
            grupo = self.estado["grupo_activo"]
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

            for p in self.estado["partidos_grupo"]:
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
                content=ft.Column([
                    ft.Row([
                        ft.Text(
                            f"🏆 Tabla de Posiciones: {grupo['nombre']}",
                            weight=ft.FontWeight.BOLD,
                            color=COLOR_CELESTE,
                            size=15,
                        ),
                        ft.Text(f"📅 {grupo['fecha']}", color=COLOR_SUBTEXTO, size=12),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Row([tabla_ui], scroll=ft.ScrollMode.ALWAYS),
                ], spacing=8),
                padding=12,
                bgcolor=COLOR_TARJETA,
                border_radius=12,
                border=ft.border.all(1, COLOR_CELESTE),
            )

        # Partidos del grupo
        partidos_mi_equipo_ui = []
        partidos_rivales_ui = []

        if self.estado["partidos_grupo"]:
            for p in self.estado["partidos_grupo"]:
                es_activo = p["id"] == self.estado["partido_activo_id"]

                def crear_handler_select(partido_obj):
                    return lambda e: (
                        self.callbacks["activar_partido_memoria"](partido_obj),
                        self.callbacks["guardar_partido"](),
                        self.callbacks["refrescar_vistas"](),
                        self.page.update(),
                    )

                if p["es_principal"]:
                    rival_nombre = (
                        p["equipo_visita"]
                        if p["equipo_local"] == self.estado["config"]["equipo_principal"]
                        else p["equipo_local"]
                    )

                    if p.get("finalizado", False):
                        texto_estado = "Finalizado"
                        color_estado = COLOR_ROJO
                    elif es_activo:
                        texto_estado = "En Curso"
                        color_estado = COLOR_VERDE
                    elif p["jugado"] or p["segundos"] > 0:
                        texto_estado = "Finalizado"
                        color_estado = COLOR_SUBTEXTO
                    else:
                        texto_estado = "Por jugar"
                        color_estado = COLOR_SUBTEXTO

                    if self.estado["es_invitado"]:
                        accion_ui = ft.ElevatedButton(
                            "Ver Detalles" if not es_activo else "Viendo",
                            icon=ft.Icons.VISIBILITY if not es_activo else ft.Icons.CHECK_CIRCLE,
                            disabled=es_activo,
                            bgcolor=COLOR_CELESTE_BOTON if not es_activo else COLOR_BORDE,
                            color=COLOR_TEXTO,
                            on_click=crear_handler_select(p),
                        )
                        acciones_card = accion_ui
                    else:
                        accion_ui = ft.ElevatedButton(
                            "Seleccionar" if not es_activo else "En Curso",
                            icon=ft.Icons.PLAY_ARROW if not es_activo else ft.Icons.CHECK_CIRCLE,
                            disabled=es_activo,
                            bgcolor=COLOR_CELESTE_BOTON if not es_activo else COLOR_BORDE,
                            color=COLOR_TEXTO,
                            on_click=crear_handler_select(p),
                        )
                        if p.get("finalizado", False) and not es_activo:
                            accion_ui.text = "Finalizado"

                        acciones_card = ft.Row([
                            accion_ui,
                            ft.IconButton(
                                icon=ft.Icons.EDIT_NOTE,
                                icon_color=COLOR_CELESTE,
                                tooltip="🛠️ Mantenedor de Eventos",
                                on_click=lambda e, pid=p["id"]: mostrar_dialogo_mantenedor_eventos(
                                    self.page, self.estado, self.callbacks, pid
                                ),
                            ),
                        ], spacing=4)

                    card = ft.Container(
                        content=ft.Row([
                            ft.Column([
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
                            ], spacing=2),
                            acciones_card,
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        padding=10,
                        bgcolor=COLOR_TARJETA,
                        border_radius=10,
                        border=ft.border.all(1.5, COLOR_CELESTE if es_activo else COLOR_BORDE),
                    )
                    partidos_mi_equipo_ui.append(card)
                else:
                    if self.estado["es_invitado"]:
                        ha_jugado = p.get("jugado", False) or p.get("goles_local", 0) > 0 or p.get("goles_visita", 0) > 0
                        marcador_destacado = ft.Container(
                            content=ft.Text(
                                f"{p['goles_local']}  -  {p['goles_visita']}",
                                weight=ft.FontWeight.BOLD,
                                size=15,
                                color=COLOR_AMBAR if ha_jugado else COLOR_TEXTO,
                            ),
                            bgcolor=COLOR_FONDO,
                            padding=ft.Padding(16, 6, 16, 6),
                            border_radius=8,
                            border=ft.border.all(1.5, COLOR_AMBAR if ha_jugado else COLOR_BORDE),
                        )
                        card_rival = ft.Container(
                            content=ft.Row([
                                ft.Text(
                                    f"{p['equipo_local']}",
                                    weight=ft.FontWeight.BOLD,
                                    size=13,
                                    color=COLOR_TEXTO,
                                    expand=True,
                                    text_align=ft.TextAlign.RIGHT,
                                ),
                                marcador_destacado,
                                ft.Text(
                                    f"{p['equipo_visita']}",
                                    weight=ft.FontWeight.BOLD,
                                    size=13,
                                    color=COLOR_TEXTO,
                                    expand=True,
                                    text_align=ft.TextAlign.LEFT,
                                ),
                            ], alignment=ft.MainAxisAlignment.CENTER, spacing=12),
                            padding=10,
                            bgcolor=COLOR_TARJETA,
                            border_radius=8,
                            border=ft.border.all(1, COLOR_BORDE),
                        )
                    else:
                        tf_g_loc = ft.TextField(
                            value=str(p["goles_local"]),
                            width=50,
                            border_color=COLOR_BORDE,
                            border_radius=8,
                            keyboard_type=ft.KeyboardType.NUMBER,
                        )
                        tf_g_vis = ft.TextField(
                            value=str(p["goles_visita"]),
                            width=50,
                            border_color=COLOR_BORDE,
                            border_radius=8,
                            keyboard_type=ft.KeyboardType.NUMBER,
                        )

                        def crear_handler_guardar_rival(p_id, input_l, input_v):
                            return lambda e: (
                                PartidoService.guardar_marcador_rival(
                                    p_id,
                                    int(input_l.value or 0),
                                    int(input_v.value or 0),
                                ),
                                self.callbacks["refrescar_vistas"](),
                                self.page.update(),
                            )

                        card_rival = ft.Container(
                            content=ft.Row([
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
                                    tooltip="Guardar Marcador",
                                    on_click=crear_handler_guardar_rival(
                                        p["id"], tf_g_loc, tf_g_vis
                                    ),
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.EDIT_NOTE,
                                    icon_color=COLOR_CELESTE,
                                    tooltip="🛠️ Mantenedor de Eventos",
                                    on_click=lambda e, pid=p["id"]: mostrar_dialogo_mantenedor_eventos(
                                        self.page, self.estado, self.callbacks, pid
                                    ),
                                ),
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            padding=6,
                            bgcolor=COLOR_TARJETA,
                            border_radius=8,
                            border=ft.border.all(1, COLOR_BORDE),
                        )
                    partidos_rivales_ui.append(card_rival)

        elementos_columna = [
            ft.Text("📅 Buscar Cuadrangular por Fecha", size=16, weight=ft.FontWeight.BOLD, color=COLOR_TEXTO),
            row_filtro,
            ft.Divider(height=10, color=COLOR_BORDE),
            ft.Text("⚙️ Configuración del Grupo y Torneo", size=20, weight=ft.FontWeight.BOLD, color=COLOR_TEXTO),
            componente_tabla,
        ]

        elementos_columna.extend([
            ft.Row([
                ft.Text(
                    f"Partidos de {self.estado['config']['equipo_principal']}",
                    weight=ft.FontWeight.BOLD,
                    color=COLOR_CELESTE,
                ),
                ft.ElevatedButton(
                    "🛠️ Mantenedor de Eventos",
                    icon=ft.Icons.EDIT_NOTE,
                    bgcolor=COLOR_TARJETA,
                    color=COLOR_CELESTE,
                    visible=not self.estado["es_invitado"],
                    on_click=lambda e: mostrar_dialogo_mantenedor_eventos(
                        self.page, self.estado, self.callbacks
                    ),
                ),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Column(
                controls=partidos_mi_equipo_ui or [ft.Text("Sin partidos asignados", color=COLOR_SUBTEXTO)],
                spacing=8,
            ),
            ft.Text(
                "Marcadores entre Rivales del Grupo (Combinatoria)",
                weight=ft.FontWeight.BOLD,
                color=COLOR_AMBAR,
            ),
            ft.Column(
                controls=partidos_rivales_ui or [ft.Text("Sin partidos de rivales", color=COLOR_SUBTEXTO)],
                spacing=6,
            ),
        ])

        # Formulario de nuevo grupo
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
            value=self.estado.get("fecha_filtro", datetime.now().strftime("%Y-%m-%d")),
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
            if self.estado["es_invitado"]:
                return
            nom_g = tf_nombre_grupo.value.strip()
            f_g = tf_fecha_grupo.value.strip()
            eq_princ = tf_equipo_principal.value.strip()
            rivales_str = tf_equipos_rivales.value.strip()

            if not nom_g or not eq_princ or not rivales_str:
                texto_feedback_grupo.value = "⚠️ Completa todos los campos del grupo."
                texto_feedback_grupo.color = COLOR_ROJO
                self.page.update()
                return

            lista_rivales = [r.strip() for r in rivales_str.split(",") if r.strip()]
            if not lista_rivales:
                texto_feedback_grupo.value = "⚠️ Ingresa al menos un equipo rival."
                texto_feedback_grupo.color = COLOR_ROJO
                self.page.update()
                return

            todos_los_equipos = [eq_princ] + lista_rivales
            GrupoService.crear_grupo(nom_g, f_g, eq_princ, todos_los_equipos, self.estado["es_invitado"])

            self.estado["fecha_filtro"] = f_g
            self.estado["partido_activo_id"] = None
            self.estado["minutos_partido_actual"] = {}
            self.estado["segundos"] = 0
            self.estado["segundos_acumulados"] = 0
            self.estado["segs_al_iniciar"] = 0
            self.estado["ultimo_segundo_procesado"] = 0
            self.estado["hora_inicio"] = None
            self.estado["corriendo"] = False
            self.estado["finalizado"] = False
            self.estado["alerta_custom"] = None
            self.estado["titulares_seleccionados"] = []
            self.estado["eventos_registrados"] = []
            self.estado["goles_local"] = 0
            self.estado["goles_rival"] = 0
            texto_feedback_grupo.value = f"✅ Grupo '{nom_g}' generado con {len(todos_los_equipos)} equipos y sus partidos combinados."
            texto_feedback_grupo.color = COLOR_VERDE
            self.callbacks["cargar_grupo"]()
            self.callbacks["refrescar_vistas"]()
            self.page.update()

        def confirmar_reset(e):
            if self.estado["es_invitado"]:
                return

            fecha_a_borrar = (
                self.estado.get("fecha_filtro")
                or tf_buscar_fecha.value.strip()
                or datetime.now().strftime("%Y-%m-%d")
            )

            def cerrar_dlg(ev):
                self.page.close(dialogo_reset)

            def procesar_reset(ev):
                GrupoService.eliminar_grupo_por_fecha(fecha_a_borrar, self.estado["es_invitado"])

                self.estado["partido_activo_id"] = None
                self.estado["minutos_partido_actual"] = {}
                self.estado["segundos"] = 0
                self.estado["segundos_acumulados"] = 0
                self.estado["segs_al_iniciar"] = 0
                self.estado["ultimo_segundo_procesado"] = 0
                self.estado["hora_inicio"] = None
                self.estado["corriendo"] = False
                self.estado["finalizado"] = False
                self.estado["alerta_custom"] = None
                self.estado["titulares_seleccionados"] = []
                self.estado["eventos_registrados"] = []
                self.estado["goles_local"] = 0
                self.estado["goles_rival"] = 0

                texto_feedback_grupo.value = f"🔄 Información del día {fecha_a_borrar} eliminada de la BD."
                texto_feedback_grupo.color = COLOR_VERDE
                self.page.close(dialogo_reset)
                self.callbacks["cargar_grupo"]()
                self.callbacks["refrescar_vistas"]()
                self.page.update()

            dialogo_reset = ft.AlertDialog(
                title=ft.Text(f"¿Borrar datos del día ({fecha_a_borrar})?", color=COLOR_TEXTO),
                content=ft.Text(f"Se eliminarán de la BD el grupo y partidos registrados únicamente para la fecha {fecha_a_borrar}."),
                actions=[
                    ft.TextButton("Cancelar", on_click=cerrar_dlg),
                    ft.ElevatedButton(
                        "Borrar Día",
                        bgcolor=COLOR_ROJO,
                        color=COLOR_TEXTO,
                        on_click=procesar_reset,
                    ),
                ],
                bgcolor=COLOR_TARJETA,
            )
            self.page.open(dialogo_reset)

        if not self.estado["es_invitado"]:
            elementos_columna.append(
                ft.Container(
                    content=ft.Column([
                        ft.Text("1. Definir Nuevo Grupo / Torneo", weight=ft.FontWeight.BOLD, color=COLOR_CELESTE),
                        ft.Row([tf_nombre_grupo, tf_fecha_grupo]),
                        ft.Row([tf_equipo_principal, tf_equipos_rivales]),
                        ft.Row([
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
                                style=ft.ButtonStyle(color=COLOR_ROJO, side=ft.BorderSide(1, COLOR_ROJO)),
                                on_click=confirmar_reset,
                            ),
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        texto_feedback_grupo,
                    ], spacing=8),
                    padding=14,
                    bgcolor=COLOR_TARJETA,
                    border_radius=14,
                    border=ft.border.all(1, COLOR_BORDE),
                )
            )

        return ft.Column(elementos_columna, spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)
