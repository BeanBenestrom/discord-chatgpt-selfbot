import os, json, socket, pickle, time, threading
from colorama import Fore
from structure import dev_json
from queue import Queue

from conversation import ComplexMemoryConversation
from memory import VirtualComplexMemory
from delay import NaturalDelay
from vector_database import CollectionType

FILE = "dev.json"
_send = Queue()
_received = {}


def send(id: int, command: str, args: list):
    _send.put([id, [ command, args ]])


def receive(id: int, timeout: int=0):
    start_time = time.time()
    if timeout == 0:
        while not str(id) in _received:
            time.sleep(0.1)
    else:
        while not str(id) in _received and time.time() - start_time < timeout:
            time.sleep(0.1)
    if str(id) in _received:
        value = _received[str(id)]
        del _received[str(id)]
        return value



if (not os.path.isfile(FILE) or os.path.getsize(FILE) == 0):
    with open(FILE, 'w', encoding="utf-8") as file:
        json.dump(dev_json, file, ensure_ascii=False)


maxTries = 5
maxSize = 10
headerSize = 7
bufferSize = 500
maxheaderSize = pow(10, headerSize-2)
run_server = True


def recv(conn):
    global run_server
    res = conn.recv(headerSize)
    if not res:
        return
    length = int(res)
    data = bytes("", "utf-8")
    while run_server:
        if len(data)+bufferSize < length: 
            data += conn.recv(bufferSize)
        else:
            data += conn.recv(length - len(data))
        if len(data) >= length: 
            break
    return data


def socket_communication(conn):
    global run_server
    try:
        while run_server:
            while _send.empty() and run_server:
                time.sleep(0.1)
            if not run_server: break
            command = _send.get()
            data = pickle.dumps(command[1])
            conn.send(bytes(f"{len(data):<{headerSize}}", "utf-8") + data)
            # print("SENT")
            res = recv(conn)
            if not res: 
                print("EXITSSS")
                break
            response = pickle.loads(res)
            _received[str(command[0])] = response
    except Exception as e:
        print(f"\n{Fore.RED}ERROR: {e}{Fore.RESET}")


def print_main_menu():
    with open(FILE) as r_file:
        dev_json: dict = json.load(r_file)
        print()
        print(f"{Fore.BLUE}CHANNELS{Fore.RESET}")
        print(f"   {Fore.LIGHTBLACK_EX}{'alias'.ljust(30)}  {'channel id'.ljust(18)}{Fore.RESET}")
        i = 1
        keys = [None, ]
        for key, value in dev_json["channels"].items():
            alias = value['alias'][:30]
            line = f"{alias.ljust(30)}  {key.ljust(18)}"
            print(f"{i}. {f'{Fore.RED}{line}   blacklisted{Fore.RESET}' if value['blacklisted'] else f'{Fore.WHITE}{line}{Fore.RESET}'}")
            keys.append(key)
            i += 1
        print()
        print(f"{Fore.BLUE}COMMANDS{Fore.RESET}")
        print("blacklist [CHANNEL ID]    b [CHANNEL ID]")
        print("virtual [CHANNEL ID]      v [CHANNEL ID]")
        print("quit                      q")
        print()


def blacklist_channel(id):
    dev_json: dict
    try:
        with open(FILE) as r_file:
            dev_json: dict = json.load(r_file)
        dev_json["channels"][str(id)]["blacklisted"] = not dev_json["channels"][str(id)]["blacklisted"]
        with open(FILE, 'w') as w_file:
            json.dump(dev_json, w_file)
    except Exception as e:
        print(f"{Fore.RED}Failed to blacklist channel{Fore.RESET}")



def virtual_conversation(id):
    try:
        send(1, "CREATE_VIRTUAL_CONVERSATION", [id])
        if not receive(1): raise Exception("")

        print("VIRTUAL CONVERSATION")
        while True:
            user_message = input("> ")
            if user_message == "quit" or user_message == 'q': break
            print(user_message)
            send(1, "SEND_VIRTUAL_MESSAGE", [id, user_message])
            bot_message = receive(1)
            if not bot_message: raise Exception("")
            print(bot_message)

        send(1, "REMOVE_VIRTUAL_CONVERSATION", [id])
        if not receive(1): raise Exception("")

    except Exception as e:
        print(f"{Fore.RED}Virtual conversation failure{Fore.RESET}")



def main():
    global run_server

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((socket.gethostbyname(socket.gethostname()), 54543))
    server.listen(1)
    conn, address = server.accept()

    thread = threading.Thread(target=socket_communication, args=(conn, ))
    thread.start()

    while True:
        print_main_menu()
        res = input("> ").lower()
        args = res.split(' ')
        if len(args) > 2: continue

        try:
            if   args[0] == "quit"      or args[0] == 'q': break
            elif args[0] == "blacklist" or args[0] == 'b': blacklist_channel(args[1])
            elif args[0] == "virtual"   or args[0] == 'v': virtual_conversation(args[1])
        except Exception as e:
            print(f"{Fore.RED}Invalid command{Fore.RESET}")

    run_server = False
    conn.close()
    server.close()

if __name__ == "__main__":
    main()
