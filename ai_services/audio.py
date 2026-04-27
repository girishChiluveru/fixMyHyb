import torch
from transformers import pipeline

class AudioTranscriber:
    def __init__(self, model_id="openai/whisper-tiny"):
        """
        Uses OpenAI's Whisper model (tiny version) for fast, local transcription.
        You can upgrade to 'whisper-base' or 'whisper-small' if your PC has more RAM/GPU.
        """
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        # We use pipeline for an easy ASR (Automatic Speech Recognition) interface
        self.pipe = pipeline(
            "automatic-speech-recognition", 
            model=model_id, 
            device=self.device,
            chunk_length_s=30 # Processes audio in chunks for memory efficiency
        )

    def transcribe(self, audio_path):
        """
        Transcribes the given audio file (.ogg, .wav, .mp3) to text.
        """
        try:
            # Whisper handles raw audio files perfectly well
            result = self.pipe(audio_path, return_timestamps=False)
            return {
                "success": True,
                "text": result["text"].strip()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
