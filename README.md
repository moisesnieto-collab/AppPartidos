# Real Dunalastair FC - Control de Torneo

Aplicación de gestión de partidos de fútbol con Flet, refactorizada con arquitectura full stack.

## 📁 Estructura del Proyecto

```
AppPartidos/
├── backend/                    # Lógica de negocio y acceso a datos
│   ├── models/               # Modelos de datos
│   │   ├── jugador.py        # Modelo Jugador
│   │   ├── grupo.py          # Modelo Grupo
│   │   ├── partido.py        # Modelo Partido
│   │   └── evento.py         # Modelo Evento
│   ├── database/             # Capa de base de datos
│   │   ├── connection.py    # Conexión a Turso/LibSQL
│   │   └── repositories.py   # Operaciones CRUD
│   └── services/             # Servicios de negocio
│       ├── jugador_service.py
│       ├── grupo_service.py
│       └── partido_service.py
├── frontend/                  # Interfaz de usuario
│   ├── screens/              # Pantallas principales
│   │   ├── configuracion.py  # Configuración y tabla de posiciones
│   │   ├── plantel.py        # Gestión de jugadores
│   │   ├── partido.py        # Partido en vivo
│   │   └── estadisticas.py   # Estadísticas de minutos
│   ├── components/           # Componentes reutilizables
│   │   ├── reloj.py          # Cronómetro
│   │   ├── tabla_posiciones.py
│   │   └── selector_jugadores.py
│   └── styles/               # Estilos y colores
│       └── colors.py
├── config/                    # Configuración
│   ├── settings.py           # Configuración de la app
│   └── constants.py          # Constantes (colores, datos iniciales)
├── utils/                     # Utilidades
│   ├── time_utils.py         # Funciones de tiempo
│   └── data_utils.py         # Funciones de datos
├── main.py                    # Entry point de la aplicación
├── requirements.txt          # Dependencias
├── Dockerfile               # Configuración Docker
└── README.md                # Este archivo
```

## 🚀 Instalación

### Requisitos
- Python 3.10+
- pip

### Pasos

1. Crear entorno virtual:
```bash
python3 -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

2. Instalar dependencias:
```bash
pip install -r requirements.txt
```

3. Ejecutar aplicación:
```bash
python main.py
```

## 🐳 Docker

### Construir imagen:
```bash
docker build -t app-partidos .
```

### Ejecutar contenedor:
```bash
docker run -p 8080:8080 -e PORT=8080 app-partidos
```

## 📦 Módulos

### Backend

**Models**: Definen la estructura de datos usando dataclasses.
- `Jugador`: Información de jugadores
- `Grupo`: Información de grupos/torneos
- `Partido`: Información de partidos
- `Evento`: Eventos durante partidos

**Database**: 
- `connection.py`: Conexión a base de datos Turso/LibSQL
- `repositories.py`: Operaciones CRUD para cada modelo

**Services**: Lógica de negocio
- `JugadorService`: Gestión de jugadores
- `GrupoService`: Gestión de grupos y generación de partidos
- `PartidoService`: Gestión de partidos, cronómetro y sincronización

### Frontend

**Screens**: Cada pantalla de la aplicación
- `ConfiguracionScreen`: Configuración de torneos y tabla de posiciones
- `PlantelScreen`: Gestión de plantel y titulares
- `PartidoScreen`: Control de partido en vivo
- `EstadisticasScreen`: Visualización de estadísticas

**Components**: Componentes UI reutilizables
- `RelojCronometro`: Widget de cronómetro
- `TablaPosiciones`: Tabla de posiciones
- `SelectorJugadores`: Selector de jugadores con checkboxes

### Config

- `settings.py`: Configuración de la aplicación (URLs, tokens, título)
- `constants.py`: Colores, constantes, datos iniciales

### Utils

- `time_utils.py`: Funciones para formato y cálculo de tiempo
- `data_utils.py`: Funciones para exportación y cálculo de estadísticas

## 🔧 Variables de Entorno

- `TURSO_URL`: URL de la base de datos Turso (opcional, tiene valor por defecto)
- `TURSO_TOKEN`: Token de autenticación Turso (opcional, tiene valor por defecto)
- `PORT`: Puerto de la aplicación (default: 8080)

## 📝 Notas

- El archivo original `main.py` se respaldó como `main.py.backup`
- La aplicación usa Flet para la interfaz de usuario
- La base de datos está en Turso (LibSQL)
- Soporta sincronización multi-dispositivo
- Tiene roles de Administrador e Invitado

## 🤝 Contribución

Para agregar nuevas funcionalidades:

1. **Backend**: Agregar modelo en `backend/models/`, repository en `backend/database/repositories.py`, y servicio en `backend/services/`
2. **Frontend**: Agregar pantalla en `frontend/screens/` o componente en `frontend/components/`
3. **Config**: Agregar constantes en `config/constants.py` o configuración en `config/settings.py`
4. **Utils**: Agregar funciones auxiliares en `utils/`
