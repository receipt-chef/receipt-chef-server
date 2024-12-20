import uuid
import logging
import re
import json

meal_plan_storage = {}

def save_meal_plan(meal_plan):
    meal_plan_id = str(uuid.uuid4())
    meal_plan_storage[meal_plan_id] = json.dumps(meal_plan)  # Store as JSON string
    logger.info("Meal plan saved with ID: %s", meal_plan_id)
    return meal_plan_id

def get_meal_plan(meal_plan_id):
    meal_plan_json = meal_plan_storage.get(meal_plan_id)
    if meal_plan_json is None:
        logger.warning("Meal plan with ID %s not found", meal_plan_id)
        return None
    
    meal_plan = json.loads(meal_plan_json)
    logger.info("Retrieved meal plan with ID: %s", meal_plan_id)
    
    return meal_plan

logger = logging.getLogger('meal')
logger.setLevel(logging.INFO)
