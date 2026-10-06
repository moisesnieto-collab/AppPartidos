from typing import List, Dict, Any, Optional
import flet as ft

from config.constants import (
    COLOR_TARJETA, COLOR_BORDE, COLOR_CELESTE, COLOR_CELESTE_BOTON,
    COLOR_TEXTO, COLOR_SUBTEXTO, COLOR_VERDE, COLOR_ROJO, COLOR_AMBAR, COLOR_FONDO
)
from backend.services.usuario_service import UsuarioService


def mostrar_dialogo_admin_usuarios(page: ft.Page, estado: dict, callbacks: dict):
    """
    Abre un diálogo modal para que el SuperAdministrador gestione los
    Administradores de Equipo (Delegados) por RUT y Club asignado.
    """
    es_superadmin = estado.get("es_superadmin", False)
    if not es_superadmin:
        page.open(
            ft.SnackBar(
                content=ft.Text("⚠️ Solo el SuperAdministrador puede gestionar administradores de equipo."),
                bgcolor=COLOR_AMBAR,
                open=True,
            )
        )
        return

    # Extraer lista de equipos disponibles en el día
    equipos_disponibles = set()
    grupos_dia = estado.get("grupos_dia", [])
    for g in grupos_dia:
        grupo_obj = g.get("grupo", {})
        if grupo_obj.get("equipo_principal"):
            equipos_disponibles.add(grupo_obj["equipo_principal"])
        for eq in grupo_obj.get("equipos", []):
            if eq:
                equipos_disponibles.add(eq)
    
    # Agregar equipo por defecto si está vacío
    if not equipos_disponibles:
        equipos_disponibles.add("Real Dunalastair")

    # Controles del formulario
    tf_rut = ft.TextField(
        label="RUT (sin puntos ni guion)",
        hint_text="Ej: 12345678K",
        width=180,
        text_size=13,
        border_color=COLOR_BORDE,
        focused_border_color=COLOR_CELESTE,
        border_radius=8,
    )

    tf_nombre = ft.TextField(
        label="Nombre / Contacto",
        hint_text="Ej: Juan Pérez (DT)",
        width=200,
        text_size=13,
        border_color=COLOR_BORDE,
        focused_border_color=COLOR_CELESTE,
        border_radius=8,
    )

    dd_equipo = ft.Dropdown(
        label="Equipo Asignado",
        options=[ft.dropdown.Option(eq) for eq in sorted(equipos_disponibles)] + [ft.dropdown.Option("Otro / Personalizado")],
        value=sorted(equipos_disponibles)[0] if equipos_disponibles else "Real Dunalastair",
        width=200,
        text_size=13,
        border_color=COLOR_BORDE,
        focused_border_color=COLOR_CELESTE,
        border_radius=8,
    )

    tf_equipo_custom = ft.TextField(
        label="Nombre de Equipo Personalizado",
        hint_text="Ej: Colo-Colo",
        width=200,
        text_size=13,
        border_color=COLOR_BORDE,
        focused_border_color=COLOR_CELESTE,
        border_radius=8,
        visible=False,
    )

    sw_superadmin = ft.Switch(
        label="SuperAdministrador",
        value=False,
        active_color=COLOR_CELESTE,
    )

    texto_mensaje = ft.Text("", size=12, color=COLOR_VERDE)

    def on_cambio_dropdown_equipo(e):
        tf_equipo_custom.visible = (dd_equipo.value == "Otro / Personalizado")
        page.update()

    dd_equipo.on_change = on_cambio_dropdown_equipo

    lista_usuarios_col = ft.Column(spacing=8, scroll=ft.ScrollMode.ADAPTIVE)

    def limpiar_formulario():
        tf_rut.value = ""
        tf_rut.disabled = False
        tf_nombre.value = ""
        if equipos_disponibles:
            dd_equipo.value = sorted(equipos_disponibles)[0]
        tf_equipo_custom.value = ""
        tf_equipo_custom.visible = False
        sw_superadmin.value = False
        texto_mensaje.value = ""

    def cargar_lista_usuarios():
        lista_usuarios_col.controls.clear()
        usuarios = UsuarioService.obtener_todos_delegados()
        
        if not usuarios:
            lista_usuarios_col.controls.append(
                ft.Text("No hay administradores registrados.", size=12, color=COLOR_SUBTEXTO)
            )
            return

        for u in usuarios:
            rut_u = u["rut"]
            nom_u = u["nombre_contacto"]
            eq_u = u["equipo_asignado"]
            es_super_u = u["es_superadmin"]

            es_principal_fijo = (rut_u == "11165045")

            def editar_usuario(u_datos=u):
                tf_rut.value = u_datos["rut"]
                tf_rut.disabled = True
                tf_nombre.value = u_datos["nombre_contacto"]
                if u_datos["equipo_asignado"] in [opt.key for opt in dd_equipo.options if opt.key != "Otro / Personalizado"]:
                    dd_equipo.value = u_datos["equipo_asignado"]
                    tf_equipo_custom.visible = False
                else:
                    dd_equipo.value = "Otro / Personalizado"
                    tf_equipo_custom.value = u_datos["equipo_asignado"]
                    tf_equipo_custom.visible = True
                sw_superadmin.value = u_datos["es_superadmin"]
                texto_mensaje.value = f"✏️ Editando administrador {u_datos['rut']}"
                texto_mensaje.color = COLOR_CELESTE
                page.update()

            def confirmar_eliminar_usuario(rut_eliminar=rut_u, nom_eliminar=nom_u):
                def ejecutar_eliminar(e):
                    ok, msg = UsuarioService.eliminar_delegado(rut_eliminar, solicitante_es_superadmin=True)
                    page.close(dlg_confirm)
                    if ok:
                        texto_mensaje.value = f"✅ Administrador {nom_eliminar} eliminado."
                        texto_mensaje.color = COLOR_VERDE
                        limpiar_formulario()
                        cargar_lista_usuarios()
                    else:
                        texto_mensaje.value = f"❌ {msg}"
                        texto_mensaje.color = COLOR_ROJO
                    page.update()

                dlg_confirm = ft.AlertDialog(
                    title=ft.Text("Eliminar Administrador", color=COLOR_TEXTO),
                    content=ft.Text(f"¿Está seguro de eliminar al delegado {nom_eliminar} (RUT: {rut_eliminar})?", color=COLOR_SUBTEXTO),
                    actions=[
                        ft.TextButton("Cancelar", on_click=lambda e: page.close(dlg_confirm)),
                        ft.ElevatedButton("Eliminar", bgcolor=COLOR_ROJO, color=COLOR_TEXTO, on_click=ejecutar_eliminar),
                    ],
                    bgcolor=COLOR_TARJETA,
                )
                page.open(dlg_confirm)

            badge_rol = ft.Container(
                content=ft.Text(
                    "👑 SuperAdmin" if es_super_u else "🛡️ Delegado",
                    size=10,
                    weight=ft.FontWeight.BOLD,
                    color=COLOR_VERDE if es_super_u else COLOR_CELESTE,
                ),
                bgcolor=ft.Colors.with_opacity(0.15, COLOR_VERDE if es_super_u else COLOR_CELESTE),
                border=ft.border.all(1, COLOR_VERDE if es_super_u else COLOR_CELESTE),
                border_radius=6,
                padding=ft.padding.symmetric(horizontal=6, vertical=2),
            )

            fila_item = ft.Container(
                content=ft.Row([
                    ft.Column([
                        ft.Row([
                            ft.Text(f"{nom_u}", size=13, weight=ft.FontWeight.BOLD, color=COLOR_TEXTO),
                            badge_rol,
                        ], spacing=6),
                        ft.Text(f"RUT: {rut_u}  •  Equipo: {eq_u}", size=11, color=COLOR_SUBTEXTO),
                    ], spacing=2, expand=True),
                    ft.Row([
                        ft.IconButton(
                            icon=ft.Icons.EDIT,
                            icon_size=16,
                            icon_color=COLOR_CELESTE,
                            tooltip="Editar",
                            on_click=lambda e, u_d=u: editar_usuario(u_d),
                        ),
                        ft.IconButton(
                            icon=ft.Icons.DELETE_OUTLINE,
                            icon_size=16,
                            icon_color=COLOR_ROJO,
                            tooltip="Eliminar",
                            disabled=es_principal_fijo,
                            on_click=lambda e, r=rut_u, n=nom_u: confirmar_eliminar_usuario(r, n),
                        ),
                    ], spacing=0),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                bgcolor=COLOR_FONDO,
                border=ft.border.all(1, COLOR_BORDE),
                border_radius=8,
                padding=ft.padding.symmetric(horizontal=10, vertical=8),
            )
            lista_usuarios_col.controls.append(fila_item)

    def guardar_usuario(e):
        rut_val = tf_rut.value.strip()
        nom_val = tf_nombre.value.strip()
        
        if dd_equipo.value == "Otro / Personalizado":
            eq_val = tf_equipo_custom.value.strip()
        else:
            eq_val = dd_equipo.value.strip() if dd_equipo.value else ""

        es_super_val = sw_superadmin.value

        ok, msg = UsuarioService.guardar_delegado(
            rut=rut_val,
            nombre_contacto=nom_val,
            equipo_asignado=eq_val,
            es_superadmin=es_super_val,
            solicitante_es_superadmin=True,
        )

        if ok:
            texto_mensaje.value = "✅ Administrador guardado exitosamente."
            texto_mensaje.color = COLOR_VERDE
            limpiar_formulario()
            cargar_lista_usuarios()
        else:
            texto_mensaje.value = f"❌ {msg}"
            texto_mensaje.color = COLOR_ROJO
        page.update()

    btn_guardar = ft.ElevatedButton(
        "💾 Guardar Administrador",
        icon=ft.Icons.SAVE,
        bgcolor=COLOR_CELESTE_BOTON,
        color=COLOR_TEXTO,
        on_click=guardar_usuario,
    )

    btn_limpiar = ft.OutlinedButton(
        "Limpiar",
        icon=ft.Icons.CLEANING_SERVICES,
        on_click=lambda e: (limpiar_formulario(), page.update()),
    )

    cargar_lista_usuarios()

    dialogo_usuarios = ft.AlertDialog(
        title=ft.Row([
            ft.Icon(ft.Icons.MANAGE_ACCOUNTS, color=COLOR_CELESTE, size=24),
            ft.Text("Mantenedor de Administradores & Delegados", size=16, weight=ft.FontWeight.BOLD, color=COLOR_TEXTO),
        ], spacing=8),
        content=ft.Container(
            content=ft.Column([
                ft.Text(
                    "Asigne los delegados (DT / Admin de Equipo) por RUT y Club participante. "
                    "Cada delegado podrá gestionar el plantel y minutos de su equipo.",
                    size=12,
                    color=COLOR_SUBTEXTO,
                ),
                ft.Divider(height=10, color=COLOR_BORDE),
                ft.Text("➕ Crear / Editar Delegado", size=13, weight=ft.FontWeight.BOLD, color=COLOR_CELESTE),
                ft.ResponsiveRow([
                    ft.Column([tf_rut], col={"xs": 12, "sm": 6}),
                    ft.Column([tf_nombre], col={"xs": 12, "sm": 6}),
                    ft.Column([dd_equipo], col={"xs": 12, "sm": 6}),
                    ft.Column([tf_equipo_custom], col={"xs": 12, "sm": 6}),
                    ft.Column([sw_superadmin], col={"xs": 12, "sm": 6}),
                ], spacing=10),
                ft.Row([btn_guardar, btn_limpiar], spacing=10),
                texto_mensaje,
                ft.Divider(height=10, color=COLOR_BORDE),
                ft.Text("📋 Administradores Registrados", size=13, weight=ft.FontWeight.BOLD, color=COLOR_TEXTO),
                ft.Container(
                    content=lista_usuarios_col,
                    height=200,
                    border=ft.border.all(1, COLOR_BORDE),
                    border_radius=8,
                    padding=8,
                ),
            ], spacing=10, tight=True, scroll=ft.ScrollMode.ADAPTIVE),
            width=580,
            padding=5,
        ),
        actions=[
            ft.ElevatedButton(
                "Cerrar",
                bgcolor=COLOR_BORDE,
                color=COLOR_TEXTO,
                on_click=lambda e: page.close(dialogo_usuarios),
            ),
        ],
        bgcolor=COLOR_TARJETA,
    )

    page.open(dialogo_usuarios)
