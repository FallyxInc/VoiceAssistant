import datetime
import json
import sys
import os
import subprocess
import threading
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def play_audio_file(output_file):
    def play_audio():
        if os.name == 'posix':
            # Use aplay with specific device output for Orange Pi
            subprocess.run(["aplay", "-D", "plughw:3,0", output_file])
        else:
            os.system(f"start {output_file}")
    
    threading.Thread(target=play_audio).start()

def speak(message):
    """Convert text to speech using OpenAI TTS and play it back"""
    try:
        # Generate speech and save as MP3 first (required by OpenAI)
        temp_mp3 = "temp_speech.mp3"
        temp_wav = "morning_announcement.wav"
        
        response = client.audio.speech.create(
            model="tts-1",
            voice="nova",
            input=message
        )
        
        # Save the response content to MP3
        with open(temp_mp3, "wb") as f:
            for chunk in response.iter_bytes():
                f.write(chunk)
        
        # Convert MP3 to WAV with specific format for Respeaker
        subprocess.run([
            'ffmpeg', 
            '-i', temp_mp3,
            '-acodec', 'pcm_s16le',  # Use signed 16-bit PCM
            '-ar', '16000',          # Set sample rate to 16kHz
            '-ac', '1',              # Set to mono
            '-y',                    # Overwrite output file
            temp_wav
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Play the WAV file using aplay with specific device
        subprocess.run(["aplay", "-D", "plughw:3,0", temp_wav])
        
        # Clean up temporary files
        try:
            os.remove(temp_mp3)
        except:
            pass
        
    except Exception as e:
        print(f"Error in text-to-speech: {e}")

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
