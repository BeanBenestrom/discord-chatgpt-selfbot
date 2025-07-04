# External modules
import asyncio
from pymilvus import (
    connections,
    utility,
    FieldSchema,
    CollectionSchema,
    DataType,
    Collection,
    Partition,
    SearchResult,
    SearchFuture,
    MilvusException
)

from enum import Enum
from dataclasses import dataclass

from utility import multi_batch_iterator, Result, CustomThread
from structure import Message, DatabaseEntry

from debug import LogHanglerInterface, LogNothing, LogType

# ENUMS

class CollectionType(Enum):
    MAIN    = "discord_selfbot_memory"
    TESTING = "TEST_discord_selfbot_memory"

class PortType(Enum):
    gRPC    = 19530
    RESTful = 9091



# CONSTANTS

_HOST : str      = 'localhost'
_PORT : PortType = PortType.gRPC

_DIM                    : int = 1536
_MAX_AUTHOR_LENGTH      : int = 40
_MAX_CONTENT_LENGTH     : int = 2500
_MAX_INSERT_BATCH_SIZE  : int = 1000

_MILVUS = None

# STRUCTS

@dataclass(frozen=True)
class ConnectionInfo:
    # Database info
    host                   : str
    port                   : int
    # Collection info
    collection_name        : str
    dim                    : int
    schema_size            : int
    max_author_length      : int
    max_content_length     : int
    max_insert_batch_size  : int


# CLASSES

class MilvusConnection():
    _collection : Collection
    _collection_info : ConnectionInfo

    @staticmethod
    def get_partion_name(channel_id: int) -> str:
        if channel_id < 0: return f"neg{str(channel_id*-1)}"
        return f"{str(channel_id)}"



    def __init__(self, collection : Collection, collectionInfo : ConnectionInfo) -> None:
        self._collection      = collection
        self._collection_info = collectionInfo


    def has_channel(self, channel_id : int) -> bool:
        return self._collection.has_partition(MilvusConnection.get_partion_name(channel_id))


    async def create_channel_memory_if_new(self, channel_id : int, log: LogHanglerInterface=LogNothing()) -> bool:
        '''Returns True if channel was created, False if channel wasn't created because it already exists'''
        if not self.has_channel(channel_id):
            self._collection.create_partition(MilvusConnection.get_partion_name(channel_id))
            log.log(LogType.INFO, f"Channel created\nid: {channel_id}")
            return True
        return False


    async def remove_channel_memory_if_exists(self, channel_id : int, log: LogHanglerInterface=LogNothing()) -> bool:
        '''Returns True if channel was removed, False if channel wasn't removed because it doesn't exist'''
        if self.has_channel(channel_id):
            self._collection.drop_partition(MilvusConnection.get_partion_name(channel_id))
            log.log(LogType.INFO, f"Channel removed\nid: {channel_id}")
            return True
        return False


    async def add_entries(self, channel_id : int, entries : list[DatabaseEntry], log: LogHanglerInterface=LogNothing()) -> bool:
        """Returns True if entries were succesfully added, False if error occurred while inserting"""

        organized_entries = [[] for _ in range(self._collection_info.schema_size)]
        for entry in entries:
            organized_entries[0].append(entry.message.id       )
            organized_entries[1].append(entry.message.date     )
            organized_entries[2].append(entry.message.author   )
            organized_entries[3].append(entry.message.content  )
            organized_entries[4].append(entry.embedding        )

        results = []
        try:
            for organized_entries_batch in multi_batch_iterator(organized_entries, self._collection_info.max_insert_batch_size):
                res = await asyncio.get_event_loop().run_in_executor(None, lambda _ : self._collection.insert(
                        organized_entries_batch, 
                        partition_name=MilvusConnection.get_partion_name(channel_id))
                    , "param")
                #results.append(res)
                log.log(LogType.DEBUG, f"Batch added into {self._collection_info.collection_name} - size: {len(organized_entries_batch[0])}")
        except MilvusException as e:
            log.log(LogType.ERROR, f"Failed to insert messages into {self._collection_info.collection_name}!\namount: {len(entries)}\nfirst message: {entries[0].message}")
            return False
        
        # for result in results:
        #     result.result()

        self._collection.flush()
        log.log(LogType.DEBUG, "Insert success!")
        return True


    async def remove_entries(self, channel_id : int, entry_ids : list[int], log: LogHanglerInterface=LogNothing()) -> bool:
        """Returns True if entries were succesfully removed, False if channel doesn't exist or error occurred while deleting"""
        if not self.has_channel(channel_id): return False
        expr = "id in " + str(entry_ids)
        try: 
            await asyncio.get_event_loop().run_in_executor(None, lambda _ : self._collection.delete(expr, partition_name=MilvusConnection.get_partion_name(channel_id)), "param")
        except MilvusException as e:
            log.log(LogType.ERROR, f"Failed to remove messages from {self._collection_info.collection_name}!\namount: {len(entry_ids)}\nfirst message id: {entry_ids[0]}")
            return False
        return True



    async def create_index(self, log: LogHanglerInterface=LogNothing()) -> bool:
        """Returns True if index was succesfully created, False if error occurred"""
        index = {
            "index_type": "IVF_FLAT",
            "metric_type": "L2",
            "params": {"nlist": 128},
        }
        try:
            await asyncio.get_event_loop().run_in_executor(None, lambda _ : self._collection.create_index("embedding", index), "param")
        except MilvusException as e:
            log.log(LogType.ERROR, f"Failed to create index for {self._collection_info.collection_name}!")
            return False
        return True


    async def search(self, 
                     channel_id : int, 
                     vectors : list[list[float]] | None = None, expr : str | None = None, 
                     log: LogHanglerInterface=LogNothing()) -> Result[list[list[Message]]]:
        search_param = {
            "data"              :   vectors,
            "anns_field"        :   "embedding",
            "param"             :   {"metric_type": "L2", "params": {"nprobe": 10}},
            "limit"             :   10,
            "expr"              :   expr,
            "partition_names"   :   [MilvusConnection.get_partion_name(channel_id)],
            "output_fields"     :   ["date", "author", "content"]
        }

        partitionName = MilvusConnection.get_partion_name(channel_id)
        log.log(LogType.WARNING, partitionName)

        try:
            await asyncio.get_event_loop().run_in_executor(None, lambda _ : self._collection.load([partitionName]), "param")
            result = await asyncio.get_event_loop().run_in_executor(None, lambda _ : self._collection.search(**search_param), "param")
        except MilvusException as e:
            log.log(LogType.ERROR, f"Search failed for {self._collection_info.collection_name}!\nvector amount: {len(vectors) if vectors else '0'}\nexpr: {expr}")
            return Result.err(e)
        
        # Structure result to a list of messages
        if isinstance(result, SearchFuture): res = result.result()
        else                               : res = result

        await asyncio.get_event_loop().run_in_executor(None, lambda _ : self._collection.release(), "param")
        log.log(LogType.DEBUG, "Search success!")

        messages : list[list[Message]] = [
            [ Message(hit.id, hit.entity.date , hit.entity.author, hit.entity.content) for hit in hits ] 
            for hits in res ]

        return Result.ok(messages)
        # else:
        #     log.log(LogType.ERROR, f"Failed to retreive result from search!\nstatus: {status}")
        #     return Result.err(Exception(f"Failed to retreive result from search!\nstatus: {status}"))

    

# MODULE INTERFACE

_CONNECTIONS: dict[str, MilvusConnection] = {}


async def connect_to_database() -> None:
    await asyncio.get_event_loop().run_in_executor(None, lambda _ : connections.connect("default", host=_HOST, port=_PORT.value), "param")
    

async def disconnect_from_database() -> None:
    await asyncio.get_event_loop().run_in_executor(None, lambda _ : connections.disconnect("default"), "param")


async def create_connection_to_collection(collectionType : CollectionType) -> MilvusConnection:
    global _CONNECTIONS
    if collectionType.value in _CONNECTIONS:
        return _CONNECTIONS[str(collectionType)]

    fields = [
        FieldSchema(name="id",        dtype=DataType.INT64,         is_primary=True,                description="Primary Entry ID"),
        FieldSchema(name="date",      dtype=DataType.VARCHAR,       max_length=26,                  description="Date"),
        FieldSchema(name="author",    dtype=DataType.VARCHAR,       max_length=_MAX_AUTHOR_LENGTH,  description="Author"),
        FieldSchema(name="content",   dtype=DataType.VARCHAR,       max_length=_MAX_CONTENT_LENGTH, description="Actual Message"),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR,  dim=_DIM,                       description="Vector")
    ]
    schema = CollectionSchema(fields, "Discord selfbot's long-term memory", auto_id=False)
    collection = Collection(collectionType.value, schema)

    connectionInfo : ConnectionInfo = ConnectionInfo(
        host                    =   _HOST, 
        port                    =   _PORT.gRPC.value, 
        collection_name         =   collectionType.value, 
        dim                     =   _DIM, 
        schema_size             =   5, 
        max_author_length       =   _MAX_AUTHOR_LENGTH, 
        max_content_length      =   _MAX_CONTENT_LENGTH, 
        max_insert_batch_size   =   _MAX_INSERT_BATCH_SIZE)

    _CONNECTIONS[str(collectionType)] = MilvusConnection(collection, connectionInfo)
    return _CONNECTIONS[str(collectionType)]


async def DROP_ALL_MEMORY(collectionType : CollectionType):
    if utility.has_collection(collectionType.value):
        utility.drop_collection(collectionType.value)