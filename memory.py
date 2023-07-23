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



class MemoryMilvus():
    connection: MilvusConnection
    channel_id: int

    def __init__(self, channel_id: int, collectionType: CollectionType) -> None:
        self.connection = create_connection_to_collection(collectionType)
        self.channel_id = channel_id
        self.connection.create_channel_memory_if_new(channel_id)
        self.connection.create_index()


    def add_messages(self, messages: list[Message], embeddings: list[list[float]]) -> None:
        entries: list[DatabaseEntry] = [DatabaseEntry(entryInfo[0], entryInfo[1]) for entryInfo in zip(messages, embeddings)]
        self.connection.add_entries(self.channel_id, entries)
        self.connection.create_index()
        

    def remove_messages(self, message_ids: list[int]) -> None:
        self.connection.remove_entries(self.channel_id, message_ids)
        self.connection.create_index()


    def search(self, embedding: list[float]) -> Result[list[Message]]:
        return self.connection.search(self.channel_id, [embedding]).map(lambda r : r[0])
     

    def clear(self)	-> None:
        self.connection.remove_channel_memory_if_exists(self.channel_id)
        self.connection.create_channel_memory_if_new(self.channel_id)


    
class MemoryJson():
    channel_id: int
    file_path : str
    memory    : ShortTermMemory
    textModel : prompt.DefaultTextModel

    @staticmethod
    def get_memory_file_path(channel_id: int, extra_identifier: str="") -> str:
        return f"channel-memory/{extra_identifier+'_' if len(extra_identifier) else ''}{channel_id}.json"


    @staticmethod
    def remove_channel_memory_if_exists(channel_id: int, extra_identifier: str="") -> bool:
        '''Returns True if channel was removed, False if channel wasn't removed because it doesn't exist'''
        if os.path.isfile(MemoryJson.get_memory_file_path(channel_id, extra_identifier)):
            os.remove(MemoryJson.get_memory_file_path(channel_id, extra_identifier))
            return True
        return False


    @staticmethod
    def create_channel_memory_if_new(channel_id, extra_identifier) -> bool:
        '''Returns True if channel was created, False if channel wasn't created because it already exists'''
        file_path: str = MemoryJson.get_memory_file_path(channel_id, extra_identifier)
        if (not os.path.isfile (file_path) or os.path.getsize(file_path) == 0):
            with open(file_path, 'w', encoding="utf-8") as file:
                json.dump(ShortTermMemory().to_json(), file, ensure_ascii=False)
            return True
        return False
    

    def __init__(self, channel_id: int, extra_identifier: str="") -> None:
        self.channel_id = channel_id
        self.file_path = MemoryJson.get_memory_file_path(channel_id, extra_identifier)
        self.memory = ShortTermMemory()
        MemoryJson.create_channel_memory_if_new(channel_id, extra_identifier)
        self._load_memory()
        self.textModel = prompt.DefaultTextModel()


    def _load_memory(self):  
        with open(self.file_path, encoding="utf-8") as file:
            self.memory.from_json(json.load(file))


    def _save_memory(self):
        with open(self.file_path, 'w', encoding="utf-8") as file:
            json.dump(self.memory.to_json(), file, ensure_ascii=False)


    def add_messages(self, messages: list[Message]) -> None:
        for message in messages:
            self.memory.tokens += self.textModel._tokens_from_message(self.memory.messages[0] if len(self.memory.messages) else None, message)
            self.memory.messages.append(message)
        self._save_memory()
        

    def remove_oldest_messages(self, amount: int) -> None:
        # Remove messages
        self.memory.messages = self.memory.messages[amount:]
        self.memory.tokens = self.textModel._process_messages(self.memory.messages).tokens
        self._save_memory()


    def get(self) -> ShortTermMemory:
        return self.memory


    def clear(self)	-> None:
        self.memory = ShortTermMemory()
        self._save_memory()



class ComplexMemory(MemoryInterface):
    LTM      : MemoryMilvus
    LTM_Json : MemoryJson
    STM      : MemoryJson
    STM_LIMIT: int
    textModel: prompt.DefaultTextModel


    def __init__(self, channel_id: int, stm_limit: int, collectionType: CollectionType) -> None:
        self.LTM      = MemoryMilvus(channel_id, collectionType)
        self.LTM_Json = MemoryJson  (channel_id, "ltm")
        self.STM      = MemoryJson  (channel_id)
        self.textModel = prompt.DefaultTextModel()
        super().__init__(channel_id, stm_limit)


    def add_messages(self, messages: list[Message]) -> None:
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
            embeddings: list[list[float]] = ai.embed_strings([message.content for message in messages_to_add_to_ltm])
            self.LTM.add_messages(messages_to_add_to_ltm, embeddings)
    
    
    def remove_messages(self, message_ids: list[int]) -> None:
        # Find from STM with binary search
        # If not removed, remove from LTM
        # Else 
        ...
    
    
    def search_long_term_memory(self, text: str) -> list[Message]:
        embedding: list[float] = ai.embed_strings([text])[0]
        return self.LTM.search(embedding).unwrap()


    def get_short_term_memory(self) -> list[Message]:
        return self.STM.get().messages


    def clear_long_term_memory(self) -> None:
        self.LTM.clear()
        self.LTM_Json.clear()


    def clear_short_term_memory(self) -> None:
        self.STM.clear()



class DebugMemory(MemoryInterface):
    def __init__(self, channel_id: int, stm_limit: int) -> None:
        super().__init__(channel_id, stm_limit)


    def add_messages(self, messages: list[Message]) -> None:
        pass
    
    
    def remove_messages(self, message_ids: list[int]) -> None:
        pass
    
    
    def search_long_term_memory(self, text: str) -> list[Message]:
        return Message.debug_messages(5)


    def get_short_term_memory(self) -> list[Message]:
        time: datetime = datetime.now()
        messages: list[Message] = []
        for i in range(100):
            messages.append(Message(i, str(time), "Bob" if random.random() > 0.5 else "Mike", "Hello, World!"))
            time += timedelta(minutes=random.random()*3)
        return messages


    def clear_long_term_memory(self) -> None:
        pass


    def clear_short_term_memory(self) -> None:
        pass