import pytest
from memory import MemoryJson
from structure import Message

# memory.add_messages()
# memory.remove_messages()
# memory.get()
# memory.clear()


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
    return -1


def test_MemoryJson_add_list(test_channel: int, messages: list[Message]):
    memory: MemoryJson = MemoryJson(test_channel)
    memory.add_messages(messages[:5])
    memory.add_messages(messages[5:7])
    assert memory.get() == messages[:7]
    memory.clear()


def test_MemoryJson_add_empty_list(test_channel: int, messages: list[Message]):
    memory: MemoryJson = MemoryJson(test_channel)
    memory.add_messages([])
    assert memory.get() == []
    memory.clear()


def test_MemoryJson_clear(test_channel: int, messages: list[Message]):
    memory: MemoryJson = MemoryJson(test_channel)
    memory.add_messages(messages[:5])
    memory.clear()
    assert memory.get() == []