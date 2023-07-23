import pytest
from vector_database import CollectionType, DatabaseEntry, _DIM, connect_to_database, disconnect_from_database, DROP_ALL_MEMORY
from random import random
from structure import Message
from datetime import datetime, timedelta
from random import random
import prompt

from memory import ComplexMemory



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
    time: datetime = datetime.now()
    messages: list[Message] = []
    for i in range(50):
        messages.append(Message(i, str(time), "Bob" if random() > 0.5 else "Mike", "Hello, World!"))
        time += timedelta(minutes=random()*3)
    return messages


@pytest.fixture()
def test_channel() -> int:
    return -1


@pytest.fixture()
def memory(setup, test_channel):
    memory: ComplexMemory = ComplexMemory(test_channel, 300, CollectionType.TESTING)
    memory.clear_long_term_memory()
    memory.clear_short_term_memory()
    yield memory


@pytest.fixture()
def memory2(setup, test_channel):
    memory2: ComplexMemory = ComplexMemory(test_channel, 0, CollectionType.TESTING)
    memory2.clear_long_term_memory()
    memory2.clear_short_term_memory()
    yield memory2



def test_add_1_message(memory: ComplexMemory, messages: list[Message]):
    memory.add_messages([messages[0]])
    assert memory.get_short_term_memory() == [messages[0]]
    assert memory.search_long_term_memory("Hello, World!") == []
    assert memory.STM.get().tokens <= 300


def test_add_1_message_memory2(memory2: ComplexMemory, messages: list[Message]):
    memory2.add_messages([messages[0]])
    assert memory2.get_short_term_memory() == []
    assert memory2.search_long_term_memory("Hello, World!") == [messages[0]]
    assert memory2.STM.get().tokens <= 0


def test_add_messages(memory: ComplexMemory, messages: list[Message]):
    conversation: prompt.GeneratedConversation = prompt.DefaultTextModel().conversation_crafter_newest_to_oldest(messages, 300)
    messages_that_should_be_in_ltm : list[Message] = messages[:len(messages)-len(conversation.messages)]
  # print(len(messages_that_should_be_in_ltm))
    memory.add_messages(messages)
    assert memory.get_short_term_memory() == messages[len(messages_that_should_be_in_ltm):]
    assert len(memory.search_long_term_memory("Hello, World!")) > 0
    assert memory.STM.get().tokens <= 300
  # print(prompt.tokens_from_string(prompt.DefaultTextModel()._process_messages(memory.STM.get().messages).string))


# def test_remove_messages(memory: ComplexMemory, test_channel: int, messages: list[Message]):
#     pass


def test_add_no_messages(memory: ComplexMemory, messages: list[Message]):
    memory.add_messages([])
    assert memory.get_short_term_memory() == []
    assert memory.search_long_term_memory("Hello, World!") == []


def test_clear_messages(memory: ComplexMemory, messages: list[Message]):
    test_add_messages(memory, messages)
    memory.clear_short_term_memory()
    assert memory.get_short_term_memory() == []
    assert len(memory.search_long_term_memory("Hello, World!")) > 0
    memory.clear_long_term_memory()
    assert memory.get_short_term_memory() == []
    assert memory.search_long_term_memory("Hello, World!") == []
    