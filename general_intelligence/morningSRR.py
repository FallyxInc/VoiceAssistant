import datetime
import json
import sys
import os

# Import speak from wake_word_listener.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from wake_word_listener import speak

def get_ordinal(n):
    # Returns the ordinal string for a given integer n (e.g., 1 -> '1st')
    if 10 <= n % 100 <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f"{n}{suffix}"

def speak_morning_schedule_announcement():
    today_dt = datetime.datetime.now()
    today = today_dt.strftime('%Y-%m-%d')
    month = today_dt.strftime('%B')
    day = get_ordinal(today_dt.day)
    year = today_dt.year
    try:
        # Get schedule
        with open('general_intelligence/may_2025_calendar.json', 'r') as f:
            calendar = json.load(f)
        
        # Get food menu
        with open('general_intelligence/food.json', 'r') as f:
            food_data = json.load(f)
        
        # Build schedule message
        if today in calendar:
            day_info = calendar[today]
            day_of_week = day_info.get('Day', '')
            events = day_info.get('Events', [])
            if not events:
                message = f"Good morning residents, hope you all slept well. It is {month} {day}, {year}. There are no scheduled events today."
            else:
                message = f"Good morning residents, hope you all slept well. It is {month} {day}, {year}. Here is your schedule: "
                event_lines = []
                for event in events:
                    time = event.get('Time', '').strip()
                    name = event.get('Name', '').strip()
                    location = event.get('Location', '').strip()
                    line = ""
                    if time:
                        line += f"At {time} "
                    if name:
                        line += f"there is {name}"
                    if location:
                        line += f" in the {location}"
                    if line:
                        event_lines.append(line)
                message += ". ".join(event_lines)
        else:
            message = f"Good morning residents, hope you all slept well. It is {month} {day}, {year}. There is no schedule found for today."

        # Add food menu
        if today in food_data['days']:
            menu = food_data['days'][today]
            message += "\n\nHere's today's menu: "
            
            # Add soup
            if 'soup' in menu:
                message += f"\nFor soup, we have {menu['soup']}."
            
            # Add lunch
            if 'lunch' in menu:
                message += "\nFor lunch:"
                if 'main_1' in menu['lunch']:
                    message += f"\n- {menu['lunch']['main_1']}"
                if 'main_2' in menu['lunch']:
                    message += f"\n- Alternatively, if you want something else, we have {menu['lunch']['main_2']}"
                if 'note' in menu['lunch']:
                    message += f"\nNote: {menu['lunch']['note']}"
                if 'dessert_lunch' in menu:
                    message += f"\nDessert: {menu['dessert_lunch']}"
            
            # Add dinner
            if 'dinner' in menu:
                message += "\nFor dinner:"
                if 'main_1' in menu['dinner']:
                    message += f"\n- {menu['dinner']['main_1']}"
                if 'main_2' in menu['dinner']:
                    message += f"\n- Alternatively, if you want something else, we have {menu['dinner']['main_2']}"
                if 'sides' in menu['dinner']:
                    message += f"\nSides: {menu['dinner']['sides']}"
                if 'note' in menu['dinner']:
                    message += f"\nNote: {menu['dinner']['note']}"
                if 'dessert_dinner' in menu:
                    message += f"\nDessert: {menu['dessert_dinner']}"
        else:
            message += "\n\nI'm sorry, I couldn't find today's menu in the system."

    except Exception as e:
        message = f"Good morning residents, hope you all slept well. I'm sorry, I couldn't retrieve today's information: {str(e)}"
    
    speak(message)

if __name__ == "__main__":
    speak_morning_schedule_announcement()
