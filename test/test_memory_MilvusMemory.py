import pytest
from vector_database import CollectionType, DatabaseEntry, _DIM, connect_to_database, disconnect_from_database, DROP_ALL_MEMORY
from random import random
from memory import MemoryMilvus
from structure import Message

# memory.add_messages()
# memory.remove_messages()
# memory.get()
# memory.clear()

@pytest.fixture(scope="module")
def setup():
    try:
        connect_to_database()
    except Exception as e:
        pytest.fail("Failed to connect to the database: {}".format(str(e)))
    DROP_ALL_MEMORY(CollectionType.TESTING)
    yield
    DROP_ALL_MEMORY(CollectionType.TESTING)
    disconnect_from_database()


@pytest.fixture()
def embeddings() -> list[list[float]]:
    return [[random()*2-1 for _ in range(_DIM)] for i in range(11) ]


@pytest.fixture()
def messages() -> list[Message]:
    return [
        Message(1 , "1"    , "Josh"     , "Hi"              ),
        Message(2 , "12"   , "Dylan"    , "Hola"            ),
        Message(3 , "1345" , "Dylan"    , "Hi"              ),
        Message(4 , "235"  , "Josh"     , "Whatch up bros!" ),
        Message(5 , "643"  , "Mike"     , "Sutt up!"        ),
        Message(6 , "624"  , "Mike"     , "jk"              ),
        Message(7 , "631"  , "Dylan"    , "Alright"         ),
        Message(8 , "653"  , "Josh"     , "???"             ),
        Message(9 , "233"  , "Mike"     , ":)"              ),
        Message(10, "143"  , "Jessica"  , "Hi guys!"        ),
        Message(11, "636"  , "Mike"     , "Shut up!"        )]


@pytest.fixture()
def test_channel() -> int:
    return 1


@pytest.fixture()
def memory(setup, test_channel):
    DROP_ALL_MEMORY(CollectionType.TESTING)
    yield MemoryMilvus(test_channel, CollectionType.TESTING)
    DROP_ALL_MEMORY(CollectionType.TESTING)


def test_MemoryMilvus_add_list(memory: MemoryMilvus, test_channel: int, messages: list[Message], embeddings: list[list[float]]):
    memory.add_messages(messages[:3], embeddings[:3])
    assert len(memory.search(embeddings[2])) == 3
    assert memory.search(embeddings[2])[0] == messages[2]


def test_MemoryMilvus_add_empty_list(memory: MemoryMilvus, test_channel: int, messages: list[Message], embeddings: list[list[float]]):
    memory.add_messages([], [])
    assert memory.search(embeddings[0]) == []


def test_MemoryMilvus_clear(memory: MemoryMilvus, test_channel: int, messages: list[Message], embeddings: list[list[float]]):
    memory.add_messages(messages[:5], embeddings[:5])
    memory.clear()
    assert memory.search(embeddings[0]) == []


def test_MemoryMilvus_remove_messages(memory: MemoryMilvus, test_channel: int, messages: list[Message], embeddings: list[list[float]]):
    memory.add_messages(messages[:5], embeddings[:5])
    memory.remove_messages([2, 3])
    res: list[Message] = memory.search(embeddings[2])
    assert len(res) == 3
    assert res[0].id != 2
