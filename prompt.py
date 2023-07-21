import datetime, tiktoken
from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import Callable

from structure import Message# , ShortTermMemory
from ai import MAX_TOKENS

# def get_token_amount(message):
enc = tiktoken.get_encoding("cl100k_base")


# STRUCTS

@dataclass(frozen=True)
class GeneratedConversation:
    string: str
    tokens: int
    messages: list[Message]


# iterator


# class ConversationTokenIterator():
#     messages: list[Message] = []
#     tokens  : int
#     iteration_function: Callable[[list[Message], int], tuple[list[Message], int]]
    

#     def __init__(self, messages : list[Message], tokens : int, iteration_function: Callable[[list[Message], int], tuple[list[Message], int]]):
#         self.messages = messages
#         self.tokens = tokens
#         self.iteration_function = iteration_function

#     def __iter__(self):
#         return self

#     def __next__(self):
#         if len(self.messages) == 0:
#             raise StopIteration
#         batch : list = self.array[self.batchSize*self.currentBatch:self.batchSize*(self.currentBatch+1)]
#         self.currentBatch += 1
#         return batch


# GENERAL FUNCTIONS

# the added * 2 is there to get a more accurate answer for this kind of usage, as Discord messages aren't like typical paragraphs
def tokens_from_string(string: str):
    return len(enc.encode(string))


# INTERFACES

class TextModelInterface(ABC):
    conversation: GeneratedConversation

    @abstractmethod
    def _process_messages(self, messages: list[Message]) -> GeneratedConversation:
        ...

    @abstractmethod
    def conversation_crafter_oldest_to_newest(self, messages: list[Message], max_tokens: int) -> GeneratedConversation:
        '''
        Crafts a string representation of a chain of messages which complies with being inside the token threshold.
        # ! BLA BLA BLA
        Returned string could then be placed onto a prompt.
        '''
        ...
    @abstractmethod
    def conversation_crafter_newest_to_oldest(self, messages: list[Message], max_tokens: int) -> GeneratedConversation:
        '''
        Crafts a string representation of a chain of messages which complies with being inside the token threshold.
        # ! BLA BLA BLA
        Returned string could then be placed onto a prompt.
        '''
        ...
    @abstractmethod
    def conversation_crafter_center_to_ends(self, messages: list[Message], max_tokens: int) -> GeneratedConversation:
        '''
        Crafts a string representation of a chain of messages which complies with being inside the token threshold.
        # ! BLA BLA BLA
        Returned string could then be placed onto a prompt.
        '''
        ...



# CONCRETE IMPLEMENTATIONS

class DefaultTextModel(TextModelInterface):

    def _message_to_string(self, prev_message: Message | None, current_message: Message) -> str:
        if prev_message is None: return f"\n({current_message.date.split('.')[0]}) {current_message.author}:\n{current_message.content}\n"

        if current_message.content == "": current_message.content = "[attachment]"

        if len(prev_message.date)    == 19:    prev_message.date += ".000000"
        if len(current_message.date) == 19: current_message.date += ".000000"

        prev_date    = datetime.datetime.strptime(   prev_message.date, '%Y-%m-%d %H:%M:%S.%f')
        current_date = datetime.datetime.strptime(current_message.date, '%Y-%m-%d %H:%M:%S.%f')  
        if current_message.author == prev_message.author and abs( current_date - prev_date ).total_seconds() < 5 * 60:    
            return current_message.content + '\n'
        else:                                           
            return f"\n({current_message.date.split('.')[0]}) {current_message.author}:\n{current_message.content}\n"


    def _tokens_from_message(self, prev_message: Message | None, current_message: Message) -> int:
        return tokens_from_string(self._message_to_string(prev_message, current_message))


    def tokens_from_messages(self, messages: list[Message]):
        info = {
            "total" : 0,
            "each"  : []
        }

        prev_message = None
        for message in messages:
            next_tokens = self._tokens_from_message(prev_message, message)
            info["total"] += next_tokens
            info["each"].append(next_tokens) 
            prev_message   = message

        return info
    

    # def _tokens_from_message(self, prev_message: Message | None, message: Message):
    #     return tokens_from_string(self._message_to_string(prev_message, message))



    def _process_messages(self, messages: list[Message]) -> GeneratedConversation: 
        string = ""
        prev_message: Message | None = None
        for message in messages:
            string += self._message_to_string(prev_message, message)
            prev_message = message
        return GeneratedConversation(string, tokens_from_string(string) if len(messages) else 0, messages)



    def conversation_crafter_oldest_to_newest(self, messages: list[Message], max_tokens: int) -> GeneratedConversation:
        '''
        Crafts a string representation of a chain of messages which complies with being inside the token threshold.
        Returned string could then be placed onto a prompt.
        '''

        string      : str = ""
        total_tokens: int = 0
        amount      : int = 0
        prev_message = None
        for message in messages:
            next        = self._message_to_string(prev_message, message)
            next_tokens = tokens_from_string(next)
            if total_tokens + next_tokens > max_tokens: break
            total_tokens += next_tokens
            string += next
            prev_message = message
            amount += 1

        return GeneratedConversation(string, total_tokens, messages[:amount])


    def conversation_crafter_newest_to_oldest(self, messages: list[Message], max_tokens: int) -> GeneratedConversation:
        '''
        Crafts a string representation of a chain of messages which complies with being inside the token threshold.
        Returned string could then be placed onto a prompt.
        '''

        strings     : list[str] = []
        tokens      : list[int] = []
        total_tokens: int = 0
        amount      : int = 0

        for i in range(len(messages) - 1, -1, -1):
            next        = self._message_to_string(messages[i - 1] if not i == 0 else None, messages[i])
            next_tokens = tokens_from_string(next)
            total_tokens += next_tokens
            tokens.append(next_tokens)
            strings.append(next)
            
            if total_tokens > max_tokens:
                while total_tokens > max_tokens:
                    total_tokens -= tokens.pop()
                    strings.pop()
                    if i == len(messages) - 1: break
                    next          = self._message_to_string(None, messages[i+1])
                    next_tokens   = tokens_from_string(next)
                    total_tokens -= tokens.pop()
                    strings.pop()
                    total_tokens += next_tokens
                    tokens.append(next_tokens)
                    strings.append(next)
                break

        return GeneratedConversation(''.join(strings), total_tokens, messages[len(messages)-len(strings):])


    def conversation_crafter_center_to_ends(self, messages: list[Message], max_tokens: int) -> GeneratedConversation:
        '''
        Crafts a string representation of a chain of messages which complies with being inside the token threshold.
        This functions starts adding messages from the center of the 
        Returned string could then be placed onto a prompt.
        '''
        if len(messages) == 0: return GeneratedConversation("", 0, [])

        string      : str = ""
        total_tokens: int = 0
        
        result = self.tokens_from_messages(messages)

        switch = True
        section = [0, len(messages) - 1]
        while result["total"] > max_tokens:
            if switch:
                result["total"] -= result["each"][section[0]]
                section[0]      += 1
                switch           = False
            else:
                result["total"] -= result["each"][section[1]]
                section[1]      -= 1
                switch           = True

        result["total"] -= result["each"][section[0]]
        tokens = self._tokens_from_message(None, messages[section[0]])
        result["total"] += tokens

        while result["total"] > max_tokens:
            if switch:
                result["total"] -= result["each"][section[0]]
                section[0]      += 1
                switch           = False
            else:
                result["total"] -= result["each"][section[1]]
                section[1]      -= 1
                switch           = True

        prev_message = None
        for message in messages[section[0]:section[1]+1]:
            next        = self._message_to_string(prev_message, message)
            next_tokens = tokens_from_string(next)
            total_tokens += next_tokens
            string += next
            prev_message = message

        return GeneratedConversation(string, total_tokens, messages[section[0]:section[1]+1])



def prompt_crafter(long_term_memory: list[list[Message]], short_term_memory: list[Message], token_ratio: float, textModel: TextModelInterface) -> str:
    '''
    Craft a prompt containing long-term memory and short-term memory.
    '''
    assert token_ratio >= 0 and token_ratio <= 1

    SPINE_TOKENS = 634 #! TODO:
    max_tokens_for_crafter = MAX_TOKENS - 500 - SPINE_TOKENS
    max_stm_tokens = int(max_tokens_for_crafter*(1-token_ratio))

    ltm: str = ""
    stm: str = ""
    ltm_tokens_per_memory: int = int(max_tokens_for_crafter*token_ratio / len(long_term_memory))
    ltm_tokens: int = 0
    stm_tokens: int = 0

    i = 1
    for memory in long_term_memory:
        ltm_snippet  = textModel.conversation_crafter_center_to_ends(memory, ltm_tokens_per_memory).string
        ltm         += f"MEMORY {i}{ltm_snippet}\n"
        i           += 1
    
    stm = textModel.conversation_crafter_newest_to_oldest(short_term_memory, max_stm_tokens).string
    # print(short_term_memory, max_stm_tokens)
    # print(tokens_from_string(stm))
    prompt = DEFAULT(ltm.strip(), stm.strip())
    return prompt

    # ltm_tokens = tokens_from_string(ltm)
    # stm_tokens = tokens_from_string(stm)


def DEFAULT(long_term_memory_string, short_term_memory_string):
    '''
    Default prompt for AI.
    Returns the full prompt containing the given long-term memory and short-term memory.
    '''
    with open("prompts/default.txt") as file:
        return file.read().format(long_term_memory_string = long_term_memory_string, short_term_memory_string = short_term_memory_string)