##  Estructura

```text
/moodle-chatbot-backend
├── app/
│   ├── __init__.py
│   ├── main.py                 # Orquestador principal de la app
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py             # Gestiona las dependencias (inyección)
│   │   └── routers/
│   │       ├── __init__.py
│   │       ├── auth.py         # Rutas de autenticación para el CRM
│   │       └── whatsapp.py     # Ruta del Webhook de WhatsApp
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py           # Carga de configuración desde .env
│   ├── crud/
│   │   ├── __init__.py
│   │   ├── base.py             # CRUD genérico base
│   │   └── crud_message.py     # CRUD específico para mensajes
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base_class.py       # Modelo SQLAlchemy base
│   │   └── session.py          # Gestión de la sesión de la DB
│   ├── models/
│   │   ├── __init__.py
│   │   └── message.py          # Modelo SQLAlchemy para la tabla 'messages'
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── message.py          # Esquemas Pydantic para mensajes
│   │   ├── token.py            # Esquemas Pydantic para JWT
│   │   └── user.py             # Esquemas Pydantic para usuarios
│   └── services/
│       ├── __init__.py
│       ├── interfaces.py       # Interfaces (ABCs) para los servicios (CLAVE para OCP y DIP)
│       └── moodle_service.py   # Implementación concreta del servicio de Moodle
│       └── whatsapp_service.py # Implementación concreta del servicio de WhatsApp
├── .env
├── .gitignore
└── requirements.txt
```