import asyncio
import os
from datetime import datetime, timezone
import flet as ft

# Importaciones de los módulos refactorizados
from config.settings import APP_TITLE, APP_THEME_MODE, APP_BGCOLOR
from config.constants import (
    COLOR_FONDO, COLOR_TARJETA, COLOR_BORDE, COLOR_CELESTE, 
    COLOR_CELESTE_BOTON, COLOR_TEXTO, COLOR_SUBTEXTO, COLOR_VERDE, COLOR_ROJO, COLOR_AMBAR
)
from backend.database.repositories import DatabaseInitializer
from backend.services.grupo_service import GrupoService
from backend.services.partido_service import PartidoService
from backend.models.partido import Partido
from frontend.screens.configuracion import ConfiguracionScreen
from frontend.screens.plantel import PlantelScreen
from frontend.screens.partido import PartidoScreen
from frontend.screens.estadisticas import EstadisticasScreen
from utils.time_utils import obtener_segundos_actuales, actualizar_minutos_jugadores, formatear_tiempo


def main(page: ft.Page):
    # Inicializar base de datos
    DatabaseInitializer.inicializar()

    # Configuración de la página
    page.title = APP_TITLE
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    page.bgcolor = APP_BGCOLOR

    # Estado de la aplicación
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
        "es_invitado": True,
        "fecha_filtro": datetime.now().strftime("%Y-%m-%d"),
        "config": {
            "equipo_principal": "Real Dunalastair",
            "equipo_rival": "Rival FC",
            "tiempos_por_partido": 2,
            "minutos_por_tiempo": 10,
            "jugadores_en_cancha": 7,
            "fecha": datetime.now().strftime("%Y-%m-%d"),
        },
    }

    # Callbacks compartidos
    def cargar_grupo():
        datos_grupo = GrupoService.cargar_grupo_por_fecha(estado["fecha_filtro"])
        if datos_grupo:
            estado["grupo_activo"] = datos_grupo["grupo"]
            estado["partidos_grupo"] = datos_grupo["partidos"]
            
            # Activar partido principal si no hay uno activo
            if estado["partido_activo_id"] is None:
                partidos_principales = [p for p in estado["partidos_grupo"] if p["es_principal"]]
                if partidos_principales:
                    if estado["es_invitado"]:
                        en_curso = next((p for p in partidos_principales if p["hora_inicio"] is not None or (
                            p["segundos"] > 0 and not p["finalizado"])), None)
                        activar_partido_memoria(en_curso if en_curso else partidos_principales[0])
                    else:
                        activar_partido_memoria(partidos_principales[0])
        else:
            estado["grupo_activo"] = None
            estado["partidos_grupo"] = []
            estado["partido_activo_id"] = None
            estado["minutos_partido_actual"] = {}
            estado["segundos"] = 0
            estado["segundos_acumulados"] = 0
            estado["segs_al_iniciar"] = 0
            estado["ultimo_segundo_procesado"] = 0
            estado["hora_inicio"] = None
            estado["corriendo"] = False
            estado["finalizado"] = False
            estado["alerta_custom"] = None
            estado["titulares_seleccionados"] = []
            estado["eventos_registrados"] = []
            estado["goles_local"] = 0
            estado["goles_rival"] = 0

    def activar_partido_memoria(partido):
        if not partido:
            return
        
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

    def guardar_partido():
        if estado["es_invitado"] or estado["partido_activo_id"] is None:
            return

        seg_actuales = obtener_segundos_actuales(estado)
        actualizar_minutos_jugadores(estado, seg_actuales)

        p_act = next(
            (p for p in estado["partidos_grupo"] if p["id"] == estado["partido_activo_id"]),
            None,
        )
        if not p_act:
            return

        partido = Partido.from_dict(p_act)
        partido.segundos = seg_actuales
        partido.segundos_acumulados = estado["segundos_acumulados"]
        partido.hora_inicio = estado["hora_inicio"]
        partido.titulares = estado["titulares_seleccionados"]
        partido.eventos = estado["eventos_registrados"]
        partido.alerta_custom = estado["alerta_custom"]
        partido.minutos_partido = estado["minutos_partido_actual"]
        partido.finalizado = estado["finalizado"]

        PartidoService.guardar_estado_partido(
            partido,
            estado["goles_local"],
            estado["goles_rival"],
            estado["config"]["equipo_principal"],
        )

    # Callbacks para las pantallas
    callbacks = {
        "cargar_grupo": cargar_grupo,
        "guardar_partido": guardar_partido,
        "activar_partido_memoria": activar_partido_memoria,
        "refrescar_vistas": lambda: None,  # Se implementará después
    }

    # Cargar datos iniciales
    cargar_grupo()

    # Crear instancias de las pantallas
    screen_config = ConfiguracionScreen(estado, page, callbacks)
    screen_plantel = PlantelScreen(estado, page, callbacks)
    screen_partido = PartidoScreen(estado, page, callbacks)
    screen_estadisticas = EstadisticasScreen(estado, page, callbacks)

    # Contenedores para cada pantalla
    contenedor_config = ft.Container(content=screen_config.build(), expand=True)
    contenedor_plantel = ft.Container(content=screen_plantel.build(), expand=True, visible=False)
    contenedor_partido = ft.Container(content=screen_partido.build(), expand=True, visible=False)
    contenedor_estadisticas = ft.Container(content=screen_estadisticas.build(), expand=True, visible=False)

    # Implementar refrescar_vistas
    def refrescar_vistas():
        contenedor_config.content = screen_config.build()
        contenedor_plantel.content = screen_plantel.build()
        contenedor_partido.content = screen_partido.build()
        contenedor_estadisticas.content = screen_estadisticas.build()
        
        # Actualizar navegación según rol
        page.navigation_bar = construir_barra_navegacion()
        page.navigation_bar.selected_index = estado["pestana_activa"]
        
        # Mostrar la pestaña activa según rol
        if estado["es_invitado"]:
            contenedor_config.visible = estado["pestana_activa"] == 0
            contenedor_plantel.visible = False
            contenedor_partido.visible = estado["pestana_activa"] == 1
            contenedor_estadisticas.visible = False
        else:
            contenedor_config.visible = estado["pestana_activa"] == 0
            contenedor_plantel.visible = estado["pestana_activa"] == 1
            contenedor_partido.visible = estado["pestana_activa"] == 2
            contenedor_estadisticas.visible = estado["pestana_activa"] == 3

    callbacks["refrescar_vistas"] = refrescar_vistas

    # Navegación con NavigationBar
    def construir_barra_navegacion():
        if estado["es_invitado"]:
            destinos = [
                ft.NavigationBarDestination(icon=ft.Icons.SETTINGS, label="Config & Tabla"),
                ft.NavigationBarDestination(icon=ft.Icons.SPORTS_SOCCER, label="Partido"),
            ]
        else:
            destinos = [
                ft.NavigationBarDestination(icon=ft.Icons.SETTINGS, label="Config & Tabla"),
                ft.NavigationBarDestination(icon=ft.Icons.PEOPLE, label="Plantel"),
                ft.NavigationBarDestination(icon=ft.Icons.SPORTS_SOCCER, label="Partido"),
                ft.NavigationBarDestination(icon=ft.Icons.BAR_CHART, label="Ranking"),
            ]
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

        if estado["es_invitado"]:
            contenedor_config.visible = indice == 0
            contenedor_plantel.visible = False
            contenedor_partido.visible = indice == 1
            contenedor_estadisticas.visible = False

            if indice == 0:
                contenedor_config.content = screen_config.build()
            elif indice == 1:
                contenedor_partido.content = screen_partido.build()
        else:
            contenedor_config.visible = indice == 0
            contenedor_plantel.visible = indice == 1
            contenedor_partido.visible = indice == 2
            contenedor_estadisticas.visible = indice == 3

            if indice == 0:
                contenedor_config.content = screen_config.build()
            elif indice == 1:
                contenedor_plantel.content = screen_plantel.build()
            elif indice == 2:
                contenedor_partido.content = screen_partido.build()
            elif indice == 3:
                contenedor_estadisticas.content = screen_estadisticas.build()
        page.update()

    # Header con rol
    texto_rol_header = ft.Text(
        "👤 Invitado",
        size=10,
        weight=ft.FontWeight.BOLD,
        color=COLOR_AMBAR,
    )

    # Diálogo de selección de rol
    def mostrar_dialogo_rol():
        tf_clave = ft.TextField(
            label="RUT (sin puntos ni guion)",
            password=True,
            width=200,
            border_color=COLOR_BORDE,
            focused_border_color=COLOR_CELESTE,
            border_radius=10,
        )
        texto_error = ft.Text("", size=11, color=COLOR_ROJO)

        def seleccionar_invitado(e):
            estado["es_invitado"] = True
            texto_rol_header.value = "👤 Invitado"
            texto_rol_header.color = COLOR_AMBAR
            estado["pestana_activa"] = 0
            dialogo_rol.open = False
            page.navigation_bar = construir_barra_navegacion()
            page.navigation_bar.selected_index = 0
            refrescar_vistas()
            page.update()

        def verificar_admin(e):
            rut_limpio = tf_clave.value.replace(".", "").replace("-", "") if tf_clave.value else ""
            if rut_limpio == "11165045":  # RUT del administrador
                estado["es_invitado"] = False
                texto_rol_header.value = "👑 Administrador"
                texto_rol_header.color = COLOR_VERDE
                estado["pestana_activa"] = 0
                dialogo_rol.open = False
                page.navigation_bar = construir_barra_navegacion()
                page.navigation_bar.selected_index = 0
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

    # Loop del cronómetro y sincronización
    async def loop_reloj():
        contador_sync = 0
        while True:
            await asyncio.sleep(1)

            seg = obtener_segundos_actuales(estado)
            estado["segundos"] = seg

            duracion_tiempo_segs = estado["config"]["minutos_por_tiempo"] * 60
            duracion_total_partido = duracion_tiempo_segs * estado["config"]["tiempos_por_partido"]

            # Solo el administrador actualiza localmente
            if not estado["es_invitado"]:
                if estado["corriendo"] and not estado["finalizado"]:
                    actualizar_minutos_jugadores(estado, seg)

                    if seg >= duracion_total_partido:
                        actualizar_minutos_jugadores(estado, duracion_total_partido)
                        estado["corriendo"] = False
                        estado["finalizado"] = True
                        estado["segundos_acumulados"] = duracion_total_partido
                        estado["segundos"] = duracion_total_partido
                        estado["hora_inicio"] = None
                        estado["alerta_custom"] = None
                        guardar_partido()
                        refrescar_vistas()

                    elif duracion_tiempo_segs > 0:
                        segs_inicio = estado.get("segs_al_iniciar", 0)
                        for t in range(1, estado["config"]["tiempos_por_partido"]):
                            limite_half = t * duracion_tiempo_segs
                            if seg >= limite_half and segs_inicio < limite_half:
                                actualizar_minutos_jugadores(estado, limite_half)
                                estado["corriendo"] = False
                                estado["segundos_acumulados"] = limite_half
                                estado["segundos"] = limite_half
                                estado["hora_inicio"] = None
                                estado["alerta_custom"] = f"🏁 ¡FIN DEL TIEMPO {t}! Cronómetro pausado."
                                guardar_partido()
                                refrescar_vistas()
                                break

            # Sincronización multi-dispositivo
            contador_sync += 1
            intervalo_sync = 2 if estado["pestana_activa"] == 2 else 10

            if contador_sync >= intervalo_sync:
                if estado["grupo_activo"] and estado["partido_activo_id"]:
                    hubo_cambio, nuevos_partidos = PartidoService.sincronizar_desde_bd(
                        estado["grupo_activo"]["id"],
                        estado["partido_activo_id"],
                        estado,
                        estado["config"]["equipo_principal"],
                    )
                    if hubo_cambio:
                        estado["partidos_grupo"] = nuevos_partidos
                        refrescar_vistas()
                contador_sync = 0

            try:
                page.update()
            except Exception:
                pass

    page.run_task(loop_reloj)

    # Header
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
                            content=texto_rol_header,
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

    # Layout principal
    app_layout = ft.Container(
        expand=True,
        bgcolor=COLOR_FONDO,
        content=ft.Column(
            [
                header_app,
                ft.Stack(
                    [
                        contenedor_config,
                        contenedor_plantel,
                        contenedor_partido,
                        contenedor_estadisticas,
                    ],
                    expand=True,
                ),
            ],
            expand=True,
            spacing=0,
        ),
    )

    page.add(app_layout)
    
    # Inicializar navegación
    page.navigation_bar = construir_barra_navegacion()

    # Mostrar diálogo de rol al inicio
    mostrar_dialogo_rol()


if __name__ == "__main__":
    puerto = int(os.environ.get("PORT", 8080))
    ft.app(
        target=main, host="0.0.0.0", port=puerto, view=ft.AppView.WEB_BROWSER
    )
