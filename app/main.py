from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routers import whatsapp, notifications, auth, dashboard, courses, flows, crm, messages, users

app = FastAPI(
    title="Moodle Chatbot Backend",
    description="Backend funcional para recibir y enviar mensajes de WhatsApp.",
    version="1.2.0"
)

# --- 2. AÑADE ESTE BLOQUE DE CÓDIGO PARA CONFIGURAR CORS ---
# Orígenes permitidos (en este caso, tu app de React en desarrollo)
origins = [
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Permite todos los métodos (GET, POST, etc.)
    allow_headers=["*"],  # Permite todas las cabeceras
)
# --- FIN DEL BLOQUE DE CORS ---

# Router para mensajes entrantes (webhook)
app.include_router(whatsapp.router, prefix="/api/whatsapp", tags=["Whatsapp"])

# Router para mensajes salientes (notificaciones)
app.include_router(notifications.router, prefix="/api/v1/notifications", tags=["Notifications"])

# Router para la autenticación del CRM
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(dashboard.router, prefix="/api", tags=["Dashboard"])

app.include_router(courses.router, prefix="/api", tags=["Courses"])
app.include_router(flows.router, prefix="/api", tags=["Flows"])
app.include_router(crm.router, prefix="/api", tags=["CRM"])
app.include_router(messages.router, prefix="/api", tags=["Messages"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])


@app.get("/")
def read_root():
    return {"status": "API is running"}