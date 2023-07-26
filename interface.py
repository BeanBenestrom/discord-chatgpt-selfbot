import asyncio
from abc import ABC, abstractmethod

from typing import Callable, Any

from structure import Message
from utility import Result
from debug import LogHanglerInterface, LogNothing, LogType


class ConversationInterface(ABC):
    channel_id: int
    unread_message_queue : list[Message]
    unsaved_message_queue: list[Message]
    is_saving_message: bool 
    is_processing    : bool
    current_prompt   : str

    @abstractmethod
    def __init__(self, channel_id: int, log: LogHanglerInterface=LogNothing()) -> None:
        self.is_saving_message = False
        self.is_processing = False
        self.channel_id = channel_id
        self.unread_message_queue = []
        self.unsaved_message_queue = []
    
    @abstractmethod
    async def add_message(self, message: Message, reset_unread_queue: int, log: LogHanglerInterface=LogNothing()) -> None:
        ...

    @abstractmethod
    async def communicate(self, callback=Callable[[str], Any], log: LogHanglerInterface=LogNothing()) -> str:
        ...


class MemoryInterface(ABC):
    channel_id: int
    STM_LIMIT: int

    def __init__(self, channel_id: int, stm_limit: int, log: LogHanglerInterface=LogNothing()) -> None:
        self.channel_id = channel_id
        self.STM_LIMIT = stm_limit

    @abstractmethod
    def add_messages(self, messages: list[Message], log: LogHanglerInterface=LogNothing()) -> None:
        ...
    @abstractmethod
    def remove_messages(self, message_ids: list[int], log: LogHanglerInterface=LogNothing()) -> None:
        ...
    @abstractmethod
    def search_long_term_memory(self, text: str, log: LogHanglerInterface=LogNothing()) -> Result[list[Message]]:
        ...
    @abstractmethod
    def get_short_term_memory(self, log: LogHanglerInterface=LogNothing()) -> list[Message]:
        ...
    @abstractmethod
    def clear_long_term_memory(self, log: LogHanglerInterface=LogNothing()) -> None:
        ...
    @abstractmethod
    def clear_short_term_memory(self, log: LogHanglerInterface=LogNothing()) -> None:
        ...


class DelayInterface(ABC):
    @abstractmethod
    def ping(self, log: LogHanglerInterface=LogNothing()) -> float:
        ...