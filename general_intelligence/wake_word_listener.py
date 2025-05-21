import speech_recognition as sr
import time
import subprocess
import sys
import os
from openai import OpenAI
from dotenv import load_dotenv
import datetime
import requests
import json
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import threading
import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
import queue

# Load environment variables from .env file
load_dotenv()

is_speaking = False

def initialize_openai():
    """Initialize OpenAI client with API key"""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("Error: OPENAI_API_KEY not found in .env file or environment variables.")
        print("Please create a .env file with your OpenAI API key:")
        print("OPENAI_API_KEY=your-api-key-here")
        sys.exit(1)
    return OpenAI(api_key=api_key)

# Initialize OpenAI client
try:
    client = initialize_openai()
except Exception as e:
    print(f"Error initializing OpenAI client: {e}")
    sys.exit(1)

def check_flac_installation():
    """Check if FLAC is installed and provide installation instructions if not"""
    try:
        subprocess.run(['flac', '--version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("FLAC is not installed. Please install it using:")
        print("brew install flac")
        return False

def prepare_audio_recording(fs=44100):
    """Prepare audio recording settings"""
    sd.default.samplerate = fs
    sd.default.channels = 1
    sd.default.dtype = 'int16'

def play_audio_file(output_file):
    """Play audio file synchronously (waits until done)."""
    if os.name == 'posix':
        os.system(f"afplay {output_file}")
    else:
        os.system(f"start {output_file}")

def speak(text):
    """Convert text to speech using OpenAI's TTS with Onyx voice, synchronously."""
    try:
        response = client.audio.speech.create(
            model="tts-1",
            voice="onyx",
            input=text
        )
        temp_file = "temp_speech.mp3"
        with open(temp_file, 'wb') as f:
            for chunk in response.iter_bytes():
                f.write(chunk)
        play_audio_file(temp_file)  # This will block until audio is done
        try:
            os.remove(temp_file)
        except:
            pass
    except Exception as e:
        print(f"Error in text-to-speech: {e}")

def record_audio(duration=2, fs=44100):
    """Record audio from microphone"""
    print("Recording...")
    audio = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='int16')
    sd.wait()
    
    # Save to temporary file
    temp_file = "temp_recording.wav"
    write(temp_file, fs, audio)
    return temp_file

def transcribe_audio(audio_path):
    """Transcribe audio using OpenAI's Whisper"""
    try:
        with open(audio_path, "rb") as f:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=f
            )
        return transcript.text
    except Exception as e:
        print(f"Error transcribing audio: {e}")
        return None
    finally:
        # Clean up the temporary file
        try:
            os.remove(audio_path)
        except:
            pass

def listen_for_response():
    """Listen for user's response and convert to text"""
    global is_speaking
    while is_speaking:
        time.sleep(0.1)  # Wait until not speaking
    audio_path = record_audio(duration=5)
    if not audio_path:
        return None
    try:
        text = transcribe_audio(audio_path)
        print(f"[Heard]: {text}")
        return text
    except Exception as e:
        print(f"Error in response detection: {e}")
        return None

def get_weather():
    """Get current weather using OpenWeatherMap API"""
    api_key = os.getenv('OPENWEATHERMAP_API_KEY')
    if not api_key:
        return "I'm sorry, I don't have access to the weather API key."
    
    try:
        response = requests.get('http://ip-api.com/json/')
        location = response.json()
        lat, lon = location['lat'], location['lon']
        
        weather_url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"
        weather_response = requests.get(weather_url)
        weather_data = weather_response.json()
        
        temp = weather_data['main']['temp']
        description = weather_data['weather'][0]['description']
        return f"The current temperature is {temp}°C with {description}."
    except Exception as e:
        return f"I'm sorry, I couldn't get the weather information: {str(e)}"

def play_spotify_song(song_name):
    """Play a song on Spotify"""
    try:
        sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=os.getenv('SPOTIFY_CLIENT_ID'),
            client_secret=os.getenv('SPOTIFY_CLIENT_SECRET'),
            redirect_uri=os.getenv('SPOTIFY_REDIRECT_URI'),
            scope="user-modify-playback-state user-read-playback-state"
        ))
        
        # Get available devices
        devices = sp.devices()
        if not devices['devices']:
            return "No Spotify devices found. Please make sure Spotify is running on your computer or phone."
        
        # Try to find an active device first
        active_device = None
        for device in devices['devices']:
            if device['is_active']:
                active_device = device
                break
        
        # If no active device, use the first available device
        if not active_device and devices['devices']:
            active_device = devices['devices'][0]
            # Set it as the active device
            sp.transfer_playback(active_device['id'])
        
        if not active_device:
            return "No Spotify devices available. Please make sure Spotify is running."
        
        # Search for the song
        results = sp.search(q=song_name, limit=1, type='track')
        if results['tracks']['items']:
            track_uri = results['tracks']['items'][0]['uri']
            # Play the song on the active device
            sp.start_playback(device_id=active_device['id'], uris=[track_uri])
            return f"Playing {results['tracks']['items'][0]['name']} by {results['tracks']['items'][0]['artists'][0]['name']}"
        else:
            return "I couldn't find that song on Spotify."
    except Exception as e:
        error_message = str(e)
        if "No active device found" in error_message:
            return "No active Spotify device found. Please make sure Spotify is running and you're logged in."
        elif "No active device" in error_message:
            return "No active Spotify device found. Please make sure Spotify is running and you're logged in."
        else:
            return f"I'm sorry, I couldn't play the song: {error_message}"

def get_time_date():
    """Get current time and date"""
    now = datetime.datetime.now()
    return f"The current time is {now.strftime('%I:%M %p')} and the date is {now.strftime('%B %d, %Y')}"

def get_ordinal(n):
    # Returns the ordinal string for a given integer n (e.g., 1 -> '1st')
    if 10 <= n % 100 <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f"{n}{suffix}"

def get_todays_schedule():
    today_dt = datetime.datetime.now()
    today = today_dt.strftime('%Y-%m-%d')
    month = today_dt.strftime('%B')
    day = get_ordinal(today_dt.day)
    year = today_dt.year
    try:
        with open('general_intelligence/may_2025_calendar.json', 'r') as f:
            calendar = json.load(f)
        if today in calendar:
            day_info = calendar[today]
            day_of_week = day_info.get('Day', '')
            events = day_info.get('Events', [])
            if not events:
                return f"Today is {day_of_week}. It is {month} {day}, {year}. There are no scheduled events."
            response = f"Today is {day_of_week}. It is {month} {day}, {year}. The events are: "
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
            response += ". ".join(event_lines)
            return response
        else:
            return f"It is {month} {day}, {year}. There is no schedule found for today."
    except Exception as e:
        return f"I'm sorry, I couldn't retrieve today's schedule: {str(e)}"

def get_todays_menu():
    """Get today's food menu from the food.json file"""
    today_dt = datetime.datetime.now()
    today = today_dt.strftime('%Y-%m-%d')
    try:
        with open('general_intelligence/food.json', 'r') as f:
            food_data = json.load(f)
        if today in food_data['days']:
            menu = food_data['days'][today]
            response = f"Here's today's menu: "
            
            # Add soup
            if 'soup' in menu:
                response += f"\nFor soup, we have {menu['soup']}."
            
            # Add lunch
            if 'lunch' in menu:
                response += "\nFor lunch:"
                if 'main_1' in menu['lunch']:
                    response += f"\n- {menu['lunch']['main_1']}"
                if 'main_2' in menu['lunch']:
                    response += f"\n- {menu['lunch']['main_2']}"
                if 'note' in menu['lunch']:
                    response += f"\nNote: {menu['lunch']['note']}"
                if 'dessert_lunch' in menu:
                    response += f"\nDessert: {menu['dessert_lunch']}"
            
            # Add dinner
            if 'dinner' in menu:
                response += "\nFor dinner:"
                if 'main_1' in menu['dinner']:
                    response += f"\n- {menu['dinner']['main_1']}"
                if 'main_2' in menu['dinner']:
                    response += f"\n- {menu['dinner']['main_2']}"
                if 'sides' in menu['dinner']:
                    response += f"\nSides: {menu['dinner']['sides']}"
                if 'note' in menu['dinner']:
                    response += f"\nNote: {menu['dinner']['note']}"
                if 'dessert_dinner' in menu:
                    response += f"\nDessert: {menu['dessert_dinner']}"
            
            return response
        else:
            return "I'm sorry, I couldn't find today's menu in the system."
    except Exception as e:
        return f"I'm sorry, I couldn't retrieve today's menu: {str(e)}"

def interpret_intent(text):
    # Call the original GPT-based intent function here
    prompt = f"""
    Classify the following user request into one of these categories:
    1. Weather - If they're asking about weather conditions
    2. Play music - If they want to play a song or music
    3. Time and date - If they're asking about current time or date
    4. Today schedule - If they're asking about today's schedule, calendar, or events
    5. Outfit advice - If they're asking what to wear, what outfit is appropriate, or clothing suggestions based on weather or temperature
    6. Food menu - If they're asking about today's menu, what's for lunch/dinner, or food options
    7. Other - For any other type of request

    User request: "{text}"

    Respond in JSON format:
    {{
        "intent": "weather|play_music|time_date|today_schedule|outfit_advice|food_menu|other",
        "details": "any additional details needed (e.g., song name for music, temperature for outfit advice)"
    }}
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        result = json.loads(response.choices[0].message.content)
        return result
    except Exception as e:
        print(f"Error interpreting intent: {e}")
        return {"intent": "other", "details": ""}

def handle_conversation():
    while True:
        response = listen_for_response()
        while response:
            intent = interpret_intent(response)
            if intent["intent"] == "today_schedule":
                schedule_info = get_todays_schedule()
                speak(schedule_info)
            elif intent["intent"] == "weather":
                weather_info = get_weather()
                speak(weather_info)
            elif intent["intent"] == "play_music":
                if intent["details"]:
                    result = play_spotify_song(intent["details"])
                    speak(result)
                else:
                    speak("What song would you like me to play?")
                    song_response = listen_for_response()
                    if song_response:
                        result = play_spotify_song(song_response)
                        speak(result)
            elif intent["intent"] == "time_date":
                time_date_info = get_time_date()
                speak(time_date_info)
            elif intent["intent"] == "food_menu":
                menu_info = get_todays_menu()
                speak(menu_info)
            elif intent["intent"] == "outfit_advice":
                # Use GPT to generate an outfit suggestion based on the details (which may include temperature)
                try:
                    gpt_response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[{"role": "user", "content": response}],
                        temperature=0.7
                    )
                    speak(gpt_response.choices[0].message.content)
                except Exception as e:
                    speak("I'm sorry, I couldn't process that request.")
            else:
                try:
                    gpt_response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[{"role": "user", "content": response}],
                        temperature=0.7
                    )
                    speak(gpt_response.choices[0].message.content)
                except Exception as e:
                    speak("I'm sorry, I couldn't process that request.")
            # After handling, ask if anything else
            speak("Is there anything else I can help you with?")
            final_response = listen_for_response()
            if final_response and any(word in final_response.lower() for word in ["no", "nope", "that's all", "that's it", "nothing else"]):
                speak("Goodbye!")
                return
            else:
                response = final_response

def detect_wake_word(text):
    """Return True if the wake word is detected in the text."""
    if not text:
        return False
    wake_words = ["melon", "mellon", "hey melon", "hey mellon"]
    return any(wake_word in text.lower() for wake_word in wake_words)

def main():
    # Check for FLAC installation first
    if not check_flac_installation():
        return

    # Prepare audio recording settings
    prepare_audio_recording()

    print("Initializing wake word listener...")
    print("Wake word listener started. Say 'melon' or 'hey melon' to activate.")
    
    try:
        while True:
            print("Listening for wake word...")
            heard = listen_for_response()
            if detect_wake_word(heard):
                speak("I'm listening. How can I help you?")
                handle_conversation()
                time.sleep(1)  # Small delay to prevent multiple triggers
    except KeyboardInterrupt:
        print("\nWake word listener stopped.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main() 