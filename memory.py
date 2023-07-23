# External modules
import json, os, random
from dataclasses import dataclass
from io import TextIOWrapper
from datetime import datetime, timedelta

# Internal modules
import prompt, ai

# Protocols
from interface import MemoryInterface
from structure import Message, DatabaseEntry, ShortTermMemory
from utility import Result

# Impementations
from vector_database import MilvusConnection, create_connection_to_collection, CollectionType

from debug import LogHanglerInterface, LogNothing, LogType



class MemoryMilvus():
    connection: MilvusConnection
    channel_id: int

    def __init__(self, channel_id: int, collectionType: CollectionType, log: LogHanglerInterface=LogNothing()) -> None:
        self.connection = create_connection_to_collection(collectionType)
        self.channel_id = channel_id
        self.connection.create_channel_memory_if_new(channel_id, log=log.sub())
        self.connection.create_index(log=log.sub())
        log.log(LogType.DEBUG, (f"Created MemoryMilvus object:\n"
                                f"id: {channel_id}\n"
                                f"collection type: {collectionType.value}\n"
                                f"collection info: {self.connection._collection_info}"))


    def add_messages(self, messages: list[Message], embeddings: list[list[float]], log: LogHanglerInterface=LogNothing()) -> None:
        entries: list[DatabaseEntry] = [DatabaseEntry(entryInfo[0], entryInfo[1]) for entryInfo in zip(messages, embeddings)]
        self.connection.add_entries(self.channel_id, entries, log=log.sub())
        self.connection.create_index(log=log.sub())
        

    def remove_messages(self, message_ids: list[int], log: LogHanglerInterface=LogNothing()) -> None:
        self.connection.remove_entries(self.channel_id, message_ids, log=log.sub())
        self.connection.create_index(log=log.sub())


    def search(self, embedding: list[float], log: LogHanglerInterface=LogNothing()) -> Result[list[Message]]:
        return self.connection.search(self.channel_id, [embedding], log=log.sub()).map(lambda r : r[0])
     

    def clear(self, log: LogHanglerInterface=LogNothing())	-> None:
        self.connection.remove_channel_memory_if_exists(self.channel_id, log=log.sub())
        self.connection.create_channel_memory_if_new(self.channel_id, log=log.sub())


    
class MemoryJson():
    channel_id: int
    file_path : str
    memory    : ShortTermMemory
    textModel : prompt.DefaultTextModel

    @staticmethod
    def get_memory_file_path(channel_id: int, extra_identifier: str="") -> str:
        return f"channel-memory/{extra_identifier+'_' if len(extra_identifier) else ''}{channel_id}.json"


    @staticmethod
    def create_channel_memory_if_new(channel_id, extra_identifier, log: LogHanglerInterface=LogNothing()) -> bool:
        '''Returns True if channel was created, False if channel wasn't created because it already exists'''
        file_path: str = MemoryJson.get_memory_file_path(channel_id, extra_identifier)
        if (not os.path.isfile (file_path) or os.path.getsize(file_path) == 0):
            with open(file_path, 'w', encoding="utf-8") as file:
                json.dump(ShortTermMemory().to_json(), file, ensure_ascii=False)
            log.log(LogType.INFO, f"Channel created\nid: {channel_id}")
            return True
        return False
    

    @staticmethod
    def remove_channel_memory_if_exists(channel_id: int, extra_identifier: str="", log: LogHanglerInterface=LogNothing()) -> bool:
        '''Returns True if channel was removed, False if channel wasn't removed because it doesn't exist'''
        if os.path.isfile(MemoryJson.get_memory_file_path(channel_id, extra_identifier)):
            os.remove(MemoryJson.get_memory_file_path(channel_id, extra_identifier))
            log.log(LogType.INFO, f"Channel removed\nid: {channel_id}")
            return True
        return False
    

    def __init__(self, channel_id: int, extra_identifier: str="", log: LogHanglerInterface=LogNothing()) -> None:
        self.channel_id = channel_id
        self.file_path = MemoryJson.get_memory_file_path(channel_id, extra_identifier)
        self.memory = ShortTermMemory()
        MemoryJson.create_channel_memory_if_new(channel_id, extra_identifier)
        self._load_memory()
        self.textModel = prompt.DefaultTextModel()
        log.log(LogType.DEBUG, (f"Created MemoryJson object:\n"
                                f"id           : {channel_id}\n"
                                f"file path    : {self.file_path}\n"
                                f"oldest message: {str(self.memory.messages[0])}\n"
                                f"newest message: {str(self.memory.messages[-1])}"))


    def _load_memory(self):  
        with open(self.file_path, encoding="utf-8") as file:
            self.memory.from_json(json.load(file))


    def _save_memory(self):
        with open(self.file_path, 'w', encoding="utf-8") as file:
            json.dump(self.memory.to_json(), file, ensure_ascii=False)


    def add_messages(self, messages: list[Message], log: LogHanglerInterface=LogNothing()) -> None:
        for message in messages:
            self.memory.tokens += self.textModel._tokens_from_message(self.memory.messages[0] if len(self.memory.messages) else None, message)
            self.memory.messages.append(message)
        log.log(LogType.INFO, f"Added {len(messages)} message(s) to {self.file_path}")
        self._save_memory()
        

    def remove_oldest_messages(self, amount: int, log: LogHanglerInterface=LogNothing()) -> None:
        # Remove messages
        self.memory.messages = self.memory.messages[amount:]
        self.memory.tokens = self.textModel._process_messages(self.memory.messages).tokens
        log.log(LogType.INFO, f"Removed {amount} oldests message(s) from {self.file_path}")
        self._save_memory()


    def get(self, log: LogHanglerInterface=LogNothing()) -> ShortTermMemory:
        return self.memory


    def clear(self, log: LogHanglerInterface=LogNothing())	-> None:
        self.memory = ShortTermMemory()
        self._save_memory()



class ComplexMemory(MemoryInterface):
    LTM      : MemoryMilvus
    LTM_Json : MemoryJson
    STM      : MemoryJson
    STM_LIMIT: int
    textModel: prompt.DefaultTextModel


    def __init__(self, channel_id: int, stm_limit: int, collectionType: CollectionType, log: LogHanglerInterface=LogNothing()) -> None:
        self.LTM      = MemoryMilvus(channel_id, collectionType)
        self.LTM_Json = MemoryJson  (channel_id, "ltm")
        self.STM      = MemoryJson  (channel_id)
        self.textModel = prompt.DefaultTextModel()
        super().__init__(channel_id, stm_limit)
        log.log(LogType.DEBUG, (f"Created ComplexMemory object:\n"
                                f"id        : {channel_id}\n"
                                f"text model: {type(self.textModel).__name__}\n"
                                f"short term memory limit: {stm_limit}\n"))


    def add_messages(self, messages: list[Message], log: LogHanglerInterface=LogNothing()) -> None:
        # Add to STM
        self.STM.add_messages(messages)

        # Skim of excess STM
        stm: ShortTermMemory = self.STM.get()
        messages_to_add_to_ltm: list[Message] = []
        
        converation: prompt.GeneratedConversation = self.textModel.conversation_crafter_newest_to_oldest(stm.messages, self.STM_LIMIT)
        messages_to_add_to_ltm = stm.messages[:len(stm.messages) - len(converation.messages)]
        self.STM.remove_oldest_messages(len(messages_to_add_to_ltm))

        # Add excess STM to LTM
        if len(messages_to_add_to_ltm):
            self.LTM_Json.add_messages(messages_to_add_to_ltm)
            embeddings: list[list[float]] = ai.embed_strings([message.content for message in messages_to_add_to_ltm], log=log.sub())
            self.LTM.add_messages(messages_to_add_to_ltm, embeddings)
    
    
    def remove_messages(self, message_ids: list[int], log: LogHanglerInterface=LogNothing()) -> None:
        # Find from STM with binary search
        # If not removed, remove from LTM
        # Else 
        ...
    
    
    def search_long_term_memory(self, text: str, log: LogHanglerInterface=LogNothing()) -> list[Message]:
        embedding: list[float] = ai.embed_strings([text], log=log.sub())[0]
        return self.LTM.search(embedding).unwrap()


    def get_short_term_memory(self, log: LogHanglerInterface=LogNothing()) -> list[Message]:
        return self.STM.get().messages


    def clear_long_term_memory(self, log: LogHanglerInterface=LogNothing()) -> None:
        self.LTM.clear()
        self.LTM_Json.clear()


    def clear_short_term_memory(self, log: LogHanglerInterface=LogNothing()) -> None:
        self.STM.clear()



class DebugMemory(MemoryInterface):
    def __init__(self, channel_id: int, stm_limit: int, log: LogHanglerInterface=LogNothing()) -> None:
        super().__init__(channel_id, stm_limit)


    def add_messages(self, messages: list[Message], log: LogHanglerInterface=LogNothing()) -> None:
        pass
    
    
    def remove_messages(self, message_ids: list[int], log: LogHanglerInterface=LogNothing()) -> None:
        pass
    
    
    def search_long_term_memory(self, text: str, log: LogHanglerInterface=LogNothing()) -> list[Message]:
        return Message.debug_messages(5)


    def get_short_term_memory(self, log: LogHanglerInterface=LogNothing()) -> list[Message]:
        time: datetime = datetime.now()
        messages: list[Message] = []
        for i in range(100):
            messages.append(Message(i, str(time), "Bob" if random.random() > 0.5 else "Mike", "Hello, World!"))
            time += timedelta(minutes=random.random()*3)
        return messages


    def clear_long_term_memory(self, log: LogHanglerInterface=LogNothing()) -> None:
        pass


    def clear_short_term_memory(self, log: LogHanglerInterface=LogNothing()) -> None:
        pass