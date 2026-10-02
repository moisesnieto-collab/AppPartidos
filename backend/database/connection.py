import libsql_experimental as sqlite3
from config.settings import TURSO_URL, TURSO_TOKEN


def conectar_bd():
    """Establece conexión con la base de datos Turso/LibSQL"""
    return sqlite3.connect(TURSO_URL, auth_token=TURSO_TOKEN)
