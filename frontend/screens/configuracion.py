import flet as ft
from datetime import datetime
from typing import List, Optional
from config.constants import (
    COLOR_TARJETA, COLOR_BORDE, COLOR_CELESTE, COLOR_CELESTE_BOTON,
    COLOR_TEXTO, COLOR_SUBTEXTO, COLOR_VERDE, COLOR_ROJO, COLOR_AMBAR, COLOR_FONDO
)
from backend.services.grupo_service import GrupoService
from backend.services.partido_service import PartidoService
from backend.database.repositories import PartidoRepository
from frontend.screens.mantenedor_eventos import mostrar_dialogo_mantenedor_eventos
from frontend.screens.admin_usuarios import mostrar_dialogo_admin_usuarios


class ConfiguracionScreen:
    def __init__(self, estado, page, callbacks):
        self.estado = estado
        self.page = page
        self.callbacks = callbacks
        # Vista activa en configuracion: ID de grupo o "campeon"
        self.vista_activa = self.estado.get("vista_config_activa", "grupo")

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
                fecha_str = (
                    date_picker.value.strftime("%Y-%m-%d")
                    if isinstance(date_picker.value, datetime)
                    else str(date_picker.value).split("T")[0].split(" ")[0]
                )
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

        fecha_actual_filtro = self.estado.get("fecha_filtro", datetime.now().strftime("%Y-%m-%d"))

        def seleccionar_fecha_directa(f_str):
            tf_buscar_fecha.value = f_str
            click_buscar_fecha()

        fechas_registradas = GrupoService.obtener_fechas_con_cuadrangulares()
        chips_fechas = []
        for f_str in fechas_registradas:
            es_sel = (f_str == fecha_actual_filtro)
            chips_fechas.append(
                ft.Container(
                    content=ft.Row([
                        ft.Icon(
                            ft.Icons.EMOJI_EVENTS if es_sel else ft.Icons.EVENT_NOTE,
                            size=13,
                            color=COLOR_AMBAR if es_sel else COLOR_CELESTE
                        ),
                        ft.Text(
                            f_str,
                            size=12,
                            weight=ft.FontWeight.BOLD if es_sel else ft.FontWeight.NORMAL,
                            color=COLOR_TEXTO if es_sel else COLOR_SUBTEXTO
                        ),
                    ], spacing=4, alignment=ft.MainAxisAlignment.CENTER),
                    bgcolor=ft.Colors.with_opacity(0.25, COLOR_CELESTE) if es_sel else COLOR_TARJETA,
                    border=ft.border.all(1.5 if es_sel else 1, COLOR_CELESTE if es_sel else COLOR_BORDE),
                    border_radius=8,
                    padding=ft.padding.symmetric(horizontal=10, vertical=6),
                    ink=True,
                    on_click=lambda e, f=f_str: seleccionar_fecha_directa(f),
                    tooltip=f"Ver cuadrangular del {f_str}",
                )
            )

        barra_fechas_historial = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.HISTORY, size=15, color=COLOR_CELESTE),
                    ft.Text(
                        f"Fechas con Cuadrangulares ({len(fechas_registradas)}):",
                        size=12,
                        weight=ft.FontWeight.BOLD,
                        color=COLOR_CELESTE,
                    ),
                ], spacing=6),
                ft.Row(chips_fechas, scroll=ft.ScrollMode.ADAPTIVE, spacing=8),
            ], spacing=6),
            padding=ft.padding.only(top=2, bottom=4),
        ) if fechas_registradas else None

        grupos_dia = self.estado.get("grupos_dia", [])
        config_torneo = self.estado.get("config_torneo", {"partido_definicion": False})
        con_partido_def = config_torneo.get("partido_definicion", False)
        partido_def = self.estado.get("partido_definicion")

        # Determinar grupo seleccionado
        grupo_sel_id = self.estado.get("grupo_seleccionado_id")
        grupo_sel_data = None
        if grupos_dia:
            grupo_sel_data = next((g for g in grupos_dia if g["grupo"]["id"] == grupo_sel_id), grupos_dia[0])
            self.estado["grupo_seleccionado_id"] = grupo_sel_data["grupo"]["id"]

        # Funciones de cambio de pestaña
        def seleccionar_pestana_grupo(g_id):
            def handler(e):
                self.estado["grupo_seleccionado_id"] = g_id
                self.vista_activa = "grupo"
                self.estado["vista_config_activa"] = "grupo"
                self.callbacks["cargar_grupo"]()
                self.callbacks["refrescar_vistas"]()
                self.page.update()
            return handler

        def seleccionar_pestana_campeon(e):
            self.vista_activa = "campeon"
            self.estado["vista_config_activa"] = "campeon"
            self.callbacks["refrescar_vistas"]()
            self.page.update()

        # Modal para agregar nuevo grupo secundario
        def abrir_modal_nuevo_grupo(e):
            if self.estado["es_invitado"]:
                return

            tf_modal_nombre = ft.TextField(
                label="Nombre del Grupo",
                value=f"Grupo {chr(65 + len(grupos_dia))}" if len(grupos_dia) < 26 else f"Grupo {len(grupos_dia) + 1}",
                border_color=COLOR_BORDE,
                focused_border_color=COLOR_CELESTE,
                border_radius=8,
            )
            tf_modal_eq1 = ft.TextField(label="Equipo 1", value="", border_color=COLOR_BORDE, border_radius=8)
            tf_modal_eq2 = ft.TextField(label="Equipo 2", value="", border_color=COLOR_BORDE, border_radius=8)
            tf_modal_eq3 = ft.TextField(label="Equipo 3", value="", border_color=COLOR_BORDE, border_radius=8)
            tf_modal_eq4 = ft.TextField(label="Equipo 4", value="", border_color=COLOR_BORDE, border_radius=8)
            lbl_error_modal = ft.Text("", size=11, color=COLOR_ROJO)

            def cerrar_modal(ev):
                self.page.close(dlg_nuevo_grupo)

            def guardar_nuevo_grupo(ev):
                nom = tf_modal_nombre.value.strip()
                eqs = [
                    tf_modal_eq1.value.strip(),
                    tf_modal_eq2.value.strip(),
                    tf_modal_eq3.value.strip(),
                    tf_modal_eq4.value.strip(),
                ]
                eqs = [eq for eq in eqs if eq]
                if not nom:
                    lbl_error_modal.value = "⚠️ Debes ingresar un nombre para el grupo."
                    self.page.update()
                    return
                if len(eqs) != 4:
                    lbl_error_modal.value = "⚠️ Debes ingresar exactamente los 4 equipos del cuadrangular."
                    self.page.update()
                    return
                if len(set(eq.lower() for eq in eqs)) != len(eqs):
                    lbl_error_modal.value = "⚠️ Los 4 equipos deben ser distintos (no duplicados)."
                    self.page.update()
                    return

                fecha_actual = self.estado.get("fecha_filtro", datetime.now().strftime("%Y-%m-%d"))
                nuevo_id = GrupoService.crear_grupo_adicional(nom, fecha_actual, eqs, self.estado["es_invitado"])
                if nuevo_id:
                    self.estado["grupo_seleccionado_id"] = nuevo_id
                    self.vista_activa = "grupo"
                    self.estado["vista_config_activa"] = "grupo"
                    self.page.close(dlg_nuevo_grupo)
                    self.callbacks["cargar_grupo"]()
                    self.callbacks["refrescar_vistas"]()
                    self.page.update()
                else:
                    lbl_error_modal.value = "❌ Error al crear el grupo."
                    self.page.update()

            dlg_nuevo_grupo = ft.AlertDialog(
                title=ft.Text("➕ Agregar Cuadrangular Adicional", color=COLOR_TEXTO, size=16),
                content=ft.Container(
                    width=380,
                    content=ft.Column([
                        ft.Text("Define el nombre y los 4 equipos rivales:", size=12, color=COLOR_SUBTEXTO),
                        tf_modal_nombre,
                        tf_modal_eq1,
                        tf_modal_eq2,
                        tf_modal_eq3,
                        tf_modal_eq4,
                        lbl_error_modal,
                    ], spacing=8, tight=True),
                ),
                actions=[
                    ft.TextButton("Cancelar", on_click=cerrar_modal),
                    ft.ElevatedButton("Crear Grupo", bgcolor=COLOR_CELESTE_BOTON, color=COLOR_TEXTO, on_click=guardar_nuevo_grupo),
                ],
                bgcolor=COLOR_TARJETA,
            )
            self.page.open(dlg_nuevo_grupo)

        # Barra de Chips / Pestañas de Navegación por Grupo
        chips_grupos = []
        if grupos_dia:
            for g_item in grupos_dia:
                g_obj = g_item["grupo"]
                g_id = g_obj["id"]
                es_activo = (self.vista_activa == "grupo" and grupo_sel_data and grupo_sel_data["grupo"]["id"] == g_id)
                icono_chip = ft.Icons.SPORTS_SOCCER

                chips_grupos.append(
                    ft.ElevatedButton(
                        text=f"{g_obj['nombre']}",
                        icon=icono_chip,
                        bgcolor=COLOR_CELESTE_BOTON if es_activo else COLOR_TARJETA,
                        color=COLOR_TEXTO if es_activo else COLOR_SUBTEXTO,
                        on_click=seleccionar_pestana_grupo(g_id),
                    )
                )

            # Chip de Campeón del Día
            es_campeon_activo = (self.vista_activa == "campeon")
            chips_grupos.append(
                ft.ElevatedButton(
                    text="🏆 Campeón del Día",
                    icon=ft.Icons.EMOJI_EVENTS,
                    bgcolor=COLOR_AMBAR if es_campeon_activo else COLOR_TARJETA,
                    color=COLOR_FONDO if es_campeon_activo else COLOR_AMBAR,
                    on_click=seleccionar_pestana_campeon,
                )
            )

            # Botón Agregar Grupo para Administrador
            if not self.estado["es_invitado"]:
                chips_grupos.append(
                    ft.ElevatedButton(
                        text="➕ Agregar Grupo",
                        icon=ft.Icons.ADD,
                        bgcolor=COLOR_TARJETA,
                        color=COLOR_VERDE,
                        on_click=abrir_modal_nuevo_grupo,
                    )
                )

        barra_chips = ft.Container(
            content=ft.Row(chips_grupos, scroll=ft.ScrollMode.ALWAYS, spacing=8),
            padding=ft.Padding(0, 4, 0, 8),
        )

        if self.estado["es_invitado"]:
            elementos_columna = [
                ft.Text("📅 Cuadrangulares por Fecha", size=16, weight=ft.FontWeight.BOLD, color=COLOR_TEXTO),
            ]
            if barra_fechas_historial:
                elementos_columna.append(barra_fechas_historial)
            else:
                elementos_columna.append(
                    ft.Text("No hay cuadrangulares registrados actualmente.", size=12, color=COLOR_SUBTEXTO)
                )
        else:
            elementos_columna = [
                ft.Text("📅 Buscar Cuadrangular por Fecha", size=16, weight=ft.FontWeight.BOLD, color=COLOR_TEXTO),
                row_filtro,
            ]
            if barra_fechas_historial:
                elementos_columna.append(barra_fechas_historial)

        elementos_columna.append(ft.Divider(height=10, color=COLOR_BORDE))

        if grupos_dia:
            elementos_columna.append(barra_chips)

        # Renderizar según la vista activa
        if not grupos_dia:
            # No hay grupos para el día
            elementos_columna.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.INFO_OUTLINE, color=COLOR_AMBAR, size=32),
                        ft.Text(
                            f"No hay cuadrangulares creados para la fecha {self.estado.get('fecha_filtro')}.",
                            color=COLOR_SUBTEXTO,
                            size=13,
                        ),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=6),
                    padding=20,
                    alignment=ft.alignment.center,
                )
            )
        elif self.vista_activa == "campeon":
            # VISTA DE 🏆 CAMPEÓN DEL DÍA / GRAN FINAL
            resultado_campeon = GrupoService.calcular_campeon_del_dia(
                grupos_dia,
                con_partido_definicion=con_partido_def,
                partido_definicion=partido_def,
            )

            # Si hay partido de definición activado y 2 finalistas, asegurar sincronización
            finalistas = resultado_campeon.get("finalistas", [])
            if con_partido_def and len(finalistas) >= 2:
                p_sync = GrupoService.sincronizar_partido_definicion(
                    self.estado.get("fecha_filtro"),
                    finalistas[0],
                    finalistas[1],
                )
                if p_sync:
                    self.estado["partido_definicion"] = p_sync
                    partido_def = p_sync
                    resultado_campeon = GrupoService.calcular_campeon_del_dia(
                        grupos_dia,
                        con_partido_definicion=con_partido_def,
                        partido_definicion=p_sync,
                    )

            # Tarjeta de Campeón del Día
            campeon_nombre = resultado_campeon.get("campeon")
            motivo_campeon = resultado_campeon.get("motivo", "")

            if campeon_nombre:
                contenido_tarjeta_campeon = ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.EMOJI_EVENTS, color=COLOR_AMBAR, size=40),
                        ft.Column([
                            ft.Text("🏆 CAMPEÓN DEL DÍA", weight=ft.FontWeight.BOLD, color=COLOR_AMBAR, size=16),
                            ft.Text(f"🥇 {campeon_nombre}", weight=ft.FontWeight.BOLD, color=COLOR_TEXTO, size=22),
                        ], spacing=2),
                    ], alignment=ft.MainAxisAlignment.START, spacing=14),
                    ft.Text(f"Motivo: {motivo_campeon}", color=COLOR_CELESTE, size=13),
                ], spacing=6)
                color_borde_campeon = COLOR_AMBAR
            else:
                contenido_tarjeta_campeon = ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.HOURGLASS_EMPTY, color=COLOR_CELESTE, size=32),
                        ft.Column([
                            ft.Text("🏆 CAMPEONATO DEL DÍA EN CURSO", weight=ft.FontWeight.BOLD, color=COLOR_CELESTE, size=15),
                            ft.Text(motivo_campeon, color=COLOR_SUBTEXTO, size=13),
                        ], spacing=2),
                    ], alignment=ft.MainAxisAlignment.START, spacing=12),
                ], spacing=4)
                color_borde_campeon = COLOR_BORDE

            tarjeta_campeon = ft.Container(
                content=contenido_tarjeta_campeon,
                padding=16,
                bgcolor=COLOR_TARJETA,
                border_radius=12,
                border=ft.border.all(2, color_borde_campeon),
            )

            # Switch de Definición con Partido Final
            def on_cambiar_modo_definicion(e):
                if self.estado["es_invitado"]:
                    return
                nuevo_val = bool(sw_partido_def.value)
                GrupoService.actualizar_opcion_definicion(self.estado.get("fecha_filtro"), nuevo_val, self.estado["es_invitado"])
                self.callbacks["cargar_grupo"]()
                self.callbacks["refrescar_vistas"]()
                self.page.update()

            sw_partido_def = ft.Switch(
                label="Definir Campeón con Partido Final (1° vs 1°)",
                value=con_partido_def,
                disabled=self.estado["es_invitado"],
                active_color=COLOR_AMBAR,
                on_change=on_cambiar_modo_definicion,
            )

            # Tarjeta de Partido Final (si está activada la opción)
            tarjeta_partido_final = ft.Container()
            if con_partido_def and len(finalistas) >= 2:
                eq_fin_1 = finalistas[0]
                eq_fin_2 = finalistas[1]
                g_fin_1 = partido_def.get("goles_local", 0) if partido_def else 0
                g_fin_2 = partido_def.get("goles_visita", 0) if partido_def else 0
                fin_jugado = partido_def.get("jugado", False) if partido_def else False
                fin_id = partido_def.get("id") if partido_def else None

                if self.estado["es_invitado"]:
                    tarjeta_partido_final = ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Icon(ft.Icons.MILITARY_TECH, color=COLOR_AMBAR, size=20),
                                ft.Text("⚔️ GRAN FINAL DE DEFINICIÓN", weight=ft.FontWeight.BOLD, color=COLOR_AMBAR, size=14),
                            ], spacing=6),
                            ft.Row([
                                ft.Text(eq_fin_1, weight=ft.FontWeight.BOLD, color=COLOR_TEXTO, expand=True, text_align=ft.TextAlign.RIGHT),
                                ft.Container(
                                    content=ft.Text(f"{g_fin_1}  -  {g_fin_2}", weight=ft.FontWeight.BOLD, size=16, color=COLOR_AMBAR if fin_jugado else COLOR_TEXTO),
                                    bgcolor=COLOR_FONDO,
                                    padding=ft.Padding(16, 6, 16, 6),
                                    border_radius=8,
                                    border=ft.border.all(1.5, COLOR_AMBAR if fin_jugado else COLOR_BORDE),
                                ),
                                ft.Text(eq_fin_2, weight=ft.FontWeight.BOLD, color=COLOR_TEXTO, expand=True, text_align=ft.TextAlign.LEFT),
                            ], alignment=ft.MainAxisAlignment.CENTER, spacing=10),
                        ], spacing=10),
                        padding=14,
                        bgcolor=COLOR_TARJETA,
                        border_radius=12,
                        border=ft.border.all(1.5, COLOR_AMBAR),
                    )
                else:
                    tf_g_fin_1 = ft.TextField(value=str(g_fin_1), width=50, border_color=COLOR_BORDE, border_radius=8, keyboard_type=ft.KeyboardType.NUMBER)
                    tf_g_fin_2 = ft.TextField(value=str(g_fin_2), width=50, border_color=COLOR_BORDE, border_radius=8, keyboard_type=ft.KeyboardType.NUMBER)
                    chk_fin = ft.Checkbox(label="Finalizado", value=fin_jugado)

                    def guardar_resultado_final(ev):
                        if fin_id:
                            gl = int(tf_g_fin_1.value or 0)
                            gv = int(tf_g_fin_2.value or 0)
                            p_obj = PartidoRepository.obtener_por_id(fin_id)
                            if p_obj:
                                p_obj.goles_local = gl
                                p_obj.goles_visita = gv
                                p_obj.jugado = True
                                p_obj.finalizado = chk_fin.value
                                PartidoRepository.actualizar(p_obj)
                                self.callbacks["cargar_grupo"]()
                                self.callbacks["refrescar_vistas"]()
                                self.page.update()

                    tarjeta_partido_final = ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Icon(ft.Icons.MILITARY_TECH, color=COLOR_AMBAR, size=20),
                                ft.Text("⚔️ GRAN FINAL DE DEFINICIÓN (1° vs 1°)", weight=ft.FontWeight.BOLD, color=COLOR_AMBAR, size=14),
                            ], spacing=6),
                            ft.Row([
                                ft.Text(eq_fin_1, weight=ft.FontWeight.BOLD, color=COLOR_TEXTO, expand=True, text_align=ft.TextAlign.RIGHT),
                                tf_g_fin_1,
                                ft.Text("-", color=COLOR_SUBTEXTO),
                                tf_g_fin_2,
                                ft.Text(eq_fin_2, weight=ft.FontWeight.BOLD, color=COLOR_TEXTO, expand=True, text_align=ft.TextAlign.LEFT),
                                ft.ElevatedButton("Guardar Final", icon=ft.Icons.SAVE, bgcolor=COLOR_AMBAR, color=COLOR_FONDO, on_click=guardar_resultado_final),
                            ], alignment=ft.MainAxisAlignment.CENTER, spacing=10),
                            chk_fin,
                        ], spacing=8),
                        padding=14,
                        bgcolor=COLOR_TARJETA,
                        border_radius=12,
                        border=ft.border.all(1.5, COLOR_AMBAR),
                    )

            # Tabla General de Líderes
            lideres = resultado_campeon.get("lideres", [])
            filas_lideres = []
            for pos_idx, l in enumerate(lideres, start=1):
                filas_lideres.append(
                    ft.DataRow(cells=[
                        ft.DataCell(content=ft.Text(str(pos_idx), color=COLOR_TEXTO)),
                        ft.DataCell(content=ft.Text(l["equipo"], weight=ft.FontWeight.BOLD, color=COLOR_CELESTE if pos_idx == 1 else COLOR_TEXTO)),
                        ft.DataCell(content=ft.Text(l.get("nombre_grupo", "-"), color=COLOR_SUBTEXTO)),
                        ft.DataCell(content=ft.Text(str(l["PJ"]), color=COLOR_TEXTO)),
                        ft.DataCell(content=ft.Text(str(l["PG"]), color=COLOR_VERDE)),
                        ft.DataCell(content=ft.Text(str(l["PE"]), color=COLOR_AMBAR)),
                        ft.DataCell(content=ft.Text(str(l["PP"]), color=COLOR_ROJO)),
                        ft.DataCell(content=ft.Text(str(l["GF"]), color=COLOR_SUBTEXTO)),
                        ft.DataCell(content=ft.Text(str(l["GC"]), color=COLOR_SUBTEXTO)),
                        ft.DataCell(content=ft.Text(f"{l['DG']:+d}", color=COLOR_SUBTEXTO)),
                        ft.DataCell(content=ft.Text(str(l["Pts"]), weight=ft.FontWeight.BOLD, color=COLOR_VERDE)),
                    ])
                )

            tabla_lideres_ui = ft.DataTable(
                columns=[
                    ft.DataColumn(label=ft.Text("Pos", weight=ft.FontWeight.BOLD, color=COLOR_SUBTEXTO)),
                    ft.DataColumn(label=ft.Text("Equipo", weight=ft.FontWeight.BOLD, color=COLOR_CELESTE)),
                    ft.DataColumn(label=ft.Text("Grupo", weight=ft.FontWeight.BOLD, color=COLOR_SUBTEXTO)),
                    ft.DataColumn(label=ft.Text("PJ", weight=ft.FontWeight.BOLD, color=COLOR_SUBTEXTO)),
                    ft.DataColumn(label=ft.Text("PG", weight=ft.FontWeight.BOLD, color=COLOR_VERDE)),
                    ft.DataColumn(label=ft.Text("PE", weight=ft.FontWeight.BOLD, color=COLOR_AMBAR)),
                    ft.DataColumn(label=ft.Text("PP", weight=ft.FontWeight.BOLD, color=COLOR_ROJO)),
                    ft.DataColumn(label=ft.Text("GF", weight=ft.FontWeight.BOLD, color=COLOR_SUBTEXTO)),
                    ft.DataColumn(label=ft.Text("GC", weight=ft.FontWeight.BOLD, color=COLOR_SUBTEXTO)),
                    ft.DataColumn(label=ft.Text("DG", weight=ft.FontWeight.BOLD, color=COLOR_SUBTEXTO)),
                    ft.DataColumn(label=ft.Text("Pts", weight=ft.FontWeight.BOLD, color=COLOR_VERDE)),
                ],
                rows=filas_lideres,
                bgcolor=COLOR_FONDO,
                border=ft.border.all(1, COLOR_BORDE),
                border_radius=8,
                column_spacing=14,
                heading_row_height=38,
                data_row_min_height=38,
                data_row_max_height=38,
            )

            componente_tabla_lideres = ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text("📊 Tabla Comparativa de Líderes (Pts > DG > GF)", weight=ft.FontWeight.BOLD, color=COLOR_CELESTE, size=14),
                        ft.Text(f"📅 {self.estado.get('fecha_filtro')}", color=COLOR_SUBTEXTO, size=12),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Row([tabla_lideres_ui], scroll=ft.ScrollMode.ALWAYS),
                ], spacing=8),
                padding=12,
                bgcolor=COLOR_TARJETA,
                border_radius=12,
                border=ft.border.all(1, COLOR_BORDE),
            )

            elementos_columna.extend([
                tarjeta_campeon,
                sw_partido_def,
                tarjeta_partido_final if con_partido_def else ft.Container(),
                componente_tabla_lideres,
            ])

        else:
            # VISTA DE GRUPO SELECCIONADO
            grupo_actual = grupo_sel_data["grupo"]
            partidos_actuales = grupo_sel_data["partidos"]
            tabla_actual = grupo_sel_data.get("tabla", [])
            es_grupo_principal = grupo_actual.get("es_principal", False)

            # Equipo contextual (el que administra o sigue el usuario)
            mi_equipo = (
                self.estado.get("equipo_seguido_invitado", "Real Dunalastair")
                if self.estado["es_invitado"]
                else (self.estado.get("equipo_activo") or "Real Dunalastair")
            )
            pertenece_a_grupo = (
                mi_equipo.lower() == grupo_actual.get("equipo_principal", "").lower()
                or mi_equipo.lower() in [eq.lower() for eq in grupo_actual.get("equipos", [])]
            )

            # Construir tabla de posiciones
            filas_tabla = []
            for pos, st in enumerate(tabla_actual, start=1):
                nombre_eq = st["equipo"]
                es_mi_equipo = (nombre_eq.lower() == mi_equipo.lower())
                color_nombre = COLOR_CELESTE if es_mi_equipo else COLOR_TEXTO
                peso_nombre = ft.FontWeight.BOLD if es_mi_equipo else ft.FontWeight.NORMAL

                filas_tabla.append(
                    ft.DataRow(cells=[
                        ft.DataCell(content=ft.Text(str(pos), color=COLOR_TEXTO)),
                        ft.DataCell(content=ft.Text(nombre_eq, weight=peso_nombre, color=color_nombre)),
                        ft.DataCell(content=ft.Text(str(st["PJ"]), color=COLOR_TEXTO)),
                        ft.DataCell(content=ft.Text(str(st["PG"]), color=COLOR_VERDE)),
                        ft.DataCell(content=ft.Text(str(st["PE"]), color=COLOR_AMBAR)),
                        ft.DataCell(content=ft.Text(str(st["PP"]), color=COLOR_ROJO)),
                        ft.DataCell(content=ft.Text(str(st["GF"]), color=COLOR_SUBTEXTO)),
                        ft.DataCell(content=ft.Text(str(st["GC"]), color=COLOR_SUBTEXTO)),
                        ft.DataCell(content=ft.Text(f"{st['DG']:+d}", color=COLOR_SUBTEXTO)),
                        ft.DataCell(content=ft.Text(str(st["Pts"]), weight=ft.FontWeight.BOLD, color=COLOR_VERDE)),
                    ])
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

            # Botón de eliminar grupo secundario si es admin
            def confirmar_eliminar_grupo_secundario(ev):
                if self.estado["es_invitado"]:
                    return
                def cerrar_dlg_el(e):
                    self.page.close(dlg_eliminar_g)
                def proc_eliminar_g(e):
                    GrupoService.eliminar_grupo_por_id(grupo_actual["id"], self.estado["es_invitado"])
                    self.page.close(dlg_eliminar_g)
                    self.estado["grupo_seleccionado_id"] = None
                    self.callbacks["cargar_grupo"]()
                    self.callbacks["refrescar_vistas"]()
                    self.page.update()

                dlg_eliminar_g = ft.AlertDialog(
                    title=ft.Text(f"¿Eliminar '{grupo_actual['nombre']}'?", color=COLOR_TEXTO),
                    content=ft.Text("Se eliminarán el grupo y sus 6 partidos de la base de datos."),
                    actions=[
                        ft.TextButton("Cancelar", on_click=cerrar_dlg_el),
                        ft.ElevatedButton("Eliminar Grupo", bgcolor=COLOR_ROJO, color=COLOR_TEXTO, on_click=proc_eliminar_g),
                    ],
                    bgcolor=COLOR_TARJETA,
                )
                self.page.open(dlg_eliminar_g)

            btn_eliminar_g_sec = ft.IconButton(
                icon=ft.Icons.DELETE_OUTLINE,
                icon_color=COLOR_ROJO,
                tooltip="Eliminar este Grupo",
                on_click=confirmar_eliminar_grupo_secundario,
                visible=(not self.estado["es_invitado"] and not es_grupo_principal),
            )

            componente_tabla = ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Row([
                            ft.Text(f"🏆 Tabla: {grupo_actual['nombre']}", weight=ft.FontWeight.BOLD, color=COLOR_CELESTE if pertenece_a_grupo else COLOR_TEXTO, size=15),
                            btn_eliminar_g_sec,
                        ], spacing=6),
                        ft.Text(f"📅 {grupo_actual['fecha']}", color=COLOR_SUBTEXTO, size=12),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Row([tabla_ui], scroll=ft.ScrollMode.ALWAYS),
                ], spacing=8),
                padding=12,
                bgcolor=COLOR_TARJETA,
                border_radius=12,
                border=ft.border.all(1, COLOR_CELESTE if pertenece_a_grupo else COLOR_BORDE),
            )

            # Partidos del grupo seleccionado
            partidos_mi_equipo_ui = []
            partidos_rivales_ui = []

            for p in partidos_actuales:
                es_activo = p["id"] == self.estado.get("partido_activo_id")

                def crear_handler_select(partido_obj):
                    return lambda e: (
                        self.callbacks["activar_partido_memoria"](partido_obj),
                        self.callbacks["guardar_partido"](),
                        self.callbacks["refrescar_vistas"](),
                        self.page.update(),
                    )

                es_partido_mi_equipo = (p["equipo_local"] == mi_equipo or p["equipo_visita"] == mi_equipo)

                if es_partido_mi_equipo:
                    rival_nombre = (
                        p["equipo_visita"]
                        if p["equipo_local"] == mi_equipo
                        else p["equipo_local"]
                    )

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
                                ft.Text(f"vs {rival_nombre}", weight=ft.FontWeight.BOLD, size=14, color=COLOR_TEXTO),
                                ft.Text(f"Marcador: {p['goles_local']} - {p['goles_visita']}", color=COLOR_VERDE if p["jugado"] else COLOR_SUBTEXTO, size=12),
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
                    # Partidos de rivales (grupo principal o grupo secundario completo)
                    ha_jugado = p.get("jugado", False) or p.get("goles_local", 0) > 0 or p.get("goles_visita", 0) > 0

                    if self.estado["es_invitado"]:
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
                                ft.Text(f"{p['equipo_local']}", weight=ft.FontWeight.BOLD, size=13, color=COLOR_TEXTO, expand=True, text_align=ft.TextAlign.RIGHT),
                                marcador_destacado,
                                ft.Text(f"{p['equipo_visita']}", weight=ft.FontWeight.BOLD, size=13, color=COLOR_TEXTO, expand=True, text_align=ft.TextAlign.LEFT),
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
                                self.callbacks["cargar_grupo"](),
                                self.callbacks["refrescar_vistas"](),
                                self.page.update(),
                            )

                        card_rival = ft.Container(
                            content=ft.Row([
                                ft.Text(f"{p['equipo_local']}", weight=ft.FontWeight.BOLD, size=12, color=COLOR_TEXTO, expand=True),
                                tf_g_loc,
                                ft.Text("-", color=COLOR_SUBTEXTO),
                                tf_g_vis,
                                ft.Text(f"{p['equipo_visita']}", weight=ft.FontWeight.BOLD, size=12, color=COLOR_TEXTO, expand=True, text_align=ft.TextAlign.RIGHT),
                                ft.IconButton(
                                    icon=ft.Icons.SAVE,
                                    icon_color=COLOR_CELESTE,
                                    tooltip="Guardar Marcador",
                                    on_click=crear_handler_guardar_rival(p["id"], tf_g_loc, tf_g_vis),
                                ),
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            padding=6,
                            bgcolor=COLOR_TARJETA,
                            border_radius=8,
                            border=ft.border.all(1, COLOR_BORDE),
                        )
                    partidos_rivales_ui.append(card_rival)

            elementos_columna.append(componente_tabla)

            if partidos_mi_equipo_ui:
                elementos_columna.extend([
                    ft.Row([
                        ft.Text(f"Partidos de {mi_equipo}", weight=ft.FontWeight.BOLD, color=COLOR_CELESTE),
                        ft.Row([
                            ft.ElevatedButton(
                                "👥 Delegados",
                                icon=ft.Icons.MANAGE_ACCOUNTS,
                                bgcolor=COLOR_TARJETA,
                                color=COLOR_VERDE,
                                visible=bool(self.estado.get("es_superadmin", False)),
                                on_click=lambda e: mostrar_dialogo_admin_usuarios(self.page, self.estado, self.callbacks),
                                tooltip="Gestionar Administradores de Equipo (SuperAdmin)",
                            ),
                            ft.ElevatedButton(
                                "🛠️ Mantenedor de Eventos",
                                icon=ft.Icons.EDIT_NOTE,
                                bgcolor=COLOR_TARJETA,
                                color=COLOR_CELESTE,
                                visible=not self.estado["es_invitado"],
                                on_click=lambda e: mostrar_dialogo_mantenedor_eventos(self.page, self.estado, self.callbacks),
                            ),
                        ], spacing=6),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Column(controls=partidos_mi_equipo_ui, spacing=8),
                ])
                if partidos_rivales_ui:
                    elementos_columna.extend([
                        ft.Text("Marcadores entre Rivales del Grupo (Combinatoria)", weight=ft.FontWeight.BOLD, color=COLOR_AMBAR),
                        ft.Column(controls=partidos_rivales_ui, spacing=6),
                    ])
            else:
                elementos_columna.extend([
                    ft.Row([
                        ft.Text(f"Partidos del {grupo_actual['nombre']} ({len(partidos_actuales)} Partidos)", weight=ft.FontWeight.BOLD, color=COLOR_CELESTE),
                        ft.ElevatedButton(
                            "👥 Delegados",
                            icon=ft.Icons.MANAGE_ACCOUNTS,
                            bgcolor=COLOR_TARJETA,
                            color=COLOR_VERDE,
                            visible=bool(self.estado.get("es_superadmin", False)),
                            on_click=lambda e: mostrar_dialogo_admin_usuarios(self.page, self.estado, self.callbacks),
                            tooltip="Gestionar Administradores de Equipo (SuperAdmin)",
                        ),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Column(controls=partidos_rivales_ui or [ft.Text("Sin partidos asignados", color=COLOR_SUBTEXTO)], spacing=6),
                ])

        # Formulario de Crear Grupo Principal (si no existe) o Resetear Día (para Admin)
        if not self.estado["es_invitado"]:
            tf_nombre_grupo = ft.TextField(
                label="Nombre del Grupo Principal",
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
                value=self.estado.get("equipo_activo") or "Real Dunalastair",
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

                # Filtrar rivales para evitar duplicar el equipo principal o entre ellos
                lista_rivales_raw = [r.strip() for r in rivales_str.split(",") if r.strip()]
                lista_rivales = []
                for r in lista_rivales_raw:
                    if r.lower() != eq_princ.lower() and r not in lista_rivales:
                        lista_rivales.append(r)

                if not lista_rivales:
                    texto_feedback_grupo.value = "⚠️ Ingresa al menos un equipo rival distinto al equipo principal."
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
                    title=ft.Text(f"¿Borrar todos los datos del día ({fecha_a_borrar})?", color=COLOR_TEXTO),
                    content=ft.Text(f"Se eliminarán todos los grupos, partidos y configuraciones del campeonato únicamente para la fecha {fecha_a_borrar}."),
                    actions=[
                        ft.TextButton("Cancelar", on_click=cerrar_dlg),
                        ft.ElevatedButton("Borrar Día", bgcolor=COLOR_ROJO, color=COLOR_TEXTO, on_click=procesar_reset),
                    ],
                    bgcolor=COLOR_TARJETA,
                )
                self.page.open(dialogo_reset)

            # Mostrar bloque de creación de grupo principal si aún no hay grupos creados
            if not grupos_dia:
                elementos_columna.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Text("1. Definir Cuadrangular Principal", weight=ft.FontWeight.BOLD, color=COLOR_CELESTE),
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
                            ]),
                            texto_feedback_grupo,
                        ], spacing=8),
                        padding=14,
                        bgcolor=COLOR_TARJETA,
                        border_radius=14,
                        border=ft.border.all(1, COLOR_BORDE),
                    )
                )
            else:
                elementos_columna.append(
                    ft.Container(
                        content=ft.Row([
                            ft.OutlinedButton(
                                "Resetear Día en BD",
                                icon=ft.Icons.DELETE_FOREVER,
                                icon_color=COLOR_ROJO,
                                style=ft.ButtonStyle(color=COLOR_ROJO, side=ft.BorderSide(1, COLOR_ROJO)),
                                on_click=confirmar_reset,
                            ),
                            ft.ElevatedButton(
                                "➕ Agregar Otro Grupo",
                                icon=ft.Icons.ADD,
                                bgcolor=COLOR_TARJETA,
                                color=COLOR_VERDE,
                                on_click=abrir_modal_nuevo_grupo,
                            ),
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        padding=10,
                    )
                )

        return ft.Column(elementos_columna, spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)
