import sys
import os
from sqlalchemy import text

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.session import SessionLocalChatbot
from app.security import get_password_hash

def create_first_user():
    print("--- Creating first user ---")
    db = SessionLocalChatbot()
    try:
        # Check if user already exists
        query = text("SELECT id FROM crm_users WHERE username = 'zeron'")
        user = db.execute(query).first()
        if user:
            print("✅ User 'zeron' already exists.")
            return

        hashed_password = get_password_hash('admin')
        insert_query = text("INSERT INTO crm_users (username, hashed_password, role) VALUES ('zeron ', :hashed_password, 'zeron')")
        db.execute(insert_query, {"hashed_password": hashed_password})
        db.commit()
        print("✅ First user 'zeron' with password 'zeron' created successfully!")
    except Exception as e:
        print(f"❌ Error creating first user: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_first_user()
