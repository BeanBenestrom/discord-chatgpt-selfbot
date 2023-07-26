import os, json, socket, pickle, threading, datetime, asyncio
from colorama import Fore
from queue import Queue

from prompt_toolkit.application import get_app
from prompt_toolkit import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.formatted_text import HTML, FormattedText, to_formatted_text
from prompt_toolkit.layout.containers import HSplit, VSplit, Window, HorizontalAlign
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.widgets import TextArea, Box, Frame, Button
from prompt_toolkit.styles import Style

from interface import ConversationInterface
from structure import Message
from conversation import ComplexMemoryConversation
from memory import VirtualComplexMemory
from vector_database import connect_to_database, disconnect_from_database, CollectionType
from delay import NaturalDelay

from debug import LogHanglerInterface, LogStdcout, LogType


_commands = Queue()
maxSize = 3
headerSize = 7
bufferSize = 100
run_client = True


# def clear_terminal():
#     os.system('cls' if os.name == 'nt' else 'clear')


# def recv(conn):
#     global run_client
#     res = conn.recv(headerSize)
#     if not res:
#         return
#     length = int(res)
#     data = bytes("", "utf-8")
#     while run_client:
#         if len(data)+bufferSize < length:
#             data += conn.recv(bufferSize)
#         else: 
#             data += conn.recv(length - len(data))
#         if len(data) >= length: 
#             break
#     return data


# def send(conn, data):
#     d = pickle.dumps(data)
#     conn.send(bytes(f"{len(d):<{headerSize}}", "utf-8") + d)


# async def func1(a, b, log: LogHanglerInterface):
#     log.log(LogType.INFO, "FUNC1 - WAITING")
#     await asyncio.sleep(4)
#     log.log(LogType.OK, "FUNC1")

# async def func2(a, b, log: LogHanglerInterface):
#     log.log(LogType.INFO, "FUNC2 - WAITING")
#     await asyncio.sleep(2)
#     log.log(LogType.OK, "FUNC2")
#     return "Hello, World!"


# async def get_user_input():
#     # Use asyncio's event loop to read user input asynchronously
#     loop = asyncio.get_event_loop()
#     user_input = await loop.run_in_executor(None, input, "Enter your input: ")
#     return user_input



# def socket_communication(conn):
#     global run_client

#     while run_client:
#         res = recv(conn)
#         print("res")
#         if not res: 
#             print("EXITSSS")
#             break
#         res = pickle.loads(res)
#         _commands.put(res)


# async def virtual_communicate(conn):
#     log: LogHanglerInterface = LogStdcout(LogType.DEBUG, "VIRTUAL")
#     virtual_conversations = {}

#     while run_client:
        
#         while _commands.empty() and run_client:
#             await asyncio.sleep(0.1)

#         command, args = _commands.get()
        
#         log.log(LogType.INFO, F"DEVELOPER COMMAND\ncommand: {command}\nargs:{args}")

#         try:
#             # DO STUFF
#             if command == "CREATE_VIRTUAL_CONVERSATION": 
#                 channel_id = int(args[0])

#                 # Create vitual conversation
#                 virtual_conversation: ConversationInterface = ComplexMemoryConversation(
#                     channel_id,
#                     VirtualComplexMemory(channel_id, 1500, CollectionType.MAIN, log=log.sub()), 
#                     NaturalDelay(), 
#                     log=log.sub())
#                 virtual_conversations[str(channel_id)] = virtual_conversation

#                 # Send the id of the virtual conversation
#                 send(conn, True)

#             if command == "SEND_VIRTUAL_MESSAGE":
#                 channel_id = int(args[0])
#                 user_message = args[1]

#                 virtual_conversation: ConversationInterface = virtual_conversations[str(channel_id)]
#                 assert(isinstance(virtual_conversation, ConversationInterface))

#                 async def respond(string):
#                     with open("outputs/virtual-conversation.txt", 'w', encoding='utf-8') as file:
#                         file.write(virtual_conversation.current_prompt)
#                     asyncio.create_task(virtual_conversation.add_message(Message(-1, str(datetime.datetime.now()), "BEAN", string), True, log=log.sub()))
#                     send(conn, string)

#                 asyncio.create_task(virtual_conversation.add_message(Message(-1, str(datetime.datetime.now()), "USER", user_message), False, log=log.sub()))
#                 asyncio.create_task(virtual_conversation.communicate(respond, log=log.sub()))        

#             if command == "REMOVE_VIRTUAL_CONVERSATION":
#                 channel_id = int(args[0])
#                 del virtual_conversations[str(channel_id)]
#                 send(conn, True)


#         except Exception as e:
#             log.log(LogType.ERROR, f"Failed to carry out command - {e}")
#             pass
#         finally:
#             pass


text_area = FormattedTextControl()
text_element = []
log_area = FormattedTextControl()


input_field = TextArea(height=1, style="class:input-field", multiline=False)
input_prompt = FormattedTextControl('> ')

content = VSplit([
    HSplit([
        VSplit([
            Window(content=text_area, ignore_content_width=True, wrap_lines=True)]),
        VSplit([Window(content=input_prompt, dont_extend_width=True), input_field])], padding_char='-', padding=1, padding_style='#ffffff'),
    Window(content=log_area, ignore_content_width=True, wrap_lines=True)], padding_char='|', padding=1, padding_style='#ffffff')

def accept(buff):
    pass


layout = Layout(content)


bindings = KeyBindings()

@bindings.add("escape", 'q')  # Use Ctrl + Q to quit the application
def _(event):
    event.app.exit()



style = Style(
    [
        ("header", "fg:#ffffff bold underline"),
        ("error", "fg:#ff0000"),
        ("focus", "fg:#ffffff"),
        ("deselected", "fg:#000000"),
        ("ok", "fg:#00ff00"),
        ("output-field", ""),
        ("input-field", "fg:#40ff40"),
        ("line", "fg:#ffffff"),
    ]
)


app = Application(layout=layout, full_screen=True, key_bindings=bindings, style=style)


def update_text(text, row: int | None=None):
    global text_area, text_element
    if row is None:
        text_element = text
        text_area.text = FormattedText(text_element)
    elif row == 0:
        text_element.append(text)
        text_area.text = FormattedText(text_element)
    elif row > 0:
        while len(text_element) < row:
            text_element.append(('', '\n'))
        text_element[row-1] = text
        text_area.text = FormattedText(text_element)
        log_area.text = text_element        # LOG
        
    app.invalidate()


async def setup() -> bool:
    text = [('class:header', "Startup configuration\n"),
            ('', '\n'),
            ('class:focus', "[-] Connecting to vector database...\n"),
            ('class:deselected', "[ ] Setup logging terminal\n"),
            ('class:deselected', "[ ] Activate discord bot\n")]
    update_text(text)

    # Setup vector database
    update_text(('class:focus', "[-] Connecting to vector database...\n"), 3)
    try:
        await asyncio.sleep(2)
    except Exception as e:
        update_text(('class:error', "[!] Failed to connect to vector database!\n"), 3)
        return False
    update_text(('class:ok', "[#] Connected to vector database!\n"), 3)

    # Setup logging terminal
    update_text(('class:focus', "[-] Seting up logging terminal...\n"), 4)
    try:
        await asyncio.sleep(2)
        1 / 0
    except Exception as e:
        update_text(('class:error', "[!] Failed setup logging terminal!\n"), 4)
        return False
    update_text(('class:ok', "[#] Logging terminal setup!\n"), 4)

    # Setup discord bot
    update_text(('class:focus', "[-] Activating discord bot...\n"), 5)
    try:
        await asyncio.sleep(2)
        1 / 0
    except Exception as e:
        update_text(('class:error', "[!] Failed to activate discord bot!\n"), 5)
        return False
    update_text(('class:ok', "[#] Discord bot active!\n"), 5)
    return True


async def run():

    setup_success: bool = await setup()
    if not setup_success:
        input_prompt.text = FormattedText([('class:error', "EXIT > ")])

    # START VECTOR DATABASE
    # START DISCORD BOT
    # WANT TO START DEV SERVER?
    ...


async def main():
    # global run_client


    asyncio.create_task(run())
    result = await app.run_async()
    print(result)

    # CLEAN UP




    # connect_to_database()
    # conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # conn.connect((socket.gethostbyname(socket.gethostname()), 54543))

    # try:
    #     asyncio.create_task(virtual_communicate(conn))
    #     thread = threading.Thread(target=socket_communication, args=(conn, ))
    #     thread.start()
    #     await get_user_input()
    # except Exception as e:
    #     raise e
    # finally:
    #     run_client = False
    #     conn.close()
    #     disconnect_from_database()

if __name__ == "__main__":
    asyncio.run(main())