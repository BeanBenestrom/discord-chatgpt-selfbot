import os, json, socket, pickle, threading, datetime, asyncio, multiprocessing, subprocess, re
from colorama import Fore
from queue import Queue
from typing import Callable, Any, TypeVar, Generic, Coroutine
from enum import Enum
from dataclasses import dataclass

from prompt_toolkit.application import get_app
from prompt_toolkit import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.formatted_text import HTML, FormattedText, to_formatted_text
from prompt_toolkit.layout.containers import HSplit, VSplit, Window, HorizontalAlign, WindowAlign
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.scrollable_pane import ScrollablePane
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.widgets import TextArea, Box, Frame, Button
from prompt_toolkit.styles import Style

from interface import ConversationInterface
from structure import Message
from utility import create_json_file_if_not_exist
from conversation import ComplexMemoryConversation
from memory import VirtualComplexMemory
from vector_database import connect_to_database, disconnect_from_database, CollectionType
from delay import NaturalDelay

import app, configuration, bot
from app import TerminalText
from debug import LogHanglerInterface, LogStdcout, LogType, LogJsonFile
from prompt import DefaultTextModel


USERNAME = ""
VIRTUAL_CONVERSATION: ConversationInterface | None = None
virtual_conversation_messages: list[Message] = []
virtual_user_alias = ""
textModel = DefaultTextModel()


class Page(Enum):
    MAIN  = "Main",
    VIRTUAL = "Virtual"



EXIT = False
PAGE: Page = Page.MAIN


async def _async_func():
    pass

G = TypeVar("G")
@dataclass(frozen=True)
class AllocatorResult(Generic[G]):
    success: bool
    result : G


T = TypeVar("T")

class Allocator():
    deallocators: list[Callable[[], Any]]
    working: bool
    lock: bool

    def __init__(self) -> None:
        self.deallocators = []
        self.working = False
        self.lock = False

    async def allocate(self, allocator: Callable[[], Coroutine[Any, Any, T]], deallocator: Callable[[], Any]) -> AllocatorResult[T | None]:
        if not self.lock:
            self.working = True
            try:
                result = await allocator()
                success = True
            except Exception as e:
                log_terminal.append(f"Failed to run allocator!\n{e}", "error")
                result = None
                success = False
            # log_terminal.append(f"Allocator - {success}, {result}")
            self.deallocators.append(deallocator)
            self.working = False
            return AllocatorResult(success, result)
        else:
            log_terminal.append(f"Allocator is locked!", "error")
            return AllocatorResult(False, None)

    async def deallocate(self) -> None:
        for deallocator in self.deallocators[:]:
            try:
                await deallocator()
            except Exception as e:
                log_terminal.append(f"Failed to run deallocator!\n{e}", "error")
            self.deallocators.remove(deallocator)
        log_terminal.append(f"CLEANED UP", "ok")

    def empty(self) -> bool:
        return len(self.deallocators) == 0



log_terminal = TerminalText(spacing=1)
text_terminal = TerminalText()

input_field = TextArea(height=1, style="class:input-field", multiline=False)
input_prompt = FormattedTextControl('> ')

left_window = Window(content=text_terminal.target, ignore_content_width=True, wrap_lines=True)
right_window = Window(content=log_terminal.target, ignore_content_width=True, wrap_lines=True)
input_window = Window(content=input_prompt, dont_extend_width=True)

hsplit = HSplit([
            left_window,
            VSplit([input_window, input_field])], padding_char='-', padding=1, padding_style='#ffffff')

layout = Layout(
    VSplit([
        hsplit,
        right_window], 
    padding_char='|', padding=1, padding_style='#ffffff'))


# BINDINGS

bindings = KeyBindings()

# @bindings.add('i')
# def _(event):
#     get_app().layout.focus(input_field)

# @bindings.add('t')
# def _(event):
#     get_app().layout.focus(left_window)

# @bindings.add('l')
# def _(event):
#     get_app().layout.focus(right_window)

@bindings.add("escape", 'q')  # Use Ctrl + Q to quit the application
async def _(event):
    await cleanup()


style = Style(
    [
        ("header", "fg:#ffffff bold"),
        ("focus", "fg:#ffffff"),
        ("deselected", "fg:#404040"),
        ("error", "fg:#ff0000"),
        ("ok", "fg:#00ff00"),
        ("output-field", ""),
        ("input-field", "fg:#40ff40"),
        ("line", "fg:#ffffff"),
        ('cursor', 'reverse'),
    ]
)


allocator: Allocator = Allocator()
_app = Application(layout=layout, full_screen=True, key_bindings=bindings, style=style, mouse_support=True)


async def handle_input(text):
    global PAGE, VIRTUAL_CONVERSATION, virtual_conversation_messages, virtual_user_alias
    try:
        if PAGE == Page.MAIN:
            # Get input
            log_terminal.append(text, "header")
            parts = text.strip().lower().split(' ')
            command = parts[0]

            if command == "r":
                await bot.reload()
                app.print_channels(text_terminal)
                return
            
            number = int(parts[1])

            if command == "clst":
                text_terminal.remove_lines(number)   
                return
            elif command == "clsl":
                log_terminal.remove_lines(number)
                return

            id = int(parts[1])
            if not configuration.is_channel_real(id):
                log_terminal.append("Invalid channel", 'error')
                return

            if command == "v":
                
                # START CONVERSATION
                VIRTUAL_CONVERSATION = ComplexMemoryConversation(
                    id,
                    await VirtualComplexMemory.create(id, 1500, CollectionType.MAIN, LogJsonFile(LogType.DEBUG, "addMemory_VIRTUAL")),
                    NaturalDelay(),
                    log=LogJsonFile(LogType.DEBUG, "initializeVIRTUAL")
                    )
                alias = configuration.get_channel_alias(id)
                virtual_user_alias = "UNKNOWN" if alias == "" else alias
                text_terminal.clear()
                PAGE = Page.VIRTUAL

            elif command == "b":
                configuration.toggle_blacklist_channel(id)
                app.print_channels(text_terminal)

        #? -------------------------------------------------------------

        elif PAGE == Page.VIRTUAL:
            text = text.strip()
            if text == "@quit":

                # STOP CONVERSATION
                VIRTUAL_CONVERSATION = None
                virtual_conversation_messages = []
                virtual_user_alias = ""
                app.print_channels(text_terminal)
                PAGE = Page.MAIN
                return
            
            parts = text.split(' ')

            if parts[0] == "@clst":
                number = int(parts[1])
                text_terminal.remove_lines(number)   
                return
            elif parts[0] == "@clsl":
                number = int(parts[1])
                log_terminal.remove_lines(number)
                return
            elif isinstance(VIRTUAL_CONVERSATION, ConversationInterface):
                # TELL AI STUFF
                async def respond(string: str) -> None:
                    if isinstance(VIRTUAL_CONVERSATION, ConversationInterface):
                        writing_delay: float = 18/84 / 5*len(string.strip())
                        await asyncio.sleep(writing_delay)                                          # Writing delay

                        bot_message = Message.message_with_current_date(-2, USERNAME, string)
                        text_terminal.append_no_newline(await textModel._message_to_string(virtual_conversation_messages[-1] if len(virtual_conversation_messages) else None, 
                                                                                bot_message))
                        virtual_conversation_messages.append(bot_message)

                        asyncio.create_task(VIRTUAL_CONVERSATION.add_message(
                            Message.message_with_current_date(-2, USERNAME, string),
                            True, 
                            log=LogJsonFile(LogType.DEBUG, "addMessage_VIRTUAL")))
                        
                admin_message = Message.message_with_current_date(-1, virtual_user_alias, text)
                text_terminal.append_no_newline(
                    await textModel._message_to_string(virtual_conversation_messages[-1] if len(virtual_conversation_messages) else None, admin_message))
                virtual_conversation_messages.append(admin_message)

                asyncio.create_task(VIRTUAL_CONVERSATION.add_message(
                    Message.message_with_current_date(-1, virtual_user_alias, text), 
                    False, 
                    log=LogJsonFile(LogType.DEBUG, "addMessage_VIRTUAL")))
                asyncio.create_task(VIRTUAL_CONVERSATION.communicate(respond, log=LogJsonFile(LogType.DEBUG, "comunicate_VIRTUAL")))

    except Exception as e:
        log_terminal.append(f"Invalid input\n{e}", "error")



def accept(buff):
    global PAGE, VIRTUAL_CONVERSATION, virtual_conversation_messages, virtual_user_alias
    if EXIT: _app.exit()
    else:
        loop = asyncio.get_event_loop()
        loop.create_task(handle_input(buff.text))


input_given = None

def _accept(buff):
    pass


def accept_private_userName(buff):
    global input_given
    text = buff.text.strip()
    if len(text) < 1:
        log_terminal.append("Invalid username", "error")
        return
    input_field.accept_handler = accept    # type: ignore
    input_given = text

def accept_private_userId(buff):
    global input_given
    text = buff.text.strip()
    try:
        id = int(text)
        input_field.accept_handler = accept    # type: ignore
        input_given = id
    except ValueError as e:
        log_terminal.append("Invalid user id", "error")

def accept_private_token(buff):
    global input_given
    text = buff.text.strip()
    if len(text) < 1:
        log_terminal.append("Invalid token", "error")
        return
    input_field.accept_handler = accept    # type: ignore
    input_given = text

input_field.accept_handler = accept         # type: ignore


async def wait_for_input() -> str:
    global input_given
    input_given = None
    while input_given is None:
        await asyncio.sleep(0.5)
    return input_given


async def start_logging_terminal():
    cmd = f"python debug_terminal.py"
    process = subprocess.Popen(['start', 'cmd', '/k', cmd], shell=True, cwd=os.getcwd())


async def stop_logging_terminal():
    LogJsonFile().send_termination_signal()


async def activate_discord_bot():
    await bot.start(LogJsonFile())


async def setup() -> bool:
    global USERNAME
    create_json_file_if_not_exist("private.json", {})
    with open("private.json", encoding='utf-8') as file:
        data = json.load(file)
        update = False
        if not "userName" in data:
            text_terminal.append("Username missing. Input name...", "header")
            input_field.accept_handler = accept_private_userName   # type: ignore
            userName = await wait_for_input()
            data["userName"] = userName
            update = True
            text_terminal.clear()
        if not "userId" in data:
            text_terminal.append("User id missing. Input id...", "header")
            input_field.accept_handler = accept_private_userId   # type: ignore
            userId = await wait_for_input()
            data["userId"] = userId
            update = True
            text_terminal.clear()
        if not "token" in data:
            text_terminal.append("User token missing. Input token...", "header")
            input_field.accept_handler = accept_private_token   # type: ignore
            token = await wait_for_input()
            data["token"] = token
            update = True
            text_terminal.clear()
        if update:
            with open("private.json", 'w', encoding='utf-8') as w_file:
                json.dump(data, w_file)
    with open("private.json", encoding='utf-8') as file:
        USERNAME = json.load(file)["userName"]

    text_terminal.append("Startup configuration"            , "header")
    text_terminal.append("")
    text_terminal.append("[ ] Connect to vector database"   , "focus")
    text_terminal.append("[ ] Setup logging terminal"       , "deselected")
    text_terminal.append("[ ] Activate discord bot"         , "deselected")

    # Setup vector database
    text_terminal.write(3, "[-] Connecting to vector database...", "focus")
    if not (await allocator.allocate(connect_to_database, disconnect_from_database)).success:
        text_terminal.write(3, "[!] Failed to connect to vector database!", "error")
        return False
    text_terminal.write(3, "[#] Connected to vector database!", "ok")

    # Setup logging terminal
    text_terminal.write(4, "[-] Seting up logging terminal...", "focus")
    if not (await allocator.allocate(start_logging_terminal, stop_logging_terminal)).success:
        text_terminal.write(4, "[!] Failed setup logging terminal!", "error")
        return False
    text_terminal.write(4, "[#] Logging terminal setup!", "ok")

    # Setup discord bot
    text_terminal.write(5, "[-] Activating discord bot...", "focus")
    if not (await allocator.allocate(activate_discord_bot, bot.stop)).success:
        text_terminal.write(5, "[!] Failed to activate discord bot!", "error")
        return False
    text_terminal.write(5, "[#] Discord bot active!", "ok")
    input_field.accept_handler = accept     # type: ignore
    await asyncio.sleep(1)
    return True


async def cleanup():
    global EXIT
    await allocator.deallocate()
    input_prompt.text = FormattedText([('class:error', "EXIT > ")])
    EXIT = True


async def run():
    global hsplit
    # Setup
    if not await setup(): 
        await cleanup()
        return

    # Developer
    # log_terminal.append("SUCCESS")
    app.print_channels(text_terminal)


async def main():
    asyncio.create_task(run())
    result = await _app.run_async()
    print(result)


if __name__ == "__main__":
    asyncio.run(main())