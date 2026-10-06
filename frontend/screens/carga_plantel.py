import io
import os
from typing import List, Dict, Any, Optional
import flet as ft

from config.constants import (
    COLOR_TARJETA, COLOR_BORDE, COLOR_CELESTE, COLOR_CELESTE_BOTON,
    COLOR_TEXTO, COLOR_SUBTEXTO, COLOR_VERDE, COLOR_ROJO, COLOR_AMBAR, COLOR_FONDO
)
from backend.services.jugador_service import JugadorService
from utils.import_utils import (
    parsear_texto_plantel, parsear_archivo_plantel, generar_plantilla_excel
)


def mostrar_dialogo_carga_plantel(page: ft.Page, estado: dict, callbacks: dict):
    """
    Abre un diálogo modal para importar masivamente jugadores mediante:
      1. Pegado de texto libre / WhatsApp
      2. Carga de archivo Excel (.xlsx, .xls) o CSV
    """
    if estado.get("es_invitado", True):
        page.open(
            ft.SnackBar(
                content=ft.Text("⚠️ Solo el Administrador puede importar jugadores."),
                bgcolor=COLOR_AMBAR,
                open=True,
            )
        )
        return

    equipo_activo = estado.get("equipo_activo") or estado.get("config", {}).get("equipo_principal", "Real Dunalastair")
    fecha_activa = estado.get("fecha_filtro", "")

    jugadores_db = JugadorService.obtener_todos_ordenados(equipo=equipo_activo, fecha=fecha_activa)
    jugadores_actuales = {j["nombre"].lower(): j for j in jugadores_db}
    
    # Si ya existe un plantel cargado en la BD, precargar por defecto
    if jugadores_db:
        jugadores_detectados: List[Dict[str, str]] = [
            {"numero": str(j["numero"]), "nombre": j["nombre"], "puesto": j["puesto"]}
            for j in jugadores_db
        ]
        texto_inicial_whatsapp = "\n".join(
            [f"{j['numero']}. {j['nombre']} ({j['puesto']})" for j in jugadores_db]
        )
    else:
        jugadores_detectados: List[Dict[str, str]] = []
        texto_inicial_whatsapp = ""
    
    # Estado local del diálogo
    tab_actual = [0]  # 0: WhatsApp / Texto, 1: Archivo Excel
    reemplazar_todo = [False]

    # Controles de la Pestaña 1 (WhatsApp / Texto)
    tf_whatsapp = ft.TextField(
        value=texto_inicial_whatsapp,
        multiline=True,
        min_lines=6,
        max_lines=9,
        hint_text=(
            "Pega aquí la lista de WhatsApp. Ej:\n"
            "🧤 1. Claudio Bravo (ARQ)\n"
            "4. Mauricio Isla - Defensa\n"
            "8. Arturo Vidal - MED\n"
            "7 Alexis Sánchez (DEL)"
        ),
        hint_style=ft.TextStyle(color=COLOR_SUBTEXTO, size=12),
        border_color=COLOR_BORDE,
        focused_border_color=COLOR_CELESTE,
        border_radius=10,
        text_size=13,
    )

    texto_ejemplo_whatsapp = (
        "1. Claudio Bravo (ARQ)\n"
        "4. Mauricio Isla (DEF)\n"
        "17. Gary Medel (DEF)\n"
        "8. Arturo Vidal (MED)\n"
        "20. Charles Aránguiz (MED)\n"
        "10. Jorge Valdivia (MED)\n"
        "7. Alexis Sánchez (DEL)\n"
        "11. Eduardo Vargas (DEL)"
    )

    def insertar_ejemplo(e):
        tf_whatsapp.value = texto_ejemplo_whatsapp
        page.update()

    def restaurar_actual(e):
        nonlocal jugadores_detectados
        if jugadores_db:
            jugadores_detectados = [
                {"numero": str(j["numero"]), "nombre": j["nombre"], "puesto": j["puesto"]}
                for j in jugadores_db
            ]
            tf_whatsapp.value = "\n".join(
                [f"{j['numero']}. {j['nombre']} ({j['puesto']})" for j in jugadores_db]
            )
        else:
            jugadores_detectados = []
            tf_whatsapp.value = ""
        refrescar_vista_previa()
        page.update()

    def limpiar_texto(e):
        nonlocal jugadores_detectados
        tf_whatsapp.value = ""
        jugadores_detectados = []
        refrescar_vista_previa()
        page.update()

    def analizar_texto_whatsapp(e):
        nonlocal jugadores_detectados
        texto = tf_whatsapp.value or ""
        jugadores_detectados = parsear_texto_plantel(texto)
        refrescar_vista_previa()
        page.update()

    # Controles de la Pestaña 2 (Excel / CSV)
    texto_archivo_seleccionado = ft.Text("Ningún archivo seleccionado aún", size=12, color=COLOR_SUBTEXTO)
    
    def on_file_picked(e: ft.FilePickerResultEvent):
        nonlocal jugadores_detectados
        if not e.files or len(e.files) == 0:
            return
        
        file_info = e.files[0]
        fname = file_info.name
        texto_archivo_seleccionado.value = f"📄 Archivo: {fname}"
        texto_archivo_seleccionado.color = COLOR_CELESTE

        try:
            if file_info.bytes:
                jugadores_detectados = parsear_archivo_plantel(io.BytesIO(file_info.bytes), fname)
            elif file_info.path:
                with open(file_info.path, "rb") as f_obj:
                    jugadores_detectados = parsear_archivo_plantel(f_obj, fname)
            else:
                jugadores_detectados = []
        except Exception as ex:
            jugadores_detectados = []
            texto_archivo_seleccionado.value = f"❌ Error leyendo archivo: {ex}"
            texto_archivo_seleccionado.color = COLOR_ROJO

        refrescar_vista_previa()
        page.update()

    file_picker = ft.FilePicker(on_result=on_file_picked)
    if file_picker not in page.overlay:
        page.overlay.append(file_picker)

    def descargar_plantilla(e):
        try:
            bytes_excel = generar_plantilla_excel()
            # Guardar plantilla de ejemplo en la raíz del proyecto para fácil acceso
            ruta_plantilla = os.path.join(os.getcwd(), "plantilla_plantel.xlsx")
            with open(ruta_plantilla, "wb") as f_out:
                f_out.write(bytes_excel)
            
            page.open(
                ft.SnackBar(
                    content=ft.Text("✅ Plantilla generada y guardada como 'plantilla_plantel.xlsx'"),
                    bgcolor=COLOR_VERDE,
                    open=True,
                )
            )
        except Exception as ex:
            page.open(
                ft.SnackBar(
                    content=ft.Text(f"❌ Error generando plantilla: {ex}"),
                    bgcolor=COLOR_ROJO,
                    open=True,
                )
            )

    # Vista previa y opciones
    col_vista_previa = ft.Column(spacing=4, scroll=ft.ScrollMode.ADAPTIVE)
    contenedor_vista_previa = ft.Container(
        content=col_vista_previa,
        height=180,
        bgcolor=COLOR_FONDO,
        border_radius=10,
        padding=8,
        border=ft.border.all(1, COLOR_BORDE),
    )
    texto_resumen_previa = ft.Text("Vista previa (0 detectados)", size=12, weight=ft.FontWeight.BOLD, color=COLOR_TEXTO)

    cb_reemplazar = ft.Checkbox(
        label="Reemplazar plantel completo (Elimina la nómina actual)",
        value=False,
        active_color=COLOR_ROJO,
        check_color=COLOR_TEXTO,
        label_style=ft.TextStyle(size=12, color=COLOR_SUBTEXTO),
    )

    def on_reemplazar_change(e):
        reemplazar_todo[0] = bool(cb_reemplazar.value)
        if reemplazar_todo[0]:
            cb_reemplazar.label_style = ft.TextStyle(size=12, color=COLOR_ROJO, weight=ft.FontWeight.BOLD)
        else:
            cb_reemplazar.label_style = ft.TextStyle(size=12, color=COLOR_SUBTEXTO)
        page.update()

    cb_reemplazar.on_change = on_reemplazar_change

    btn_guardar = ft.ElevatedButton(
        "💾 Guardar Plantel (0)",
        icon=ft.Icons.SAVE,
        bgcolor=COLOR_VERDE,
        color=COLOR_TEXTO,
        disabled=True,
    )

    def refrescar_vista_previa():
        col_vista_previa.controls.clear()
        total = len(jugadores_detectados)
        texto_resumen_previa.value = f"👥 Vista Previa: {total} jugadores detectados"
        btn_guardar.text = f"💾 Guardar Plantel ({total})"
        btn_guardar.disabled = (total == 0)

        if total == 0:
            col_vista_previa.controls.append(
                ft.Container(
                    content=ft.Text("Sin jugadores detectados. Ingresa texto o sube un archivo.", color=COLOR_SUBTEXTO, size=12),
                    padding=10,
                    alignment=ft.alignment.center,
                )
            )
            return

        for j in jugadores_detectados:
            nom = j["nombre"]
            num = j["numero"]
            puesto = j["puesto"]
            es_existente = nom.lower() in jugadores_actuales

            badge_estado = ft.Container(
                content=ft.Text("🔄 Actualiza" if es_existente else "✨ Nuevo", size=10, color=COLOR_TEXTO, weight=ft.FontWeight.BOLD),
                bgcolor=COLOR_AMBAR if es_existente else COLOR_VERDE,
                padding=ft.Padding(6, 2, 6, 2),
                border_radius=6,
            )

            fila_j = ft.Container(
                content=ft.Row([
                    ft.Container(
                        content=ft.Text(f"#{num}", size=11, weight=ft.FontWeight.BOLD, color=COLOR_CELESTE),
                        bgcolor=COLOR_BORDE,
                        padding=ft.Padding(6, 2, 6, 2),
                        border_radius=6,
                        width=38,
                        alignment=ft.alignment.center,
                    ),
                    ft.Text(nom, size=12, weight=ft.FontWeight.BOLD, color=COLOR_TEXTO, expand=True),
                    ft.Text(puesto, size=11, color=COLOR_SUBTEXTO),
                    badge_estado,
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, spacing=6),
                padding=ft.Padding(4, 2, 4, 2),
            )
            col_vista_previa.controls.append(fila_j)

    refrescar_vista_previa()

    # Contenedores de pestañas
    fila_acciones_texto = ft.Row([
        ft.Text("Lista de jugadores:", size=12, weight=ft.FontWeight.BOLD, color=COLOR_CELESTE),
        ft.Row([
            ft.TextButton("🔄 Restaurar", tooltip="Recargar plantel actual", on_click=restaurar_actual),
            ft.TextButton("📋 Ejemplo", tooltip="Cargar lista de ejemplo", on_click=insertar_ejemplo),
            ft.TextButton("🧹 Limpiar", tooltip="Limpiar texto", on_click=limpiar_texto),
        ], spacing=2),
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    contenido_tab_whatsapp = ft.Column([
        fila_acciones_texto,
        tf_whatsapp,
        ft.Row([
            ft.ElevatedButton(
                "🔍 Analizar Lista",
                icon=ft.Icons.AUTO_AWESOME,
                bgcolor=COLOR_CELESTE_BOTON,
                color=COLOR_TEXTO,
                on_click=analizar_texto_whatsapp,
                tooltip="Detectar jugadores y actualizar vista previa",
            ),
        ]),
    ], spacing=8)

    contenido_tab_excel = ft.Column([
        ft.Text("Cargar archivo Excel (.xlsx, .xls) o CSV:", size=12, weight=ft.FontWeight.BOLD, color=COLOR_CELESTE),
        ft.Row([
            ft.ElevatedButton(
                "📁 Seleccionar Archivo",
                icon=ft.Icons.UPLOAD_FILE,
                bgcolor=COLOR_CELESTE_BOTON,
                color=COLOR_TEXTO,
                on_click=lambda _: file_picker.pick_files(
                    allowed_extensions=["xlsx", "xls", "csv"],
                    dialog_title="Seleccionar archivo de Plantel"
                ),
            ),
            ft.OutlinedButton(
                "📥 Descargar Plantilla",
                icon=ft.Icons.DOWNLOAD,
                on_click=descargar_plantilla,
            ),
        ], spacing=10),
        texto_archivo_seleccionado,
    ], spacing=10)

    contenedor_contenido_tab = ft.Container(
        content=contenido_tab_whatsapp,
        padding=4,
    )

    btn_tab_whatsapp = ft.ElevatedButton(
        "💬 WhatsApp / Texto",
        icon=ft.Icons.CHAT,
        bgcolor=COLOR_CELESTE_BOTON,
        color=COLOR_TEXTO,
    )
    btn_tab_excel = ft.OutlinedButton(
        "📊 Archivo Excel / CSV",
        icon=ft.Icons.TABLE_CHART,
    )

    def cambiar_tab(indice):
        tab_actual[0] = indice
        if indice == 0:
            btn_tab_whatsapp.style = ft.ButtonStyle(bgcolor=COLOR_CELESTE_BOTON, color=COLOR_TEXTO)
            btn_tab_excel.style = ft.ButtonStyle(bgcolor=ft.Colors.TRANSPARENT, color=COLOR_SUBTEXTO)
            contenedor_contenido_tab.content = contenido_tab_whatsapp
        else:
            btn_tab_whatsapp.style = ft.ButtonStyle(bgcolor=ft.Colors.TRANSPARENT, color=COLOR_SUBTEXTO)
            btn_tab_excel.style = ft.ButtonStyle(bgcolor=COLOR_CELESTE_BOTON, color=COLOR_TEXTO)
            contenedor_contenido_tab.content = contenido_tab_excel
        page.update()

    btn_tab_whatsapp.on_click = lambda e: cambiar_tab(0)
    btn_tab_excel.on_click = lambda e: cambiar_tab(1)

    def guardar_plantel_bd(e):
        if not jugadores_detectados:
            return

        reemplazar = bool(cb_reemplazar.value)
        insertados, actualizados = JugadorService.importar_plantel(
            jugadores_detectados,
            equipo=equipo_activo,
            fecha=fecha_activa,
            reemplazar=reemplazar,
            es_invitado=estado.get("es_invitado", False),
        )

        page.close(dialogo_carga)
        callbacks["refrescar_vistas"]()
        page.update()

        msg = f"✅ Carga masiva exitosa ({equipo_activo}): {insertados} agregados, {actualizados} actualizados."
        if reemplazar:
            msg = f"✅ Plantel de {equipo_activo} reemplazado con éxito ({insertados} jugadores)."

        page.open(
            ft.SnackBar(
                content=ft.Text(msg),
                bgcolor=COLOR_VERDE,
                open=True,
            )
        )

    btn_guardar.on_click = guardar_plantel_bd

    def cerrar_dialogo(e):
        page.close(dialogo_carga)

    dialogo_carga = ft.AlertDialog(
        title=ft.Row([
            ft.Icon(ft.Icons.FLASH_ON, color=COLOR_CELESTE, size=24),
            ft.Text(f"Carga Rápida de Plantel ({equipo_activo})", weight=ft.FontWeight.BOLD, color=COLOR_TEXTO, size=16),
        ], spacing=8),
        content=ft.Container(
            content=ft.Column([
                ft.Row([btn_tab_whatsapp, btn_tab_excel], spacing=10),
                ft.Divider(color=COLOR_BORDE),
                contenedor_contenido_tab,
                ft.Divider(color=COLOR_BORDE),
                texto_resumen_previa,
                contenedor_vista_previa,
                cb_reemplazar,
            ], spacing=8, tight=True, scroll=ft.ScrollMode.ADAPTIVE),
            width=540,
        ),
        actions=[
            ft.TextButton("Cancelar", on_click=cerrar_dialogo),
            btn_guardar,
        ],
        bgcolor=COLOR_TARJETA,
        modal=True,
    )

    page.open(dialogo_carga)
