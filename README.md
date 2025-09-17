# Ifes Chatbot Moodle CRM - Backend

This is the backend for the Ifes Chatbot Moodle CRM project. It is a FastAPI application that provides a REST API to interact with the Moodle CRM and the WhatsApp chatbot.

## Tech Stack

- **Framework:** FastAPI
- **Database:** PostgreSQL (assumed, as it is common with SQLAlchemy)
- **ORM:** SQLAlchemy
- **Authentication:** JWT

## Prerequisites

- Python 3.12
- pip
- virtualenv

## Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd Ifes_chatbot_moodle_crm/backend
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install the dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up the environment variables:**
   Copy the `.env.example` file to `.env` and fill in the required values.
   ```bash
   cp .env.example .env
   ```

## Database Setup

1. **Recreate the database:**
   This script will create the necessary tables in the database.
   ```bash
   python scripts/recreate_db.py
   ```

2. **Create the first superuser:**
   This script will create the first user with superuser privileges.
   ```bash
   python scripts/create_first_user.py
   ```

## Running the Application

To run the development server, use the following command:
```bash
uvicorn app.main:app --reload
```
The API will be available at `http://127.0.0.1:8000`.

## Project Structure
```
/backend
├── app/
│   ├── __init__.py
│   ├── main.py                 # Main application orchestrator
│   ├── security.py             # Security-related functions (e.g., password hashing)
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py             # Dependency injection management
│   │   └── routers/
│   │       ├── __init__.py
│   │       ├── auth.py         # Authentication routes
│   │       ├── courses.py      # Course-related routes
│   │       ├── crm.py          # CRM-related routes
│   │       ├── dashboard.py    # Dashboard data routes
│   │       ├── flows.py        # Chatbot flow management routes
│   │       ├── messages.py     # Message handling routes
│   │       ├── notifications.py# Notification routes
│   │       ├── users.py        # User management routes
│   │       └── whatsapp.py     # WhatsApp Webhook route
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py           # Configuration loading from .env
│   ├── crud/
│   │   ├── __init__.py
│   │   ├── auth_queries.py     # Authentication-related database queries
│   │   ├── base.py             # Base generic CRUD
│   │   ├── course_queries.py   # Course-related database queries
│   │   ├── crm_queries.py      # CRM-related database queries
│   │   ├── crud_message.py     # CRUD for messages
│   │   ├── crud_operations.py  # Generic CRUD operations
│   │   ├── messages_queries.py # Message-related database queries
│   │   ├── moodle_queries.py   # Moodle-related database queries
│   │   └── user_queries.py     # User-related database queries
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base_class.py       # Base SQLAlchemy model
│   │   └── session.py          # Database session management
│   ├── flows/
│   │   ├── flow_manager.py     # Manages the conversation flow
│   │   └── flows.json          # Defines the conversation flows
│   ├── models/
│   │   ├── __init__.py
│   │   ├── message.py          # Message model
│   │   └── student.py          # Student model
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── kpi.py              # KPI-related schemas
│   │   ├── message.py          # Message schemas
│   │   ├── notification.py     # Notification schemas
│   │   ├── student.py          # Student schemas
│   │   ├── token.py            # Token schemas
│   │   └── user.py             # User schemas
│   └── services/
│       ├── __init__.py
│       ├── interfaces.py       # Service interfaces (ABCs)
│       ├── moodle_service.py   # Moodle service implementation
│       └── whatsapp_service.py # WhatsApp service implementation
├── scripts/
│   ├── create_first_user.py
│   ├── recreate_db.py
│   └── ...                     # Other utility scripts
├── .env
├── .env.example
├── .gitignore
└── requirements.txt
```