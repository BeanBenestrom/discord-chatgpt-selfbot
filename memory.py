# External modules
import json, os, random, asyncio
from dataclasses import dataclass
from io import TextIOWrapper
from datetime import datetime, timedelta

# Internal modules
import prompt, ai, threading

# Protocols
from interface import MemoryInterface
from structure import Message, DatabaseEntry, ShortTermMemory
from utility import Result, create_json_file_if_not_exist

# Impementations
import vector_database
from vector_database import MilvusConnection, create_connection_to_collection, CollectionType

from debug import LogHanglerInterface, LogNothing, LogType



class MemoryMilvus():
    connection: MilvusConnection
    channel_id: int

    @staticmethod
    async def create(channel_id: int, collectionType: CollectionType, log: LogHanglerInterface=LogNothing()) -> 'MemoryMilvus':
        connection = await create_connection_to_collection(collectionType)
        obj: MemoryMilvus = MemoryMilvus(channel_id, connection, log=log)
        await connection.create_channel_memory_if_new(channel_id, log=log.sub())
        await connection.create_index(log=log.sub())
        log.log(LogType.DEBUG, (f"Created MemoryMilvus object:\n"
                                f"id: {channel_id}\n"
                                f"collection type: {collectionType.value}\n"
                                f"collection info: {connection._collection_info}"))
        return obj


    def __init__(self, channel_id: int, connection: vector_database.MilvusConnection, log: LogHanglerInterface=LogNothing()) -> None:
        self.connection = connection
        self.channel_id = channel_id


    async def add_messages(self, messages: list[Message], embeddings: list[list[float]], log: LogHanglerInterface=LogNothing()) -> None:
        entries: list[DatabaseEntry] = [DatabaseEntry(entryInfo[0], entryInfo[1]) for entryInfo in zip(messages, embeddings)]
        await self.connection.add_entries(self.channel_id, entries, log=log.sub())
        await self.connection.create_index(log=log.sub())
        

    async def remove_messages(self, message_ids: list[int], log: LogHanglerInterface=LogNothing()) -> None:
        await self.connection.remove_entries(self.channel_id, message_ids, log=log.sub())
        await self.connection.create_index(log=log.sub())


    async def search(self, embedding: list[float], log: LogHanglerInterface=LogNothing()) -> Result[list[Message]]:
        return (await self.connection.search(self.channel_id, [embedding], log=log.sub())).map(lambda r : r[0])
     

    async def clear(self, log: LogHanglerInterface=LogNothing()) -> None:
        await self.connection.remove_channel_memory_if_exists(self.channel_id, log=log.sub())
        await self.connection.create_channel_memory_if_new(self.channel_id, log=log.sub())


    
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
        return create_json_file_if_not_exist(file_path, ShortTermMemory().to_json())
    

    @staticmethod
    def remove_channel_memory_if_exists(channel_id: int, extra_identifier: str="", log: LogHanglerInterface=LogNothing()) -> bool:
        '''Returns True if channel was removed, False if channel wasn't removed because it doesn't exist'''
        if os.path.isfile(MemoryJson.get_memory_file_path(channel_id, extra_identifier)):
            os.remove(MemoryJson.get_memory_file_path(channel_id, extra_identifier))
            log.log(LogType.INFO, f"Channel removed\nid: {channel_id}")
            return True
        return False
    

    @staticmethod
    async def create(channel_id: int, extra_identifier: str="", log: LogHanglerInterface=LogNothing()) -> 'MemoryJson':
        obj: MemoryJson = MemoryJson(channel_id, extra_identifier, log=log)
        MemoryJson.create_channel_memory_if_new(channel_id, extra_identifier)
        await obj._load_memory()
        log.log(LogType.DEBUG, (f"Created MemoryJson object:\n"
                                f"id           : {channel_id}\n"
                                f"file path    : {obj.file_path}\n"
                                f"oldest message: {str(obj.memory.messages[0] if len(obj.memory.messages) else None)}\n"
                                f"newest message: {str(obj.memory.messages[-1] if len(obj.memory.messages) else None)}"))
        return obj


    def __init__(self, channel_id: int, extra_identifier: str="", log: LogHanglerInterface=LogNothing()) -> None:
        self.channel_id = channel_id
        self.file_path = MemoryJson.get_memory_file_path(channel_id, extra_identifier)
        self.memory = ShortTermMemory()
        self.textModel = prompt.DefaultTextModel()


    async def _load_memory(self):  
        with open(self.file_path, encoding="utf-8") as file:
            self.memory.from_json(json.load(file))


    async def _save_memory(self):
        with open(self.file_path, 'w', encoding="utf-8") as file:
            json.dump(self.memory.to_json(), file, ensure_ascii=False)


    async def add_messages(self, messages: list[Message], log: LogHanglerInterface=LogNothing()) -> None:
        before: int = len(self.memory.messages)
        for message in messages:
            self.memory.tokens += await self.textModel._tokens_from_message(self.memory.messages[0] if len(self.memory.messages) else None, message)
            self.memory.messages.append(message)
        log.log(LogType.INFO, f"Added {len(self.memory.messages) - before} message(s) to {self.file_path}")
        await self._save_memory()
        

    async def remove_oldest_messages(self, amount: int, log: LogHanglerInterface=LogNothing()) -> None:
        before: int = len(self.memory.messages)
        # Remove messages
        self.memory.messages = self.memory.messages[amount:]
        self.memory.tokens = (await self.textModel._process_messages(self.memory.messages)).tokens
        log.log(LogType.INFO, f"Removed {before - len(self.memory.messages)} oldests message(s) from {self.file_path}")
        await self._save_memory()


    async def get(self, log: LogHanglerInterface=LogNothing()) -> ShortTermMemory:
        return self.memory


    async def clear(self, log: LogHanglerInterface=LogNothing())	-> None:
        self.memory = ShortTermMemory()
        await self._save_memory()



class ComplexMemory(MemoryInterface):
    LTM      : MemoryMilvus
    LTM_Json : MemoryJson
    STM      : MemoryJson
    STM_LIMIT: int
    textModel: prompt.DefaultTextModel


    @staticmethod
    async def create(channel_id: int, stm_limit: int, collectionType: CollectionType, log: LogHanglerInterface=LogNothing()) -> 'ComplexMemory':
        LTM     : MemoryMilvus  = await MemoryMilvus.create(channel_id, collectionType, log=log.sub())
        LTM_Json: MemoryJson    = await MemoryJson  .create(channel_id, "ltm", log=log.sub())
        STM     : MemoryJson    = await MemoryJson  .create(channel_id, log=log.sub())

        obj: ComplexMemory = ComplexMemory(channel_id, stm_limit, LTM, LTM_Json, STM, log=log)
        log.log(LogType.DEBUG, (f"Created ComplexMemory object:\n"
                                f"id        : {channel_id}\n"
                                f"text model: {type(obj.textModel).__name__}\n"
                                f"short term memory limit: {stm_limit}\n"))
        return obj


    def __init__(self, channel_id: int, stm_limit: int, LTM, LTM_Json, STM, log: LogHanglerInterface=LogNothing()) -> None:
        self.LTM      = LTM
        self.LTM_Json = LTM_Json
        self.STM      = STM
        self.textModel = prompt.DefaultTextModel()
        super().__init__(channel_id, stm_limit)
        


    async def add_messages(self, messages: list[Message], log: LogHanglerInterface=LogNothing()) -> None:
        # Add to STM
        await self.STM.add_messages(messages, log=log.sub())

        # Skim of excess STM
        stm: ShortTermMemory = await self.STM.get(log=log.sub())
        messages_to_add_to_ltm: list[Message] = []
        
        converation: prompt.GeneratedConversation = await self.textModel.conversation_crafter_newest_to_oldest(stm.messages, self.STM_LIMIT)
        messages_to_add_to_ltm = stm.messages[:len(stm.messages) - len(converation.messages)]
        await self.STM.remove_oldest_messages(len(messages_to_add_to_ltm), log=log.sub())

        # Add excess STM to LTM
        if len(messages_to_add_to_ltm):
            await self.LTM_Json.add_messages(messages_to_add_to_ltm, log=log.sub())
            embeddings: list[list[float]] = (await ai.embed_strings([message.content for message in messages_to_add_to_ltm], log=log.sub())).unwrap() #! TODO: Add safety
            asyncio.create_task(self.LTM.add_messages(messages_to_add_to_ltm, embeddings, log.sub()))
    
    
    async def remove_messages(self, message_ids: list[int], log: LogHanglerInterface=LogNothing()) -> None:
        # Find from STM with binary search
        # If not removed, remove from LTM
        # Else 
        ...
    
    
    async def search_long_term_memory(self, text: str, log: LogHanglerInterface=LogNothing()) -> Result[list[Message]]:
        embedding: list[float] = (await ai.embed_strings([text], log=log.sub())).unwrap()[0] #! TODO: Add safety
        return await self.LTM.search(embedding, log=log.sub())


    async def get_short_term_memory(self, log: LogHanglerInterface=LogNothing()) -> list[Message]:
        return (await self.STM.get(log=log.sub())).messages


    async def clear_long_term_memory(self, log: LogHanglerInterface=LogNothing()) -> None:
        await asyncio.gather(self.LTM.clear(log=log.sub()), self.LTM_Json.clear(log=log.sub()))


    async def clear_short_term_memory(self, log: LogHanglerInterface=LogNothing()) -> None:
        await self.STM.clear(log=log.sub())


class VirtualComplexMemory(MemoryInterface):
    '''Complex memory that doesn't change the actual memory on disk'''
    LTM      : MemoryMilvus
    STM      : MemoryJson
    STM_LIMIT: int
    textModel: prompt.DefaultTextModel

    current_messages: list[Message]


    @staticmethod
    async def create(channel_id: int, stm_limit: int, collectionType: CollectionType, log: LogHanglerInterface=LogNothing()) -> 'VirtualComplexMemory':
        LTM     : MemoryMilvus  = await MemoryMilvus.create(channel_id, collectionType, log=log.sub())
        STM     : MemoryJson    = await MemoryJson  .create(channel_id, log=log.sub())

        obj: VirtualComplexMemory = VirtualComplexMemory(channel_id, stm_limit, LTM, STM, log=log)
        log.log(LogType.DEBUG, (f"Created ComplexMemory object:\n"
                                f"id        : {channel_id}\n"
                                f"text model: {type(obj.textModel).__name__}\n"
                                f"short term memory limit: {stm_limit}\n"))
        return obj


    def __init__(self, channel_id: int, stm_limit: int, LTM, STM, log: LogHanglerInterface=LogNothing()) -> None:
        self.LTM      = LTM
        self.STM      = STM
        self.textModel = prompt.DefaultTextModel()
        self.current_messages = []
        super().__init__(channel_id, stm_limit)
        

    async def add_messages(self, messages: list[Message], log: LogHanglerInterface=LogNothing()) -> None:
        # Add to STM
        for message in messages:
            self.current_messages.append(message)
    
    
    async def remove_messages(self, message_ids: list[int], log: LogHanglerInterface=LogNothing()) -> None:
        # Find from STM with binary search
        # If not removed, remove from LTM
        # Else 
        ...
    
    
    async def search_long_term_memory(self, text: str, log: LogHanglerInterface=LogNothing()) -> Result[list[Message]]:
        embedding: list[float] = (await ai.embed_strings([text], log=log.sub())).unwrap()[0] #! TODO: Add safety
        return await self.LTM.search(embedding, log=log.sub())


    async def get_short_term_memory(self, log: LogHanglerInterface=LogNothing()) -> list[Message]:
        return ((await self.STM.get(log=log.sub())).messages + self.current_messages)


    async def clear_long_term_memory(self, log: LogHanglerInterface=LogNothing()) -> None:
        pass


    async def clear_short_term_memory(self, log: LogHanglerInterface=LogNothing()) -> None:
        pass



class DebugMemory(MemoryInterface):
    def __init__(self, channel_id: int, stm_limit: int, log: LogHanglerInterface=LogNothing()) -> None:
        super().__init__(channel_id, stm_limit)


    async def add_messages(self, messages: list[Message], log: LogHanglerInterface=LogNothing()) -> None:
        pass
    
    
    async def remove_messages(self, message_ids: list[int], log: LogHanglerInterface=LogNothing()) -> None:
        pass
    
    
    async def search_long_term_memory(self, text: str, log: LogHanglerInterface=LogNothing()) -> list[Message]:
        return Message.debug_messages(5)


    async def get_short_term_memory(self, log: LogHanglerInterface=LogNothing()) -> list[Message]:
        time: datetime = datetime.now()
        messages: list[Message] = []
        for i in range(100):
            messages.append(Message(i, str(time), "Bob" if random.random() > 0.5 else "Mike", "Hello, World!"))
            time += timedelta(minutes=random.random()*3)
        return messages


    async def clear_long_term_memory(self, log: LogHanglerInterface=LogNothing()) -> None:
        pass


    async def clear_short_term_memory(self, log: LogHanglerInterface=LogNothing()) -> None:
        pass