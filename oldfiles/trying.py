from flask import Flask, request
from gtts import gTTS
import os
import subprocess
import pyaudio
import wave
import speech_recognition as sr
import requests
import threading
import time

app = Flask(__name__)
EMERGENCYNUMBER = "+16476772046"

def handle_fall_detection():
    try:
        # Generate speech
        tts = gTTS(text="Hey there, did you fall? If you fell, please say yes multiple times. If you're okay, then say no multiple times.", lang='en')
        tts.save("did_you_fall.mp3")
        print("TTS generated and saved as did_you_fall.mp3")

        # Convert mp3 to wav using ffmpeg and adjust volume to 10%
        subprocess.run(["ffmpeg", "-y", "-i", "did_you_fall.mp3", "-af", "volume=0.1", "did_you_fall.wav"], check=True)
        print("Converted did_you_fall.mp3 to did_you_fall.wav at 10% volume")

        # Play the wav file using aplay
        subprocess.run(["aplay", "-D", "plughw:2,0", "did_you_fall.wav"], check=True)
        print("Played did_you_fall.wav")

        # Record audio for 15 seconds
        CHUNK = 1024
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 44100
        RECORD_SECONDS = 10
        WAVE_OUTPUT_FILENAME = "output.wav"

        p = pyaudio.PyAudio()
        input_device_index = 2  # Replace with your USB microphone device index

        stream = p.open(format=FORMAT,
                        channels=CHANNELS,
                        rate=RATE,
                        input=True,
                        input_device_index=input_device_index,
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

        # Use speech recognition to convert audio to text
        recognizer = sr.Recognizer()
        with sr.AudioFile(WAVE_OUTPUT_FILENAME) as source:
            audio = recognizer.record(source)

        try:
            text = recognizer.recognize_google(audio).lower()
            print("Transcription: " + text)

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

            # Check for "yes" and "no" variations
            yes_detected = any(yes_word in text for yes_word in yes_variations)
            no_detected = any(no_word in text for no_word in no_variations)

            print(f"yes_detected: {yes_detected}, no_detected: {no_detected}")

            if yes_detected and not no_detected:
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
                subprocess.run(["aplay", "-D", "plughw:2,0", "emergency.wav"], check=True)
            elif no_detected and not yes_detected:
                print("No emergency, user confirmed they are okay.")
                tts = gTTS(text="Okay, sorry to disturb you. Enjoy the rest of your day.", lang='en')
                tts.save("no_emergency.mp3")
                subprocess.run(["ffmpeg", "-y", "-i", "no_emergency.mp3", "-af", "volume=0.1", "no_emergency.wav"], check=True)
                subprocess.run(["aplay", "-D", "plughw:2,0", "no_emergency.wav"], check=True)
            else:
                print("Ambiguous response, sending emergency request as a precaution.")
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
        print(f"Error: {e}")

@app.route('/fall', methods=['POST'])
def fall_detected():
    threading.Thread(target=handle_fall_detection).start()
    return 'Sound played and transcription done', 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
