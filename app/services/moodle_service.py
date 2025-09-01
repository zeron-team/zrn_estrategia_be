# app/services/moodle_service.py

import requests
from app.core.config import settings
from .interfaces import IMoodleService


class MoodleService(IMoodleService):
    # Principio de Responsabilidad Única (S): Solo habla con Moodle.
    def get_student_grade(self, user_id: int) -> float | None:
        params = {
            'wstoken': settings.MOODLE_API_TOKEN,
            'wsfunction': 'gradereport_user_get_grade_items',
            'moodlewsrestformat': 'json',
            'courseid': settings.MOODLE_COURSE_ID,
            'userid': user_id
        }
        try:
            response = requests.get(settings.MOODLE_API_URL, params=params)
            response.raise_for_status()
            data = response.json()

            # Lógica para extraer la calificación final del JSON de Moodle
            # Esto puede variar según tu configuración de Moodle.
            # Aquí un ejemplo genérico:
            if "usergrades" in data and data["usergrades"]:
                for grade_item in data["usergrades"][0]["gradeitems"]:
                    if grade_item["itemtype"] == "course":
                        return grade_item["gradeformatted"]
            return None
        except requests.RequestException as e:
            print(f"Error connecting to Moodle API: {e}")
            return None
        except (KeyError, IndexError) as e:
            print(f"Error parsing Moodle response: {e}")
            return None