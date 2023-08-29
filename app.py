import os
import time
import threading
import sounddevice as sd
import numpy as np
import wave
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.http import MediaFileUpload
from flask import Flask, render_template, request

# Constants
CHUNK = 44100
FORMAT = 'int16'
CHANNELS = 2
RATE = 48000
RECORDING_DURATION = 10  # 7 seconds
UPLOAD_INTERVAL = 30  # 30 seconds

# Get the directory where the current script is located
script_directory = os.path.dirname(os.path.abspath(__file__))

# Define the relative path to your client secret file
client_secret_file = os.path.join(script_directory, 'patchtoGOOGLEDRIVE.json')

# Google Drive API setup
SCOPES = ['https://www.googleapis.com/auth/drive.file']
creds = None

if os.path.exists('token.json'):
    creds = Credentials.from_authorized_user_file('token.json', SCOPES)

if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(client_secret_file, SCOPES)
        creds = flow.run_local_server(port=0)

    with open('token.json', 'w') as token:
        token.write(creds.to_json())

service = build('drive', 'v3', credentials=creds)

# Define the folder ID where you want to store the audio files
folder_id = '1EP-3A03kZzN59pwOUU7oJHmggVrvtgTA'  # Replace with your folder ID

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'XeWYp4RajRHSwziJLNnSATZ55w8MfCpK'  # Replace with your own secret key

# Function to start and stop recording based on user actions
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/record', methods=['POST'])
def record():
    if request.form['action'] == 'start':
        threading.Thread(target=record_and_upload).start()
        return 'Recording started'
    elif request.form['action'] == 'stop':
        return 'Recording stopped and uploaded'

# Function for recording and uploading
def record_and_upload():
    frames = []

    try:
        start_time = time.time()
        while time.time() - start_time < RECORDING_DURATION:
            data = sd.rec(CHUNK, samplerate=RATE, channels=CHANNELS, dtype=FORMAT)
            sd.wait()
            frames.append(data)
    except KeyboardInterrupt:
        pass

    audio_filename = f"recorded_{int(time.time())}.wav"
    audio_data = np.concatenate(frames, axis=0)
    with wave.open(audio_filename, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(audio_data.dtype.itemsize)
        wf.setframerate(RATE)
        wf.writeframes(audio_data.tobytes())

    # Upload the audio file to your Google Drive folder
    file_metadata = {
        'name': audio_filename,
        'mimeType': 'audio/wav',
        'parents': [folder_id]
    }
    media = MediaFileUpload(audio_filename, mimetype='audio/wav')
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()

    # Remove the temporary audio file after it's closed
    os.remove(audio_filename)


if __name__ == "__main__":
    app.run(debug=True)
