import os
import sqlite3
import tempfile
import unittest
from unittest import mock

from backend.database import repositories as repo
from backend.database.repositories import (
    DatabaseInitializer, JugadorRepository, GrupoRepository, PartidoRepository,
)
from backend.services.usuario_service import UsuarioService
from backend.services.jugador_service import JugadorService
from backend.services.grupo_service import GrupoService

SUPER = "11165045"


class BaseBD(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.patch = mock.patch.object(repo, "conectar_bd", lambda: sqlite3.connect(self.path))
        self.patch.start()
        DatabaseInitializer.inicializar()

    def tearDown(self):
        self.patch.stop()
        os.remove(self.path)


class TestAutenticacion(BaseBD):
    def test_superadmin_por_defecto(self):
        u = UsuarioService.autenticar("11.165.045")
        self.assertTrue(u and u["es_superadmin"])

    def test_rut_desconocido_y_vacio(self):
        self.assertIsNone(UsuarioService.autenticar("99999999"))
        self.assertIsNone(UsuarioService.autenticar(""))

    def test_delegado_contexto_equipo(self):
        ok, _ = UsuarioService.guardar_delegado("12345678-9", "Pepe", "Cobresal", solicitante_es_superadmin=True)
        self.assertTrue(ok)
        u = UsuarioService.autenticar("12.345.678-9")
        self.assertEqual(u["equipo_asignado"], "Cobresal")
        self.assertFalse(u["es_superadmin"])

    def test_permisos_gestion(self):
        ok, _ = UsuarioService.guardar_delegado("1", "X", "Y", solicitante_es_superadmin=False)
        self.assertFalse(ok)
        ok, _ = UsuarioService.eliminar_delegado(SUPER, solicitante_es_superadmin=True)
        self.assertFalse(ok)
        UsuarioService.guardar_delegado("5555", "A", "Cobresal", solicitante_es_superadmin=True)
        ok, _ = UsuarioService.eliminar_delegado("5555", solicitante_es_superadmin=True)
        self.assertTrue(ok)
        self.assertIsNone(UsuarioService.autenticar("5555"))


class TestPlantel(BaseBD):
    def test_precarga_historica_e_inmutabilidad(self):
        JugadorRepository.agregar("1", "Ana", "Delantero", "Cobresal", "2026-01-01")
        JugadorRepository.agregar("2", "Beto", "Portero", "Cobresal", "2026-01-01")
        previo = JugadorRepository.obtener_ultimo_plantel_historico("Cobresal", "2026-02-01")
        self.assertEqual({j.nombre for j in previo}, {"Ana", "Beto"})
        JugadorRepository.importar_masivo(
            [{"numero": "1", "nombre": "Ana", "puesto": "Delantero"}], "Cobresal", "2026-02-01", reemplazar=True)
        self.assertEqual(JugadorRepository.contar("Cobresal", "2026-02-01"), 1)
        self.assertEqual(JugadorRepository.contar("Cobresal", "2026-01-01"), 2)

    def test_sin_historial(self):
        self.assertEqual(JugadorRepository.obtener_ultimo_plantel_historico("Nadie", "2026-02-01"), [])

    def test_aislamiento_por_club(self):
        JugadorRepository.agregar("1", "Ana", "Delantero", "Cobresal", "2026-01-01")
        JugadorRepository.agregar("1", "Luis", "Portero", "Colo-Colo", "2026-01-01")
        nombres = [j["nombre"] for j in JugadorService.obtener_todos_ordenados("Cobresal", "2026-01-01")]
        self.assertEqual(nombres, ["Ana"])
        JugadorRepository.eliminar("Ana", "Cobresal", "2026-01-01")
        self.assertEqual(JugadorRepository.contar("Colo-Colo", "2026-01-01"), 1)

    def test_invitado_no_modifica(self):
        self.assertFalse(JugadorService.agregar("1", "Z", "Portero", "Cobresal", "2026-01-01", es_invitado=True))


class TestMarcador(BaseBD):
    def test_actualizacion_colaborativa(self):
        gid = GrupoRepository.crear(
            "G1", "2026-01-01", "Real Dunalastair", ["Real Dunalastair", "Cobresal", "Colo-Colo"])
        pid = PartidoRepository.crear(gid, "2026-01-01", "Cobresal", "Colo-Colo", "Colo-Colo", False)
        self.assertTrue(PartidoRepository.actualizar_marcador(pid, 3, 1))
        p = PartidoRepository.obtener_por_id(pid)
        self.assertEqual((p.goles_local, p.goles_visita), (3, 1))
        self.assertEqual([x.id for x in PartidoRepository.obtener_por_grupo(gid)], [pid])


class TestMultiEquipoPartidos(BaseBD):
    def test_creacion_sin_equipos_duplicados(self):
        # Si se ingresa el equipo principal repetido en la lista de rivales
        gid = GrupoService.crear_grupo(
            "Grupo A",
            "2026-01-01",
            "Rival A",
            ["Rival A", "Rival B", "Rival C", "Real Dunalastair"],
            es_invitado=False
        )
        self.assertIsNotNone(gid)
        partidos = PartidoRepository.obtener_por_grupo(gid)
        # Deben ser exactamente 6 partidos únicos entre 4 equipos distintos
        self.assertEqual(len(partidos), 6)
        for p in partidos:
            self.assertNotEqual(p.equipo_local, p.equipo_visita, "Ningún partido debe tener el mismo local y visita")

    def test_partidos_por_equipo_activo(self):
        gid = GrupoService.crear_grupo(
            "Grupo Principal",
            "2026-01-01",
            "Real Dunalastair",
            ["Cobresal", "Colo-Colo", "U. de Chile"],
            es_invitado=False
        )
        partidos = [p.to_dict() for p in PartidoRepository.obtener_por_grupo(gid)]
        
        # Para el equipo 'Cobresal', debe tener exactamente 3 partidos donde participa
        partidos_cobresal = [p for p in partidos if p["equipo_local"] == "Cobresal" or p["equipo_visita"] == "Cobresal"]
        partidos_otros = [p for p in partidos if p["equipo_local"] != "Cobresal" and p["equipo_visita"] != "Cobresal"]
        
        self.assertEqual(len(partidos_cobresal), 3)
        self.assertEqual(len(partidos_otros), 3)

        # Los rivales de Cobresal en sus 3 partidos deben ser Dunalastair, Colo-Colo y U. de Chile
        rivales_cobresal = {
            p["equipo_visita"] if p["equipo_local"] == "Cobresal" else p["equipo_local"]
            for p in partidos_cobresal
        }
        self.assertEqual(rivales_cobresal, {"Real Dunalastair", "Colo-Colo", "U. de Chile"})


class TestOpcionA_AutoridadYEventos(BaseBD):
    def setUp(self):
        super().setUp()
        from backend.services.partido_service import PartidoService
        self.partido_service = PartidoService
        self.gid = GrupoRepository.crear(
            "Grupo Torneo", "2026-01-01", "Real Dunalastair", ["Real Dunalastair", "Cobresal", "Colo-Colo"]
        )
        self.pid = PartidoRepository.crear(self.gid, "2026-01-01", "Real Dunalastair", "Cobresal", "Cobresal", True)

    def test_delegado_agrega_evento_propio_plantel(self):
        # DT Cobresal (visita) agrega gol de su jugador
        ok, msg, p = self.partido_service.agregar_evento_partido(
            partido_id=self.pid,
            tipo_evento="Gol",
            jugador="Alexis (Cobresal)",
            minuto="12'",
            equipo="Cobresal",
            es_superadmin=False,
            equipo_usuario="Cobresal"
        )
        self.assertTrue(ok)
        self.assertEqual(p.goles_visita, 1)
        self.assertEqual(p.goles_local, 0)
        self.assertEqual(len(p.eventos), 1)
        self.assertEqual(p.eventos[0]["equipo"], "Cobresal")

    def test_delegado_no_puede_agregar_evento_a_rival(self):
        # DT Cobresal intenta agregar gol a nombre de Real Dunalastair
        ok, msg, p = self.partido_service.agregar_evento_partido(
            partido_id=self.pid,
            tipo_evento="Gol",
            jugador="Juan (Real Dunalastair)",
            minuto="15'",
            equipo="Real Dunalastair",
            es_superadmin=False,
            equipo_usuario="Cobresal"
        )
        self.assertFalse(ok)
        self.assertIn("Solo puedes registrar eventos para tu propio plantel", msg)

    def test_delegado_no_puede_modificar_partido_ajeno(self):
        # Crear partido entre Colo-Colo y U. de Chile
        pid_ajeno = PartidoRepository.crear(self.gid, "2026-01-01", "Colo-Colo", "U. de Chile", "U. de Chile", False)
        # DT Cobresal intenta registrar evento en partido Colo-Colo vs U. de Chile
        ok, msg, p = self.partido_service.agregar_evento_partido(
            partido_id=pid_ajeno,
            tipo_evento="Gol",
            jugador="Alexis",
            minuto="5'",
            equipo="Cobresal",
            es_superadmin=False,
            equipo_usuario="Cobresal"
        )
        self.assertFalse(ok)
        self.assertIn("No tienes permisos", msg)

    def test_delegado_no_puede_borrar_evento_del_rival(self):
        # SuperAdmin agrega gol de Dunalastair y gol de Cobresal
        self.partido_service.agregar_evento_partido(
            self.pid, "Gol", "Juan (Real Dunalastair)", "10'", "Real Dunalastair", es_superadmin=True
        )
        self.partido_service.agregar_evento_partido(
            self.pid, "Gol", "Alexis (Cobresal)", "20'", "Cobresal", es_superadmin=True
        )
        # DT Cobresal intenta borrar el gol de Dunalastair (índice 0)
        ok, msg, p = self.partido_service.eliminar_evento_partido(
            partido_id=self.pid,
            indice_evento=0,
            es_superadmin=False,
            equipo_usuario="Cobresal"
        )
        self.assertFalse(ok)
        self.assertIn("No puedes eliminar eventos registrados por el club rival", msg)

        # Pero DT Cobresal sí puede borrar su propio gol (índice 1)
        ok, msg, p = self.partido_service.eliminar_evento_partido(
            partido_id=self.pid,
            indice_evento=1,
            es_superadmin=False,
            equipo_usuario="Cobresal"
        )
        self.assertTrue(ok)
        self.assertEqual(p.goles_visita, 0)
        self.assertEqual(p.goles_local, 1)

    def test_superadmin_control_total(self):
        # SuperAdmin puede borrar cualquier evento
        self.partido_service.agregar_evento_partido(
            self.pid, "Gol", "Juan (Real Dunalastair)", "10'", "Real Dunalastair", es_superadmin=True
        )
        ok, msg, p = self.partido_service.eliminar_evento_partido(
            partido_id=self.pid,
            indice_evento=0,
            es_superadmin=True
        )
        self.assertTrue(ok)
        self.assertEqual(p.goles_local, 0)


if __name__ == "__main__":
    unittest.main()
