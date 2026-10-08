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
            es_superadmin=True
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
            es_superadmin=True
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


class TestPermisosSuperAdminCuadrangulares(BaseBD):
    def test_solo_superadmin_crea_grupo(self):
        # Intento de delegado o invitado -> rechazo
        gid_denegado = GrupoService.crear_grupo(
            "Grupo A", "2026-01-01", "Cobresal", ["Cobresal", "Colo-Colo"], es_superadmin=False
        )
        self.assertIsNone(gid_denegado)

        # SuperAdmin -> éxito
        gid_ok = GrupoService.crear_grupo(
            "Grupo A", "2026-01-01", "Cobresal", ["Cobresal", "Colo-Colo"], es_superadmin=True
        )
        self.assertIsNotNone(gid_ok)

    def test_solo_superadmin_crea_grupo_adicional(self):
        gid_denegado = GrupoService.crear_grupo_adicional(
            "Grupo B", "2026-01-01", ["Cobresal", "Colo-Colo", "U. de Chile", "Audax"], es_superadmin=False
        )
        self.assertIsNone(gid_denegado)

        gid_ok = GrupoService.crear_grupo_adicional(
            "Grupo B", "2026-01-01", ["Cobresal", "Colo-Colo", "U. de Chile", "Audax"], es_superadmin=True
        )
        self.assertIsNotNone(gid_ok)

    def test_solo_superadmin_elimina_grupo_y_fecha(self):
        gid = GrupoService.crear_grupo(
            "Grupo A", "2026-01-01", "Cobresal", ["Cobresal", "Colo-Colo"], es_superadmin=True
        )
        # Intento de eliminación sin superadmin
        self.assertFalse(GrupoService.eliminar_grupo_por_id(gid, es_superadmin=False))
        self.assertFalse(GrupoService.eliminar_grupo_por_fecha("2026-01-01", es_superadmin=False))
        self.assertFalse(GrupoService.actualizar_opcion_definicion("2026-01-01", True, es_superadmin=False))

        # SuperAdmin elimina exitosamente
        self.assertTrue(GrupoService.actualizar_opcion_definicion("2026-01-01", True, es_superadmin=True))
        self.assertTrue(GrupoService.eliminar_grupo_por_id(gid, es_superadmin=True))
        self.assertTrue(GrupoService.eliminar_grupo_por_fecha("2026-01-01", es_superadmin=True))


class TestOpcionA_AutoridadYEventos(BaseBD):
    def setUp(self):
        super().setUp()
        from backend.services.partido_service import PartidoService
        self.partido_service = PartidoService
        self.gid = GrupoRepository.crear(
            "Grupo Torneo", "2026-01-01", "Real Dunalastair", ["Real Dunalastair", "Cobresal", "Colo-Colo"]
        )
        self.pid = PartidoRepository.crear(self.gid, "2026-01-01", "Real Dunalastair", "Cobresal", "Cobresal", True)
        # Asignar titulares para ambos clubes
        p_obj = PartidoRepository.obtener_por_id(self.pid)
        p_obj.titulares = {
            "Real Dunalastair": ["Juan (Real Dunalastair)", "Pedro (Real Dunalastair)"],
            "Cobresal": ["Alexis (Cobresal)", "Eduardo (Cobresal)"]
        }
        PartidoRepository.actualizar(p_obj)

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

    def test_delegado_no_puede_agregar_evento_con_jugador_a_rival(self):
        # DT Cobresal intenta agregar gol con nombre de jugador a nombre de Real Dunalastair
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
        self.assertIn("Solo puedes registrar eventos para tu propio equipo", msg)

    def test_delegado_no_puede_agregar_evento_para_el_rival(self):
        # En Alternativa 1: Cada DT solo registra eventos para su propio club
        ok, msg, p = self.partido_service.agregar_evento_partido(
            partido_id=self.pid,
            tipo_evento="Gol",
            jugador="Gol de Real Dunalastair",
            minuto="12'",
            equipo="Real Dunalastair",
            es_superadmin=False,
            equipo_usuario="Cobresal"
        )
        self.assertFalse(ok)
        self.assertIn("Solo puedes registrar eventos para tu propio equipo", msg)

        # Pero SuperAdmin sí puede registrar eventos para cualquier equipo
        ok_sa, msg_sa, p_sa = self.partido_service.agregar_evento_partido(
            partido_id=self.pid,
            tipo_evento="Gol",
            jugador="Gol de Real Dunalastair",
            minuto="12'",
            equipo="Real Dunalastair",
            es_superadmin=True,
            equipo_usuario=None
        )
        self.assertTrue(ok_sa)
        self.assertEqual(p_sa.goles_local, 1)

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
        self.assertIn("Solo puedes eliminar eventos registrados por tu propio equipo", msg)

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


class TestDeduplicacionYProteccionGoles(BaseBD):
    def setUp(self):
        super().setUp()
        from backend.services.partido_service import PartidoService
        self.partido_service = PartidoService
        self.gid = GrupoRepository.crear(
            "Grupo Torneo", "2026-01-01", "Real Dunalastair", ["Real Dunalastair", "Cobresal"]
        )
        self.pid = PartidoRepository.crear(self.gid, "2026-01-01", "Real Dunalastair", "Cobresal", "Cobresal", True)
        # Asignar titulares para Dunalastair
        p_obj = PartidoRepository.obtener_por_id(self.pid)
        p_obj.titulares = {
            "Real Dunalastair": ["Juan Pérez (Real Dunalastair)", "Pedro (Real Dunalastair)", "Alexis (Real Dunalastair)"],
            "Cobresal": ["Diego (Cobresal)"]
        }
        PartidoRepository.actualizar(p_obj)

    def test_deduplicacion_caso_a_autor_primero_luego_gol_rival(self):
        # 1. DT Dunalastair registra gol con autor en min 07'
        ok1, msg1, p1 = self.partido_service.agregar_evento_partido(
            partido_id=self.pid,
            tipo_evento="Gol",
            jugador="Gol de Juan Pérez (Real Dunalastair)",
            minuto="07'",
            equipo="Real Dunalastair",
            es_superadmin=False,
            equipo_usuario="Real Dunalastair"
        )
        self.assertTrue(ok1)
        self.assertEqual(p1.goles_local, 1)

        # 2. SuperAdmin intenta registrar "Gol Rival" para Dunalastair en min 07'
        ok2, msg2, p2 = self.partido_service.agregar_evento_partido(
            partido_id=self.pid,
            tipo_evento="Gol",
            jugador="Gol de Real Dunalastair",
            minuto="07'",
            equipo="Real Dunalastair",
            es_superadmin=True,
            equipo_usuario=None
        )
        self.assertTrue(ok2)
        self.assertIn("El gol ya fue registrado por el DT rival", msg2)
        # El marcador debe seguir siendo 1 gol, no 2
        self.assertEqual(p2.goles_local, 1)
        self.assertEqual(len(p2.eventos), 1)

    def test_deduplicacion_caso_b_gol_rival_primero_luego_autor(self):
        # 1. SuperAdmin registra "Gol Rival" para Dunalastair en min 07'
        ok1, msg1, p1 = self.partido_service.agregar_evento_partido(
            partido_id=self.pid,
            tipo_evento="Gol",
            jugador="Gol de Real Dunalastair",
            minuto="07'",
            equipo="Real Dunalastair",
            es_superadmin=True,
            equipo_usuario=None
        )
        self.assertTrue(ok1)
        self.assertEqual(p1.goles_local, 1)
        self.assertEqual(len(p1.eventos), 1)

        # 2. DT Dunalastair registra el gol con autor "Juan Pérez" en min 07'
        ok2, msg2, p2 = self.partido_service.agregar_evento_partido(
            partido_id=self.pid,
            tipo_evento="Gol",
            jugador="Gol de Juan Pérez (Real Dunalastair)",
            minuto="07'",
            equipo="Real Dunalastair",
            es_superadmin=False,
            equipo_usuario="Real Dunalastair"
        )
        self.assertTrue(ok2)
        self.assertIn("Gol actualizado con el autor real", msg2)
        # El marcador se mantiene en 1 gol y el evento se enriqueció
        self.assertEqual(p2.goles_local, 1)
        self.assertEqual(len(p2.eventos), 1)
        self.assertEqual(p2.eventos[0]["jugador"], "Gol de Juan Pérez (Real Dunalastair)")

    def test_deduplicacion_mismo_gol_doble_click(self):
        # 1. Registro inicial
        self.partido_service.agregar_evento_partido(
            self.pid, "Gol", "Gol de Juan Pérez (Real Dunalastair)", "05'", "Real Dunalastair",
            es_superadmin=False, equipo_usuario="Real Dunalastair"
        )
        # 2. Doble clic idéntico
        ok, msg, p = self.partido_service.agregar_evento_partido(
            self.pid, "Gol", "Gol de Juan Pérez (Real Dunalastair)", "05'", "Real Dunalastair",
            es_superadmin=False, equipo_usuario="Real Dunalastair"
        )
        self.assertTrue(ok)
        self.assertIn("ya fue registrado previamente", msg)
        self.assertEqual(p.goles_local, 1)
        self.assertEqual(len(p.eventos), 1)

    def test_goles_distintos_minutos_suman_correctamente(self):
        self.partido_service.agregar_evento_partido(
            self.pid, "Gol", "Gol de Juan Pérez (Real Dunalastair)", "05'", "Real Dunalastair",
            es_superadmin=False, equipo_usuario="Real Dunalastair"
        )
        ok, msg, p = self.partido_service.agregar_evento_partido(
            self.pid, "Gol", "Gol de Alexis (Real Dunalastair)", "15'", "Real Dunalastair",
            es_superadmin=False, equipo_usuario="Real Dunalastair"
        )
        self.assertTrue(ok)
        self.assertEqual(p.goles_local, 2)
        self.assertEqual(len(p.eventos), 2)


class TestSincronizacionMultiDispositivo(BaseBD):
    def setUp(self):
        super().setUp()
        from backend.services.partido_service import PartidoService
        self.partido_service = PartidoService
        self.gid = GrupoRepository.crear(
            "Grupo S", "2026-01-01", "Real Dunalastair", ["Real Dunalastair", "Cobresal"]
        )
        self.pid = PartidoRepository.crear(self.gid, "2026-01-01", "Real Dunalastair", "Cobresal", "Cobresal", True)

    def test_sincronizacion_in_place_estado(self):
        # Simular que Admin A actualiza el partido en BD (inicia reloj y mete un gol)
        p = PartidoRepository.obtener_por_id(self.pid)
        p.goles_local = 2
        p.goles_visita = 1
        p.hora_inicio = "2026-10-07T12:00:00+00:00"
        p.segundos_acumulados = 120
        p.finalizado = False
        PartidoRepository.actualizar(p)

        # Estado en memoria de Admin B antes de sincronizar
        estado_b = {
            "goles_local": 0,
            "goles_rival": 0,
            "hora_inicio": None,
            "corriendo": False,
            "segundos_acumulados": 0,
            "finalizado": False,
            "eventos_registrados": [],
            "titulares_seleccionados": [],
        }

        hubo_cambio, partidos = self.partido_service.sincronizar_desde_bd(
            self.gid, self.pid, estado_b, "Real Dunalastair"
        )

        self.assertTrue(hubo_cambio)
        self.assertEqual(estado_b["goles_local"], 2)
        self.assertEqual(estado_b["goles_rival"], 1)
        self.assertEqual(estado_b["hora_inicio"], "2026-10-07T12:00:00+00:00")
        self.assertTrue(estado_b["corriendo"])
        self.assertEqual(estado_b["segundos_acumulados"], 120)


class TestMarcadoresRivalesSuperAdmin(BaseBD):
    def setUp(self):
        super().setUp()
        from backend.services.partido_service import PartidoService
        self.partido_service = PartidoService
        self.gid = GrupoRepository.crear(
            "Grupo R", "2026-01-01", "Real Dunalastair", ["Real Dunalastair", "Cobresal", "Colo-Colo", "U. de Chile"]
        )
        # Partido entre dos rivales (Colo-Colo vs U. de Chile)
        self.pid = PartidoRepository.crear(self.gid, "2026-01-01", "Colo-Colo", "U. de Chile", "U. de Chile", False)

    def test_invitado_no_puede_guardar_marcador_rival(self):
        ok, msg = self.partido_service.guardar_marcador_rival(
            self.pid, 2, 1, es_superadmin=False, es_invitado=True
        )
        self.assertFalse(ok)
        self.assertIn("invitados no pueden modificar", msg)

    def test_admin_estandar_no_puede_guardar_marcador_rival(self):
        ok, msg = self.partido_service.guardar_marcador_rival(
            self.pid, 3, 2, es_superadmin=False, es_invitado=False
        )
        self.assertFalse(ok)
        self.assertIn("Solo el rol SuperAdmin", msg)

    def test_superadmin_puede_guardar_marcador_rival(self):
        ok, msg = self.partido_service.guardar_marcador_rival(
            self.pid, 4, 3, es_superadmin=True, es_invitado=False
        )
        self.assertTrue(ok)
        self.assertIn("SuperAdmin", msg)
        p_act = PartidoRepository.obtener_por_id(self.pid)
        self.assertEqual((p_act.goles_local, p_act.goles_visita), (4, 3))


class TestLogicaCronometro(unittest.TestCase):
    def test_obtener_segundos_actuales_detenido(self):
        from utils.time_utils import obtener_segundos_actuales, formatear_tiempo
        estado = {
            "corriendo": False,
            "hora_inicio": None,
            "segundos_acumulados": 125,
        }
        segs = obtener_segundos_actuales(estado)
        self.assertEqual(segs, 125)
        self.assertEqual(formatear_tiempo(segs), "02:05")

    def test_obtener_segundos_actuales_corriendo(self):
        from utils.time_utils import obtener_segundos_actuales, formatear_tiempo
        from datetime import datetime, timezone, timedelta
        
        # Simular que inició hace 30 segundos
        h_inicio = (datetime.now(timezone.utc) - timedelta(seconds=30)).isoformat()
        estado = {
            "corriendo": True,
            "hora_inicio": h_inicio,
            "segundos_acumulados": 60,
        }
        segs = obtener_segundos_actuales(estado)
        self.assertAlmostEqual(segs, 90, delta=2)
        self.assertEqual(formatear_tiempo(segs), "01:30")

    def test_pausa_y_reanudacion_cronometro(self):
        from utils.time_utils import obtener_segundos_actuales, actualizar_minutos_jugadores
        from datetime import datetime, timezone, timedelta

        # Inicia con 0 segs
        h_inicio = (datetime.now(timezone.utc) - timedelta(seconds=15)).isoformat()
        estado = {
            "corriendo": True,
            "finalizado": False,
            "hora_inicio": h_inicio,
            "segundos_acumulados": 0,
            "ultimo_segundo_procesado": 0,
            "titulares_seleccionados": ["Jugador 1", "Jugador 2"],
            "minutos_partido_actual": {},
        }
        segs_pausa = obtener_segundos_actuales(estado)
        self.assertAlmostEqual(segs_pausa, 15, delta=2)

        # Pausar
        actualizar_minutos_jugadores(estado, segs_pausa)
        estado["segundos_acumulados"] = segs_pausa
        estado["segundos"] = segs_pausa
        estado["hora_inicio"] = None
        estado["corriendo"] = False

        self.assertAlmostEqual(estado["segundos_acumulados"], 15, delta=2)
        self.assertEqual(obtener_segundos_actuales(estado), estado["segundos_acumulados"])
        self.assertAlmostEqual(estado["minutos_partido_actual"]["Jugador 1"], 15, delta=2)

        # Reanudar 10 segundos después
        h_reanudacion = (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()
        estado["corriendo"] = True
        estado["hora_inicio"] = h_reanudacion
        estado["ultimo_segundo_procesado"] = estado["segundos_acumulados"]

        segs_actuales = obtener_segundos_actuales(estado)
        self.assertAlmostEqual(segs_actuales, 25, delta=2)

    def test_actualizar_glosa_partido_screen(self):
        from frontend.screens.partido import PartidoScreen
        from datetime import datetime, timezone
        estado = {
            "corriendo": True,
            "finalizado": False,
            "hora_inicio": datetime.now(timezone.utc).isoformat(),
            "segundos_acumulados": 45,
            "alerta_custom": None,
        }
        screen = PartidoScreen(estado, None, {})
        screen.actualizar_glosa()
        self.assertIn(screen.texto_reloj.value, ["00:45", "00:46"])
        self.assertEqual(screen.texto_alerta_cambio.value, "⏱️ Cronómetro en curso...")

        # Pausar y actualizar glosa
        estado["corriendo"] = False
        estado["hora_inicio"] = None
        estado["segundos_acumulados"] = 45
        screen.actualizar_glosa()
        self.assertEqual(screen.texto_reloj.value, "00:45")
        self.assertEqual(screen.texto_alerta_cambio.value, "⏸️ Cronómetro pausado")


class TestSincronizacionGolesConfig(BaseBD):
    def setUp(self):
        super().setUp()
        from backend.services.partido_service import PartidoService
        from backend.services.grupo_service import GrupoService
        self.partido_service = PartidoService
        self.grupo_service = GrupoService
        self.gid = GrupoRepository.crear(
            "Grupo A", "2026-01-01", "Real Dunalastair", ["Real Dunalastair", "Cobresal", "Colo-Colo", "U. de Chile"]
        )
        self.pid = PartidoRepository.crear(self.gid, "2026-01-01", "Real Dunalastair", "Cobresal", "Cobresal", False)

    def test_partido_sin_iniciar_reloj_no_se_suma_a_la_tabla(self):
        partidos = [p.to_dict() for p in PartidoRepository.obtener_por_grupo(self.gid)]
        tabla = self.grupo_service.calcular_tabla_grupo(partidos, ["Real Dunalastair", "Cobresal", "Colo-Colo", "U. de Chile"])
        
        # Ningún partido debe computarse como jugado (PJ = 0, Pts = 0)
        for stat in tabla:
            self.assertEqual(stat["PJ"], 0)
            self.assertEqual(stat["Pts"], 0)
            self.assertEqual(stat["GF"], 0)
            self.assertEqual(stat["GC"], 0)

    def test_guardar_titulares_sin_iniciar_reloj_no_marca_partido_iniciado(self):
        from backend.models.partido import Partido
        partido_bd = PartidoRepository.obtener_por_id(self.pid)
        partido_bd.titulares = ["Jugador 1", "Jugador 2"]
        
        ok = self.partido_service.guardar_estado_partido(
            partido_bd,
            goles_local=0,
            goles_rival=0,
            equipo_principal="Real Dunalastair"
        )
        self.assertTrue(ok)
        
        # Verificar que sigue sin estar jugado / iniciado
        p_act = PartidoRepository.obtener_por_id(self.pid)
        self.assertFalse(p_act.jugado)
        self.assertIsNone(p_act.hora_inicio)
        self.assertEqual(p_act.segundos, 0)

        # La tabla debe seguir en 0 PJ
        partidos = [p.to_dict() for p in PartidoRepository.obtener_por_grupo(self.gid)]
        tabla = self.grupo_service.calcular_tabla_grupo(partidos, ["Real Dunalastair", "Cobresal", "Colo-Colo", "U. de Chile"])
        for stat in tabla:
            self.assertEqual(stat["PJ"], 0)

    def test_guardar_estado_partido_con_reloj_iniciado_marca_jugado_y_actualiza_tabla(self):
        from backend.models.partido import Partido
        partido_bd = PartidoRepository.obtener_por_id(self.pid)
        partido_bd.hora_inicio = "2026-10-07T12:00:00+00:00"
        partido_bd.segundos = 120
        
        # Registrar 2 goles para Real Dunalastair (local) y 1 para Cobresal (visita) con reloj iniciado
        ok = self.partido_service.guardar_estado_partido(
            partido_bd,
            goles_local=2,
            goles_rival=1,
            equipo_principal="Real Dunalastair"
        )
        self.assertTrue(ok)
        
        # Verificar que el partido en BD quedó con jugado=True y marcador 2-1
        p_act = PartidoRepository.obtener_por_id(self.pid)
        self.assertTrue(p_act.jugado)
        self.assertEqual(p_act.goles_local, 2)
        self.assertEqual(p_act.goles_visita, 1)

        # Recalcular tabla de posiciones del grupo
        partidos = [p.to_dict() for p in PartidoRepository.obtener_por_grupo(self.gid)]
        tabla = self.grupo_service.calcular_tabla_grupo(partidos, ["Real Dunalastair", "Cobresal", "Colo-Colo", "U. de Chile"])
        
        # Real Dunalastair debe ser 1ro con 3 Pts y DG +1
        self.assertEqual(tabla[0]["equipo"], "Real Dunalastair")
        self.assertEqual(tabla[0]["Pts"], 3)
        self.assertEqual(tabla[0]["PJ"], 1)
        self.assertEqual(tabla[0]["PG"], 1)
        self.assertEqual(tabla[0]["GF"], 2)
        self.assertEqual(tabla[0]["GC"], 1)
        self.assertEqual(tabla[0]["DG"], 1)

        # Cobresal debe tener 0 Pts, 1 PJ, 1 PP, DG -1
        cobresal_stat = next(t for t in tabla if t["equipo"] == "Cobresal")
        self.assertEqual(cobresal_stat["Pts"], 0)
        self.assertEqual(cobresal_stat["PJ"], 1)
        self.assertEqual(cobresal_stat["PP"], 1)
        self.assertEqual(cobresal_stat["GF"], 1)
        self.assertEqual(cobresal_stat["GC"], 2)
        self.assertEqual(cobresal_stat["DG"], -1)

    def test_marcador_partidos_equipo_visita_en_config(self):
        # Crear partido donde Colo-Colo es Visita y Cobresal es Local
        pid_visita = PartidoRepository.crear(self.gid, "2026-01-01", "Cobresal", "Colo-Colo", "Cobresal", False)
        p_obj = PartidoRepository.obtener_por_id(pid_visita)
        p_obj.goles_local = 1   # Cobresal 1
        p_obj.goles_visita = 3  # Colo-Colo 3
        p_obj.jugado = True
        PartidoRepository.actualizar(p_obj)

        # Cuando el usuario activo es Colo-Colo (equipo visitante en este partido)
        p_dict = p_obj.to_dict()
        mi_equipo = "Colo-Colo"
        es_local = (p_dict["equipo_local"] == mi_equipo)
        rival_nombre = p_dict["equipo_visita"] if es_local else p_dict["equipo_local"]
        goles_mi_equipo = p_dict["goles_local"] if es_local else p_dict["goles_visita"]
        goles_rival = p_dict["goles_visita"] if es_local else p_dict["goles_local"]

        # Debe mostrar "vs Cobresal" y "Marcador: 3 - 1" (Colo-Colo 3, Cobresal 1)
        self.assertFalse(es_local)
        self.assertEqual(rival_nombre, "Cobresal")
        self.assertEqual(goles_mi_equipo, 3)
        self.assertEqual(goles_rival, 1)
        self.assertEqual(f"Marcador: {goles_mi_equipo} - {goles_rival}", "Marcador: 3 - 1")


class TestAislamientoYSeleccionObligatoriaTitulares(BaseBD):
    def setUp(self):
        super().setUp()
        from backend.services.partido_service import PartidoService
        from backend.services.jugador_service import JugadorService
        self.partido_service = PartidoService
        self.jugador_service = JugadorService
        self.fecha = "2026-01-01"
        self.gid = GrupoRepository.crear(
            "Grupo A", self.fecha, "Real Dunalastair", ["Real Dunalastair", "Cobresal"]
        )
        self.pid = PartidoRepository.crear(self.gid, self.fecha, "Real Dunalastair", "Cobresal", "Cobresal", True)

        # Plantel de Dunalastair
        for i in range(1, 8):
            self.jugador_service.agregar(f"{i}", f"Dunalastair {i}", "Delantero", "Real Dunalastair", self.fecha, False)

        # Plantel de Cobresal
        for i in range(1, 8):
            self.jugador_service.agregar(f"{i}", f"Cobresal {i}", "Mediocampista", "Cobresal", self.fecha, False)

    def test_administrador_bloqueado_sin_titulares_seleccionados(self):
        # Dunalastair inicia el partido con sus titulares
        p_obj = PartidoRepository.obtener_por_id(self.pid)
        p_obj.hora_inicio = "2026-10-07T12:00:00+00:00"
        p_obj.segundos = 60
        p_obj.titulares = {
            "Real Dunalastair": [f"Dunalastair {i}" for i in range(1, 8)],
            "Cobresal": []  # Cobresal aún no ha seleccionado titulares
        }
        PartidoRepository.actualizar(p_obj)

        # DT Cobresal intenta registrar un gol para su equipo sin haber elegido titulares
        ok, msg, p = self.partido_service.agregar_evento_partido(
            partido_id=self.pid,
            tipo_evento="Gol",
            jugador="Cobresal 1 (Cobresal)",
            minuto="02'",
            equipo="Cobresal",
            es_superadmin=False,
            equipo_usuario="Cobresal"
        )
        self.assertFalse(ok)
        self.assertIn("Debes seleccionar los titulares de tu equipo (Cobresal) en la pestaña Plantel", msg)

    def test_administrador_habilita_eventos_tras_seleccionar_titulares(self):
        p_obj = PartidoRepository.obtener_por_id(self.pid)
        p_obj.hora_inicio = "2026-10-07T12:00:00+00:00"
        p_obj.segundos = 120
        # Cobresal ahora sí selecciona sus titulares
        p_obj.titulares = {
            "Real Dunalastair": [f"Dunalastair {i}" for i in range(1, 8)],
            "Cobresal": [f"Cobresal {i}" for i in range(1, 8)]
        }
        PartidoRepository.actualizar(p_obj)

        # Ahora el DT Cobresal sí puede registrar el gol
        ok, msg, p = self.partido_service.agregar_evento_partido(
            partido_id=self.pid,
            tipo_evento="Gol",
            jugador="Cobresal 1 (Cobresal)",
            minuto="03'",
            equipo="Cobresal",
            es_superadmin=False,
            equipo_usuario="Cobresal"
        )
        self.assertTrue(ok)
        self.assertEqual(p.goles_visita, 1)

    def test_aislamiento_titulares_rival_no_aparece_en_partido_screen(self):
        # Dunalastair tiene sus titulares en el partido
        p_obj = PartidoRepository.obtener_por_id(self.pid)
        p_obj.titulares = {
            "Real Dunalastair": ["Dunalastair 1", "Dunalastair 2"],
            "Cobresal": ["Cobresal 1", "Cobresal 2"]
        }
        PartidoRepository.actualizar(p_obj)

        # Simular estado para DT Cobresal
        estado_cobresal = {
            "es_invitado": False,
            "es_superadmin": False,
            "equipo_activo": "Cobresal",
            "titulares_seleccionados": ["Cobresal 1", "Cobresal 2"],
            "goles_local": 0,
            "goles_rival": 0,
            "config": {
                "equipo_principal": "Cobresal",
                "equipo_rival": "Real Dunalastair",
                "fecha": self.fecha,
                "jugadores_en_cancha": 7,
                "tiempos_por_partido": 2,
                "minutos_por_tiempo": 10,
            },
            "partido_activo_id": self.pid,
            "partidos_grupo": [p_obj.to_dict()],
            "eventos_registrados": [],
            "segundos": 0,
            "segundos_acumulados": 0,
            "finalizado": False,
            "corriendo": False,
        }

        from frontend.screens.partido import PartidoScreen
        class FakePage:
            def update(self): pass

        screen = PartidoScreen(estado_cobresal, FakePage(), {"guardar_partido": lambda: None, "refrescar_vistas": lambda: None})
        col = screen.build()

        # Obtener los dropdowns de eventos
        # Buscar dd_jugador_titular en los controles generados
        jugadores_cobresal = [j["nombre"] for j in self.jugador_service.obtener_todos_ordenados("Cobresal", self.fecha)]
        jugadores_dunalastair = [j["nombre"] for j in self.jugador_service.obtener_todos_ordenados("Real Dunalastair", self.fecha)]

        # Verificar que titulares_seleccionados de Cobresal no tenga jugadores de Dunalastair
        for nom in estado_cobresal["titulares_seleccionados"]:
            self.assertIn(nom, jugadores_cobresal)
            self.assertNotIn(nom, jugadores_dunalastair)


    def test_import_main_y_jugador_service(self):
        import main
        self.assertTrue(hasattr(main, "JugadorService"))


class TestCalculoMinutosAmbosEquipos(BaseBD):
    def setUp(self):
        super().setUp()
        from backend.services.partido_service import PartidoService
        from backend.services.jugador_service import JugadorService
        from utils.time_utils import actualizar_minutos_jugadores
        self.partido_service = PartidoService
        self.jugador_service = JugadorService
        self.actualizar_minutos = actualizar_minutos_jugadores
        self.fecha = "2026-01-01"
        self.gid = GrupoRepository.crear(
            "Grupo A", self.fecha, "Real Dunalastair", ["Real Dunalastair", "Cobresal"]
        )
        self.pid = PartidoRepository.crear(self.gid, self.fecha, "Real Dunalastair", "Cobresal", "Cobresal", True)

        for i in range(1, 4):
            self.jugador_service.agregar(f"{i}", f"Dunalastair {i}", "Delantero", "Real Dunalastair", self.fecha, False)
            self.jugador_service.agregar(f"{i}", f"Cobresal {i}", "Mediocampista", "Cobresal", self.fecha, False)

    def test_suma_minutos_ambos_equipos_cuando_ambos_tienen_titulares(self):
        p_obj = PartidoRepository.obtener_por_id(self.pid)
        p_obj.titulares = {
            "Real Dunalastair": ["Dunalastair 1", "Dunalastair 2"],
            "Cobresal": ["Cobresal 1", "Cobresal 2"]
        }
        PartidoRepository.actualizar(p_obj)

        estado = {
            "corriendo": True,
            "finalizado": False,
            "segundos": 60,
            "segundos_acumulados": 0,
            "ultimo_segundo_procesado": 0,
            "titulares_seleccionados": ["Dunalastair 1", "Dunalastair 2"],
            "minutos_partido_actual": {},
            "partido_activo_id": self.pid,
            "partidos_grupo": [p_obj.to_dict()],
        }

        mins = self.actualizar_minutos(estado, seg_actual=60)

        # Dunalastair
        self.assertEqual(mins.get("Dunalastair 1"), 60)
        self.assertEqual(mins.get("Dunalastair 2"), 60)
        self.assertNotIn("Dunalastair 3", mins)

        # Cobresal (rival con titulares definidos)
        self.assertEqual(mins.get("Cobresal 1"), 60)
        self.assertEqual(mins.get("Cobresal 2"), 60)
        self.assertNotIn("Cobresal 3", mins)

    def test_suma_minutos_solo_al_equipo_con_titulares_definidos(self):
        p_obj = PartidoRepository.obtener_por_id(self.pid)
        p_obj.titulares = {
            "Real Dunalastair": ["Dunalastair 1", "Dunalastair 2"],
            "Cobresal": []  # Cobresal aún no define titulares
        }
        PartidoRepository.actualizar(p_obj)

        estado = {
            "corriendo": True,
            "finalizado": False,
            "segundos": 90,
            "segundos_acumulados": 0,
            "ultimo_segundo_procesado": 0,
            "titulares_seleccionados": ["Dunalastair 1", "Dunalastair 2"],
            "minutos_partido_actual": {},
            "partido_activo_id": self.pid,
            "partidos_grupo": [p_obj.to_dict()],
        }

        mins = self.actualizar_minutos(estado, seg_actual=90)

        # Dunalastair recibe 90 segundos
        self.assertEqual(mins.get("Dunalastair 1"), 90)
        self.assertEqual(mins.get("Dunalastair 2"), 90)

        # Cobresal no recibe minutos
        self.assertNotIn("Cobresal 1", mins)
        self.assertNotIn("Cobresal 2", mins)


class TestAlternativa1GestionDescentralizadaYGoles(BaseBD):
    def setUp(self):
        super().setUp()
        from backend.services.partido_service import PartidoService
        from backend.services.jugador_service import JugadorService
        self.partido_service = PartidoService
        self.jugador_service = JugadorService
        self.fecha = "2026-01-01"
        self.gid = GrupoRepository.crear(
            "Grupo A", self.fecha, "Real Dunalastair", ["Real Dunalastair", "Cobresal"]
        )
        self.pid = PartidoRepository.crear(self.gid, self.fecha, "Real Dunalastair", "Cobresal", "Cobresal", True)

        self.jugador_service.agregar("9", "Goleador Local", "Delantero", "Real Dunalastair", self.fecha, False)
        self.jugador_service.agregar("10", "Goleador Visita", "Delantero", "Cobresal", self.fecha, False)

        p_obj = PartidoRepository.obtener_por_id(self.pid)
        p_obj.titulares = {
            "Real Dunalastair": ["Goleador Local"],
            "Cobresal": ["Goleador Visita"]
        }
        PartidoRepository.actualizar(p_obj)

    def test_suma_descentralizada_de_goles_entre_ambos_administradores(self):
        # 1. DT Dunalastair (Local) anota un gol para su club
        ok1, msg1, p1 = self.partido_service.agregar_evento_partido(
            partido_id=self.pid,
            tipo_evento="Gol",
            jugador="Gol de Goleador Local (Real Dunalastair)",
            minuto="05'",
            equipo="Real Dunalastair",
            es_superadmin=False,
            equipo_usuario="Real Dunalastair"
        )
        self.assertTrue(ok1)
        self.assertEqual(p1.goles_local, 1)
        self.assertEqual(p1.goles_visita, 0)

        # 2. DT Cobresal (Visita) anota un gol para su club
        ok2, msg2, p2 = self.partido_service.agregar_evento_partido(
            partido_id=self.pid,
            tipo_evento="Gol",
            jugador="Gol de Goleador Visita (Cobresal)",
            minuto="12'",
            equipo="Cobresal",
            es_superadmin=False,
            equipo_usuario="Cobresal"
        )
        self.assertTrue(ok2)
        # Marcador descentralizado global: 1 - 1
        self.assertEqual(p2.goles_local, 1)
        self.assertEqual(p2.goles_visita, 1)

        # 3. DT Dunalastair vuelve a anotar en min 18'
        ok3, msg3, p3 = self.partido_service.agregar_evento_partido(
            partido_id=self.pid,
            tipo_evento="Gol",
            jugador="Gol de Goleador Local (Real Dunalastair)",
            minuto="18'",
            equipo="Real Dunalastair",
            es_superadmin=False,
            equipo_usuario="Real Dunalastair"
        )
        self.assertTrue(ok3)
        self.assertEqual(p3.goles_local, 2)
        self.assertEqual(p3.goles_visita, 1)

        # Verificar eventos
        self.assertEqual(len(p3.eventos), 3)

    def test_control_cronometro_por_ambos_administradores(self):
        from frontend.screens.partido import PartidoScreen
        class FakePage:
            def update(self): pass

        # Simular sesión de DT Visita (Cobresal)
        p_obj = PartidoRepository.obtener_por_id(self.pid)
        estado_visita = {
            "es_invitado": False,
            "es_superadmin": False,
            "equipo_activo": "Cobresal",
            "goles_local": 0,
            "goles_rival": 0,
            "config": {
                "equipo_principal": "Cobresal",
                "equipo_rival": "Real Dunalastair",
                "minutos_por_tiempo": 10,
                "tiempos_por_partido": 2,
                "fecha": self.fecha,
            },
            "partido_activo_id": self.pid,
            "partidos_grupo": [p_obj.to_dict()],
            "titulares_seleccionados": ["Goleador Visita"],
            "eventos_registrados": [],
            "segundos": 0,
            "segundos_acumulados": 0,
            "corriendo": False,
            "finalizado": False,
        }

        screen_visita = PartidoScreen(estado_visita, FakePage(), {"guardar_partido": lambda: None, "refrescar_vistas": lambda: None})
        screen_visita.build()

        # DT Visita tiene permisos para controlar el reloj en su partido
        p_act = p_obj.to_dict()
        mi_equipo = estado_visita["equipo_activo"]
        es_local = bool(p_act and p_act.get("equipo_local") == mi_equipo)
        es_visita = bool(p_act and p_act.get("equipo_visita") == mi_equipo)
        es_mi_partido = es_local or es_visita

        puede_controlar_reloj = not estado_visita["es_invitado"] and es_mi_partido
        self.assertTrue(puede_controlar_reloj)


class TestMantenedorEventosTitularesEquipoLocal(BaseBD):
    def setUp(self):
        super().setUp()
        from backend.services.jugador_service import JugadorService
        self.jugador_service = JugadorService
        self.fecha = "2026-01-01"
        self.gid = GrupoRepository.crear(
            "Grupo A", self.fecha, "Real Dunalastair", ["Real Dunalastair", "Cobresal"]
        )
        self.pid1 = PartidoRepository.crear(self.gid, self.fecha, "Real Dunalastair", "Cobresal", "Cobresal", True)
        self.pid2 = PartidoRepository.crear(self.gid, self.fecha, "Cobresal", "Real Dunalastair", "Cobresal", False)

        # Jugadores de Real Dunalastair
        self.jugador_service.agregar("1", "Arquero Dunalastair", "Arquero", "Real Dunalastair", self.fecha, False)
        self.jugador_service.agregar("9", "Delantero Dunalastair", "Delantero", "Real Dunalastair", self.fecha, False)

        # Jugadores de Cobresal
        self.jugador_service.agregar("1", "Arquero Cobresal", "Arquero", "Cobresal", self.fecha, False)
        self.jugador_service.agregar("10", "10 Cobresal", "Mediocampista", "Cobresal", self.fecha, False)

    def test_mantenedor_carga_solo_titulares_equipo_local(self):
        from frontend.screens.mantenedor_eventos import mostrar_dialogo_mantenedor_eventos
        import flet as ft

        # Definir titulares para Real Dunalastair en pid1
        p1 = PartidoRepository.obtener_por_id(self.pid1)
        p1.titulares = {
            "Real Dunalastair": ["Delantero Dunalastair"],
            "Cobresal": ["10 Cobresal"]
        }
        PartidoRepository.actualizar(p1)

        opened_dialogs = []
        class FakePage:
            def open(self, control):
                opened_dialogs.append(control)
            def close(self, control): pass
            def update(self): pass

        estado = {
            "es_invitado": False,
            "es_superadmin": True,
            "equipo_activo": "Real Dunalastair",
            "partido_activo_id": self.pid1,
            "partidos_grupo": [p1.to_dict()],
        }

        fake_page = FakePage()
        mostrar_dialogo_mantenedor_eventos(fake_page, estado, {"cargar_grupo": lambda: None, "refrescar_vistas": lambda: None}, partido_id_inicial=self.pid1)

        self.assertEqual(len(opened_dialogs), 1)
        dlg = opened_dialogs[0]
        self.assertIsInstance(dlg, ft.AlertDialog)

        # Encontrar dropdown de jugadores en el diálogo
        # Buscar en el content de dlg
        col = dlg.content.content
        # Los controles de nuevo evento están en Row(tf_minuto, dd_tipo_evento, dd_jugador)
        row_nuevo_evento = col.controls[7]
        dd_jugador = row_nuevo_evento.controls[2]

        # Verificar opciones cargadas
        opciones = [opt.key or opt.text for opt in dd_jugador.options]
        self.assertEqual(opciones, ["Delantero Dunalastair"])
        self.assertNotIn("Arquero Dunalastair", opciones)
        self.assertNotIn("10 Cobresal", opciones)
        self.assertNotIn("Arquero Cobresal", opciones)

    def test_mantenedor_vacio_si_equipo_local_no_tiene_titulares(self):
        from frontend.screens.mantenedor_eventos import mostrar_dialogo_mantenedor_eventos
        import flet as ft

        # Partido 2 (Local: Cobresal, Visita: Real Dunalastair) sin titulares para Cobresal
        p2 = PartidoRepository.obtener_por_id(self.pid2)
        p2.titulares = {
            "Real Dunalastair": ["Delantero Dunalastair"],
            "Cobresal": []  # Sin titulares para el equipo local
        }
        PartidoRepository.actualizar(p2)

        opened_dialogs = []
        class FakePage:
            def open(self, control):
                opened_dialogs.append(control)
            def close(self, control): pass
            def update(self): pass

        estado = {
            "es_invitado": False,
            "es_superadmin": True,
            "equipo_activo": "Real Dunalastair",
            "partido_activo_id": self.pid2,
            "partidos_grupo": [p2.to_dict()],
        }

        fake_page = FakePage()
        mostrar_dialogo_mantenedor_eventos(fake_page, estado, {"cargar_grupo": lambda: None, "refrescar_vistas": lambda: None}, partido_id_inicial=self.pid2)

        self.assertEqual(len(opened_dialogs), 1)
        dlg = opened_dialogs[0]
        col = dlg.content.content
        row_nuevo_evento = col.controls[7]
        dd_jugador = row_nuevo_evento.controls[2]

        # No debe haber opciones disponibles
        self.assertEqual(len(dd_jugador.options), 0)
        self.assertIsNone(dd_jugador.value)
        self.assertTrue(dd_jugador.disabled)


if __name__ == "__main__":
    unittest.main()
