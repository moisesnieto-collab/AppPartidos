from typing import List, Optional, Tuple, Dict, Any
from backend.database.repositories import UsuarioRepository
from backend.models.usuario import UsuarioAdmin


class UsuarioService:
    @staticmethod
    def limpiar_rut(rut: str) -> str:
        if not rut:
            return ""
        return rut.replace(".", "").replace("-", "").strip()

    @staticmethod
    def autenticar(rut: str) -> Optional[Dict[str, Any]]:
        rut_limpio = UsuarioService.limpiar_rut(rut)
        if not rut_limpio:
            return None
        
        usuario = UsuarioRepository.autenticar_por_rut(rut_limpio)
        if usuario:
            return usuario.to_dict()
        return None

    @staticmethod
    def obtener_todos_delegados() -> List[Dict[str, Any]]:
        usuarios = UsuarioRepository.obtener_todos()
        return [u.to_dict() for u in usuarios]

    @staticmethod
    def guardar_delegado(
        rut: str,
        nombre_contacto: str,
        equipo_asignado: str,
        es_superadmin: bool = False,
        solicitante_es_superadmin: bool = False,
    ) -> Tuple[bool, str]:
        if not solicitante_es_superadmin:
            return False, "Solo el SuperAdministrador puede gestionar administradores de equipo."

        rut_limpio = UsuarioService.limpiar_rut(rut)
        nombre = nombre_contacto.strip()
        equipo = equipo_asignado.strip()

        if not rut_limpio:
            return False, "El RUT no puede estar vacío."
        if not nombre:
            return False, "El nombre de contacto es obligatorio."
        if not equipo:
            return False, "Debe especificar un equipo asignado."

        exito = UsuarioRepository.crear_o_actualizar(
            rut=rut_limpio,
            nombre_contacto=nombre,
            equipo_asignado=equipo,
            es_superadmin=es_superadmin,
        )
        if exito:
            return True, "Administrador de equipo guardado correctamente."
        return False, "Error al guardar el administrador en la base de datos."

    @staticmethod
    def eliminar_delegado(rut: str, solicitante_es_superadmin: bool = False) -> Tuple[bool, str]:
        if not solicitante_es_superadmin:
            return False, "Solo el SuperAdministrador puede eliminar administradores de equipo."

        rut_limpio = UsuarioService.limpiar_rut(rut)
        if not rut_limpio:
            return False, "RUT inválido."

        # Proteger superadmin principal
        if rut_limpio == "11165045":
            return False, "No se puede eliminar al SuperAdministrador principal del sistema."

        exito = UsuarioRepository.eliminar(rut_limpio)
        if exito:
            return True, "Administrador eliminado correctamente."
        return False, "Error al eliminar el administrador."
