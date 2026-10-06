from datetime import datetime
import flet as ft
import pandas as pd
from config.constants import COLOR_TARJETA, COLOR_BORDE, COLOR_CELESTE, COLOR_CELESTE_BOTON, COLOR_TEXTO, COLOR_SUBTEXTO, COLOR_VERDE
from backend.services.jugador_service import JugadorService
from backend.services.partido_service import PartidoService
from utils.time_utils import actualizar_minutos_jugadores


class EstadisticasScreen:
    def __init__(self, estado, page, callbacks):
        self.estado = estado
        self.page = page
        self.callbacks = callbacks

    def build(self):
        actualizar_minutos_jugadores(self.estado)
        equipo_activo = self.estado.get("equipo_activo") or self.estado.get("config", {}).get("equipo_principal", "Real Dunalastair")
        fecha_filtro = (
            self.estado.get("fecha_filtro")
            or self.estado.get("config", {}).get("fecha")
            or datetime.now().strftime("%Y-%m-%d")
        )
        jugadores = JugadorService.obtener_todos_ordenados(equipo=equipo_activo, fecha=fecha_filtro)
        minutos_acumulados_bd = PartidoService.obtener_minutos_totales(
            partido_activo_id=self.estado.get("partido_activo_id"),
            minutos_actuales=self.estado.get("minutos_partido_actual", {}),
            fecha=fecha_filtro,
        )
        stats_ui = []
        texto_export = ft.Text("", color=COLOR_VERDE)

        def click_exportar(e):
            try:
                datos_jugadores = []
                for j in jugadores:
                    nom = j["nombre"]
                    segs = minutos_acumulados_bd.get(nom, 0)
                    datos_jugadores.append({
                        "Fecha": fecha_filtro,
                        "Equipo": equipo_activo,
                        "Número": j["numero"],
                        "Jugador": nom,
                        "Puesto": j["puesto"],
                        "Minutos Acumulados Día": segs // 60,
                    })
                df = pd.DataFrame(datos_jugadores)
                nombre_archivo = f"Reporte_Minutos_{equipo_activo.replace(' ', '_')}_{fecha_filtro}.xlsx"
                df.to_excel(nombre_archivo, index=False)
                texto_export.value = f"✅ '{nombre_archivo}' guardado con éxito."
            except Exception as ex:
                texto_export.value = f"❌ Error exportando: {ex}"
            self.page.update()

        selector_equipo_superadmin = None
        if self.estado.get("es_superadmin", False):
            equipos_dia = set()
            for g in self.estado.get("grupos_dia", []):
                grupo_obj = g.get("grupo", {})
                if grupo_obj.get("equipo_principal"):
                    equipos_dia.add(grupo_obj["equipo_principal"])
                for eq in grupo_obj.get("equipos", []):
                    if eq:
                        equipos_dia.add(eq)
            if not equipos_dia:
                equipos_dia.add("Real Dunalastair")

            def on_cambiar_equipo_stats(e):
                self.estado["equipo_activo"] = e.control.value
                self.callbacks["refrescar_vistas"]()
                self.page.update()

            selector_equipo_superadmin = ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.SWAP_HORIZ, size=16, color=COLOR_CELESTE),
                    ft.Text("Ver Estadísticas del Club:", size=12, color=COLOR_SUBTEXTO, weight=ft.FontWeight.BOLD),
                    ft.Dropdown(
                        value=equipo_activo if equipo_activo in equipos_dia else sorted(equipos_dia)[0],
                        options=[ft.dropdown.Option(eq) for eq in sorted(equipos_dia)],
                        width=180,
                        text_size=12,
                        content_padding=ft.padding.symmetric(horizontal=8, vertical=4),
                        border_color=COLOR_CELESTE,
                        focused_border_color=COLOR_VERDE,
                        border_radius=8,
                        on_change=on_cambiar_equipo_stats,
                    ),
                ], spacing=8, alignment=ft.MainAxisAlignment.START),
                padding=ft.padding.only(bottom=4),
            )

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
                content=ft.Row([
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
                    ft.Column([
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
                    ], expand=True, spacing=1),
                    ft.Text(
                        f"{mins_totales} min",
                        color=COLOR_CELESTE,
                        weight=ft.FontWeight.BOLD,
                        size=15,
                    ),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                padding=10,
                bgcolor=COLOR_TARJETA,
                border_radius=10,
                border=ft.border.all(1, COLOR_BORDE),
            )
            stats_ui.append(tarjeta)

        elementos_stats = [
            ft.Text(
                f"📊 Ranking de Minutos: {equipo_activo} ({fecha_filtro})",
                size=18,
                weight=ft.FontWeight.BOLD,
                color=COLOR_TEXTO,
            ),
        ]

        if selector_equipo_superadmin:
            elementos_stats.append(selector_equipo_superadmin)

        elementos_stats.extend([
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
        ])

        return ft.Column(
            elementos_stats,
            expand=True,
        )
