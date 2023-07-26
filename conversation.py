# External modules
import asyncio, threading, multiprocessing 
from typing import Callable, Any
from colorama import Fore

# Internal modules
import prompt, ai
from interface import ConversationInterface, MemoryInterface, DelayInterface
from structure import Message
from utility import Result, CustomThread
from debug import LogHanglerInterface, LogNothing, LogType


def get_messages_around_MAGIC(message: Message) -> list[Message]:   #! Make not magic
    return [message]



class ComplexMemoryConversation(ConversationInterface):
    memory: MemoryInterface
    delay : DelayInterface

    reading_seconds_per_char: float = 18/377   # In seconds
    writing_seconds_per_char: float = 18/84    # In seconds

    def __init__(self, channel_id: int, memory: MemoryInterface, delay: DelayInterface, log: LogHanglerInterface=LogNothing()) -> None:
        self.memory = memory
        self.delay = delay
        super().__init__(channel_id)


    def get_is_processing(self):
        return self.is_processing


    async def respond(self, log: LogHanglerInterface=LogNothing()) -> str:
        stm_messages: list[Message] = self.memory.get_short_term_memory(log=log.sub())
        log.log(LogType.INFO, f"Got short term memory")
        log.log(LogType.DEBUG, (f"STM INFO:\n"
                                f"len   : {len(stm_messages)}\n"
                                f"oldest: {str(stm_messages[ 0] if len(stm_messages) else None)}\n"
                                f"newest: {str(stm_messages[-1] if len(stm_messages) else None)}"))

        ltm_search_results: list[Message] = self.memory.search_long_term_memory('\n'.join([message.content for message in self.unread_message_queue]), log.sub()).unwrap()
        log.log(LogType.INFO, "Got long term memory")
        log.log(LogType.DEBUG, "LTM INFO:\nresults: {}".format('\n         '.join([str(message) for message in ltm_search_results])))

        ltm_messages: list[list[Message]] = [get_messages_around_MAGIC(message) for message in ltm_search_results ] #! Make not magic
        log.log(LogType.INFO, "Magic done on long term memory!")

        ai_prompt: str = prompt.prompt_crafter(ltm_messages[:3], stm_messages, 0.5, prompt.DefaultTextModel(), log=log.sub())
        self.current_prompt = ai_prompt
        log.log(LogType.INFO, "Prompt crafted!")

        response: str = ai.openai_generate_response(ai_prompt, log=log.sub())
        log.log(LogType.INFO, "Response generated!")

        return response

    
    async def add_message(self, message: Message, reset_unread_queue: int, log: LogHanglerInterface=LogNothing()) -> None:
        log.log(LogType.DEBUG, "Unread message queue before:\n[{}]".format('\n'.join([str(message) for message in self.unread_message_queue])))
        
        # Add or clean unread message queue
        if reset_unread_queue: self.unread_message_queue = []
        else                 : self.unread_message_queue.append(message)

        self.unsaved_message_queue.append(message)
        if not self.is_saving_message:
            self.is_saving_message = True
            while len(self.unsaved_message_queue) != 0:
                unsaved_messages = self.unsaved_message_queue.copy()
                self.unsaved_message_queue.clear()
                self.memory.add_messages(unsaved_messages, log=log.sub())
                log.log(LogType.INFO, f"Added message(s) to memory!\nmessage: {str(message)}")
            self.is_saving_message = False
        log.log(LogType.DEBUG, "Unread message queue after:\n[{}]".format('\n'.join([str(message) for message in self.unread_message_queue])))


    async def communicate(self, callback=Callable[[str], Any], log: LogHanglerInterface=LogNothing()):
        log.log(LogType.INFO, "Communicating...")
        response: str = ""
        if not self.is_processing and len(self.unread_message_queue) != 0:
            self.is_processing = True 
            reading_attempts : int = 0
            response_attempts: int = 0

            # Sleeping delay
            delay: float = self.delay.ping()
            log.log(LogType.INFO, f"Sleeping... ({delay})")
            if delay > 0: await asyncio.sleep(delay)                                        # Bot start computing delay

            while len(self.unread_message_queue) != 0 and reading_attempts < 5 and response_attempts < 3:
                current_amount_of_unread_messages: int = len(self.unread_message_queue)

                # Wait for all messages to be in memory
                while self.is_saving_message:
                    await asyncio.sleep(0.1)

                # Reading delay
                reading_delay: float = self.reading_seconds_per_char*sum([len(message.content.strip()) for message in self.unread_message_queue])
                log.log(LogType.INFO, f"Reading... ({reading_delay})")
                await asyncio.sleep(reading_delay)                                          # Readig delay
                reading_attempts += 1
                if len(self.unread_message_queue) == 0: break

                # Redo if message amount has changed
                if current_amount_of_unread_messages != len(self.unread_message_queue):
                    log.log(LogType.INFO, "New message(s) added. Rereading...") 
                    continue

                # Response
                log.log(LogType.INFO, "Generating response...")
                response = await self.respond(log=log.sub())
                response_attempts += 1

                # Writing delay
                writing_delay: float = self.writing_seconds_per_char*len(response.strip())
                log.log(LogType.INFO, f"Writing... ({writing_delay})")
                await asyncio.sleep(writing_delay)                                          # Writing delay
                if len(self.unread_message_queue) == 0: break

                # Redo if message amount has changed
                if current_amount_of_unread_messages != len(self.unread_message_queue):
                    log.log(LogType.INFO, "New message(s) added. Recalculating...") 
                    continue
                break

            log.log(LogType.DEBUG, "CONVERSATION\nreading attempts: {}\nresponse attempts: {}\nmessages:\n    {}\nresponse:\n    {}".format(
                reading_attempts,
                response_attempts, 
                '\n    '.join([str(message) for message in self.unread_message_queue]),
                response))
            
            if len(self.unread_message_queue) != 0:
                asyncio.create_task(callback(response))
            self.unread_message_queue.clear()
            self.is_processing = False


