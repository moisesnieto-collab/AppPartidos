import os
from config.constants import COLOR_FONDO

# --- CONFIGURACIÓN DE BASE DE DATOS TURSO ---
TURSO_URL = os.environ.get(
    "TURSO_URL", "libsql://apppartidos-mnieto.aws-us-east-2.turso.io"
)
TURSO_TOKEN = os.environ.get(
    "TURSO_TOKEN",
    "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3OTAzNzYzNDUsImlkIjoiMDFhMGQ4NzctNzEwMS03NjMyLThiOWYtY2ExOWMzYmI1NDc3Iiwia2lkIjoiTDl6UGpCZkwtX2JXbzVlZWl3RElTcUZ2TFIwNms2c2Z2RGRDRTV3Q20wUSIsInJpZCI6IjUwMzI1MGM2LWFlNzgtNGZkMC1iZTg2LWY1YzkxOGE4NDFjNCJ9.UyizRZgwWnWUqqjb0rfP5logT8KAvTok0cobUkBfRwTRJywZiQowjyJ4B1SZzRUtE5XFrUxC8mMw9gA5w3gOCg",
)

# --- CONFIGURACIÓN DE LA APLICACIÓN ---
APP_TITLE = "Real Dunalastair FC - Control de Torneo"
APP_THEME_MODE = "dark"
APP_BGCOLOR = COLOR_FONDO
