import pytest
from memory import MemoryJson
from structure import Message
from datetime import datetime, timedelta
import random

# memory.add_messages()
# memory.remove_messages()
# memory.get()
# memory.clear()


@pytest.fixture()
def messages() -> list[Message]:
    time: datetime = datetime.now()
    messages: list[Message] = []
    for i in range(100):
        messages.append(Message(i, str(time), "Bob" if random.random() > 0.5 else "Mike", "Hello, World!"))
        time += timedelta(minutes=random.random()*3)
    return messages


@pytest.fixture()
def memory(test_channel):
    memory: MemoryJson = MemoryJson(test_channel)
    memory.clear()
    yield memory


@pytest.fixture()
def test_channel() -> int:
    return -1


def test_MemoryJson_add_list(memory: MemoryJson, messages: list[Message]):
    memory.add_messages(messages[:5])
    memory.add_messages(messages[5:7])
    assert memory.get().messages == messages[:7]


def test_MemoryJson_add_empty_list(memory: MemoryJson, messages: list[Message]):
    memory.add_messages([])
    assert memory.get().messages == []


def test_MemoryJson_clear(memory: MemoryJson, messages: list[Message]):
    memory.add_messages(messages[:5])
    memory.clear()
    assert memory.get().messages == []