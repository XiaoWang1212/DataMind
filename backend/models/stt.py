from dataclasses import dataclass


@dataclass
class STTResult:
    text: str
    model: str
    language: str | None = None

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "model": self.model,
            "language": self.language,
        }
