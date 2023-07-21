# External modules
from pymilvus import (
    connections,
    utility,
    FieldSchema,
    CollectionSchema,
    DataType,
    Collection,
    Partition,
    SearchResult,
    Milvus
)

from enum import Enum
from dataclasses import dataclass

from utility import multi_batch_iterator
from structure import Message

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
_CONNECTIONS = {}

_DIM                    : int = 1536
_MAX_AUTHOR_LENGTH      : int = 40
_MAX_CONTENT_LENGTH     : int = 2500
_MAX_INSERT_BATCH_SIZE  : int = 1000



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


    def __init__(self, collection : Collection, collectionInfo : ConnectionInfo) -> None:
        self._collection      = collection
        self._collection_info = collectionInfo


    def has_channel(self, channel_id : int) -> bool:
        return self._collection.has_partition(str(channel_id))


    def create_channel_memory_if_new(self, channel_id : int) -> None:
        if not self.has_channel(channel_id):
            self._collection.create_partition(str(channel_id))


    def remove_channel_memory_if_exists(self, channel_id : int) -> None:
        if self.has_channel(channel_id):
            self._collection.drop_partition(str(channel_id))


    def add_entries(self, channel_id : int, entries : list[DatabaseEntry]) -> None:
        self.create_channel_memory_if_new(channel_id)

        organized_entries = [[] for _ in range(self._collection_info.schema_size)]
        for entry in entries:
            organized_entries[0].append(entry.message.id       )
            organized_entries[1].append(entry.message.date     )
            organized_entries[2].append(entry.message.author   )
            organized_entries[3].append(entry.message.content  )
            organized_entries[4].append(entry.embedding        )

        for organized_entries_batch in multi_batch_iterator(organized_entries, self._collection_info.max_insert_batch_size):
            # print(f"INSERT BATCH {organized_entries_batch[0]}")
            self._collection.insert(organized_entries_batch, partition_name=str(channel_id))

        self._collection.flush()


    def remove_entries(self, channel_id : int, entry_ids : list[int]) -> None:
        expr = "id in " + str(entry_ids)
        if self.has_channel(channel_id):  
            self._collection.delete(expr, partition_name=str(channel_id))


    def create_index(self):
        index = {
            "index_type": "IVF_FLAT",
            "metric_type": "L2",
            "params": {"nlist": 128},
        }
        self._collection.create_index("embedding", index)


    def search(self, channel_id : int, vectors : list[list[float]] | None = None, expr : str | None = None) -> list[list[Message]]:
        self.create_channel_memory_if_new(channel_id)
        search_param = {
            "data"              :   vectors,
            "anns_field"        :   "embedding",
            "param"             :   {"metric_type": "L2", "params": {"nprobe": 10}},
            "limit"             :   10,
            "expr"              :   expr,
            "partition_names"   :   [str(channel_id)],
            "output_fields"     :   ["date", "author", "content"]
        }

        self._collection.load([str(channel_id)])
        res = self._collection.search(**search_param)
        self._collection.release()
        assert isinstance(res, SearchResult)

        messages : list[list[Message]] = [
            [ Message(hit.id, hit.entity.date , hit.entity.author, hit.entity.content) for hit in hits ] 
            for hits in res ]

        return messages

    

# MODULE INTERFACE

def connect_to_database() -> None:
    connections.connect("default", host=_HOST, port=_PORT.value)


def disconnect_from_database() -> None:
    connections.disconnect("default")


def create_connection_to_collection(collectionType : CollectionType):
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


def DROP_ALL_MEMORY(collectionType : CollectionType):
    if utility.has_collection(collectionType.value):
        utility.drop_collection(collectionType.value)