from abc import ABC, abstractmethod

from structure import Message


class ConversationInterface(ABC):
    channel_id: int
    unread_message_queue : list[Message]
    unsaved_message_queue: list[Message]
    is_saving_message: bool 
    is_processing    : bool 

    @abstractmethod
    def __init__(self, channel_id: int) -> None:
        self.message_queue = []
        self.is_saving_message = False
        self.is_processing = False
        self.channel_id = channel_id
    
    @abstractmethod
    def communicate(self, messages: list[Message]) -> str:
        ...


class MemoryInterface(ABC):
    channel_id: int

    def __init__(self, channel_id: int) -> None:
        self.channel_id = channel_id

    @abstractmethod
    def add_messages(self, messages: list[Message]) -> None:
        ...
    @abstractmethod
    def remove_messages(self, message_ids: list[int]) -> None:
        ...
    @abstractmethod
    def search_long_term_memory(self, text: str) -> list[Message]:
        ...
    @abstractmethod
    def get_short_term_memory(self) -> list[Message]:
        ...
    @abstractmethod
    def clear_long_term_memory(self) -> None:
        ...
    @abstractmethod
    def clear_short_term_memory(self) -> None:
        ...


class DelayInterface(ABC):
    @abstractmethod
    def ping(self) -> float:
        ...