from flask import Flask, request
from gtts import gTTS
import os
import subprocess

app = Flask(__name__)

@app.route('/fall', methods=['POST'])
def fall_detected():
    try:
        # Generate speech
        tts = gTTS(text="Hey there, did you fall? If you fell, please say yes multiple times. If you're okay, then say no multiple times.", lang='en')
        tts.save("did_you_fall.mp3")
        print("TTS generated and saved as did_you_fall.mp3")

        # Remove existing wav file if it exists
        if os.path.exists("did_you_fall.wav"):
            os.remove("did_you_fall.wav")
            print("Existing did_you_fall.wav removed")

        # Convert mp3 to wav using ffmpeg
        subprocess.run(["ffmpeg", "-i", "did_you_fall.mp3", "did_you_fall.wav"], check=True)
        print("Converted did_you_fall.mp3 to did_you_fall.wav")

        # Check if file exists and play it
        if os.path.exists("did_you_fall.wav"):
            print("did_you_fall.wav exists, attempting to play it")
            subprocess.run(["paplay", "did_you_fall.wav"], check=True)  # Wait for the command to finish
            print("paplay command executed")
        else:
            print("did_you_fall.wav file does not exist")
    except Exception as e:
        print(f"Error: {e}")

    return 'Sound played', 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
