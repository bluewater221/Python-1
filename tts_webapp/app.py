from flask import Flask, render_template, request, jsonify
from gtts import gTTS
import pygame
import os
import threading
import atexit
import time

app = Flask(__name__)

class TTSController:
    def __init__(self):
        try:
            pygame.mixer.init()
            print("Pygame mixer initialized successfully")
        except Exception as e:
            print(f"Error initializing pygame mixer: {e}")
        self.is_speaking = False
        self.is_paused = False
        self.audio_file = "output.mp3"
        self.lock = threading.Lock()

    def play_audio(self, text):
        try:
            with self.lock:
                # Clean up any previous audio
                print(f"Current state: is_speaking={self.is_speaking}, is_paused={self.is_paused}")
                if self.is_speaking or os.path.exists(self.audio_file):
                    print("Cleaning up previous audio state")
                    pygame.mixer.music.stop()
                    pygame.mixer.music.unload()
                    self.is_speaking = False
                    self.is_paused = False
                    if os.path.exists(self.audio_file):
                        try:
                            time.sleep(0.2)
                            os.remove(self.audio_file)
                            print("Previous audio file removed")
                        except Exception as e:
                            print(f"Error removing previous audio file: {e}")

                # Limit text length for gTTS
                if len(text) > 5000:
                    text = text[:5000]
                    print("Text truncated to 5000 characters for gTTS")

                print(f"Generating audio for text: {text[:50]}...")
                tts = gTTS(text, slow=True)
                tts.save(self.audio_file)
                print(f"Audio file saved: {self.audio_file}")
                pygame.mixer.music.load(self.audio_file)
                print("Audio file loaded into pygame")
                try:
                    pygame.mixer.music.play()
                    print("Audio playback started")
                    self.is_speaking = True
                except Exception as e:
                    print(f"Error playing audio with pygame: {e}")
                    self.is_speaking = False
                    raise

            while self.is_speaking and pygame.mixer.music.get_busy():
                with self.lock:
                    if self.is_paused:
                        pygame.mixer.music.pause()
                        print("Audio paused")
                    else:
                        pygame.mixer.music.unpause()
                        print("Audio unpaused")
                time.sleep(0.1)

            with self.lock:
                print("Playback finished or stopped")
                self.is_speaking = False
                self.is_paused = False
                if os.path.exists(self.audio_file):
                    try:
                        pygame.mixer.music.unload()
                        time.sleep(0.2)
                        os.remove(self.audio_file)
                        print("Audio file removed after playback")
                    except Exception as e:
                        print(f"Error removing audio file after playback: {e}")
        except Exception as e:
            print(f"Error in play_audio: {e}")
            with self.lock:
                self.is_speaking = False
                self.is_paused = False
                if os.path.exists(self.audio_file):
                    try:
                        pygame.mixer.music.unload()
                        time.sleep(0.2)
                        os.remove(self.audio_file)
                        print("Audio file removed after error")
                    except Exception as e:
                        print(f"Error removing audio file after error: {e}")

    def stop(self):
        with self.lock:
            try:
                if self.is_speaking:
                    pygame.mixer.music.stop()
                    print("Audio stopped")
                    pygame.mixer.music.unload()
                    time.sleep(0.2)
                self.is_speaking = False
                self.is_paused = False
                if os.path.exists(self.audio_file):
                    try:
                        os.remove(self.audio_file)
                        print("Audio file removed in stop")
                    except Exception as e:
                        print(f"Error removing audio file in stop: {e}")
            except Exception as e:
                print(f"Error in stop: {e}")

    def toggle_pause(self):
        with self.lock:
            if self.is_speaking:
                self.is_paused = not self.is_paused
                print(f"Audio {'paused' if self.is_paused else 'resumed'}")
                return "Paused" if self.is_paused else "Speaking"
            print("Toggle pause called but not speaking")
            return "Not speaking"

    def cleanup(self):
        with self.lock:
            if self.is_speaking:
                pygame.mixer.music.stop()
            if os.path.exists(self.audio_file):
                try:
                    pygame.mixer.music.unload()
                    time.sleep(0.2)
                    os.remove(self.audio_file)
                    print("Audio file removed during cleanup")
                except Exception as e:
                    print(f"Error removing audio file during cleanup: {e}")
        pygame.mixer.quit()

tts = TTSController()
atexit.register(tts.cleanup)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/speak', methods=['POST'])
def speak():
    print("Received /speak request")
    text = request.form.get('text', '')
    print(f"Text received: {text[:50]}...")
    if not text:
        return jsonify({'status': 'No text provided'})
    try:
        print("Starting audio thread")
        threading.Thread(target=tts.play_audio, args=(text,), daemon=True).start()
        print("Audio thread started")
        return jsonify({'status': 'Speaking'})
    except Exception as e:
        print(f"Error in /speak: {e}")
        return jsonify({'status': 'Error', 'message': str(e)}), 500

@app.route('/pause', methods=['POST'])
def pause():
    print("Received /pause request")
    try:
        status = tts.toggle_pause()
        print(f"Pause status: {status}")
        return jsonify({'status': status})
    except Exception as e:
        print(f"Error in /pause: {e}")
        return jsonify({'status': 'Error', 'message': str(e)}), 500

@app.route('/stop', methods=['POST'])
def stop():
    print("Received /stop request")
    try:
        tts.stop()
        return jsonify({'status': 'Stopped'})
    except Exception as e:
        print(f"Error in /stop: {e}")
        return jsonify({'status': 'Error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000, use_reloader=False)