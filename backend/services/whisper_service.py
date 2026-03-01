import os

import whisper

from models.stt import STTResult


class WhisperSTTService:
    def __init__(self) -> None:
        self.model_name = os.getenv("WHISPER_MODEL", "base")
        self.model = whisper.load_model(self.model_name)

    def transcribe(
        self,
        audio_path: str,
        language: str | None = None,
        prompt: str | None = None,
        temperature: float | None = None,
    ) -> STTResult:
        options = {}
        if language:
            options["language"] = language
        if prompt:
            options["initial_prompt"] = prompt
        if temperature is not None:
            options["temperature"] = temperature

        result = self.model.transcribe(audio_path, **options)
        text = result.get("text", "")
        detected_language = result.get("language")

        return STTResult(text=text, model=self.model_name, language=detected_language)
