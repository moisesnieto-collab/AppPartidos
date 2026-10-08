import flet as ft
from typing import Optional, Dict, Any, List
from config.constants import (
    COLOR_FONDO, COLOR_TARJETA, COLOR_BORDE, COLOR_CELESTE,
    COLOR_CELESTE_BOTON, COLOR_TEXTO, COLOR_SUBTEXTO, COLOR_VERDE, COLOR_ROJO, COLOR_AMBAR,
    EVENTOS_DEFECTO
)
from backend.services.jugador_service import JugadorService
from backend.services.partido_service import PartidoService
from backend.models.partido import Partido
from utils.time_utils import ordenar_eventos


def mostrar_dialogo_mantenedor_eventos(
    page: ft.Page,
    estado: Dict[str, Any],
    callbacks: Dict[str, Any],
    partido_id_inicial: Optional[int] = None,
):
    if estado.get("es_invitado", True):
        return

    es_superadmin = estado.get("es_superadmin", False)
    mi_equipo = estado.get("equipo_activo") or "Real Dunalastair"

    partidos_todos = estado.get("partidos_grupo", [])
    if es_superadmin:
        partidos = partidos_todos
    else:
        partidos = [
            p for p in partidos_todos
            if p.get("equipo_local") == mi_equipo or p.get("equipo_visita") == mi_equipo
        ]

    if not partidos:
        page.open(
            ft.SnackBar(
                content=ft.Text("⚠️ No hay partidos disponibles para tu equipo en este grupo."),
                bgcolor=COLOR_AMBAR,
                open=True,
            )
        )
        return

    # Determinar partido seleccionado por defecto
    partido_seleccionado = None
    if partido_id_inicial:
        partido_seleccionado = next((p for p in partidos if p["id"] == partido_id_inicial), None)
    if not partido_seleccionado:
        if estado.get("partido_activo_id"):
            partido_seleccionado = next(
                (p for p in partidos if p["id"] == estado["partido_activo_id"]), None
            )
    if not partido_seleccionado:
        partido_seleccionado = partidos[0]

    # Cargar datos del partido actual en variables locales de edición
    current_partido_id = partido_seleccionado["id"]
    partido_obj = PartidoService.obtener_partido_por_id(current_partido_id)
    if not partido_obj:
        partido_obj = Partido.from_dict(partido_seleccionado)

    eventos_locales: List[Dict[str, Any]] = ordenar_eventos([dict(ev) for ev in partido_obj.eventos])
    goles_local_val = [partido_obj.goles_local]
    goles_visita_val = [partido_obj.goles_visita]
    finalizado_val = [partido_obj.finalizado]

    def obtener_titulares_equipo_local(partido: Partido) -> List[str]:
        eq_local = partido.equipo_local
        titulares_data = partido.titulares
        if isinstance(titulares_data, dict):
            return [nom for nom in titulares_data.get(eq_local, []) if nom and str(nom).strip()]
        elif isinstance(titulares_data, list):
            jugadores_eq = [
                j["nombre"]
                for j in JugadorService.obtener_todos_ordenados(equipo=eq_local, fecha=partido.fecha)
            ]
            return [nom for nom in titulares_data if nom in jugadores_eq and str(nom).strip()]
        return []

    # Contenedores dinámicos
    lista_eventos_col = ft.Column(spacing=6, scroll=ft.ScrollMode.ADAPTIVE)
    texto_feedback = ft.Text("", size=12)

    # Campos de goles
    tf_goles_local = ft.TextField(
        value=str(goles_local_val[0]),
        label=f"Goles {partido_obj.equipo_local}",
        width=110,
        text_align=ft.TextAlign.CENTER,
        keyboard_type=ft.KeyboardType.NUMBER,
        border_color=COLOR_BORDE,
        focused_border_color=COLOR_CELESTE,
        border_radius=8,
        read_only=not es_superadmin and partido_obj.equipo_local != mi_equipo,
    )
    tf_goles_visita = ft.TextField(
        value=str(goles_visita_val[0]),
        label=f"Goles {partido_obj.equipo_visita}",
        width=110,
        text_align=ft.TextAlign.CENTER,
        keyboard_type=ft.KeyboardType.NUMBER,
        border_color=COLOR_BORDE,
        focused_border_color=COLOR_CELESTE,
        border_radius=8,
        read_only=not es_superadmin and partido_obj.equipo_visita != mi_equipo,
    )
    cb_finalizado = ft.Checkbox(
        label="Partido Finalizado",
        value=finalizado_val[0],
        fill_color=COLOR_CELESTE,
        check_color=COLOR_FONDO,
        disabled=not es_superadmin and partido_obj.equipo_local != mi_equipo,
    )

    # Formulario para nuevo evento
    tf_minuto = ft.TextField(
        label="Minuto",
        hint_text="ej: 12'",
        width=85,
        border_color=COLOR_BORDE,
        focused_border_color=COLOR_CELESTE,
        border_radius=8,
        dense=True,
    )
    dd_tipo_evento = ft.Dropdown(
        label="Tipo Evento",
        options=[ft.dropdown.Option(ev) for ev in EVENTOS_DEFECTO],
        value="Gol",
        width=150,
        border_color=COLOR_BORDE,
        focused_border_color=COLOR_CELESTE,
        border_radius=8,
        dense=True,
    )

    dd_jugador = ft.Dropdown(
        label="Titular",
        options=[],
        value=None,
        expand=True,
        border_color=COLOR_BORDE,
        focused_border_color=COLOR_CELESTE,
        border_radius=8,
        dense=True,
    )

    dd_suplente_entra = ft.Dropdown(
        label="Entra suplente",
        options=[],
        value=None,
        expand=True,
        border_color=COLOR_BORDE,
        focused_border_color=COLOR_CELESTE,
        border_radius=8,
        visible=False,
        dense=True,
    )

    def actualizar_dropdown_jugadores():
        nombres_titulares = obtener_titulares_equipo_local(partido_obj)
        if nombres_titulares:
            dd_jugador.options = [ft.dropdown.Option(nom) for nom in nombres_titulares]
            dd_jugador.value = nombres_titulares[0]
            dd_jugador.label = f"Titulares ({partido_obj.equipo_local})"
            dd_jugador.disabled = False
            dd_suplente_entra.options = [ft.dropdown.Option(nom) for nom in nombres_titulares]
            dd_suplente_entra.value = nombres_titulares[1] if len(nombres_titulares) > 1 else None
            dd_suplente_entra.disabled = False
        else:
            dd_jugador.options = []
            dd_jugador.value = None
            dd_jugador.label = f"Sin titulares ({partido_obj.equipo_local})"
            dd_jugador.disabled = True
            dd_suplente_entra.options = []
            dd_suplente_entra.value = None
            dd_suplente_entra.disabled = True

    actualizar_dropdown_jugadores()

    def on_tipo_evento_change(e):
        dd_suplente_entra.visible = (dd_tipo_evento.value == "Cambio")
        page.update()

    dd_tipo_evento.on_change = on_tipo_evento_change

    # Dropdown selector de partido
    def generar_opciones_partidos():
        opts = []
        for p in partidos:
            tag_prin = " [Principal]" if p.get("es_principal") else " [Rival]"
            tag_fin = " 🏁" if p.get("finalizado") else ""
            txt = f"{p['equipo_local']} vs {p['equipo_visita']} ({p['goles_local']}-{p['goles_visita']}){tag_prin}{tag_fin}"
            opts.append(ft.dropdown.Option(key=str(p["id"]), text=txt))
        return opts

    dd_selector_partido = ft.Dropdown(
        label="Seleccionar Partido a Mantener",
        options=generar_opciones_partidos(),
        value=str(current_partido_id),
        expand=True,
        border_color=COLOR_BORDE,
        focused_border_color=COLOR_CELESTE,
        border_radius=8,
    )

    texto_equipos_header = ft.Text(
        f"{partido_obj.equipo_local}  vs  {partido_obj.equipo_visita}",
        size=15,
        weight=ft.FontWeight.BOLD,
        color=COLOR_CELESTE,
    )

    def refrescar_lista_eventos_ui():
        lista_eventos_col.controls.clear()
        if not eventos_locales:
            lista_eventos_col.controls.append(
                ft.Container(
                    content=ft.Text("No hay eventos registrados en este partido.", color=COLOR_SUBTEXTO, size=12),
                    padding=10,
                )
            )
        else:
            for idx, ev in enumerate(reversed(eventos_locales)):
                # idx_real es el índice en eventos_locales
                idx_real = len(eventos_locales) - 1 - idx
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

                eq_ev = ev.get("equipo")
                es_gol_generico = (tipo == "Gol" and ("Gol Rival" in jug or "Gol de " in jug or "⚡" in jug))
                puede_editar_borrar = (
                    es_superadmin or
                    (eq_ev == mi_equipo or (not eq_ev and mi_equipo in jug)) or
                    es_gol_generico
                )

                def crear_handler_borrar(indice_a_borrar):
                    def handler_borrar(ev_btn):
                        if not puede_editar_borrar:
                            texto_feedback.value = "⚠️ Solo el DT del club autor o SuperAdmin puede eliminar este evento."
                            texto_feedback.color = COLOR_ROJO
                            page.update()
                            return
                        ev_eliminado = eventos_locales.pop(indice_a_borrar)
                        # Si era gol, consultar si se descuenta gol
                        if ev_eliminado.get("evento") == "Gol":
                            jug_ev = ev_eliminado.get("jugador", "")
                            eq_del_ev = ev_eliminado.get("equipo")
                            if eq_del_ev == partido_obj.equipo_local or (not eq_del_ev and partido_obj.equipo_local in jug_ev):
                                goles_local_val[0] = max(0, int(tf_goles_local.value or 0) - 1)
                                tf_goles_local.value = str(goles_local_val[0])
                            elif eq_del_ev == partido_obj.equipo_visita or (not eq_del_ev and partido_obj.equipo_visita in jug_ev):
                                goles_visita_val[0] = max(0, int(tf_goles_visita.value or 0) - 1)
                                tf_goles_visita.value = str(goles_visita_val[0])
                            else:
                                if partido_obj.equipo_local == mi_equipo:
                                    goles_local_val[0] = max(0, int(tf_goles_local.value or 0) - 1)
                                    tf_goles_local.value = str(goles_local_val[0])
                                else:
                                    goles_visita_val[0] = max(0, int(tf_goles_visita.value or 0) - 1)
                                    tf_goles_visita.value = str(goles_visita_val[0])

                        texto_feedback.value = f"🗑️ Evento '{tipo}: {jug}' eliminado."
                        texto_feedback.color = COLOR_AMBAR
                        refrescar_lista_eventos_ui()
                        page.update()
                    return handler_borrar

                def crear_handler_editar(indice_a_editar):
                    def handler_editar(ev_btn):
                        if not puede_editar_borrar:
                            texto_feedback.value = "⚠️ Solo el DT del club autor o SuperAdmin puede editar este evento."
                            texto_feedback.color = COLOR_ROJO
                            page.update()
                            return
                        ev_actual = eventos_locales[indice_a_editar]
                        tf_edit_min = ft.TextField(
                            value=ev_actual.get("minuto", ""),
                            label="Minuto",
                            width=100,
                            border_color=COLOR_BORDE,
                        )
                        tf_edit_desc = ft.TextField(
                            value=ev_actual.get("jugador", ""),
                            label="Detalle / Jugador",
                            expand=True,
                            border_color=COLOR_BORDE,
                        )

                        def guardar_edicion(e_save):
                            min_val = tf_edit_min.value.strip() or "00'"
                            if not min_val.endswith("'") and ":" not in min_val:
                                min_val = f"{min_val}'"
                            ev_actual["minuto"] = min_val
                            ev_actual["jugador"] = tf_edit_desc.value.strip()
                            eventos_locales[:] = ordenar_eventos(eventos_locales)
                            page.close(dlg_edit)
                            refrescar_lista_eventos_ui()
                            page.update()

                        def cerrar_edicion(e_close):
                            page.close(dlg_edit)

                        dlg_edit = ft.AlertDialog(
                            title=ft.Text(f"Editar Evento ({ev_actual.get('evento')})", color=COLOR_TEXTO),
                            content=ft.Row([tf_edit_min, tf_edit_desc], spacing=10),
                            actions=[
                                ft.TextButton("Cancelar", on_click=cerrar_edicion),
                                ft.ElevatedButton("Actualizar", bgcolor=COLOR_CELESTE_BOTON, color=COLOR_TEXTO, on_click=guardar_edicion),
                            ],
                            bgcolor=COLOR_TARJETA,
                        )
                        page.open(dlg_edit)
                    return handler_editar

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
                                expand=True,
                            ),
                            ft.Row(
                                [
                                    ft.IconButton(
                                        icon=ft.Icons.EDIT_OUTLINED,
                                        icon_color=COLOR_CELESTE if puede_editar_borrar else COLOR_BORDE,
                                        icon_size=16,
                                        disabled=not puede_editar_borrar,
                                        tooltip="Editar minuto/detalle" if puede_editar_borrar else f"Evento de {eq_ev or 'rival'}",
                                        on_click=crear_handler_editar(idx_real),
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.DELETE_OUTLINED,
                                        icon_color=COLOR_ROJO if puede_editar_borrar else COLOR_BORDE,
                                        icon_size=16,
                                        disabled=not puede_editar_borrar,
                                        tooltip="Eliminar evento" if puede_editar_borrar else f"Evento de {eq_ev or 'rival'}",
                                        on_click=crear_handler_borrar(idx_real),
                                    ),
                                ],
                                spacing=0,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    padding=ft.Padding(8, 4, 8, 4),
                    bgcolor=COLOR_FONDO,
                    border_radius=8,
                    border=ft.border.all(1, COLOR_BORDE),
                )
                lista_eventos_col.controls.append(card_ev)

    def cambiar_partido_seleccionado(e):
        nonlocal partido_obj, current_partido_id
        try:
            nuevo_id = int(dd_selector_partido.value)
        except (ValueError, TypeError):
            return

        current_partido_id = nuevo_id
        p_encontrado = PartidoService.obtener_partido_por_id(nuevo_id)
        if not p_encontrado:
            p_dict = next((p for p in partidos if p["id"] == nuevo_id), None)
            if p_dict:
                p_encontrado = Partido.from_dict(p_dict)

        if p_encontrado:
            partido_obj = p_encontrado
            eventos_locales.clear()
            eventos_locales.extend(ordenar_eventos([dict(ev) for ev in partido_obj.eventos]))
            goles_local_val[0] = partido_obj.goles_local
            goles_visita_val[0] = partido_obj.goles_visita
            finalizado_val[0] = partido_obj.finalizado

            tf_goles_local.value = str(goles_local_val[0])
            tf_goles_visita.value = str(goles_visita_val[0])
            cb_finalizado.value = finalizado_val[0]
            texto_equipos_header.value = f"{partido_obj.equipo_local}  vs  {partido_obj.equipo_visita}"
            texto_feedback.value = ""
            actualizar_dropdown_jugadores()
            refrescar_lista_eventos_ui()
            page.update()

    dd_selector_partido.on_change = cambiar_partido_seleccionado

    def agregar_evento_nuevo(e):
        tipo_ev = dd_tipo_evento.value
        jug_sel = dd_jugador.value
        min_txt = tf_minuto.value.strip()

        if not min_txt:
            min_txt = "00'"
        elif not min_txt.endswith("'"):
            min_txt = f"{min_txt}'"

        if not tipo_ev or not jug_sel:
            texto_feedback.value = f"⚠️ No hay jugadores titulares definidos para {partido_obj.equipo_local}." if not jug_sel else "⚠️ Debes seleccionar tipo de evento y jugador."
            texto_feedback.color = COLOR_ROJO
            page.update()
            return

        eq_ev = partido_obj.equipo_local
        if tipo_ev == "Gol":
            desc_ev = f"Gol de {jug_sel} ({eq_ev})"
            goles_local_val[0] = int(tf_goles_local.value or 0) + 1
            tf_goles_local.value = str(goles_local_val[0])

            eventos_locales.append({
                "minuto": min_txt,
                "evento": "Gol",
                "jugador": desc_ev,
                "equipo": eq_ev,
            })
        elif tipo_ev == "Cambio":
            suplente = dd_suplente_entra.value
            if not suplente:
                texto_feedback.value = "⚠️ Debes seleccionar el suplente que entra."
                texto_feedback.color = COLOR_ROJO
                page.update()
                return
            desc_ev = f"Sale {jug_sel} ➔ Entra {suplente}"
            eventos_locales.append({
                "minuto": min_txt,
                "evento": "Cambio",
                "jugador": desc_ev,
                "equipo": eq_ev,
            })
        else:
            eventos_locales.append({
                "minuto": min_txt,
                "evento": tipo_ev,
                "jugador": f"{jug_sel} ({eq_ev})",
                "equipo": eq_ev,
            })

        tf_minuto.value = ""
        texto_feedback.value = f"✅ Evento agregado: {tipo_ev}"
        texto_feedback.color = COLOR_VERDE
        eventos_locales[:] = ordenar_eventos(eventos_locales)
        refrescar_lista_eventos_ui()
        page.update()

    def guardar_mantencion(e):
        try:
            g_loc = int(tf_goles_local.value.strip())
            g_vis = int(tf_goles_visita.value.strip())
        except ValueError:
            texto_feedback.value = "❌ Los goles deben ser valores numéricos."
            texto_feedback.color = COLOR_ROJO
            page.update()
            return

        is_fin = bool(cb_finalizado.value)
        eventos_ordenados = ordenar_eventos(eventos_locales)

        # Guardar en BD
        exito = PartidoService.actualizar_eventos_y_marcador(
            partido_id=current_partido_id,
            eventos=eventos_ordenados,
            goles_local=g_loc,
            goles_visita=g_vis,
            finalizado=is_fin,
        )

        if not exito:
            texto_feedback.value = "❌ Error al guardar en base de datos."
            texto_feedback.color = COLOR_ROJO
            page.update()
            return

        # Si el partido editado es el partido activo en memoria, sincronizar estado en memoria
        if estado.get("partido_activo_id") == current_partido_id:
            estado["eventos_registrados"] = [dict(ev) for ev in eventos_ordenados]
            eq_princ = estado.get("config", {}).get("equipo_principal", "Real Dunalastair")
            es_local = partido_obj.equipo_local == eq_princ
            estado["goles_local"] = g_loc if es_local else g_vis
            estado["goles_rival"] = g_vis if es_local else g_loc
            estado["finalizado"] = is_fin

        callbacks["cargar_grupo"]()
        callbacks["refrescar_vistas"]()

        page.close(dialogo)
        page.open(
            ft.SnackBar(
                content=ft.Text(f"✅ Mantención de eventos guardada para {partido_obj.equipo_local} vs {partido_obj.equipo_visita}"),
                bgcolor=COLOR_VERDE,
                open=True,
            )
        )

    def cerrar_dialogo(e):
        page.close(dialogo)

    refrescar_lista_eventos_ui()

    dialogo = ft.AlertDialog(
        title=ft.Row(
            [
                ft.Icon(ft.Icons.EDIT_NOTE, color=COLOR_CELESTE, size=24),
                ft.Text("Mantenedor de Eventos de Partidos", color=COLOR_TEXTO, size=17, weight=ft.FontWeight.BOLD),
            ],
            spacing=8,
        ),
        content=ft.Container(
            content=ft.Column(
                [
                    ft.Text("Selecciona el partido y realiza ajustes a eventos y marcadores:", color=COLOR_SUBTEXTO, size=12),
                    ft.Row([dd_selector_partido]),
                    ft.Divider(color=COLOR_BORDE),
                    ft.Row(
                        [
                            texto_equipos_header,
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    ft.Row(
                        [
                            tf_goles_local,
                            ft.Text("VS", weight=ft.FontWeight.BOLD, color=COLOR_SUBTEXTO),
                            tf_goles_visita,
                            cb_finalizado,
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=12,
                    ),
                    ft.Divider(color=COLOR_BORDE),
                    ft.Text("➕ Registrar / Agregar Nuevo Evento:", weight=ft.FontWeight.BOLD, color=COLOR_CELESTE, size=13),
                    ft.Row(
                        [
                            tf_minuto,
                            dd_tipo_evento,
                            dd_jugador,
                        ],
                        spacing=8,
                    ),
                    ft.Row([dd_suplente_entra], spacing=8),
                    ft.Row(
                        [
                            ft.ElevatedButton(
                                "Agregar Evento",
                                icon=ft.Icons.ADD_CIRCLE,
                                bgcolor=COLOR_CELESTE_BOTON,
                                color=COLOR_TEXTO,
                                on_click=agregar_evento_nuevo,
                            ),
                            texto_feedback,
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Divider(color=COLOR_BORDE),
                    ft.Text("📋 Eventos Registrados en el Partido:", weight=ft.FontWeight.BOLD, color=COLOR_TEXTO, size=13),
                    ft.Container(
                        content=lista_eventos_col,
                        height=200,
                        padding=6,
                        bgcolor=COLOR_TARJETA,
                        border_radius=8,
                        border=ft.border.all(1, COLOR_BORDE),
                    ),
                ],
                tight=True,
                spacing=8,
                scroll=ft.ScrollMode.ADAPTIVE,
            ),
            width=560,
        ),
        actions=[
            ft.TextButton("Cerrar", on_click=cerrar_dialogo),
            ft.ElevatedButton(
                "💾 Guardar Mantención",
                icon=ft.Icons.SAVE,
                bgcolor=COLOR_VERDE,
                color=COLOR_FONDO,
                on_click=guardar_mantencion,
            ),
        ],
        bgcolor=COLOR_TARJETA,
        modal=True,
    )

    page.open(dialogo)
