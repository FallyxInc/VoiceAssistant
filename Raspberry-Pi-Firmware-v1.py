from flask import Flask, request, render_template_string
from gtts import gTTS
import os
import subprocess

app = Flask(__name__)

@app.route('/')
def index():
    return render_template_string('''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Fall Detection</title>
</head>
<body>
    <h1>Fall Detection</h1>
    <button onclick="playMessage()">Start</button>
    <div id="transcription"></div>

    <script>
        function playMessage() {
            fetch('/fall', {method: 'POST'})
                .then(response => response.json())
                .then(data => {
                    console.log(data.message);
                    startRecording();
                })
                .catch(error => console.error('Error:', error));
        }

        function startRecording() {
            let recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
            recognition.lang = 'en-US';
            recognition.continuous = false;
            recognition.interimResults = false;

            recognition.onstart = function() {
                console.log('Recording started');
                setTimeout(() => {
                    recognition.stop();
                }, 15000); // Stop recording after 15 seconds
            };

            recognition.onresult = function(event) {
                let transcript = '';
                for (let i = 0; i < event.results.length; ++i) {
                    transcript += event.results[i][0].transcript;
                }
                document.getElementById('transcription').innerText = transcript;
                console.log('Transcription: ', transcript);
            };

            recognition.onerror = function(event) {
                console.error('Error occurred in recognition: ', event.error);
            };

            recognition.start();
        }
    </script>
</body>
</html>
''')

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

    return jsonify({"message": "Sound played, start recording"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
