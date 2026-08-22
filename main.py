import flet as ft
import pandas as pd
import os
import asyncio
import json


def main(page: ft.Page):
    page.title = "Dunalastairs - Control de Cambios"
    page.window.width = 400
    page.window.height = 800
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0

    # --- Estado Global ---
    estado = {
        "segundos": 0,
        "corriendo": False,
        "partido_actual": 1,
        "minutos_jugadores": {},
        "minutos_partido_actual": {},
        "titulares_seleccionados": [],
        "config": {
            "partidos_torneo": 3,
            "minutos_por_tiempo": 10,
            "tiempos_por_partido": 2,
            "jugadores_en_cancha": 7,
            "min_alto": 40,
            "min_medio": 30,
            "min_bajo": 20,
            "max_min_partido": 15
        }
    }

    # --- FUNCIONES DE PERSISTENCIA ---
    def guardar_estado_local():
        datos_a_guardar = {
            "partido_actual": estado["partido_actual"],
            "minutos_jugadores": estado["minutos_jugadores"],
            "minutos_partido_actual": estado["minutos_partido_actual"],
            "config": estado["config"],
            "titulares_seleccionados": estado["titulares_seleccionados"]
        }
        try:
            with open("estado_torneo.json", "w", encoding="utf-8") as f:
                json.dump(datos_a_guardar, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error al guardar estado: {e}")

    def cargar_estado_local():
        if os.path.exists("estado_torneo.json"):
            try:
                with open("estado_torneo.json", "r", encoding="utf-8") as f:
                    datos = json.load(f)
                    estado["partido_actual"] = datos.get("partido_actual", 1)
                    estado["minutos_jugadores"] = datos.get("minutos_jugadores", {})
                    estado["minutos_partido_actual"] = datos.get("minutos_partido_actual", {})
                    estado["titulares_seleccionados"] = datos.get("titulares_seleccionados", [])
                    estado["config"].update(datos.get("config", {}))
            except Exception as e:
                print(f"Error al cargar estado: {e}")

    def reiniciar_torneo_completo():
        estado["segundos"] = 0
        estado["corriendo"] = False
        estado["partido_actual"] = 1
        estado["minutos_jugadores"] = {}
        estado["minutos_partido_actual"] = {}
        estado["titulares_seleccionados"] = []
        if os.path.exists("estado_torneo.json"):
            os.remove("estado_torneo.json")

    def exportar_a_excel(jugadores):
        try:
            datos = []
            for j in jugadores:
                nom = j['nombre']
                puesto = j['puesto']
                segs = estado["minutos_jugadores"].get(nom, 0)
                mins = segs // 60

                if "arquero" in puesto.lower():
                    meta = estado["config"]["partidos_torneo"] * estado["config"]["tiempos_por_partido"] * \
                           estado["config"]["minutos_por_tiempo"]
                elif '0.75' in j['rendimiento']:
                    meta = estado["config"]["min_medio"]
                elif '0.5' in j['rendimiento']:
                    meta = estado["config"]["min_bajo"]
                else:
                    meta = estado["config"]["min_alto"]

                datos.append({
                    "Jugador": nom,
                    "Puesto": puesto,
                    "Minutos Jugados": mins,
                    "Minutos Meta": meta,
                    "Cumplimiento (%)": round((mins / meta * 100), 1) if meta > 0 else 0
                })
            df_export = pd.DataFrame(datos)
            df_export.to_excel("Reporte_Minutos_Final.xlsx", index=False)
            df_export.to_csv("Reporte_Minutos_Final.csv", index=False, encoding="utf-8-sig")
            return True
        except Exception as e:
            print(f"Error exportando: {e}")
            return False

    cargar_estado_local()

    texto_reloj = ft.Text("00:00", size=80, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_200)
    texto_alerta_cambio = ft.Text("Partido en curso", weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_400)
    texto_alerta_limite = ft.Text("", weight=ft.FontWeight.BOLD, color=ft.Colors.RED_400)
    texto_indicador_partido = ft.Text(f"Partido {estado['partido_actual']} de {estado['config']['partidos_torneo']}",
                                      size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_200)

    def formatear_tiempo(segs):
        return f"{segs // 60:02d}:{segs % 60:02d}"

    # --- MOTOR DEL RELOJ ---
    async def loop_reloj():
        contador_guardado = 0
        while True:
            await asyncio.sleep(1)
            if estado["corriendo"]:
                estado["segundos"] += 1
                seg = estado["segundos"]
                texto_reloj.value = formatear_tiempo(seg)

                max_segs_partido = estado["config"]["max_min_partido"] * 60
                jugadores_excedidos = []

                for jugador in estado["titulares_seleccionados"]:
                    estado["minutos_jugadores"][jugador] = estado["minutos_jugadores"].get(jugador, 0) + 1
                    estado["minutos_partido_actual"][jugador] = estado["minutos_partido_actual"].get(jugador, 0) + 1

                    if estado["minutos_partido_actual"][jugador] >= max_segs_partido:
                        jugadores_excedidos.append(jugador)

                contador_guardado += 1
                if contador_guardado >= 10:
                    guardar_estado_local()
                    contador_guardado = 0

                en_ventana_alerta = any(abs(seg - bloque) <= 10 for bloque in range(300, 3600, 300))

                if jugadores_excedidos:
                    nombres_alertas = ", ".join(jugadores_excedidos)
                    texto_alerta_limite.value = f"🚨 ¡LÍMITE ALCANZADO ({estado['config']['max_min_partido']} min)! Cambiar a: {nombres_alertas}"
                else:
                    texto_alerta_limite.value = ""

                if en_ventana_alerta or jugadores_excedidos:
                    texto_reloj.color = ft.Colors.RED_400
                    if en_ventana_alerta and not jugadores_excedidos:
                        minuto_actual = seg // 60
                        texto_alerta_cambio.value = f"🔔 ¡MINUTO {minuto_actual}! Evaluar cambios."
                        texto_alerta_cambio.color = ft.Colors.RED_400
                else:
                    texto_reloj.color = ft.Colors.BLUE_200
                    texto_alerta_cambio.value = "Tiempo de juego normal"
                    texto_alerta_cambio.color = ft.Colors.GREY_400

                if texto_reloj.page:
                    try:
                        texto_reloj.update()
                        texto_alerta_cambio.update()
                        texto_alerta_limite.update()
                    except:
                        pass

    page.run_task(loop_reloj)

    def play_click(e):
        estado["corriendo"] = True

    def pause_click(e):
        estado["corriendo"] = False
        guardar_estado_local()

    def stop_click(e):
        estado["corriendo"] = False
        estado["segundos"] = 0
        texto_reloj.value = "00:00"
        texto_reloj.color = ft.Colors.BLUE_200
        texto_alerta_cambio.value = "Partido detenido"
        texto_alerta_cambio.color = ft.Colors.GREY_400
        texto_alerta_limite.value = ""
        guardar_estado_local()
        if texto_reloj.page:
            texto_reloj.update()
            texto_alerta_limite.update()

    def obtener_datos_jugadores():
        archivo_excel = "Equipo_Dunalastairs.xlsx"
        jugadores = []
        if not os.path.exists(archivo_excel): return jugadores
        try:
            df = pd.read_excel(archivo_excel, sheet_name="Plan de Partidos", header=None)
            header_idx = -1
            for idx, row in df.iterrows():
                if "Nombre" in [str(cell).strip() for cell in row.values]:
                    header_idx = idx;
                    break
            if header_idx == -1: return jugadores
            df.columns = df.iloc[header_idx]
            df.columns = [str(c).strip() for c in df.columns]
            df = df[header_idx + 1:]

            for index, row in df.iterrows():
                nombre = str(row.get('Nombre', ''))
                puesto = str(row.get('Puesto', ''))
                rendimiento = str(row.get('Rendimiento', ''))
                if nombre == 'nan' or nombre.strip() == '' or nombre.lower() == 'none': continue
                if puesto.lower() not in ["arquero", "defensa", "medio", "delantero"]: continue

                jugadores.append({"nombre": nombre, "puesto": puesto, "rendimiento": rendimiento})
                if nombre not in estado["minutos_jugadores"]:
                    estado["minutos_jugadores"][nombre] = 0
                if nombre not in estado["minutos_partido_actual"]:
                    estado["minutos_partido_actual"][nombre] = 0

            return jugadores
        except:
            return jugadores

    # --- PANTALLA 1: CONFIGURACIÓN ---
    def view_configuracion():
        tf_partidos = ft.TextField(label="Partidos en el torneo", value=str(estado["config"]["partidos_torneo"]),
                                   keyboard_type=ft.KeyboardType.NUMBER)
        tf_tiempos = ft.TextField(label="Tiempos por partido", value=str(estado["config"]["tiempos_por_partido"]),
                                  keyboard_type=ft.KeyboardType.NUMBER)
        tf_minutos_tiempo = ft.TextField(label="Minutos por tiempo", value=str(estado["config"]["minutos_por_tiempo"]),
                                         keyboard_type=ft.KeyboardType.NUMBER)
        tf_jugadores_cancha = ft.TextField(label="Jugadores en cancha (Titulares)",
                                           value=str(estado["config"]["jugadores_en_cancha"]),
                                           keyboard_type=ft.KeyboardType.NUMBER)

        dd_alto = ft.Dropdown(label="Alto (min)", value=str(estado["config"]["min_alto"]),
                              options=[ft.dropdown.Option("30"), ft.dropdown.Option("40"), ft.dropdown.Option("50")],
                              width=100)
        dd_medio = ft.Dropdown(label="Medio (min)", value=str(estado["config"]["min_medio"]),
                               options=[ft.dropdown.Option("20"), ft.dropdown.Option("30"), ft.dropdown.Option("40")],
                               width=100)
        dd_bajo = ft.Dropdown(label="Bajo (min)", value=str(estado["config"]["min_bajo"]),
                              options=[ft.dropdown.Option("10"), ft.dropdown.Option("20"), ft.dropdown.Option("30")],
                              width=100)

        tf_max_partido = ft.TextField(label="Minutos máx. por jugador por partido",
                                      value=str(estado["config"]["max_min_partido"]),
                                      keyboard_type=ft.KeyboardType.NUMBER)
        texto_balance = ft.Text("", weight=ft.FontWeight.BOLD)
        texto_feedback = ft.Text("", color=ft.Colors.GREEN)

        def calcular_balance():
            try:
                partidos = int(tf_partidos.value)
                tiempos = int(tf_tiempos.value)
                min_tiempo = int(tf_minutos_tiempo.value)
                cancha = int(tf_jugadores_cancha.value)
                alto = int(dd_alto.value)
                medio = int(dd_medio.value)
                bajo = int(dd_bajo.value)

                minutos_partido = tiempos * min_tiempo
                capacidad_total = partidos * minutos_partido * cancha

                jugadores = obtener_datos_jugadores()
                demanda_total = 0
                for j in jugadores:
                    puesto = j["puesto"].lower()
                    rend = j["rendimiento"]
                    if "arquero" in puesto:
                        demanda_total += partidos * minutos_partido
                    elif "0.75" in rend:
                        demanda_total += medio
                    elif "0.5" in rend:
                        demanda_total += bajo
                    else:
                        demanda_total += alto

                diferencia = capacidad_total - demanda_total
                if diferencia >= 0:
                    texto_balance.value = f"🟢 Factible: Disponibles {capacidad_total} min | Requeridos {demanda_total} min"
                    texto_balance.color = ft.Colors.GREEN_400
                else:
                    texto_balance.value = f"🔴 Imposible: Disponibles {capacidad_total} min | Requeridos {demanda_total} min"
                    texto_balance.color = ft.Colors.RED_400
            except:
                texto_balance.value = "⚠️ Ingresa números válidos."
                texto_balance.color = ft.Colors.YELLOW_400

        def al_cambiar_parametro(e):
            calcular_balance()
            page.update()

        tf_partidos.on_change = al_cambiar_parametro
        tf_tiempos.on_change = al_cambiar_parametro
        tf_minutos_tiempo.on_change = al_cambiar_parametro
        tf_jugadores_cancha.on_change = al_cambiar_parametro
        dd_alto.on_change = al_cambiar_parametro
        dd_medio.on_change = al_cambiar_parametro
        dd_bajo.on_change = al_cambiar_parametro

        def guardar_config(e):
            try:
                estado["config"]["partidos_torneo"] = int(tf_partidos.value)
                estado["config"]["tiempos_por_partido"] = int(tf_tiempos.value)
                estado["config"]["minutos_por_tiempo"] = int(tf_minutos_tiempo.value)
                estado["config"]["jugadores_en_cancha"] = int(tf_jugadores_cancha.value)
                estado["config"]["min_alto"] = int(dd_alto.value)
                estado["config"]["min_medio"] = int(dd_medio.value)
                estado["config"]["min_bajo"] = int(dd_bajo.value)
                estado["config"]["max_min_partido"] = int(tf_max_partido.value)
                texto_indicador_partido.value = f"Partido {estado['partido_actual']} de {estado['config']['partidos_torneo']}"
                texto_feedback.value = "✅ Parámetros guardados."
                guardar_estado_local()
                page.update()
            except ValueError:
                texto_feedback.value = "❌ Ingresa valores válidos."
                texto_feedback.color = ft.Colors.RED
                page.update()

        def confirmar_reset(e):
            def cerrar_dlg(ev):
                dialogo_reset.open = False
                page.update()

            def procesar_reset(ev):
                reiniciar_torneo_completo()
                texto_reloj.value = "00:00"
                texto_indicador_partido.value = f"Partido 1 de {estado['config']['partidos_torneo']}"
                texto_feedback.value = "🔄 Torneo reiniciado a 0."
                dialogo_reset.open = False
                page.update()

            dialogo_reset = ft.AlertDialog(
                title=ft.Text("¿Reiniciar Torneo?"),
                content=ft.Text("Esto borrará los minutos acumulados y el progreso del campeonato actual."),
                actions=[
                    ft.TextButton("Cancelar", on_click=cerrar_dlg),
                    ft.ElevatedButton("Sí, Reiniciar", bgcolor=ft.Colors.RED_700, color=ft.Colors.WHITE,
                                      on_click=procesar_reset),
                ],
            )
            page.overlay.append(dialogo_reset)
            dialogo_reset.open = True
            page.update()

        calcular_balance()

        return ft.Column([
            ft.Text("⚙️ Configuración del Torneo", size=24, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            ft.Text("Parámetros Generales", weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_200),
            tf_partidos, tf_tiempos, tf_minutos_tiempo, tf_jugadores_cancha,
            ft.Divider(),
            ft.Text("1. Minutos Objetivo por Rendimiento", weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_200),
            ft.Row([dd_alto, dd_medio, dd_bajo], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Card(
                content=ft.Container(content=texto_balance, padding=10, bgcolor=ft.Colors.GREY_900, border_radius=8)),
            ft.Divider(),
            ft.Text("2. Límites por Partido", weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_200),
            tf_max_partido,
            ft.Divider(),
            ft.Row([
                ft.ElevatedButton("Guardar", icon=ft.Icons.SAVE, width=150, on_click=guardar_config),
                ft.OutlinedButton("Reset Torneo", icon=ft.Icons.DELETE_FOREVER, width=150, icon_color=ft.Colors.RED_400,
                                  on_click=confirmar_reset)
            ], alignment=ft.MainAxisAlignment.SPACE_EVENLY),
            texto_feedback
        ], spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)

    # --- PANTALLA 2: PLANTEL DIVIDIDO ---
    def view_plantel():
        jugadores = obtener_datos_jugadores()
        max_titulares = estado["config"]["jugadores_en_cancha"]
        max_segs_partido = estado["config"]["max_min_partido"] * 60
        mins_partido_total = estado['config']['tiempos_por_partido'] * estado['config']['minutos_por_tiempo']

        texto_contador = ft.Text(
            f"Titulares en cancha: {len(estado['titulares_seleccionados'])} / {max_titulares}",
            color=ft.Colors.GREEN_400, weight=ft.FontWeight.BOLD
        )
        texto_alerta = ft.Text("", color=ft.Colors.RED_400)

        titulares_ui = []
        suplentes_ui = []

        for idx, j in enumerate(jugadores, start=1):
            nombre = j['nombre']
            puesto = j['puesto']

            color_badge = ft.Colors.GREY_700
            if "arquero" in puesto.lower():
                color_badge = ft.Colors.AMBER_800
            elif "defensa" in puesto.lower():
                color_badge = ft.Colors.BLUE_800
            elif "medio" in puesto.lower():
                color_badge = ft.Colors.GREEN_800
            elif "delantero" in puesto.lower():
                color_badge = ft.Colors.RED_800

            es_titular = nombre in estado["titulares_seleccionados"]
            segs_jugados_hoy = estado["minutos_partido_actual"].get(nombre, 0)
            mins_jugados_hoy = segs_jugados_hoy // 60

            es_arquero = "arquero" in puesto.lower()
            alcanzo_limite = (not es_arquero) and (segs_jugados_hoy >= max_segs_partido)

            if es_arquero:
                texto_tiempo = f"En este partido: {mins_jugados_hoy}/{mins_partido_total} min (Arquero)"
                subtexto_color = ft.Colors.GREY_400
            else:
                texto_tiempo = f"En este partido: {mins_jugados_hoy}/{estado['config']['max_min_partido']} min"
                if alcanzo_limite: texto_tiempo += " ⚠️ (MÁXIMO)"
                subtexto_color = ft.Colors.RED_400 if alcanzo_limite else ft.Colors.GREY_400

            def crear_on_change(nom):
                def on_change(e):
                    limite = estado["config"]["jugadores_en_cancha"]
                    if e.control.value:
                        if len(estado["titulares_seleccionados"]) < limite:
                            if nom not in estado["titulares_seleccionados"]:
                                estado["titulares_seleccionados"].append(nom)
                            texto_alerta.value = ""
                        else:
                            e.control.value = False
                            texto_alerta.value = f"⚠️ Máximo {limite} jugadores en cancha."
                    else:
                        if nom in estado["titulares_seleccionados"]:
                            estado["titulares_seleccionados"].remove(nom)
                        texto_alerta.value = ""

                    guardar_estado_local()
                    main_container.content = view_plantel()
                    page.update()

                return on_change

            switch_titular = ft.Switch(value=es_titular, on_change=crear_on_change(nombre))

            fila_jugador = ft.Container(
                content=ft.Row([
                    ft.Container(
                        content=ft.Text(f"#{idx}", weight=ft.FontWeight.BOLD, size=11, color=ft.Colors.BLUE_200),
                        bgcolor=ft.Colors.GREY_800, padding=6, border_radius=10
                    ),
                    ft.Column([
                        ft.Row([
                            ft.Text(nombre, weight=ft.FontWeight.BOLD, size=15),
                            ft.Container(
                                content=ft.Text(puesto.upper(), size=9, weight=ft.FontWeight.BOLD),
                                bgcolor=color_badge, padding=4, border_radius=5
                            )
                        ], spacing=6),
                        ft.Text(texto_tiempo, color=subtexto_color, size=11,
                                weight=ft.FontWeight.BOLD if alcanzo_limite else ft.FontWeight.NORMAL)
                    ], expand=True, spacing=2),
                    switch_titular
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                padding=4
            )

            if es_titular:
                titulares_ui.append(fila_jugador)
            else:
                suplentes_ui.append(fila_jugador)

        return ft.Column([
            ft.Text("📋 Plantel y Rotaciones", size=24, weight=ft.FontWeight.BOLD),
            texto_contador,
            texto_alerta,
            ft.Divider(),

            ft.Text(f"🟢 TITULARES EN CANCHA ({len(titulares_ui)})", weight=ft.FontWeight.BOLD,
                    color=ft.Colors.GREEN_400),
            ft.Container(
                content=ft.Column(controls=titulares_ui if titulares_ui else [
                    ft.Text("Sin titulares seleccionados", color=ft.Colors.GREY_500)]),
                bgcolor=ft.Colors.GREY_900, padding=10, border_radius=10
            ),

            ft.Divider(),

            ft.Text(f"🟡 BANCA / SUPLENTES ({len(suplentes_ui)})", weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER_400),
            ft.Container(
                content=ft.Column(controls=suplentes_ui if suplentes_ui else [
                    ft.Text("Toda la plantilla está en cancha", color=ft.Colors.GREY_500)]),
                bgcolor=ft.Colors.GREY_900, padding=10, border_radius=10
            )
        ], scroll=ft.ScrollMode.AUTO, expand=True)

    # --- PANTALLA 3: PARTIDO EN VIVO ---
    def view_partido():
        texto_reloj.value = formatear_tiempo(estado["segundos"])
        texto_indicador_partido.value = f"Partido {estado['partido_actual']} de {estado['config']['partidos_torneo']}"

        def partido_anterior(e):
            if estado["partido_actual"] > 1 and not estado["corriendo"]:
                estado["partido_actual"] -= 1
                estado["segundos"] = 0
                for k in estado["minutos_partido_actual"]: estado["minutos_partido_actual"][k] = 0
                texto_reloj.value = "00:00"
                texto_indicador_partido.value = f"Partido {estado['partido_actual']} de {estado['config']['partidos_torneo']}"
                texto_alerta_limite.value = ""
                guardar_estado_local()
                page.update()

        def partido_siguiente(e):
            if estado["partido_actual"] < estado["config"]["partidos_torneo"] and not estado["corriendo"]:
                estado["partido_actual"] += 1
                estado["segundos"] = 0
                for k in estado["minutos_partido_actual"]: estado["minutos_partido_actual"][k] = 0
                texto_reloj.value = "00:00"
                texto_indicador_partido.value = f"Partido {estado['partido_actual']} de {estado['config']['partidos_torneo']}"
                texto_alerta_limite.value = ""
                guardar_estado_local()
                page.update()

        return ft.Column([
            ft.Text("⏱️ Partido en Vivo", size=24, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            ft.Row([
                ft.IconButton(icon=ft.Icons.ARROW_BACK_IOS, on_click=partido_anterior),
                texto_indicador_partido,
                ft.IconButton(icon=ft.Icons.ARROW_FORWARD_IOS, on_click=partido_siguiente),
            ], alignment=ft.MainAxisAlignment.CENTER),
            ft.Container(content=texto_reloj, alignment="center", padding=5),
            ft.Container(content=texto_alerta_limite, alignment="center", padding=2),
            ft.Container(content=texto_alerta_cambio, alignment="center", padding=2),
            ft.Row([
                ft.IconButton(icon=ft.Icons.PLAY_ARROW_ROUNDED, icon_size=50, icon_color=ft.Colors.GREEN,
                              on_click=play_click),
                ft.IconButton(icon=ft.Icons.PAUSE_ROUNDED, icon_size=50, icon_color=ft.Colors.ORANGE,
                              on_click=pause_click),
                ft.IconButton(icon=ft.Icons.STOP_ROUNDED, icon_size=50, icon_color=ft.Colors.RED, on_click=stop_click),
            ], alignment=ft.MainAxisAlignment.CENTER),
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("ℹ️ Gestión de Tiempo por Partido", weight=ft.FontWeight.BOLD),
                        ft.Text(f"• Límite por jugador de campo hoy: {estado['config']['max_min_partido']} min."),
                        ft.Text("• Al sonar la alarma, conmuta en Plantel los jugadores activos.")
                    ]), padding=12, bgcolor=ft.Colors.GREY_900, border_radius=8
                )
            )
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    # --- PANTALLA 4: DASHBOARD DE MINUTOS ---
    def view_minutos():
        jugadores = obtener_datos_jugadores()
        stats_ui = []
        texto_export = ft.Text("", color=ft.Colors.GREEN_400)

        def click_exportar(e):
            if exportar_a_excel(jugadores):
                texto_export.value = "✅ 'Reporte_Minutos_Final.xlsx' generado con éxito."
            else:
                texto_export.value = "❌ Error al generar el Excel."
            page.update()

        jugadores_ordenados = sorted(
            jugadores,
            key=lambda x: estado["minutos_jugadores"].get(x['nombre'], 0),
            reverse=True
        )

        for idx, j in enumerate(jugadores_ordenados, start=1):
            nombre = j['nombre']
            rendimiento = j['rendimiento']
            puesto = j['puesto']

            segs_acumulados = estado["minutos_jugadores"].get(nombre, 0)
            minutos_jugados = segs_acumulados // 60

            if "arquero" in puesto.lower():
                meta_minutos = estado["config"]["partidos_torneo"] * estado["config"]["tiempos_por_partido"] * \
                               estado["config"]["minutos_por_tiempo"]
            elif '0.75' in rendimiento:
                meta_minutos = estado["config"]["min_medio"]
            elif '0.5' in rendimiento:
                meta_minutos = estado["config"]["min_bajo"]
            else:
                meta_minutos = estado["config"]["min_alto"]

            porcentaje = 0.0 if meta_minutos == 0 else minutos_jugados / meta_minutos
            if porcentaje > 1.0: porcentaje = 1.0

            color_barra = ft.Colors.RED_400
            if porcentaje >= 1.0:
                color_barra = ft.Colors.GREEN_400
            elif porcentaje >= 0.5:
                color_barra = ft.Colors.AMBER_400

            tarjeta_jugador = ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Container(
                                content=ft.Text(f"#{idx}", weight=ft.FontWeight.BOLD, size=12,
                                                color=ft.Colors.BLUE_200),
                                bgcolor=ft.Colors.GREY_800, padding=6, border_radius=10
                            ),
                            ft.Column([
                                ft.Text(nombre, weight=ft.FontWeight.BOLD, size=14),
                                ft.Text(puesto, size=11, color=ft.Colors.GREY_400)
                            ], expand=True, spacing=1),
                            ft.Text(f"{minutos_jugados}/{meta_minutos} min", color=color_barra,
                                    weight=ft.FontWeight.BOLD, size=13)
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.ProgressBar(value=porcentaje, color=color_barra, bgcolor=ft.Colors.GREY_900, height=6)
                    ], spacing=8), padding=12, bgcolor=ft.Colors.GREY_900, border_radius=8
                )
            )
            stats_ui.append(tarjeta_jugador)

        return ft.Column([
            ft.Text("📊 Ranking de Minutos", size=24, weight=ft.FontWeight.BOLD),
            ft.ElevatedButton("Exportar Reporte a Excel", icon=ft.Icons.EXPLICIT, width=300, on_click=click_exportar),
            texto_export,
            ft.Divider(),
            ft.Column(controls=stats_ui, scroll=ft.ScrollMode.AUTO, expand=True)
        ], expand=True)

    main_container = ft.Container(content=view_configuracion(), expand=True, padding=20)

    def cambiar_pantalla(indice):
        if indice == 0:
            main_container.content = view_configuracion()
        elif indice == 1:
            main_container.content = view_plantel()
        elif indice == 2:
            main_container.content = view_partido()
        elif indice == 3:
            main_container.content = view_minutos()
        page.update()

    def abrir_dialogo_salir(e):
        def confirmar_salida(ev):
            dlg_salir.open = False
            page.update()

        def cancelar_salida(ev):
            dlg_salir.open = False
            page.update()

        dlg_salir = ft.AlertDialog(
            title=ft.Text("¿Deseas salir?"),
            content=ft.Text("El estado actual del torneo ha sido guardado automáticamente."),
            actions=[
                ft.TextButton("Cancelar", on_click=cancelar_salida),
                ft.ElevatedButton("Cerrar AVISO", bgcolor=ft.Colors.RED_700, color=ft.Colors.WHITE,
                                  on_click=confirmar_salida),
            ]
        )
        page.overlay.append(dlg_salir)
        dlg_salir.open = True
        page.update()

    bottom_nav = ft.Container(
        bgcolor=ft.Colors.GREY_900, padding=10,
        content=ft.Row(
            controls=[
                ft.IconButton(icon=ft.Icons.SETTINGS, on_click=lambda e: cambiar_pantalla(0), tooltip="Configuración"),
                ft.IconButton(icon=ft.Icons.PEOPLE, on_click=lambda e: cambiar_pantalla(1), tooltip="Plantel"),
                ft.IconButton(icon=ft.Icons.SPORTS_SOCCER, on_click=lambda e: cambiar_pantalla(2), tooltip="Partido"),
                ft.IconButton(icon=ft.Icons.BAR_CHART, on_click=lambda e: cambiar_pantalla(3),
                              tooltip="Ranking Minutos"),
                ft.IconButton(icon=ft.Icons.EXIT_TO_APP, icon_color=ft.Colors.RED_400, on_click=abrir_dialogo_salir,
                              tooltip="Salir"),
            ], alignment=ft.MainAxisAlignment.SPACE_AROUND,
        )
    )

    app_layout = ft.Container(
        width=450,
        expand=True,
        bgcolor=ft.Colors.GREY_900,
        content=ft.Column(
            controls=[main_container, bottom_nav],
            expand=True,
            spacing=0
        )
    )

    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.bgcolor = ft.Colors.BLACK
    page.add(app_layout)


if __name__ == "__main__":
    puerto = int(os.environ.get("PORT", 8080))
    ft.app(target=main, host="0.0.0.0", port=puerto, view=ft.AppView.WEB_BROWSER)