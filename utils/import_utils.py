import io
import re
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd


def normalizar_puesto(puesto_raw: str) -> str:
    """Normaliza un texto o abreviatura a un puesto estándar de fútbol."""
    if not puesto_raw:
        return "Jugador"
    
    p = puesto_raw.strip().upper()
    
    # Arquero
    if any(k in p for k in ["ARQ", "GK", "PORTERO", "GUARDAMETA", "GOLERO"]):
        return "Arquero"
    
    # Defensa
    if any(k in p for k in ["DEF", "DF", "CENTRAL", "LATERAL", "DEFENSA", "DEFENSOR", "ZAGUERO", "STOPPER", "LIBERO"]):
        return "Defensa"
    
    # Mediocampista / Volante
    if any(k in p for k in ["MED", "VOL", "MF", "CENTRO", "VOLANTE", "MEDIO", "MEDIOCAMPISTA", "ENGANCHE", "CREACION", "MIXTO", "MC", "MCO", "MCD", "MD", "MI"]):
        return "Mediocampista"
    
    # Delantero
    if any(k in p for k in ["DEL", "FW", "ATACANTE", "DELANTERO", "EXTREMO", "PUNTERO", "PUNTA", "DEL.", "9"]):
        return "Delantero"
    
    return puesto_raw.strip().title()


def parsear_texto_plantel(texto: str) -> List[Dict[str, str]]:
    """
    Parsea texto libre (ej. lista copiada de WhatsApp) y extrae número, nombre y puesto.
    Soporta múltiples formatos habituales de WhatsApp:
      - 1. Matías (ARQ)
      - 10 - Juan Pérez - Delantero
      - *7* Alexis Sánchez DEL
      - 🧤 1 Claudio Bravo - Arquero
      - 4 Mauricio Isla
      - Arturo Vidal (MED)
    """
    if not texto:
        return []

    lineas = texto.strip().split("\n")
    jugadores: List[Dict[str, str]] = []
    puesto_seccion_actual: Optional[str] = None
    num_auto = 1

    # Patrones para detectar cabeceras de sección (ej. "Arqueros:", "Defensas:")
    patrones_seccion = {
        r"^(?:arqueros?|porteros?|guardametas?|gk)\s*[:\-]": "Arquero",
        r"^(?:defensas?|defensores?|laterales?|centrales?|df)\s*[:\-]": "Defensa",
        r"^(?:volantes?|medios?|mediocampistas?|mf)\s*[:\-]": "Mediocampista",
        r"^(?:delanteros?|atacantes?|punteros?|extremos?|fw)\s*[:\-]": "Delantero",
        r"^(?:banca|suplentes?)\s*[:\-]": None,
    }

    # Regex para puestos entre paréntesis o corchetes: (ARQ), [DEF], etc.
    re_puesto_parentesis = re.compile(
        r"[\(\[\{]\s*(ARQ(?:UERO)?|DEF(?:ENSA|ENSOR)?|MED(?:IO|IOCAMPISTA)?|VOL(?:ANTE)?|DEL(?:ANTERO)?|PORTERO|LATERAL|CENTRAL|EXTREMO|PUNTERO|GK|DF|MF|FW)\.?\s*[\)\]\}]",
        re.IGNORECASE
    )

    # Regex para puestos con guión o al final: " - ARQ", " - Delantero", " ARQ"
    re_puesto_sufijo = re.compile(
        r"(?:[\-\–\—\:]|\s{2,}|\b)\s*(ARQ(?:UERO)?|DEF(?:ENSA|ENSOR)?|MED(?:IO|IOCAMPISTA)?|VOL(?:ANTE)?|DEL(?:ANTERO)?|PORTERO|LATERAL|CENTRAL|EXTREMO|PUNTERO|GK|DF|MF|FW)\.?\s*$",
        re.IGNORECASE
    )

    for linea_raw in lineas:
        linea = linea_raw.strip()
        if not linea:
            continue

        # Limpiar emojis y asteriscos de formato de WhatsApp
        linea_limpia = re.sub(r"[\*\_~`]", "", linea).strip()
        # Quitar viñetas típicas (•, -, >, ⚽, 🧤, 🏃, 👤, 👕, etc.)
        linea_limpia = re.sub(r"^[•\-\–\—\>\+\#\s\U00010000-\U0010ffff\u2600-\u26ff\u2700-\u27bf]+", "", linea_limpia).strip()

        if not linea_limpia:
            continue

        # Verificar si la línea es un encabezado de sección
        es_seccion = False
        for pat, puesto_sec in patrones_seccion.items():
            if re.match(pat, linea_limpia, re.IGNORECASE):
                puesto_seccion_actual = puesto_sec
                es_seccion = True
                break
        if es_seccion:
            continue

        # Si parece una línea no relacionada o título general (ej. "Plantel sábado", "Lista para hoy", "Hora: 10:00", "Total: 14")
        if re.match(r"^(?:plantel|nomina|nómina|citaci[oó]n|convocatoria|lista|partido|cuadrangular|cancha|fecha|hora|total|citados|convocados|equipo|rival|rivales|vs)\b", linea_limpia, re.IGNORECASE):
            continue

        # Si termina en dos puntos y no tiene números (ej. "Titulares:", "Lista:", "Grupo A:")
        if linea_limpia.endswith(":") and not re.search(r"\d", linea_limpia):
            continue

        puesto_detectado = None

        # 1. Detectar puesto entre paréntesis / corchetes
        match_puesto = re_puesto_parentesis.search(linea_limpia)
        if match_puesto:
            puesto_detectado = normalizar_puesto(match_puesto.group(1))
            linea_limpia = (linea_limpia[:match_puesto.start()] + " " + linea_limpia[match_puesto.end():]).strip()
        else:
            # 2. Detectar puesto al final de la línea
            match_sufijo = re_puesto_sufijo.search(linea_limpia)
            if match_sufijo:
                puesto_detectado = normalizar_puesto(match_sufijo.group(1))
                linea_limpia = linea_limpia[:match_sufijo.start()].strip()

        # 3. Detectar número de camiseta
        numero_detectado = None
        
        # Patrón N° al inicio: "1.", "1 -", "10:", "1)", "#7", "N° 10"
        match_num_inicio = re.match(r"^(?:n[°º\.]?\s*|\#\s*)?(\d{1,3})[\s\.\-\–\—\:\)\/]+(.*)$", linea_limpia, re.IGNORECASE)
        if match_num_inicio:
            numero_detectado = match_num_inicio.group(1)
            linea_limpia = match_num_inicio.group(2).strip()
        else:
            # Patrón solo número al inicio separado por espacio: "10 Messi"
            match_num_espacio = re.match(r"^(\d{1,3})\s+([a-zA-ZáéíóúÁÉÍÓÚñÑ].*)$", linea_limpia)
            if match_num_espacio:
                numero_detectado = match_num_espacio.group(1)
                linea_limpia = match_num_espacio.group(2).strip()
            else:
                # Patrón número al final: "Alexis Sánchez 7" o "Alexis Sánchez - 7"
                match_num_final = re.search(r"[\s\-\–\—\:\(\[]+(\d{1,3})[\s\)\]]*$", linea_limpia)
                if match_num_final:
                    numero_detectado = match_num_final.group(1)
                    linea_limpia = linea_limpia[:match_num_final.start()].strip()

        # Limpiar caracteres restantes del nombre
        nombre_limpio = re.sub(r"^[\s\.\-\–\—\:\)\/]+", "", linea_limpia)
        nombre_limpio = re.sub(r"[\s\.\-\–\—\:\)\/]+$", "", nombre_limpio).strip()
        # Normalizar espacios múltiples
        nombre_limpio = re.sub(r"\s+", " ", nombre_limpio)

        if not nombre_limpio or len(nombre_limpio) < 2:
            continue

        # Si no se detectó número, usar auto-incremental
        if not numero_detectado:
            numero_detectado = str(num_auto)
            num_auto += 1
        else:
            try:
                num_auto = max(num_auto, int(numero_detectado) + 1)
            except ValueError:
                pass

        # Puesto final
        puesto_final = puesto_detectado or puesto_seccion_actual or "Jugador"

        jugadores.append({
            "numero": str(numero_detectado),
            "nombre": nombre_limpio.title(),
            "puesto": puesto_final,
        })

    return jugadores


def parsear_dataframe_plantel(df: pd.DataFrame) -> List[Dict[str, str]]:
    """Parsea un DataFrame de pandas para extraer la lista de jugadores."""
    if df.empty:
        return []

    # Normalizar nombres de columnas a minúsculas sin acentos ni espacios
    cols_map = {}
    for col in df.columns:
        c_str = str(col).strip().lower()
        c_clean = c_str.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u").replace("ñ", "n")
        cols_map[col] = c_clean

    col_nom = None
    col_num = None
    col_puesto = None

    for orig, clean in cols_map.items():
        if any(k in clean for k in ["nombre", "jugador", "name", "player", "futbolista"]):
            col_nom = orig
            break

    for orig, clean in cols_map.items():
        if any(k in clean for k in ["numero", "n°", "nro", "num", "dorsal", "camisa", "jersey"]) and orig != col_nom:
            col_num = orig
            break

    for orig, clean in cols_map.items():
        if any(k in clean for k in ["puesto", "posicion", "pos", "position", "rol"]) and orig not in (col_nom, col_num):
            col_puesto = orig
            break

    # Si no encontró por nombre de columna, usar orden de columnas por posición
    cols_list = list(df.columns)
    if not col_nom:
        if len(cols_list) >= 2:
            # Típicamente col 0 es Nro y col 1 es Nombre, o col 0 es Nombre
            col_nom = cols_list[1] if len(cols_list) > 1 else cols_list[0]
        else:
            col_nom = cols_list[0]

    if not col_num and len(cols_list) >= 2:
        col_num = cols_list[0] if col_nom != cols_list[0] else (cols_list[1] if len(cols_list) > 1 else None)

    if not col_puesto and len(cols_list) >= 3:
        for c in cols_list:
            if c not in (col_nom, col_num):
                col_puesto = c
                break

    jugadores: List[Dict[str, str]] = []
    num_seq = 1

    for _, row in df.iterrows():
        nom_val = str(row.get(col_nom, "")).strip() if col_nom else ""
        if not nom_val or nom_val.lower() in ["nan", "none", "null", ""]:
            continue

        # Limpieza de número
        num_val = ""
        if col_num:
            raw_num = row.get(col_num, "")
            if pd.notna(raw_num):
                try:
                    num_val = str(int(float(raw_num)))
                except (ValueError, TypeError):
                    num_val = str(raw_num).strip()

        if not num_val or num_val.lower() in ["nan", "none", "null", ""]:
            num_val = str(num_seq)
            num_seq += 1
        else:
            try:
                num_seq = max(num_seq, int(num_val) + 1)
            except ValueError:
                pass

        # Puesto
        puesto_val = "Jugador"
        if col_puesto:
            raw_puesto = row.get(col_puesto, "")
            if pd.notna(raw_puesto):
                puesto_val = normalizar_puesto(str(raw_puesto))

        jugadores.append({
            "numero": num_val,
            "nombre": nom_val.title(),
            "puesto": puesto_val,
        })

    return jugadores


def parsear_archivo_plantel(file_bytes_or_path: Any, filename: str) -> List[Dict[str, str]]:
    """Lee un archivo Excel (.xlsx, .xls) o CSV y extrae la lista de jugadores."""
    fname = filename.lower()
    try:
        if fname.endswith((".xlsx", ".xls")):
            df = pd.read_excel(file_bytes_or_path)
        elif fname.endswith(".csv"):
            try:
                df = pd.read_csv(file_bytes_or_path, encoding="utf-8")
            except UnicodeDecodeError:
                if isinstance(file_bytes_or_path, (bytes, bytearray)):
                    file_bytes_or_path = io.BytesIO(file_bytes_or_path)
                elif hasattr(file_bytes_or_path, "seek"):
                    file_bytes_or_path.seek(0)
                df = pd.read_csv(file_bytes_or_path, encoding="latin-1", sep=None, engine="python")
        else:
            return []

        return parsear_dataframe_plantel(df)
    except Exception as e:
        print(f"Error parseando archivo {filename}: {e}")
        return []


def generar_plantilla_excel() -> bytes:
    """Genera un archivo Excel de ejemplo listo para descargar y rellenar."""
    datos_ejemplo = [
        {"Numero": 1, "Nombre": "Claudio Bravo", "Puesto": "Arquero"},
        {"Numero": 4, "Nombre": "Mauricio Isla", "Puesto": "Defensa"},
        {"Numero": 17, "Nombre": "Gary Medel", "Puesto": "Defensa"},
        {"Numero": 8, "Nombre": "Arturo Vidal", "Puesto": "Mediocampista"},
        {"Numero": 20, "Nombre": "Charles Aránguiz", "Puesto": "Mediocampista"},
        {"Numero": 10, "Nombre": "Jorge Valdivia", "Puesto": "Mediocampista"},
        {"Numero": 7, "Nombre": "Alexis Sánchez", "Puesto": "Delantero"},
        {"Numero": 11, "Nombre": "Eduardo Vargas", "Puesto": "Delantero"},
    ]
    df = pd.DataFrame(datos_ejemplo)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Plantel")
    
    return output.getvalue()
