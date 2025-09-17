import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Ensure this script is run within a virtual environment
if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
    print("Error: This script should be run within a virtual environment.")
    print("Please activate your virtual environment first (e.g., 'source .venv/bin/activate').")
    sys.exit(1)

# Import necessary modules after setting up the path
from app.db.session import engine_chatbot
from app.models.message import Base as CrmBase

def create_crm_tables():
    """
    Creates all tables related to the CRM module.
    It will check for the existence of tables first and will not attempt
    to re-create tables that already exist.
    """
    print("Creating CRM database tables...")
    # The following models will be created as they inherit from CrmBase:
    # - CrmUser
    # - Message
    # - Student
    # - CaseAction
    # - ActionNote
    CrmBase.metadata.create_all(bind=engine_chatbot)
    print("CRM tables created successfully (if they didn't exist already).")

if __name__ == "__main__":
    create_crm_tables()
