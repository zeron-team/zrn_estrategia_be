import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Ensure this script is run within a virtual environment
if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
    print("Error: This script should be run within a virtual environment.")
    print("Please activate your virtual environment first (e.g., 'source .venv/bin/activate').")
    sys.exit(1)

# Import necessary modules after setting up the path
from app.db.session import engine_chatbot
from app.models.message import Base

print("Dropping all tables...")
Base.metadata.drop_all(engine_chatbot)
print("Creating all tables...")
Base.metadata.create_all(engine_chatbot)
print("Database recreated successfully.")

# Reminder to install dependencies if not already done
print("\nRemember to install backend dependencies if you haven't already:")
print("pip install -r backend/requirements.txt")
