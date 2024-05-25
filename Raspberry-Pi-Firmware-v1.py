from flask import Flask, request
from gtts import gTTS
import os
import speech_recognition as sr
import requests
import subprocess

app = Flask(__name__)

@app.route('/fall', methods=['POST'])
def fall_detected():
    data = request.get_json()
    print(f"Received data: {data}")

    try:
        # Print the current working directory
        print(f"Current working directory: {os.getcwd()}")

        # Generate speech
        tts = gTTS(text="Do you need help? Say YES multiple times or say NO if you're okay.", lang='en')
        tts.save("help.mp3")
        print("TTS generated and saved as help.mp3")
    except Exception as e:
        print(f"Error generating TTS: {e}")

    try:
        # Check if file exists
        if os.path.exists("help.mp3"):
            print("help.mp3 exists, attempting to play it")
            subprocess.run(["mpg321", "help.mp3"], check=True)  # Wait for the command to finish
            print("mpg321 command executed")
        else:
            print("help.mp3 file does not exist")
    except Exception as e:
        print(f"Error playing sound: {e}")

    try:
        # Record audio from the microphone for 7 seconds
        recognizer = sr.Recognizer()
        with sr.Microphone(device_index=1) as source:  # Specify the correct device index
            print("Adjusting for ambient noise...")
            recognizer.adjust_for_ambient_noise(source)
            print("Listening for 7 seconds...")
            audio = recognizer.listen(source, timeout=10, phrase_time_limit=7)
            print("Audio recorded, processing...")

        # Save the audio to a file
        with open("recorded_audio.wav", "wb") as f:
            f.write(audio.get_wav_data())
        print("Audio saved as recorded_audio.wav")

        # Transcribe speech to text
        text = recognizer.recognize_google(audio)
        print(f"Transcription: {text}")

        # Count occurrences of "yes" and "no"
        yes_count = text.lower().count("yes")
        no_count = text.lower().count("no")
        print(f"Detected 'yes' {yes_count} times and 'no' {no_count} times.")

        if yes_count > 1:
            print("Detected 'yes' more than once. Preparing to call for help...")
            tts = gTTS(text="Okay, we're calling for help", lang='en')
            tts.save("call_help.mp3")
            subprocess.run(["mpg321", "call_help.mp3"], check=True)

            url = "https://724cu8r3wk.execute-api.ca-central-1.amazonaws.com/Prod/outcall"
            headers = {'Content-Type': 'application/json'}
            data = {
                "emergencyPhoneNumber": "+16476772046",
                "emergencyFirstname": "Clay",
                "userFirstName": "Clay",
                "userLastName": ""
            }
            response = requests.post(url, json=data, headers=headers)
            print(f"Emergency call request sent. Status code: {response.status_code}")
        elif no_count > 1:
            print("Detected 'no' more than once. No action taken.")
            tts = gTTS(text="Okay, sorry to disturb you! Bye!", lang='en')
            tts.save("bye.mp3")
            subprocess.run(["mpg321", "bye.mp3"], check=True)
        else:
            print("No significant response detected. No action taken.")

    except sr.WaitTimeoutError:
        print("Listening timed out while waiting for phrase to start")
        tts = gTTS(text="Okay, sorry to disturb you! Bye!", lang='en')
        tts.save("bye.mp3")
        subprocess.run(["mpg321", "bye.mp3"], check=True)
    except sr.RequestError as e:
        print(f"Could not request results from Google Speech Recognition service; {e}")
    except sr.UnknownValueError:
        print("Google Speech Recognition could not understand the audio")
        tts = gTTS(text="Okay, sorry to disturb you! Bye!", lang='en')
        tts.save("bye.mp3")
        subprocess.run(["mpg321", "bye.mp3"], check=True)
    except Exception as e:
        print(f"Error recording or transcribing speech: {e}")

    return 'Data received, sound played, and speech transcribed', 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

