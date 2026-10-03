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
        jugadores = JugadorService.obtener_todos_ordenados()
        fecha_filtro = (
            self.estado.get("fecha_filtro")
            or self.estado.get("config", {}).get("fecha")
            or datetime.now().strftime("%Y-%m-%d")
        )
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
                        "Número": j["numero"],
                        "Jugador": nom,
                        "Puesto": j["puesto"],
                        "Minutos Acumulados Día": segs // 60,
                    })
                df = pd.DataFrame(datos_jugadores)
                nombre_archivo = f"Reporte_Minutos_{fecha_filtro}.xlsx"
                df.to_excel(nombre_archivo, index=False)
                texto_export.value = f"✅ '{nombre_archivo}' guardado."
            except Exception as ex:
                texto_export.value = f"❌ Error exportando: {ex}"
            self.page.update()

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

        return ft.Column(
            [
                ft.Text(
                    f"📊 Ranking de Minutos por Día ({fecha_filtro})",
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
