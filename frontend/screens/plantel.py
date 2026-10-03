import flet as ft
from config.constants import (
    COLOR_TARJETA, COLOR_BORDE, COLOR_CELESTE, COLOR_CELESTE_BOTON,
    COLOR_TEXTO, COLOR_SUBTEXTO, COLOR_VERDE, COLOR_ROJO, COLOR_AMBAR
)
from backend.services.jugador_service import JugadorService
from backend.services.partido_service import PartidoService
from utils.time_utils import actualizar_minutos_jugadores


class PlantelScreen:
    def __init__(self, estado, page, callbacks):
        self.estado = estado
        self.page = page
        self.callbacks = callbacks

    def build(self):
        actualizar_minutos_jugadores(self.estado)
        jugadores = JugadorService.obtener_todos_ordenados()
        max_titulares = self.estado["config"]["jugadores_en_cancha"]
        es_bloqueado = self.estado["finalizado"] or self.estado["es_invitado"]

        tf_nuevo_num = ft.TextField(
            label="N°", width=60, border_color=COLOR_BORDE,
            focused_border_color=COLOR_CELESTE, border_radius=10, disabled=es_bloqueado,
        )
        tf_nuevo_nom = ft.TextField(
            label="Nombre Jugador", expand=True, border_color=COLOR_BORDE,
            focused_border_color=COLOR_CELESTE, border_radius=10, disabled=es_bloqueado,
        )
        tf_nuevo_puesto = ft.TextField(
            label="Puesto", width=110, border_color=COLOR_BORDE,
            focused_border_color=COLOR_CELESTE, border_radius=10, disabled=es_bloqueado,
        )
        texto_status_jugador = ft.Text("", size=11)

        def click_agregar_jugador(e):
            if self.estado["es_invitado"]:
                return
            if tf_nuevo_nom.value and tf_nuevo_num.value:
                res = JugadorService.agregar(
                    tf_nuevo_num.value.strip(),
                    tf_nuevo_nom.value.strip(),
                    tf_nuevo_puesto.value.strip() or "Jugador",
                    self.estado["es_invitado"]
                )
                if res:
                    texto_status_jugador.value = "✅ Agregado a la BD."
                    texto_status_jugador.color = COLOR_VERDE
                    self.callbacks["refrescar_vistas"]()
                else:
                    texto_status_jugador.value = "⚠️ Ya existe el jugador."
                    texto_status_jugador.color = COLOR_ROJO
                self.page.update()

        def pedir_confirmacion_borrado(nom_jugador):
            if self.estado["es_invitado"]:
                return
            fecha_filtro = (
                self.estado.get("fecha_filtro")
                or self.estado.get("config", {}).get("fecha")
            )
            minutos_totales = PartidoService.obtener_minutos_totales(
                partido_activo_id=self.estado.get("partido_activo_id"),
                minutos_actuales=self.estado.get("minutos_partido_actual", {}),
                fecha=fecha_filtro,
            )
            mins = minutos_totales.get(nom_jugador, 0) // 60

            def cerrar_dlg(ev):
                self.page.close(dlg_confirm)

            def procesar_borrado(ev):
                JugadorService.eliminar(nom_jugador, self.estado["es_invitado"])
                self.page.close(dlg_confirm)
                self.callbacks["refrescar_vistas"]()
                self.page.update()

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
            self.page.open(dlg_confirm)

        titulares_ui, suplentes_ui = [], []
        fecha_filtro = (
            self.estado.get("fecha_filtro")
            or self.estado.get("config", {}).get("fecha")
        )
        minutos_dia = PartidoService.obtener_minutos_totales(
            partido_activo_id=self.estado.get("partido_activo_id"),
            minutos_actuales=self.estado.get("minutos_partido_actual", {}),
            fecha=fecha_filtro,
        )

        for j in jugadores:
            nombre = j["nombre"]
            puesto = j["puesto"]
            num = j["numero"]

            es_titular = nombre in self.estado["titulares_seleccionados"]
            segs_hoy = minutos_dia.get(nombre, 0)
            mins_hoy = segs_hoy // 60

            def crear_on_change(nom):
                def on_change(e):
                    if self.estado["es_invitado"]:
                        return
                    actualizar_minutos_jugadores(self.estado)
                    limite = self.estado["config"]["jugadores_en_cancha"]
                    if e.control.value:
                        if len(self.estado["titulares_seleccionados"]) < limite:
                            if nom not in self.estado["titulares_seleccionados"]:
                                self.estado["titulares_seleccionados"].append(nom)
                        else:
                            e.control.value = False
                    else:
                        if nom in self.estado["titulares_seleccionados"]:
                            self.estado["titulares_seleccionados"].remove(nom)

                    self.callbacks["guardar_partido"]()
                    self.callbacks["refrescar_vistas"]()
                    self.page.update()
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
                disabled=self.estado["es_invitado"],
                on_click=crear_handler_borrar(nombre),
            )

            fila = ft.Container(
                content=ft.Row([
                    ft.Container(
                        content=ft.Text(f"#{num}", weight=ft.FontWeight.BOLD, size=11, color=COLOR_CELESTE),
                        bgcolor=COLOR_BORDE, padding=6, border_radius=8,
                    ),
                    ft.Column([
                        ft.Text(nombre, weight=ft.FontWeight.BOLD, size=13, color=COLOR_TEXTO),
                        ft.Text(f"{puesto} | {mins_hoy} min hoy", size=11, color=COLOR_SUBTEXTO),
                    ], expand=True, spacing=1),
                    switch_titular,
                    icon_borrar,
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                padding=4,
            )

            if es_titular:
                titulares_ui.append(fila)
            else:
                suplentes_ui.append(fila)

        elementos_plantel = [
            ft.Text("📋 Plantel de Jugadores", size=20, weight=ft.FontWeight.BOLD, color=COLOR_TEXTO),
            ft.Container(
                content=ft.Row([
                    ft.Text("Titulares en cancha:", color=COLOR_TEXTO, weight=ft.FontWeight.W_500),
                    ft.Container(
                        content=ft.Text(
                            f"{len(self.estado['titulares_seleccionados'])} / {max_titulares}",
                            color=COLOR_TEXTO, weight=ft.FontWeight.BOLD,
                        ),
                        bgcolor=COLOR_CELESTE_BOTON,
                        padding=ft.Padding(10, 4, 10, 4),
                        border_radius=12,
                    ),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                padding=12, bgcolor=COLOR_TARJETA, border_radius=12, border=ft.border.all(1, COLOR_BORDE),
            ),
        ]

        if not self.estado["es_invitado"]:
            elementos_plantel.append(
                ft.Container(
                    content=ft.Column([
                        ft.Text("Nuevo Jugador", size=12, weight=ft.FontWeight.BOLD, color=COLOR_CELESTE),
                        ft.Row([tf_nuevo_num, tf_nuevo_nom, tf_nuevo_puesto]),
                        ft.Row([
                            ft.ElevatedButton(
                                "Agregar", icon=ft.Icons.PERSON_ADD,
                                bgcolor=COLOR_CELESTE_BOTON, color=COLOR_TEXTO,
                                disabled=es_bloqueado, on_click=click_agregar_jugador,
                            ),
                            texto_status_jugador,
                        ]),
                    ], spacing=6),
                    padding=12, bgcolor=COLOR_TARJETA, border_radius=12, border=ft.border.all(1, COLOR_BORDE),
                )
            )

        elementos_plantel.extend([
            ft.Text(f"🟢 TITULARES EN CANCHA ({len(titulares_ui)})", weight=ft.FontWeight.BOLD, color=COLOR_VERDE, size=12),
            ft.Container(
                content=ft.Column(controls=titulares_ui or [ft.Text("Sin titulares", color=COLOR_SUBTEXTO)]),
                bgcolor=COLOR_TARJETA, padding=8, border_radius=12, border=ft.border.all(1, COLOR_VERDE),
            ),
            ft.Text(f"🟡 BANCA / SUPLENTES ({len(suplentes_ui)})", weight=ft.FontWeight.BOLD, color=COLOR_AMBAR, size=12),
            ft.Container(
                content=ft.Column(controls=suplentes_ui or [ft.Text("Sin suplentes", color=COLOR_SUBTEXTO)]),
                bgcolor=COLOR_TARJETA, padding=8, border_radius=12, border=ft.border.all(1, COLOR_BORDE),
            ),
        ])

        return ft.Column(elementos_plantel, scroll=ft.ScrollMode.AUTO, expand=True, spacing=8)
