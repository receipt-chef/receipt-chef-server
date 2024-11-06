# meal.py
import uuid
import logging

meal_plan_storage = {}

def parse_meal_plan_response(clova_x_response):
    """
    Parses the meal plan response from Clova X and structures it as a dictionary.
    Expected format:
    "| 요일 | 아침 | 점심 | 저녁 |\n| --- | --- | --- | --- |\n| 월요일 | ... | ... | ... |"
    """
    meal_plan = {}
    rows = clova_x_response.split("\\n")
    for row in rows[2:]:  # Skip the header rows
        try:
            day, breakfast, lunch, dinner = row.split(" | ")[1:5]
            meal_plan[day.strip()] = {
                "breakfast": breakfast.strip(),
                "lunch": lunch.strip(),
                "dinner": dinner.strip()
            }
        except ValueError:
            # Handle any rows that don't match the expected format
            continue

    return meal_plan

def save_meal_plan(meal_plan):
    """
    Stores the meal plan in an in-memory dictionary with a unique ID.
    """
    meal_plan_id = str(uuid.uuid4())
    meal_plan_storage[meal_plan_id] = meal_plan
    return meal_plan_id

def get_meal_plan(meal_plan_id):
    """
    Retrieves the meal plan from storage using its ID.
    """
    return meal_plan_storage.get(meal_plan_id)

# Optional: Configure a logger for meal.py
logger = logging.getLogger('meal')
