

import _thread as thread
import base64
import hashlib
import hmac
import json
import queue
import re
import ssl
import time
from abc import ABC
from datetime import datetime
from time import mktime
from typing import Literal, Optional
from urllib.parse import urlencode
from wsgiref.handlers import format_date_time
from dataclasses import dataclass, field

import httpx
import ormsgpack
import requests
import websocket

from src.rag.utils import num_tokens_from_string


@dataclass
class ServeReferenceAudio:
    audio: bytes = b""
    text: str = ""


@dataclass
class ServeTTSRequest:
    text: str = ""
    chunk_length: int = 200  # Range: 100-300
    format: Literal["wav", "pcm", "mp3"] = "mp3"
    mp3_bitrate: Literal[64, 128, 192] = 128
    references: list = field(default_factory=list)
    reference_id: Optional[str] = None
    normalize: bool = True
    latency: Literal["normal", "balanced"] = "normal"

    def __post_init__(self):
        """驗證 chunk_length 範圍"""
        if not 100 <= self.chunk_length <= 300:
            raise ValueError(f"chunk_length must be between 100 and 300, got {self.chunk_length}")


class Base(ABC):
    def __init__(self, key, model_name, base_url, **kwargs):
        """
        Abstract base class constructor.
        Parameters are not stored; subclasses should handle their own initialization.
        """
        pass

    def tts(self, audio):
        pass

    def normalize_text(self, text):
        return re.sub(r"(\*\*|##\d+\$\$|#)", "", text)




class OpenAITTS(Base):
    _FACTORY_NAME = "OpenAI"

    def __init__(self, key, model_name="tts-1", base_url="https://api.openai.com/v1"):
        if not base_url:
            base_url = "https://api.openai.com/v1"
        self.api_key = key
        self.model_name = model_name
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def tts(self, text, voice="alloy"):
        text = self.normalize_text(text)
        payload = {"model": self.model_name, "voice": voice, "input": text}

        response = requests.post(f"{self.base_url}/audio/speech", headers=self.headers, json=payload, stream=True)

        if response.status_code != 200:
            raise Exception(f"**Error**: {response.status_code}, {response.text}")
        for chunk in response.iter_content():
            if chunk:
                yield chunk



class OllamaTTS(Base):
    def __init__(self, key, model_name="ollama-tts", base_url="https://api.ollama.ai/v1"):
        if not base_url:
            base_url = "https://api.ollama.ai/v1"
        self.model_name = model_name
        self.base_url = base_url
        self.headers = {"Content-Type": "application/json"}
        if key and key != "x":
            self.headers["Authorization"] = f"Bearer {key}"

    def tts(self, text, voice="standard-voice"):
        payload = {"model": self.model_name, "voice": voice, "input": text}

        response = requests.post(f"{self.base_url}/audio/tts", headers=self.headers, json=payload, stream=True)

        if response.status_code != 200:
            raise Exception(f"**Error**: {response.status_code}, {response.text}")

        for chunk in response.iter_content():
            if chunk:
                yield chunk


class GPUStackTTS(Base):
    _FACTORY_NAME = "GPUStack"

    def __init__(self, key, model_name, **kwargs):
        self.base_url = kwargs.get("base_url", None)
        self.api_key = key
        self.model_name = model_name
        self.headers = {"accept": "application/json", "Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}

    def tts(self, text, voice="Chinese Female", stream=True):
        payload = {"model": self.model_name, "input": text, "voice": voice}

        response = requests.post(f"{self.base_url}/v1/audio/speech", headers=self.headers, json=payload, stream=stream)

        if response.status_code != 200:
            raise Exception(f"**Error**: {response.status_code}, {response.text}")

        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                yield chunk


class SILICONFLOWTTS(Base):
    _FACTORY_NAME = "SILICONFLOW"

    def __init__(self, key, model_name="FunAudioLLM/CosyVoice2-0.5B", base_url="https://api.siliconflow.cn/v1"):
        if not base_url:
            base_url = "https://api.siliconflow.cn/v1"
        self.api_key = key
        self.model_name = model_name
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def tts(self, text, voice="anna"):
        text = self.normalize_text(text)
        payload = {
            "model": self.model_name,
            "input": text,
            "voice": f"{self.model_name}:{voice}",
            "response_format": "mp3",
            "sample_rate": 123,
            "stream": True,
            "speed": 1,
            "gain": 0,
        }

        response = requests.post(f"{self.base_url}/audio/speech", headers=self.headers, json=payload)

        if response.status_code != 200:
            raise Exception(f"**Error**: {response.status_code}, {response.text}")
        for chunk in response.iter_content():
            if chunk:
                yield chunk

class DeepInfraTTS(OpenAITTS):
    _FACTORY_NAME = "DeepInfra"

    def __init__(self, key, model_name, base_url="https://api.deepinfra.com/v1/openai", **kwargs):
        if not base_url:
            base_url = "https://api.deepinfra.com/v1/openai"
        super().__init__(key, model_name, base_url, **kwargs)

class CometAPITTS(OpenAITTS):
    _FACTORY_NAME = "CometAPI"

    def __init__(self, key, model_name, base_url="https://api.cometapi.com/v1", **kwargs):
        if not base_url:
            base_url = "https://api.cometapi.com/v1"
        super().__init__(key, model_name, base_url, **kwargs)
