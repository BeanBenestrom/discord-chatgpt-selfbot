from dataclasses import dataclass


@dataclass
class Message:
    id        : int
    date      : str
    author    : str
    content   : str
    
    def object_to_list(self):
        return [self.id, self.date, self.author, self.content]
    
    @staticmethod
    def list_to_object(messageInfo: list) -> 'Message':
        return Message(messageInfo[0], messageInfo[1], messageInfo[2], messageInfo[3])


@dataclass(frozen=True)
class DatabaseEntry:
    message   : Message
    embedding : list[float]


@dataclass
class ShortTermMemory:
    tokens  : int = 0
    messages: list[Message] = []

    def from_json(self, json: dict) -> None:
        self.tokens   = json["tokens"]
        self.messages = [Message.list_to_object(message) for message in json["messages"]]

    def to_json(self) -> dict:
        return { 
            "tokens": self.tokens, 
            "messages": [Message.object_to_list(message) for message in self.messages] 
        }