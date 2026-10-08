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
from backend.services.jugador_service import JugadorService
from backend.services.partido_service import PartidoService
from backend.services.usuario_service import UsuarioService
from backend.models.partido import Partido
from frontend.screens.configuracion import ConfiguracionScreen
from frontend.screens.plantel import PlantelScreen
from frontend.screens.partido import PartidoScreen
from frontend.screens.estadisticas import EstadisticasScreen
from utils.time_utils import (
    obtener_segundos_actuales, actualizar_minutos_jugadores, formatear_tiempo, ordenar_eventos
)


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
        "grupos_dia": [],
        "grupo_seleccionado_id": None,
        "config_torneo": {"partido_definicion": False},
        "partido_definicion": None,
        "partido_activo_id": None,
        "minutos_partido_actual": {},
        "titulares_seleccionados": [],
        "eventos_registrados": [],
        "es_invitado": True,
        "es_superadmin": False,
        "usuario_autenticado": None,
        "equipo_activo": "Real Dunalastair",
        "equipo_seguido_invitado": "Real Dunalastair",
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
        datos_dia = GrupoService.cargar_grupos_por_fecha(estado["fecha_filtro"])
        grupos = datos_dia.get("grupos", [])
        estado["grupos_dia"] = grupos
        estado["config_torneo"] = datos_dia.get("config_torneo", {"partido_definicion": False})
        estado["partido_definicion"] = datos_dia.get("partido_definicion")

        target_team = (
            estado.get("equipo_seguido_invitado", "Real Dunalastair")
            if estado["es_invitado"]
            else (estado.get("equipo_activo") or "Real Dunalastair")
        )

        if grupos:
            # Buscar el grupo que contenga a target_team
            grupo_target_data = None
            for g in grupos:
                grupo_obj = g["grupo"]
                if grupo_obj.get("equipo_principal") == target_team or target_team in grupo_obj.get("equipos", []):
                    grupo_target_data = g
                    break
            
            if not grupo_target_data:
                grupo_target_data = next((g for g in grupos if g["grupo"].get("es_principal")), grupos[0])
            
            sel_id = estado.get("grupo_seleccionado_id")
            grupo_sel_data = next((g for g in grupos if g["grupo"]["id"] == sel_id), None)
            if not grupo_sel_data:
                grupo_sel_data = grupo_target_data
                estado["grupo_seleccionado_id"] = grupo_sel_data["grupo"]["id"]

            estado["grupo_activo"] = grupo_sel_data["grupo"]
            estado["partidos_grupo"] = grupo_sel_data["partidos"]

            # Buscar partidos del equipo target
            partidos_target = [
                p for p in grupo_target_data["partidos"]
                if p["equipo_local"] == target_team or p["equipo_visita"] == target_team
            ]
            if not partidos_target:
                partidos_target = grupo_target_data["partidos"]

            if partidos_target:
                if estado["partido_activo_id"] is None or not any(p["id"] == estado["partido_activo_id"] for p in partidos_target):
                    if estado["es_invitado"]:
                        en_curso = next(
                            (p for p in partidos_target if p["hora_inicio"] is not None or (p["segundos"] > 0 and not p["finalizado"])),
                            None
                        )
                        activar_partido_memoria(en_curso if en_curso else partidos_target[0])
                    else:
                        activar_partido_memoria(partidos_target[0])
        else:
            estado["grupos_dia"] = []
            estado["grupo_seleccionado_id"] = None
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
        
        target_team = (
            estado.get("equipo_seguido_invitado", "Real Dunalastair")
            if estado["es_invitado"]
            else (estado.get("equipo_activo") or "Real Dunalastair")
        )

        es_mi_equipo_en_partido = (partido["equipo_local"] == target_team or partido["equipo_visita"] == target_team)

        if es_mi_equipo_en_partido:
            es_local = (partido["equipo_local"] == target_team)
            rival = partido["equipo_visita"] if es_local else partido["equipo_local"]
            estado["config"]["equipo_principal"] = target_team
            estado["config"]["equipo_rival"] = rival
            estado["goles_local"] = partido["goles_local"] if es_local else partido["goles_visita"]
            estado["goles_rival"] = partido["goles_visita"] if es_local else partido["goles_local"]
        else:
            estado["config"]["equipo_principal"] = partido["equipo_local"]
            estado["config"]["equipo_rival"] = partido["equipo_visita"]
            estado["goles_local"] = partido["goles_local"]
            estado["goles_rival"] = partido["goles_visita"]

        estado["partido_activo_id"] = partido["id"]
        estado["segundos_acumulados"] = partido.get("segundos_acumulados", partido["segundos"])
        estado["segs_al_iniciar"] = estado["segundos_acumulados"]
        estado["hora_inicio"] = partido.get("hora_inicio")
        estado["corriendo"] = estado["hora_inicio"] is not None
        estado["segundos"] = obtener_segundos_actuales(estado)
        estado["ultimo_segundo_procesado"] = estado["segundos"]

        # Filtrar titulares para que correspondan estrictamente al equipo activo (target_team)
        titulares_raw = partido.get("titulares", [])
        if isinstance(titulares_raw, dict):
            titulares_de_mi_equipo = list(titulares_raw.get(target_team, []))
        else:
            jugadores_eq = [
                j["nombre"]
                for j in JugadorService.obtener_todos_ordenados(
                    equipo=target_team,
                    fecha=partido.get("fecha", datetime.now().strftime("%Y-%m-%d"))
                )
            ]
            titulares_de_mi_equipo = [nom for nom in titulares_raw if nom in jugadores_eq]
        estado["titulares_seleccionados"] = titulares_de_mi_equipo

        estado["eventos_registrados"] = ordenar_eventos(list(partido["eventos"]))
        estado["alerta_custom"] = partido.get("alerta_custom")
        estado["minutos_partido_actual"] = dict(partido["minutos_partido"])
        estado["finalizado"] = bool(partido.get("finalizado", False))

        estado["config"].update({
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

        # Sincronizar diccionario en memoria y marcador
        es_local = (p_act["equipo_local"] == estado["config"]["equipo_principal"])
        p_act["goles_local"] = estado["goles_local"] if es_local else estado["goles_rival"]
        p_act["goles_visita"] = estado["goles_rival"] if es_local else estado["goles_local"]
        p_act["jugado"] = True if (
            estado.get("hora_inicio") is not None
            or seg_actuales > 0
            or estado.get("segundos_acumulados", 0) > 0
            or estado.get("finalizado", False)
            or p_act.get("jugado", False)
        ) else False
        p_act["segundos"] = seg_actuales
        p_act["segundos_acumulados"] = estado["segundos_acumulados"]
        p_act["hora_inicio"] = estado["hora_inicio"]

        # Guardar titulares indexados por club para no sobreescribir ni mezclar con el rival
        titulares_actuales = p_act.get("titulares", {})
        if isinstance(titulares_actuales, dict):
            titulares_dict = dict(titulares_actuales)
        else:
            titulares_dict = {}
            if p_act.get("equipo_local"):
                titulares_dict[p_act["equipo_local"]] = [n for n in titulares_actuales]

        mi_club = estado["config"]["equipo_principal"]
        titulares_dict[mi_club] = list(estado["titulares_seleccionados"])
        p_act["titulares"] = titulares_dict

        p_act["eventos"] = list(estado["eventos_registrados"])
        p_act["alerta_custom"] = estado["alerta_custom"]
        p_act["minutos_partido"] = dict(estado["minutos_partido_actual"])
        p_act["finalizado"] = estado["finalizado"]

        # Recalcular tabla de posiciones para el grupo activo en grupos_dia
        for g_data in estado.get("grupos_dia", []):
            if any(p["id"] == p_act["id"] for p in g_data.get("partidos", [])):
                g_data["tabla"] = GrupoService.calcular_tabla_grupo(
                    g_data.get("partidos", []),
                    g_data.get("grupo", {}).get("equipos", [])
                )
                break

        partido = Partido.from_dict(p_act)
        partido.segundos = seg_actuales
        partido.segundos_acumulados = estado["segundos_acumulados"]
        partido.hora_inicio = estado["hora_inicio"]
        partido.titulares = titulares_dict
        partido.eventos = estado["eventos_registrados"]
        partido.alerta_custom = estado["alerta_custom"]
        partido.minutos_partido = estado["minutos_partido_actual"]
        partido.finalizado = estado["finalizado"]
        partido.jugado = p_act["jugado"]

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

    # Header con rol
    texto_rol_header = ft.Text(
        "👤 Invitado",
        size=10,
        weight=ft.FontWeight.BOLD,
        color=COLOR_AMBAR,
    )

    def construir_header_app():
        equipos_dia = set()
        for g in estado.get("grupos_dia", []):
            grupo_obj = g.get("grupo", {})
            if grupo_obj.get("equipo_principal"):
                equipos_dia.add(grupo_obj["equipo_principal"])
            for eq in grupo_obj.get("equipos", []):
                if eq:
                    equipos_dia.add(eq)
        if not equipos_dia:
            equipos_dia.add("Real Dunalastair")

        if estado["es_invitado"]:
            eq_seguido = estado.get("equipo_seguido_invitado", "Real Dunalastair")
            if eq_seguido not in equipos_dia and equipos_dia:
                eq_seguido = sorted(equipos_dia)[0]
                estado["equipo_seguido_invitado"] = eq_seguido

            def on_cambiar_equipo_seguido(e):
                estado["equipo_seguido_invitado"] = e.control.value
                estado["partido_activo_id"] = None
                estado["grupo_seleccionado_id"] = None
                cargar_grupo()
                refrescar_vistas()
                actualizar_header_app()
                page.update()

            selector_invitado = ft.Row([
                ft.Icon(ft.Icons.VISIBILITY, size=13, color=COLOR_AMBAR),
                ft.Text("Siguiendo:", size=11, weight=ft.FontWeight.BOLD, color=COLOR_SUBTEXTO),
                ft.Dropdown(
                    value=eq_seguido,
                    options=[ft.dropdown.Option(eq) for eq in sorted(equipos_dia)],
                    width=150,
                    text_size=11,
                    content_padding=ft.padding.symmetric(horizontal=6, vertical=2),
                    border_color=COLOR_AMBAR,
                    focused_border_color=COLOR_CELESTE,
                    border_radius=8,
                    on_change=on_cambiar_equipo_seguido,
                ),
            ], spacing=4)

            lado_izquierdo = ft.Row([
                ft.Row([
                    ft.Icon(ft.Icons.SPORTS_SOCCER, color=COLOR_CELESTE, size=20),
                    ft.Text("Cuadrangulares", weight=ft.FontWeight.BOLD, size=13, color=COLOR_TEXTO),
                ], spacing=4),
                selector_invitado,
            ], spacing=8)

        elif estado.get("es_superadmin", False):
            eq_gestionado = estado.get("equipo_activo")
            if eq_gestionado not in equipos_dia:
                eq_gestionado = sorted(equipos_dia)[0]
                estado["equipo_activo"] = eq_gestionado

            def on_cambiar_equipo_gestionado(e):
                estado["equipo_activo"] = e.control.value
                estado["config"]["equipo_principal"] = e.control.value
                estado["partido_activo_id"] = None
                estado["grupo_seleccionado_id"] = None
                cargar_grupo()
                refrescar_vistas()
                page.update()

            lado_izquierdo = ft.Row([
                ft.Icon(ft.Icons.ADMIN_PANEL_SETTINGS, color=COLOR_VERDE, size=20),
                ft.Text("SuperAdmin", weight=ft.FontWeight.BOLD, size=13, color=COLOR_TEXTO),
                ft.Dropdown(
                    value=eq_gestionado,
                    options=[ft.dropdown.Option(eq) for eq in sorted(equipos_dia)],
                    width=150,
                    text_size=11,
                    content_padding=ft.padding.symmetric(horizontal=6, vertical=2),
                    border_color=COLOR_VERDE,
                    focused_border_color=COLOR_CELESTE,
                    border_radius=8,
                    on_change=on_cambiar_equipo_gestionado,
                ),
            ], spacing=6)

        else:
            eq_adm = estado.get("equipo_activo") or "Real Dunalastair"
            contacto = estado.get("usuario_autenticado", {}).get("nombre_contacto", "Delegado")
            lado_izquierdo = ft.Row([
                ft.Icon(ft.Icons.SPORTS_SOCCER, color=COLOR_CELESTE, size=20),
                ft.Text(f"{eq_adm} ({contacto})", weight=ft.FontWeight.BOLD, size=14, color=COLOR_TEXTO),
            ], spacing=6)

        return ft.Row(
            [
                lado_izquierdo,
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
        )

    header_app = ft.Container(
        content=construir_header_app(),
        padding=ft.Padding(12, 10, 12, 10),
        bgcolor=COLOR_TARJETA,
    )

    def actualizar_header_app():
        header_app.content = construir_header_app()

    # Implementar refrescar_vistas
    def refrescar_vistas():
        actualizar_header_app()
        # Asegurar que las tablas de posiciones de cada grupo estén actualizadas
        for g_data in estado.get("grupos_dia", []):
            g_data["tabla"] = GrupoService.calcular_tabla_grupo(
                g_data.get("partidos", []),
                g_data.get("grupo", {}).get("equipos", [])
            )
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

        # Asegurar recálculo de tablas al navegar
        for g_data in estado.get("grupos_dia", []):
            g_data["tabla"] = GrupoService.calcular_tabla_grupo(
                g_data.get("partidos", []),
                g_data.get("grupo", {}).get("equipos", [])
            )

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

    # Diálogo de selección de rol
    def mostrar_dialogo_rol():
        tf_clave = ft.TextField(
            label="RUT (sin puntos ni guion)",
            hint_text="Ej: 11165045 o RUT de delegado",
            password=True,
            width=220,
            border_color=COLOR_BORDE,
            focused_border_color=COLOR_CELESTE,
            border_radius=10,
        )
        texto_error = ft.Text("", size=11, color=COLOR_ROJO)

        def seleccionar_invitado(e):
            estado["es_invitado"] = True
            estado["es_superadmin"] = False
            estado["usuario_autenticado"] = None
            estado["partido_activo_id"] = None
            estado["grupo_seleccionado_id"] = None
            texto_rol_header.value = "👤 Invitado"
            texto_rol_header.color = COLOR_AMBAR
            estado["pestana_activa"] = 0
            page.close(dialogo_rol)
            cargar_grupo()
            refrescar_vistas()
            page.update()

        def verificar_admin(e):
            rut_input = tf_clave.value or ""
            user = UsuarioService.autenticar(rut_input)
            if user:
                estado["es_invitado"] = False
                estado["usuario_autenticado"] = user
                estado["es_superadmin"] = bool(user["es_superadmin"])
                estado["equipo_activo"] = user["equipo_asignado"]
                estado["config"]["equipo_principal"] = user["equipo_asignado"]
                estado["partido_activo_id"] = None
                estado["grupo_seleccionado_id"] = None

                if user["es_superadmin"]:
                    texto_rol_header.value = "👑 SuperAdmin"
                    texto_rol_header.color = COLOR_VERDE
                else:
                    texto_rol_header.value = f"🛡️ DT {user['equipo_asignado']}"
                    texto_rol_header.color = COLOR_CELESTE

                estado["pestana_activa"] = 0
                page.close(dialogo_rol)
                cargar_grupo()
                refrescar_vistas()
                page.update()
            else:
                texto_error.value = "❌ RUT no registrado. Ingrese un RUT válido de administrador o delegado."
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
                    ft.Text("Acceso Administrador / Delegado:", weight=ft.FontWeight.BOLD, color=COLOR_CELESTE),
                    tf_clave,
                    ft.ElevatedButton(
                        "Entrar con RUT",
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
        page.open(dialogo_rol)

    # Loop del cronómetro (alta precisión UI) y loop de sincronización en segundo plano
    async def loop_reloj():
        while True:
            await asyncio.sleep(0.5)

            seg = obtener_segundos_actuales(estado)
            estado["segundos"] = seg

            duracion_tiempo_segs = estado["config"]["minutos_por_tiempo"] * 60
            duracion_total_partido = duracion_tiempo_segs * estado["config"]["tiempos_por_partido"]

            # Solo el administrador actualiza localmente minutos y límites de tiempo
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

            # Actualizar glosa del reloj en pantalla Partido
            try:
                screen_partido.actualizar_glosa()
                if hasattr(screen_partido, "texto_reloj") and screen_partido.texto_reloj.page:
                    screen_partido.texto_reloj.update()
                    if hasattr(screen_partido, "texto_alerta_cambio") and screen_partido.texto_alerta_cambio.page:
                        screen_partido.texto_alerta_cambio.update()
                else:
                    page.update()
            except Exception:
                pass

    # Sincronización multi-dispositivo en segundo plano (asíncrona y no bloqueante)
    async def loop_sincronizacion():
        while True:
            intervalo_sync = 2 if estado["pestana_activa"] == 2 else 10
            await asyncio.sleep(intervalo_sync)
            try:
                if estado["grupo_activo"] and estado["partido_activo_id"]:
                    hubo_cambio, nuevos_partidos = await asyncio.to_thread(
                        PartidoService.sincronizar_desde_bd,
                        estado["grupo_activo"]["id"],
                        estado["partido_activo_id"],
                        estado,
                        estado["config"]["equipo_principal"],
                    )
                    if hubo_cambio:
                        estado["partidos_grupo"] = nuevos_partidos
                        for g_data in estado.get("grupos_dia", []):
                            if g_data.get("grupo", {}).get("id") == estado["grupo_activo"]["id"]:
                                g_data["partidos"] = nuevos_partidos
                                g_data["tabla"] = GrupoService.calcular_tabla_grupo(
                                    nuevos_partidos,
                                    g_data.get("grupo", {}).get("equipos", [])
                                )
                                break
                        refrescar_vistas()
                        page.update()
            except Exception:
                pass

    page.run_task(loop_reloj)
    page.run_task(loop_sincronizacion)

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
