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
import queue
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('wake_word_listener.log'),
        logging.StreamHandler()
    ]
)

# Load environment variables from .env file
load_dotenv()

is_speaking = False

def log_operation(operation, details=None):
    """Log an operation with timing information"""
    if details:
        logging.info(f"{operation}: {details}")
    else:
        logging.info(operation)

def initialize_openai():
    """Initialize OpenAI client with API key"""
    log_operation("Initializing OpenAI client")
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        logging.error("OPENAI_API_KEY not found in .env file or environment variables.")
        print("Error: OPENAI_API_KEY not found in .env file or environment variables.")
        print("Please create a .env file with your OpenAI API key:")
        print("OPENAI_API_KEY=your-api-key-here")
        sys.exit(1)
    return OpenAI(api_key=api_key)

# Initialize OpenAI client
try:
    client = initialize_openai()
    log_operation("OpenAI client initialized successfully")
except Exception as e:
    logging.error(f"Error initializing OpenAI client: {e}")
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

def play_audio_file(output_file):
    """Play audio file synchronously (waits until done)."""
    if os.name == 'posix':
        # Use aplay with specific device output for Orange Pi
        subprocess.run(["aplay", "-D", "plughw:3,0", output_file])
    else:
        os.system(f"start {output_file}")

def speak(text):
    """Convert text to speech using OpenAI's TTS with Onyx voice, synchronously."""
    start_time = time.time()
    log_operation("Starting text-to-speech conversion", f"Text: {text[:50]}...")
    
    try:
        # Generate speech
        tts_start = time.time()
        response = client.audio.speech.create(
            model="tts-1",
            voice="onyx",
            input=text
        )
        tts_time = time.time() - tts_start
        log_operation("TTS generation completed", f"Time taken: {tts_time:.2f}s")
        
        # Save as MP3 first (required by OpenAI)
        temp_mp3 = "temp_speech.mp3"
        temp_wav = "temp_speech.wav"
        
        # Save MP3
        save_start = time.time()
        with open(temp_mp3, 'wb') as f:
            for chunk in response.iter_bytes():
                f.write(chunk)
        save_time = time.time() - save_start
        log_operation("MP3 file saved", f"Time taken: {save_time:.2f}s")
        
        # Convert MP3 to WAV using ffmpeg
        convert_start = time.time()
        subprocess.run(['ffmpeg', '-i', temp_mp3, '-y', temp_wav], 
                      stdout=subprocess.DEVNULL, 
                      stderr=subprocess.DEVNULL)
        convert_time = time.time() - convert_start
        log_operation("MP3 to WAV conversion completed", f"Time taken: {convert_time:.2f}s")
        
        # Play the WAV file using the specific device
        play_start = time.time()
        if os.name == 'posix':
            subprocess.run(["aplay", "-D", "plughw:3,0", temp_wav])
        else:
            os.system(f"start {temp_wav}")
        play_time = time.time() - play_start
        log_operation("Audio playback completed", f"Time taken: {play_time:.2f}s")
        
        # Clean up temporary files
        try:
            os.remove(temp_mp3)
            os.remove(temp_wav)
            log_operation("Temporary files cleaned up")
        except:
            log_operation("Warning: Failed to clean up temporary files")
            
        total_time = time.time() - start_time
        log_operation("Text-to-speech process completed", 
                     f"Total time: {total_time:.2f}s (TTS: {tts_time:.2f}s, Save: {save_time:.2f}s, Convert: {convert_time:.2f}s, Play: {play_time:.2f}s)")
            
    except Exception as e:
        logging.error(f"Error in text-to-speech: {e}")
        print(f"Error in text-to-speech: {e}")

def record_audio(duration=2, fs=44100):
    """Record audio from microphone"""
    start_time = time.time()
    log_operation("Starting audio recording", f"Duration: {duration}s")
    
    # Use arecord with specific device for Orange Pi
    temp_file = "temp_recording.wav"
    subprocess.run([
        "arecord",
        "-D", "plughw:3,0",
        "-f", "cd",
        "-d", str(duration),
        temp_file
    ])
    
    record_time = time.time() - start_time
    log_operation("Audio recording completed", f"Time taken: {record_time:.2f}s")
    return temp_file

def transcribe_audio(audio_path):
    """Transcribe audio using OpenAI's Whisper"""
    start_time = time.time()
    log_operation("Starting audio transcription")
    
    try:
        with open(audio_path, "rb") as f:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=f
            )
        transcribe_time = time.time() - start_time
        log_operation("Transcription completed", 
                     f"Time taken: {transcribe_time:.2f}s, Text: {transcript.text[:50]}...")
        return transcript.text
    except Exception as e:
        logging.error(f"Error transcribing audio: {e}")
        return None
    finally:
        # Clean up the temporary file
        try:
            os.remove(audio_path)
            log_operation("Temporary audio file cleaned up")
        except:
            log_operation("Warning: Failed to clean up temporary audio file")

def listen_for_response():
    """Listen for user's response and convert to text"""
    start_time = time.time()
    log_operation("Starting response listening")
    
    global is_speaking
    while is_speaking:
        time.sleep(0.1)  # Wait until not speaking
    
    audio_path = record_audio(duration=5)
    if not audio_path:
        log_operation("No audio recorded")
        return None
    
    try:
        text = transcribe_audio(audio_path)
        log_operation("Response processed", f"Heard: {text}")
        return text
    except Exception as e:
        logging.error(f"Error in response detection: {e}")
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
                return f"Today is {day_of_week}, {month} {day}, {year}. There are no scheduled events for today."
            
            response = f"Today is {day_of_week}, {month} {day}, {year}. Here's what's on your schedule: "
            event_lines = []
            for i, event in enumerate(events):
                time = event.get('Time', '').strip()
                name = event.get('Name', '').strip()
                location = event.get('Location', '').strip()
                
                line = ""
                if time:
                    line += f"At {time}, "
                if name:
                    line += f"you have {name}"
                if location:
                    line += f" in the {location}"
                if line:
                    if i == len(events) - 1:
                        line = f"and {line}"
                    event_lines.append(line)
            
            response += ", ".join(event_lines) + "."
            return response
        else:
            return f"It's {month} {day}, {year}. There is no schedule found for today."
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
            response = "Here's what's on the menu for today: "
            
            # Add soup
            if 'soup' in menu:
                response += f"\nFor soup, we're serving {menu['soup']}."
            
            # Add lunch
            if 'lunch' in menu:
                response += "\nFor lunch, "
                lunch_items = []
                if 'main_1' in menu['lunch']:
                    lunch_items.append(menu['lunch']['main_1'])
                if 'main_2' in menu['lunch']:
                    lunch_items.append(f"or you can have {menu['lunch']['main_2']}")
                if lunch_items:
                    response += " ".join(lunch_items)
                if 'note' in menu['lunch']:
                    response += f"\nNote: {menu['lunch']['note']}"
                if 'dessert_lunch' in menu:
                    response += f"\nFor dessert, we have {menu['dessert_lunch']}"
            
            # Add dinner
            if 'dinner' in menu:
                response += "\nFor dinner, "
                dinner_items = []
                if 'main_1' in menu['dinner']:
                    dinner_items.append(menu['dinner']['main_1'])
                if 'main_2' in menu['dinner']:
                    dinner_items.append(f"or you can have {menu['dinner']['main_2']}")
                if dinner_items:
                    response += " ".join(dinner_items)
                if 'sides' in menu['dinner']:
                    response += f"\nThe sides include {menu['dinner']['sides']}"
                if 'note' in menu['dinner']:
                    response += f"\nNote: {menu['dinner']['note']}"
                if 'dessert_dinner' in menu:
                    response += f"\nFor dessert, we have {menu['dessert_dinner']}"
            
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
    
    # Normalize the text by removing punctuation and converting to lowercase
    text = text.lower().replace('.', '').replace(',', '').replace('!', '').replace('?', '')
    
    # List of possible wake word variations
    wake_words = [
        "woolly", "hey woolly",
        "wolly", "hey wolly",
        "wooly", "hey wooly",
        "willy", "hey willy",
        "willie", "hey willie",
        "wally", "hey wally",
        "olly", "hey olly",
        "wollie", "hey wollie",
        "wolli", "hey wolli",
        "woli", "hey woli",
        "woll", "hey woll"
    ]
    
    # Check for exact matches
    if any(wake_word in text for wake_word in wake_words):
        return True
    
    # Check for similar pronunciations using common mishearings
    similar_words = {
        "woolly": ["willy", "wally", "olly", "wollie", "wolli", "woli", "woll"],
        "wolly": ["willy", "wally", "olly", "wollie", "wolli", "woli", "woll"],
        "wooly": ["willy", "wally", "olly", "wollie", "wolli", "woli", "woll"]
    }
    
    # Check if any part of the text contains a similar word
    words = text.split()
    for word in words:
        for base_word, variations in similar_words.items():
            if word in variations:
                return True
    
    return False

def main():
    # Check for FLAC installation first
    if not check_flac_installation():
        return

    log_operation("=== Starting Wake Word Listener ===")
    print("Initializing wake word listener...")
    print("Wake word listener started. Say 'Woolly' or 'Hey Woolly' to activate.")
    
    try:
        while True:
            log_operation("Listening for wake word...")
            print("Listening for wake word...")
            heard = listen_for_response()
            if detect_wake_word(heard):
                log_operation("Wake word detected", f"Heard: {heard}")
                speak("Hello! I'm Woolly. How can I help you today?")
                handle_conversation()
                time.sleep(1)  # Small delay to prevent multiple triggers
    except KeyboardInterrupt:
        log_operation("Wake word listener stopped by user")
        print("\nWake word listener stopped.")
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main() 