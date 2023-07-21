# External modules
import asyncio
from typing import Callable

# Internal modules
from interface import ConversationInterface
from structure import Message

import prompt, ai
from memory import MemoryInterface
from delay import DelayInterface


def get_messages_around_MAGIC(message: Message) -> list[Message]:   #! Make not magic
    return [message]


class ComplexMemoryConversation(ConversationInterface):
    memory: MemoryInterface
    delay : DelayInterface

    reading_seconds_per_char: float = 18/377   # In seconds
    writing_seconds_per_char: float = 18/84    # In seconds

    def __init__(self, channel_id: int, memory: MemoryInterface, delay: DelayInterface) -> None:
        self.memory = memory
        self.delay = delay
        super().__init__(channel_id)


    def get_is_processing(self):
        return self.is_processing


    def respond(self) -> str:
        stm_messages = self.memory.get_short_term_memory()
        ltm_search_results = self.memory.search_long_term_memory('\n'.join([message.content for message in self.unread_message_queue]))
        ltm_messages: list[list[Message]] = [get_messages_around_MAGIC(message) for message in ltm_search_results ] #! Make not magic
        ai_prompt: str = prompt.prompt_crafter(ltm_messages[:3], stm_messages, 0.5, prompt.DefaultTextModel())
        return ai.openai_generate_response(ai_prompt)

    
    async def add_message(self, message: Message, reset_unread_queue: int) -> None:
        if reset_unread_queue: self.unread_message_queue = []
        else                 : self.unread_message_queue.append(message)
        self.unsaved_message_queue.append(message)
        if not self.is_saving_message:
            self.is_saving_message = True
            while len(self.unsaved_message_queue) != 0:
                unsaved_messages = self.unsaved_message_queue
                self.unsaved_message_queue.clear()
                self.memory.add_messages(unsaved_messages)
            self.is_saving_message = False


    async def communicate(self) -> str:
        response: str = ""
        if not self.is_processing:
            self.is_processing = True 
            attempts: int = 0
            await asyncio.sleep(self.delay.ping())                                      # Bot start computing delay
            while len(self.unread_message_queue) != 0 and attempts < 3:
                attempts += 1
                current_amount_of_unread_messages: int = len(self.unread_message_queue)
                while self.is_saving_message:
                    await asyncio.sleep(0.1)

                await asyncio.sleep(self.reading_seconds_per_char*sum([len(message.content.strip()) for message in self.unread_message_queue])) # Readig delay
                if len(self.unread_message_queue) == 0: return ""

                response = self.respond()

                await asyncio.sleep(self.writing_seconds_per_char*len(response.strip())) # Writing delay
                if len(self.unread_message_queue) == 0: return ""
                if current_amount_of_unread_messages != len(self.unread_message_queue): continue

                break
            self.is_processing = False
        return response