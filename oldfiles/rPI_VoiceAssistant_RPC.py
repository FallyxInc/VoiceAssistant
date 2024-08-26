import paho.mqtt.client as mqtt
import json
import time
import signal
import sys
from datetime import datetime, timedelta
from gtts import gTTS
import subprocess
import pyaudio
import wave
import speech_recognition as sr
import requests
import simpleaudio as sa

# MQTT and Thingsboard configuration
thingsboard_host = "3.99.30.21"
ACCESS_TOKEN = "3iGKyFyNrPgCmVY6ppBW"
EMERGENCYNUMBER = "+16474532309"

# Initialize MQTT client
print(f'Connecting to: {thingsboard_host} using access token: {ACCESS_TOKEN}')
client = mqtt.Client()
client.username_pw_set(ACCESS_TOKEN)
client.connect(thingsboard_host, 1883, 60)

# Debounce configuration
DEBOUNCE_PERIOD = timedelta(seconds=30)
last_fall_event_time = datetime.min
fall_detection_in_progress = False

# Define callbacks
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print('Client connected successfully!')
        client.subscribe('v1/devices/me/rpc/request/+')
        print('Subscribed to RPC requests')
    else:
        print(f'Failed to connect, return code {rc}')

def on_message(client, userdata, msg):
    global last_fall_event_time, fall_detection_in_progress
    print(f'Received message on topic {msg.topic}')
    print(f'Message: {msg.payload.decode()}')
    message = json.loads(msg.payload.decode())

    current_time = datetime.now()

    if message.get('method') == 'fallEvent' and message.get('params') == True:
        print("Fall event detected")
        if not fall_detection_in_progress and (current_time - last_fall_event_time >= DEBOUNCE_PERIOD):
            last_fall_event_time = current_time
            fall_detection_in_progress = True
            handle_fall_detection()
            response = {"msg": {"params": True, "method": "fallEvent"}, "metadata": {}, "msgType": "RPC message"}
            client.publish('v1/devices/me/rpc/response/' + msg.topic.split('/')[-1], json.dumps(response))
        else:
            print("Fall event ignored due to debounce period or in-progress detection")
    else:
        print("Non-fall event or invalid message received")

def handle_fall_detection():
    global fall_detection_in_progress
    try:
        # Generate speech
        tts = gTTS(text="Hey there, did you fall? If you fell, please say yes multiple times. If you're okay, then say no multiple times.", lang='en')
        tts.save("did_you_fall.mp3")
        print("TTS generated and saved as did_you_fall.mp3")

        # Convert mp3 to wav using ffmpeg and adjust volume to 10%
        subprocess.run(["ffmpeg", "-y", "-i", "did_you_fall.mp3", "-af", "volume=0.1", "did_you_fall.wav"], check=True)
        print("Converted did_you_fall.mp3 to did_you_fall.wav at 10% volume")

        # Play the wav file using simpleaudio
        wave_obj = sa.WaveObject.from_wave_file("did_you_fall.wav")
        play_obj = wave_obj.play()
        play_obj.wait_done()
        print("Played did_you_fall.wav")

        # Record audio for 15 seconds
        CHUNK = 1024
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 44100
        RECORD_SECONDS = 15
        WAVE_OUTPUT_FILENAME = "output.wav"

        p = pyaudio.PyAudio()

        stream = p.open(format=FORMAT,
                        channels=CHANNELS,
                        rate=RATE,
                        input=True,
                        frames_per_buffer=CHUNK)

        print("Recording audio for 15 seconds...")

        frames = []

        for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
            data = stream.read(CHUNK)
            frames.append(data)

        print("Finished recording")

        stream.stop_stream()
        stream.close()
        p.terminate()

        wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
        wf.close()

        print("Audio recorded and saved as output.wav")

        # Use speech recognition to convert audio to text
        recognizer = sr.Recognizer()
        with sr.AudioFile(WAVE_OUTPUT_FILENAME) as source:
            audio = recognizer.record(source)

        try:
            text = recognizer.recognize_google(audio).lower()
            print(f"Transcription: {text}")

            # Define variations of "yes" and "no"
            yes_variations = [
                "yes", "i fell", "help", "i need help", "assistance", "i'm down", "i have fallen", 
                "i can't get up", "emergency", "fallen", "down", "not okay", "hurt", "injured", 
                "accident", "help me", "can't stand", "need assistance", "urgent", "please help",
                "i'm on the ground", "can't move", "in pain", "i need aid", "assist me", "i'm stuck",
                "need help", "please assist", "get help", "i'm in trouble", "i need support", "i'm hurt",
                "please hurry", "i'm in distress", "medical emergency"
            ]

            no_variations = [
                "no", "i'm okay", "fine", "all good", "no fall", "didn't fall", "okay", "all right", 
                "no help", "no issue", "no problem", "nothing happened", "i'm fine", "no need", 
                "no assistance", "safe", "unharmed", "good", "all clear", "no thanks",
                "i'm alright", "everything's fine", "not hurt", "not injured", "no damage", "no worries",
                "i'm good", "don't need help", "no concern", "all is well", "not necessary", "no need for help",
                "not required", "no harm", "everything's okay"
            ]

            if any(yes_word in text for yes_word in yes_variations):
                # Send emergency request
                url = "https://724cu8r3wk.execute-api.ca-central-1.amazonaws.com/Prod/outcall"
                headers = {'Content-Type': 'application/json'}
                data = {
                    "emergencyPhoneNumber": EMERGENCYNUMBER,
                    "emergencyFirstname": "SRR",
                    "userFirstName": "Clay",
                    "userLastName": ""
                }
                response = requests.post(url, json=data, headers=headers)
                print(f"Emergency request sent, response status code: {response.status_code}")
                tts = gTTS(text="Ok don't worry, the nurse is coming to help you. Please remain calm.", lang='en')
                tts.save("emergency.mp3")
                subprocess.run(["ffmpeg", "-y", "-i", "emergency.mp3", "-af", "volume=1", "emergency.wav"], check=True)
                wave_obj = sa.WaveObject.from_wave_file("emergency.wav")
                play_obj = wave_obj.play()
                play_obj.wait_done()
            elif any(no_word in text for no_word in no_variations):
                print("No emergency, user confirmed they are okay.")
                tts = gTTS(text="Okay, sorry to disturb you. Enjoy the rest of your day.", lang='en')
                tts.save("no_emergency.mp3")
                subprocess.run(["ffmpeg", "-y", "-i", "no_emergency.mp3", "-af", "volume=0.1", "no_emergency.wav"], check=True)
                wave_obj = sa.WaveObject.from_wave_file("no_emergency.wav")
                play_obj = wave_obj.play()
                play_obj.wait_done()
            else:
                raise sr.UnknownValueError("Unrecognized response")

        except sr.UnknownValueError:
            print("No or minimal input detected. Sending emergency request.")
            url = "https://724cu8r3wk.execute-api.ca-central-1.amazonaws.com/Prod/outcall"
            headers = {'Content-Type': 'application/json'}
            data = {
                    "emergencyPhoneNumber": EMERGENCYNUMBER,
                    "emergencyFirstname": "SRR",
                    "userFirstName": "Clay",
                    "userLastName": ""
            }
            response = requests.post(url, json=data, headers=headers)
            print(f"Emergency request sent, response status code: {response.status_code}")
        except sr.RequestError as e:
            print(f"Could not request results from Google Speech Recognition service; {e}")

    except Exception as e:
        print(f"Error in handle_fall_detection: {e}")
    finally:
        fall_detection_in_progress = False

# Catches Ctrl+C event
def signal_handler(sig, frame):
    print()
    print('Disconnecting...')
    client.disconnect()
    print('Exited!')
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

client.on_connect = on_connect
client.on_message = on_message
client.loop_start()

# Keeping the script running
while True:
    time.sleep(1)
