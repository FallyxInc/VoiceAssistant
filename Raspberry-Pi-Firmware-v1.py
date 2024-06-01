from flask import Flask, request
from gtts import gTTS
import os
import subprocess
import pyaudio
import wave
import speech_recognition as sr
import requests

app = Flask(__name__)

@app.route('/fall', methods=['POST'])
def fall_detected():
    try:
        # Generate speech
        tts = gTTS(text="Hey there, did you fall? If you fell, please say yes multiple times. If you're okay, then say no multiple times.", lang='en')
        tts.save("did_you_fall.mp3")
        print("TTS generated and saved as did_you_fall.mp3")

        # Convert mp3 to wav using ffmpeg and adjust volume to 10%
        subprocess.run(["ffmpeg", "-y", "-i", "did_you_fall.mp3", "-af", "volume=0.1", "did_you_fall.wav"], check=True)
        print("Converted did_you_fall.mp3 to did_you_fall.wav at 10% volume")

        # Play the wav file
        subprocess.run(["paplay", "did_you_fall.wav"], check=True)
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

        # Use speech recognition to convert audio to text
        recognizer = sr.Recognizer()
        with sr.AudioFile(WAVE_OUTPUT_FILENAME) as source:
            audio = recognizer.record(source)

        try:
            text = recognizer.recognize_google(audio)
            print("Transcription: " + text)
            # Check if transcription is minimal
            if len(text.strip()) < 10:  # Adjust the threshold as needed
                raise sr.UnknownValueError("Minimal input detected")
        except sr.UnknownValueError:
            print("No or minimal input detected. Sending emergency request.")
            url = "https://724cu8r3wk.execute-api.ca-central-1.amazonaws.com/Prod/outcall"
            headers = {'Content-Type': 'application/json'}
            data = {
                "emergencyPhoneNumber": "+16476772046",
                "emergencyFirstname": "Clay",
                "userFirstName": "Clay",
                "userLastName": ""
            }
            response = requests.post(url, json=data, headers=headers)
            print(f"Emergency request sent, response status code: {response.status_code}")
        except sr.RequestError as e:
            print(f"Could not request results from Google Speech Recognition service; {e}")

    except Exception as e:
        print(f"Error: {e}")

    return 'Sound played and transcription done', 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
