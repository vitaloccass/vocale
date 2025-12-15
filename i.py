"""
Système de Reconnaissance Vocale Avancé avec Python
Supporte plusieurs moteurs : Whisper (OpenAI), Google, Vosk
"""

import speech_recognition as sr
import pyaudio
import wave
import threading
import queue
import time
from pathlib import Path
import json

class AdvancedSpeechRecognizer:
    def __init__(self, engine="whisper", language="fr-FR"):
        """
        Initialise le système de reconnaissance vocale
        
        Args:
            engine: "whisper", "google", "vosk", "sphinx"
            language: code langue (fr-FR, en-US, etc.)
        """
        self.recognizer = sr.Recognizer()
        self.engine = engine
        self.language = language
        self.audio_queue = queue.Queue()
        self.is_listening = False
        
        # Optimisation des paramètres
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8
        
        print(f"🎤 Reconnaissance vocale initialisée ({engine})")
    
    def recognize_from_file(self, audio_file):
        """Reconnaissance depuis un fichier audio"""
        try:
            with sr.AudioFile(audio_file) as source:
                audio = self.recognizer.record(source)
            return self._recognize_audio(audio)
        except Exception as e:
            return {"error": str(e), "success": False}
    
    def recognize_from_microphone(self, duration=None):
        """Reconnaissance depuis le microphone"""
        try:
            with sr.Microphone() as source:
                print("🎧 Calibration du bruit ambiant...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                
                print("🔴 Parlez maintenant...")
                if duration:
                    audio = self.recognizer.record(source, duration=duration)
                else:
                    audio = self.recognizer.listen(source, timeout=5)
                
            print("⏳ Traitement en cours...")
            return self._recognize_audio(audio)
            
        except sr.WaitTimeoutError:
            return {"error": "Timeout - aucun son détecté", "success": False}
        except Exception as e:
            return {"error": str(e), "success": False}
    
    def _recognize_audio(self, audio):
        """Traite l'audio avec le moteur sélectionné"""
        start_time = time.time()
        
        try:
            if self.engine == "whisper":
                text = self.recognizer.recognize_whisper(
                    audio, 
                    language=self.language.split("-")[0],
                    model="base"
                )
            elif self.engine == "google":
                text = self.recognizer.recognize_google(
                    audio, 
                    language=self.language
                )
            elif self.engine == "sphinx":
                text = self.recognizer.recognize_sphinx(audio)
            else:
                return {"error": f"Moteur {self.engine} non supporté", "success": False}
            
            processing_time = time.time() - start_time
            
            return {
                "text": text,
                "engine": self.engine,
                "language": self.language,
                "processing_time": f"{processing_time:.2f}s",
                "success": True
            }
            
        except sr.UnknownValueError:
            return {"error": "Audio incompréhensible", "success": False}
        except sr.RequestError as e:
            return {"error": f"Erreur API: {e}", "success": False}
        except Exception as e:
            return {"error": str(e), "success": False}
    
    def continuous_recognition(self, callback, stop_event=None):
        """Reconnaissance continue en arrière-plan"""
        def listen_worker():
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                print("🔴 Écoute continue activée...")
                
                while not (stop_event and stop_event.is_set()):
                    try:
                        audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=10)
                        result = self._recognize_audio(audio)
                        if result["success"]:
                            callback(result)
                    except sr.WaitTimeoutError:
                        continue
                    except Exception as e:
                        print(f"Erreur: {e}")
        
        thread = threading.Thread(target=listen_worker, daemon=True)
        thread.start()
        return thread
    
    def save_audio(self, audio, filename="recording.wav"):
        """Sauvegarde l'audio capturé"""
        with open(filename, "wb") as f:
            f.write(audio.get_wav_data())
        print(f"💾 Audio sauvegardé: {filename}")


class RealtimeTranscriber:
    """Transcription en temps réel avec bufferisation"""
    def __init__(self, engine="whisper", chunk_duration=3):
        self.recognizer = AdvancedSpeechRecognizer(engine=engine)
        self.chunk_duration = chunk_duration
        self.full_transcript = []
    
    def start_realtime(self, duration=30):
        """Démarre la transcription temps réel"""
        print(f"⏱️  Transcription temps réel pendant {duration}s...")
        
        def on_transcript(result):
            if result["success"]:
                text = result["text"]
                self.full_transcript.append(text)
                print(f"📝 {text}")
        
        stop_event = threading.Event()
        thread = self.recognizer.continuous_recognition(on_transcript, stop_event)
        
        time.sleep(duration)
        stop_event.set()
        thread.join(timeout=2)
        
        return " ".join(self.full_transcript)


# ===== EXEMPLES D'UTILISATION =====

if __name__ == "__main__":
    print("=" * 60)
    print("🎤 SYSTÈME DE RECONNAISSANCE VOCALE AVANCÉ")
    print("=" * 60)
    
    # Mode 1: Reconnaissance simple depuis micro
    print("\n📌 MODE 1: Reconnaissance simple (5 secondes)")
    recognizer = AdvancedSpeechRecognizer(engine="whisper", language="fr-FR")
    result = recognizer.recognize_from_microphone()
    
    if result["success"]:
        print(f"\n✅ Texte reconnu: {result['text']}")
        print(f"⏱️  Temps de traitement: {result['processing_time']}")
    else:
        print(f"\n❌ Erreur: {result['error']}")
    
    # Mode 2: Reconnaissance depuis fichier
    # print("\n📌 MODE 2: Depuis fichier audio")
    # result = recognizer.recognize_from_file("audio.wav")
    # print(result)
    
    # Mode 3: Écoute continue
    # print("\n📌 MODE 3: Écoute continue (10 secondes)")
    # def handle_speech(result):
    #     print(f"➡️  {result['text']}")
    # 
    # stop = threading.Event()
    # recognizer.continuous_recognition(handle_speech, stop)
    # time.sleep(10)
    # stop.set()
    
    # Mode 4: Transcription temps réel
    # print("\n📌 MODE 4: Transcription temps réel")
    # transcriber = RealtimeTranscriber(engine="whisper")
    # full_text = transcriber.start_realtime(duration=15)
    # print(f"\n📄 Transcription complète:\n{full_text}")
    
    print("\n✨ Terminé!")