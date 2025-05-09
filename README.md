# Voice Assistant

This directory contains a voice assistant system designed to detect and respond to falls in elderly care settings.

## Contents

### Core Files

- `generate_prompts.py`: Generates audio prompts using OpenAI's text-to-speech API

  - Creates three audio files in the `audiofiles` folder:
    - `audiofiles/prompt.mp3`: Initial fall detection query
    - `audiofiles/emergency.mp3`: Emergency response message
    - `audiofiles/false_alarm.mp3`: False alarm response message
  - Uses OpenAI's tts-1-hd model with the "shimmer" voice for high-quality audio

- `speech_to_text.py`: Main interaction script that:

  - Plays audio prompts from the `audiofiles` folder
  - Records user responses
  - Transcribes speech using Whisper
  - Classifies intent using GPT-3.5
  - Plays appropriate response audio
  - Creates timestamped folders for each interaction

- `r1.py`: MQTT and emergency handling implementation:

  - MQTT integration with Thingsboard for real-time fall detection
  - Emergency calling system with API integration
  - Debounce mechanism to prevent false alarms (30-second cooldown)
  - Emergency contact calling through AWS Lambda API

### Audio Files

Located in the `audiofiles` folder:
- `prompt.mp3`: Initial query "Hi... did you fall?"
- `emergency.mp3`: Emergency response message
- `false_alarm.mp3`: False alarm response message

### Run Folders

The system creates timestamped folders for each interaction (format: `run_YYYYMMDD_HHMMSS/`), containing:

- `interaction_log.txt`: Detailed log of the interaction
- `response.wav`: Recorded audio response from the user

## Usage

1. Generate audio prompts:

```bash
python generate_prompts.py
```

2. Run the main interaction script:

```bash
python speech_to_text.py
```

3. For MQTT integration and emergency handling:

```bash
python r1.py
```

## Dependencies

- OpenAI API (for text-to-speech and speech-to-text)
- sounddevice (for audio recording)
- numpy (for audio processing)
- scipy (for audio file handling)
- paho-mqtt (for MQTT communication)
- requests (for API calls)

## Configuration

The system requires the following configuration:

- Thingsboard host and access token for MQTT
- Emergency contact number
- AWS Lambda API endpoint for emergency calls
