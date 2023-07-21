import pytest
from random import random
from structure import Message
from vector_database import (
    _DIM,
    SearchResult,
    MilvusConnection,
    CollectionType,
    DatabaseEntry,
    connect_to_database,
    disconnect_from_database,
    create_connection_to_collection,
    DROP_ALL_MEMORY)


@pytest.fixture(scope="module")
def setup():
    try:
        connect_to_database()
    except Exception as e:
        pytest.fail("Failed to connect to the database: {}".format(str(e)))
    yield
    disconnect_from_database()


@pytest.fixture()
def embeddings() -> list[list[float]]:
    return [[random()*2-1 for _ in range(_DIM)] for i in range(11) ]


@pytest.fixture()
def entries(embeddings : list[list[float]]) -> list[DatabaseEntry]:
    return [
        DatabaseEntry(Message(1 , "1"    , "Josh"     , "Hi"              ), embeddings[0]),
        DatabaseEntry(Message(2 , "12"   , "Dylan"    , "Hola"            ), embeddings[1]),
        DatabaseEntry(Message(3 , "1345" , "Dylan"    , "Hi"              ), embeddings[2]),
        DatabaseEntry(Message(4 , "235"  , "Josh"     , "Whatch up bros!" ), embeddings[3]),
        DatabaseEntry(Message(5 , "643"  , "Mike"     , "Sutt up!"        ), embeddings[4]),
        DatabaseEntry(Message(6 , "624"  , "Mike"     , "jk"              ), embeddings[5]),
        DatabaseEntry(Message(7 , "631"  , "Dylan"    , "Alright"         ), embeddings[6]),
        DatabaseEntry(Message(8 , "653"  , "Josh"     , "???"             ), embeddings[7]),
        DatabaseEntry(Message(9 , "233"  , "Mike"     , ":)"              ), embeddings[8]),
        DatabaseEntry(Message(10, "143"  , "Jessica"  , "Hi guys!"        ), embeddings[9]),
        DatabaseEntry(Message(11, "636"  , "Mike"     , "Shut up!"        ), embeddings[10])]


@pytest.fixture()
def connection(setup):
    DROP_ALL_MEMORY(CollectionType.TESTING)
    yield create_connection_to_collection(CollectionType.TESTING)
    DROP_ALL_MEMORY(CollectionType.TESTING)


def test_inserting_and_search(connection : MilvusConnection, embeddings : list[list[float]], entries : list[DatabaseEntry]):
    connection.add_entries(1, entries[:5])
    connection.create_index()
    res : list[list[Message]] = connection.search(1, embeddings[2:5])

    assert res != []
    assert res[0][0].id == 3
    assert res[1][0].id == 4
    assert res[2][0].id == 5


def test_adding_empty_list(connection : MilvusConnection, embeddings : list[list[float]], entries : list[DatabaseEntry]):
    connection.add_entries(1, [entries[0]])
    connection.add_entries(1, [])
    connection.create_index()
    res : list[list[Message]] = connection.search(1, [embeddings[0]])
    assert len(res) == 1
    assert len(res[0]) == 1


def test_empty_collection(connection : MilvusConnection, embeddings : list[list[float]], entries : list[DatabaseEntry]):
    connection.create_index()
    res : list[list[Message]] = connection.search(1, [])
    assert str(res) == "[]"


def test_remove_entries(connection : MilvusConnection, embeddings : list[list[float]], entries : list[DatabaseEntry]):
    connection.add_entries(15, entries[:3])
    connection.remove_entries(15, [1, 2])
    connection.create_index()
    res : list[list[Message]] = connection.search(15, [embeddings[2]])
    assert len(res) == 1
    assert len(res[0]) == 1


def test_remove_wrong_and_no_entry(connection : MilvusConnection, embeddings : list[list[float]], entries : list[DatabaseEntry]):
    connection.add_entries(15, entries[:3])
    connection.remove_entries(15, [5, 6])
    connection.remove_entries(15, [])
    connection.create_index()
    res : list[list[Message]] = connection.search(15, [embeddings[2]])
    assert len(res) == 1
    assert len(res[0]) == 3


def test_channel_creation_check_and_removal(connection : MilvusConnection):
    assert connection.has_channel(1) == False
    connection.create_channel_memory_if_new(1)
    connection.create_channel_memory_if_new(1)
    assert connection.has_channel(1) == True
    connection.create_channel_memory_if_new(2)
    connection.remove_channel_memory_if_exists(1)
    connection.remove_channel_memory_if_exists(1)
    assert connection.has_channel(1) == False
    assert connection.has_channel(2) == True
