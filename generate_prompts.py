# V2/generate_prompt.py
import openai
import os

openai.api_key = "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"

def generate_prompt_audio(text="Hi............. **Resident Name. Did    you    fall     down?", output_file="audiofiles/prompt.mp3"):
    response = openai.audio.speech.create(
        model="tts-1-hd",
        voice="shimmer",
        input=text
    )
    with open(output_file, "wb") as f:
        f.write(response.content)
    print(f"Generated audio file: {output_file}")

def generate_emergency_audio(text="Ok don't worry, the nurse is coming to help you! Please remain calm and take some deep breaths, everything is going to be okay!", output_file="audiofiles/emergency.mp3"):
    response = openai.audio.speech.create(
        model="tts-1-hd",
        voice="shimmer",
        input=text
    )
    with open(output_file, "wb") as f:
        f.write(response.content)
    print(f"Generated audio file: {output_file}")

def generate_false_alarm_audio(text="I'm so sorry to disturb you, I just wanted to check if you're okay! Have a great day!", output_file="audiofiles/false_alarm.mp3"):
    response = openai.audio.speech.create(
        model="tts-1-hd",
        voice="shimmer",
        input=text
    )
    with open(output_file, "wb") as f:
        f.write(response.content)
    print(f"Generated audio file: {output_file}")

if __name__ == "__main__":
    generate_prompt_audio()
    generate_emergency_audio()
    generate_false_alarm_audio()