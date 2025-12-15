import queue
import sounddevice as sd
import numpy as np
import torch
from transformers import Wav2Vec2Processor, Wav2Vec2ForCTC

# Charger modèle malgache
print("Loading model…")
processor = Wav2Vec2Processor.from_pretrained("badrex/w2v-bert-2.0-malagasy-asr")
model = Wav2Vec2ForCTC.from_pretrained("badrex/w2v-bert-2.0-malagasy-asr")

# Paramètres audio
RATE = 16000
BLOCKSIZE = 8000   # plus petit = plus rapide
q_audio = queue.Queue()

def audio_callback(indata, frames, time, status):
    """Callback micro → envoie le son dans la file."""
    q_audio.put(indata.copy())

print("\nMihaino anao… (Appuie Ctrl+C hijanona)\n")

# Stream microphone
with sd.InputStream(samplerate=RATE, channels=1, dtype="float32",
                    blocksize=BLOCKSIZE, callback=audio_callback):

    buffer_audio = np.zeros(0, dtype=np.float32)

    while True:
        # Récupération du son
        block = q_audio.get().flatten()
        buffer_audio = np.concatenate((buffer_audio, block))

        # Traitement toutes les ~0.5 sec
        if len(buffer_audio) > RATE * 0.5:

            audio_chunk = buffer_audio[-RATE:]  # dernière seconde

            inputs = processor(audio_chunk, sampling_rate=RATE,
                               return_tensors="pt", padding=True)

            with torch.no_grad():
                logits = model(inputs.input_values).logits

            predicted_ids = torch.argmax(logits, dim=-1)
            text = processor.decode(predicted_ids[0]).strip()

            if text:
                print("➡️", text)

