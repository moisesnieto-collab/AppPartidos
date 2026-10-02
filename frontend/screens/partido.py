import flet as ft
from datetime import datetime, timezone
from config.constants import (
    COLOR_TARJETA, COLOR_BORDE, COLOR_CELESTE, COLOR_CELESTE_BOTON,
    COLOR_TEXTO, COLOR_SUBTEXTO, COLOR_VERDE, COLOR_ROJO, COLOR_AMBAR, EVENTOS_DEFECTO
)
from backend.services.jugador_service import JugadorService
from utils.time_utils import obtener_segundos_actuales, actualizar_minutos_jugadores, formatear_tiempo


class PartidoScreen:
    def __init__(self, estado, page, callbacks):
        self.estado = estado
        self.page = page
        self.callbacks = callbacks

    def actualizar_glosa(self):
        if self.estado["corriendo"]:
            self.texto_reloj.value = formatear_tiempo(obtener_segundos_actuales(self.estado))
            self.texto_reloj.color = COLOR_VERDE
            self.texto_alerta_cambio.value = "⏱️ Cronómetro en curso..."
            self.texto_alerta_cambio.color = COLOR_SUBTEXTO
        elif self.estado["finalizado"]:
            self.texto_reloj.value = formatear_tiempo(self.estado["segundos_acumulados"])
            self.texto_reloj.color = COLOR_ROJO
            self.texto_alerta_cambio.value = "🏁 Partido finalizado"
            self.texto_alerta_cambio.color = COLOR_ROJO
        else:
            self.texto_reloj.value = formatear_tiempo(self.estado["segundos_acumulados"])
            self.texto_reloj.color = COLOR_CELESTE
            alerta = self.estado.get("alerta_custom")
            if alerta:
                self.texto_alerta_cambio.value = alerta
                self.texto_alerta_cambio.color = COLOR_AMBAR
            else:
                self.texto_alerta_cambio.value = "⏸️ Cronómetro pausado"
                self.texto_alerta_cambio.color = COLOR_SUBTEXTO

    def build(self):
        self.texto_reloj = ft.Text("00:00", size=48, weight=ft.FontWeight.BOLD, color=COLOR_CELESTE)
        self.texto_alerta_cambio = ft.Text("", size=14, weight=ft.FontWeight.W_500)
        
        segs_actuales = obtener_segundos_actuales(self.estado)
        self.actualizar_glosa()
        jugadores = JugadorService.obtener_todos_ordenados()

        nombre_principal = self.estado["config"]["equipo_principal"]
        nombre_rival = self.estado["config"]["equipo_rival"]
        fecha_partido = self.estado["config"].get("fecha", datetime.now().strftime("%Y-%m-%d"))
        es_fin = self.estado["finalizado"]

        marcador_ui = ft.Container(
            content=ft.Column([
                ft.Text(f"📅 {fecha_partido}", size=11, color=COLOR_SUBTEXTO),
                ft.Row([
                    ft.Column([
                        ft.Text(nombre_principal, weight=ft.FontWeight.BOLD, size=15, color=COLOR_TEXTO),
                        ft.Text(f"{self.estado['goles_local']}", size=42, weight=ft.FontWeight.BOLD, color=COLOR_CELESTE),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, expand=True),
                    ft.Text("VS", size=18, weight=ft.FontWeight.BOLD, color=COLOR_SUBTEXTO),
                    ft.Column([
                        ft.Text(nombre_rival, weight=ft.FontWeight.BOLD, size=15, color=COLOR_TEXTO, overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Text(f"{self.estado['goles_rival']}", size=42, weight=ft.FontWeight.BOLD, color=COLOR_ROJO),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, expand=True),
                ], alignment=ft.MainAxisAlignment.CENTER),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=COLOR_TARJETA, padding=14, border_radius=14, border=ft.border.all(1, COLOR_BORDE),
        )

        def iniciar_reloj(e):
            if self.estado["es_invitado"] or self.estado["finalizado"]:
                return
            if not self.estado["corriendo"]:
                self.estado["corriendo"] = True
                self.estado["segs_al_iniciar"] = self.estado["segundos_acumulados"]
                self.estado["hora_inicio"] = datetime.now(timezone.utc).isoformat()
                self.estado["ultimo_segundo_procesado"] = self.estado["segundos_acumulados"]
                self.estado["alerta_custom"] = None
                self.actualizar_glosa()
                self.callbacks["guardar_partido"]()
                self.callbacks["refrescar_vistas"]()
                self.page.update()

        def pausar_reloj(e):
            if self.estado["es_invitado"] or self.estado["finalizado"]:
                return
            if self.estado["corriendo"]:
                segs = obtener_segundos_actuales(self.estado)
                actualizar_minutos_jugadores(self.estado, segs)
                self.estado["segundos_acumulados"] = segs
                self.estado["segundos"] = segs
                self.estado["hora_inicio"] = None
                self.estado["corriendo"] = False
                self.estado["alerta_custom"] = None
                self.actualizar_glosa()
                self.callbacks["guardar_partido"]()
                self.callbacks["refrescar_vistas"]()
                self.page.update()

        def alternar_finalizacion(e):
            if self.estado["es_invitado"]:
                return
            if self.estado["corriendo"]:
                pausar_reloj(None)

            self.estado["finalizado"] = not self.estado["finalizado"]
            self.estado["alerta_custom"] = None
            self.actualizar_glosa()

            self.callbacks["guardar_partido"]()
            self.callbacks["refrescar_vistas"]()
            self.page.update()

        # Sistema de eventos
        dd_evento = ft.Dropdown(
            label="Evento",
            options=[ft.dropdown.Option(ev) for ev in EVENTOS_DEFECTO],
            expand=True,
            border_color=COLOR_BORDE,
            focused_border_color=COLOR_CELESTE,
            border_radius=10,
            disabled=es_fin or self.estado["es_invitado"],
        )
        opciones_titulares = [
            ft.dropdown.Option(nom) for nom in self.estado["titulares_seleccionados"]
        ]
        dd_jugador_titular = ft.Dropdown(
            label="Jugador Titular",
            options=opciones_titulares,
            expand=True,
            border_color=COLOR_BORDE,
            focused_border_color=COLOR_CELESTE,
            border_radius=10,
            disabled=es_fin or self.estado["es_invitado"],
        )

        suplentes_actuales = [
            j["nombre"]
            for j in jugadores
            if j["nombre"] not in self.estado["titulares_seleccionados"]
        ]
        dd_suplente_entra = ft.Dropdown(
            label="Entra (Suplente)",
            options=[ft.dropdown.Option(nom) for nom in suplentes_actuales],
            expand=True,
            visible=False,
            border_color=COLOR_BORDE,
            focused_border_color=COLOR_CELESTE,
            border_radius=10,
            disabled=es_fin or self.estado["es_invitado"],
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
            self.page.update()

        dd_evento.on_change = al_cambiar_dropdown_evento

        def registrar_evento_click(e):
            if self.estado["es_invitado"] or self.estado["finalizado"]:
                return

            tipo_evento = dd_evento.value
            jugador_sel = dd_jugador_titular.value

            if not tipo_evento or not jugador_sel:
                texto_status_evento.value = "⚠️ Selecciona evento y jugador."
                texto_status_evento.color = COLOR_ROJO
                self.page.update()
                return

            minuto_actual = f"{obtener_segundos_actuales(self.estado) // 60:02d}'"

            if tipo_evento == "Gol":
                if jugador_sel == "⚡ Equipo Rival":
                    self.estado["goles_rival"] += 1
                    desc_evento = f"Gol de {self.estado['config']['equipo_rival']}"
                else:
                    self.estado["goles_local"] += 1
                    desc_evento = f"Gol de {jugador_sel}"

                self.estado["eventos_registrados"].append({
                    "minuto": minuto_actual,
                    "evento": "Gol",
                    "jugador": desc_evento,
                })

            elif tipo_evento == "Cambio":
                jugador_entra = dd_suplente_entra.value
                if not jugador_entra:
                    texto_status_evento.value = "⚠️ Selecciona suplente que entra."
                    texto_status_evento.color = COLOR_ROJO
                    self.page.update()
                    return

                actualizar_minutos_jugadores(self.estado)

                if jugador_sel in self.estado["titulares_seleccionados"]:
                    self.estado["titulares_seleccionados"].remove(jugador_sel)
                if jugador_entra not in self.estado["titulares_seleccionados"]:
                    self.estado["titulares_seleccionados"].append(jugador_entra)

                desc_evento = f"Sale {jugador_sel} ➔ Entra {jugador_entra}"
                self.estado["eventos_registrados"].append({
                    "minuto": minuto_actual,
                    "evento": "Cambio",
                    "jugador": desc_evento,
                })

            else:
                self.estado["eventos_registrados"].append({
                    "minuto": minuto_actual,
                    "evento": tipo_evento,
                    "jugador": jugador_sel,
                })

            self.callbacks["guardar_partido"]()
            self.callbacks["refrescar_vistas"]()
            self.page.update()

        def crear_handler_eliminar_evento(ev_obj):
            def handler(e):
                if self.estado["es_invitado"]:
                    return
                if ev_obj in self.estado["eventos_registrados"]:
                    self.estado["eventos_registrados"].remove(ev_obj)
                    if ev_obj.get("evento") == "Gol":
                        if "Equipo Rival" in ev_obj.get("jugador", "") or self.estado['config']['equipo_rival'] in ev_obj.get("jugador", ""):
                            self.estado["goles_rival"] = max(0, self.estado["goles_rival"] - 1)
                        else:
                            self.estado["goles_local"] = max(0, self.estado["goles_local"] - 1)
                    self.callbacks["guardar_partido"]()
                    self.callbacks["refrescar_vistas"]()
                    self.page.update()

            return handler

        eventos_ui = []
        if self.estado["eventos_registrados"]:
            for ev in reversed(self.estado["eventos_registrados"]):
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
                    content=ft.Row([
                        ft.Row([
                            ft.Icon(icono, color=color_ev, size=18),
                            ft.Text(f"[{minuto}]", weight=ft.FontWeight.BOLD, color=COLOR_CELESTE, size=12),
                            ft.Text(f"{tipo}: {jug}", color=COLOR_TEXTO, size=13, weight=ft.FontWeight.W_500),
                        ], spacing=8),
                        ft.IconButton(
                            icon=ft.Icons.DELETE_OUTLINED,
                            icon_color=COLOR_ROJO,
                            icon_size=16,
                            disabled=es_fin or self.estado["es_invitado"],
                            tooltip="Eliminar evento",
                            on_click=crear_handler_eliminar_evento(ev)
                        )
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
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
            ft.Row([
                ft.Text(
                    "⏱️ Control del Partido",
                    size=18,
                    weight=ft.FontWeight.BOLD,
                    color=COLOR_TEXTO,
                ),
                ft.OutlinedButton(
                    "Reabrir Partido" if es_fin else "Finalizar Partido",
                    icon=ft.Icons.LOCK_OPEN if es_fin else ft.Icons.LOCK,
                    visible=not self.estado["es_invitado"],
                    style=ft.ButtonStyle(
                        color=COLOR_VERDE if es_fin else COLOR_ROJO,
                        side=ft.BorderSide(1, COLOR_VERDE if es_fin else COLOR_ROJO),
                    ),
                    on_click=alternar_finalizacion,
                ),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            marcador_ui,
            ft.Container(content=self.texto_reloj, alignment=ft.Alignment(0, 0)),
            ft.Container(content=self.texto_alerta_cambio, alignment=ft.Alignment(0, 0)),
        ]

        if not self.estado["es_invitado"]:
            elementos_partido.append(
                ft.Row([
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
                ], alignment=ft.MainAxisAlignment.CENTER)
            )

        elementos_partido.append(ft.Divider(height=5, color=COLOR_BORDE))

        if not self.estado["es_invitado"]:
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
