# Ifes Chatbot Moodle CRM - Backend

This is the backend for the Ifes Chatbot Moodle CRM project. It is a FastAPI application that provides a REST API to interact with the Moodle CRM and the WhatsApp chatbot.

## Features

*   **User Authentication & Authorization:** Secure user management with JWT-based authentication.
*   **Moodle Integration:** Interact with Moodle for course information, student data, and grade management.
*   **CRM Functionality:** Manage customer relationships and student interactions.
*   **WhatsApp Chatbot:** Integrate with WhatsApp for automated communication and flow management.
*   **Dynamic Flows:** Define and manage conversational flows for the chatbot.
*   **Notifications:** Send various notifications (e.g., absent, failed, grade, passed) to students.
*   **Dashboard & Analytics:** Provide data for dashboard visualizations and KPIs.
*   **Message Management:** Handle incoming and outgoing messages.

## Tech Stack

-   **Framework:** FastAPI
-   **Database:** PostgreSQL (assumed, as it is common with SQLAlchemy)
-   **ORM:** SQLAlchemy
-   **Authentication:** JWT

## Prerequisites

-   Python 3.12
-   pip
-   virtualenv (or pyenv for managing Python versions)

## Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd Ifes_chatbot_moodle_crm/backend
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```
    If you use `pyenv`, you might do:
    ```bash
    pyenv install 3.12
    pyenv local 3.12
    python -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install the dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up the environment variables:**
    Copy the `.env.example` file to `.env` and fill in the required values.

    ```bash
    cp .env.example .env
    ```

    **Required Environment Variables:**

    *   **Database Configuration (for the CRM backend):**
        *   `DB_USER`: Username for the CRM database.
        *   `DB_PASSWORD`: Password for the CRM database.
        *   `DB_HOST`: Host for the CRM database (e.g., `localhost`).
        *   `DB_PORT`: Port for the CRM database (e.g., `5432` for PostgreSQL, `3306` for MySQL).
        *   `DB_NAME`: Name of the CRM database.

    *   **Moodle Database Configuration:**
        *   `MOODLE_DB_USER`: Username for the Moodle database.
        *   `MOODLE_DB_PASSWORD`: Password for the Moodle database.
        *   `MOODLE_DB_HOST`: Host for the Moodle database.
        *   `MOODLE_DB_PORT`: Port for the Moodle database.
        *   `MOODLE_DB_NAME`: Name of the Moodle database.
        *   `TARGET_COURSE_ID`: The ID of the target course in Moodle for specific operations.

    *   **Twilio (WhatsApp) Configuration:**
        *   `TWILIO_ACCOUNT_SID`: Your Twilio Account SID.
        *   `TWILIO_AUTH_TOKEN`: Your Twilio Auth Token.
        *   `TWILIO_FROM_NUMBER`: Your Twilio WhatsApp-enabled phone number (e.g., `whatsapp:+1234567890`).

    *   **WhatsApp Webhook Verification:**
        *   `WHATSAPP_VERIFY_TOKEN`: A token used to verify WhatsApp webhooks.

    *   **Authentication Secrets:**
        *   `SECRET_KEY`: A strong secret key for JWT token encoding.
        *   `ALGORITHM`: The algorithm used for JWT signing (e.g., `HS256`).
        *   `ACCESS_TOKEN_EXPIRE_MINUTES`: Expiration time for access tokens in minutes.

## Database Setup

1.  **Recreate the database:**
    This script will create the necessary tables in the database based on the SQLAlchemy models.
    ```bash
    python scripts/recreate_db.py
    ```

2.  **Create the first superuser:**
    This script will create the first user with superuser privileges, which can be used to access the admin functionalities.
    ```bash
    python scripts/create_first_user.py
    ```
3.  **Create CRM Database (Optional):**
    If you need to specifically set up the CRM database, you can use:
    ```bash
    python scripts/create_crm_db.py
    ```

## Running the Application

To run the development server, use the following command:
```bash
uvicorn app.main:app --reload
```
The API will be available at `http://127.0.0.1:8000`.

**API Documentation:**
FastAPI automatically generates interactive API documentation. You can access it at:
*   **Swagger UI:** `http://127.0.0.1:8000/docs`
*   **ReDoc:** `http://127.00.1:8000/redoc`

## Utility Scripts

The `scripts/` directory contains several utility scripts to manage the application:

*   `create_crm_db.py`: Initializes or recreates the CRM-specific database tables.
*   `create_first_user.py`: Creates an initial superuser account for administrative access.
*   `recreate_db.py`: Drops and recreates all database tables defined by the application's models.
*   `send_absent_notifications.py`: Sends notifications to students marked as absent.
*   `send_failed_notifications.py`: Sends notifications to students who have failed a course or assessment.
*   `send_grade_notifications.py`: Sends notifications regarding student grades.
*   `send_passed_notifications.py`: Sends notifications to students who have passed a course or assessment.

To run any script, activate your virtual environment and execute it with `python`:
```bash
source .venv/bin/activate
python scripts/your_script_name.py
```

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
│   │   ├── alert.py            # Alert schemas
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
│   ├── create_crm_db.py
│   ├── create_first_user.py
│   ├── recreate_db.py
│   ├── send_absent_notifications.py
│   ├── send_failed_notifications.py
│   ├── send_grade_notifications.py
│   ├── send_passed_notifications.py
│   └── ...                     # Other utility scripts
├── .env
├── .env.example
├── .gitignore
└── requirements.txt
```