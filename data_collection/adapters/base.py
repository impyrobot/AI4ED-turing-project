from abc import ABC, abstractmethod


class ModelAdapter(ABC):
    name: str
    version: str

    @abstractmethod
    def generate(self, prompt: str, temperature: float, max_tokens: int) -> str:
        """Single-shot completion."""
        ...

    @abstractmethod
    def chat(self, messages: list[dict], temperature: float, max_tokens: int) -> str:
        """Multi-turn chat. messages: [{"role": "user"|"assistant"|"system", "content": "..."}]"""
        ...
