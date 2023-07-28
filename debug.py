import logging, inspect, typing, time, colorama, json, subprocess, os
import multiprocessing as mp
from enum import Enum
from abc import ABC, abstractmethod
from datetime import datetime
from debug_terminal import json_file_path as debug_terminal_json_file_path
from debug_terminal import termination_signal as debug_terminal_termination_signal
from utility import create_json_file_if_not_exist

# def init():
#     colorama.init()

# def deinit():
#     colorama.deinit()
logger = logging.getLogger('simple_example')
logger.setLevel(logging.DEBUG)
# create file handler which logs even debug messages
fh = logging.FileHandler('logs/logs.log', encoding='utf-8')
fh.setLevel(logging.DEBUG)
# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
# create formatter and add it to the handlers
formatter = logging.Formatter('%(message)s')
ch.setFormatter(formatter)
fh.setFormatter(formatter)
# add the handlers to logger
# logger.addHandler(ch)
logger.addHandler(fh)
LOGGED = False

class LogType(Enum):
    DEBUG      = 0
    INFO       = 1
    WARNING    = 2
    ERROR      = 3
    CRITICAL   = 4
    OK         = 5



# def log(func):
#     def wrapper(*args, **kwargs):

#         print(inspect.get_annotations(func))

#         # if "log" in kwargs:
#         #     kwargs["log"] = kwargs["log"].sub()
#         # else:
#         #     kwargs["log"] = LogNothing()
#         # print(args, kwargs)
#         # return func(*args, **kwargs)
#     return wrapper



class LogHanglerInterface(ABC):
    loggingLevel: LogType
    identifier: str
    depth: int
    first_line_printed: bool

    def __init__(self, loggingLevel: LogType=LogType.INFO, identifier: str="", depth: int=0) -> None:
        global LOGGED
        if not LOGGED: logger.log(logging.INFO, f"\n{'-'*100}\n\nRan: {datetime.now()}\n{'-'*100}\n")
        LOGGED = True
        self.loggingLevel = loggingLevel
        self.identifier = identifier
        self.depth = depth
        self.first_line_printed = False

    @classmethod
    def _newInstance(cls, loggingLevel, identifier, depth) -> 'LogHanglerInterface':
        return cls(loggingLevel, identifier, depth)

    def sub(self, identifier: str | None = None) -> 'LogHanglerInterface':
        return self._newInstance(self.loggingLevel, self.identifier if not identifier else identifier, self.depth + 1)

    @abstractmethod
    def log(self, level: LogType, message: str) -> None:
        ...


LAST_IDENTIFIER_PRINTED_STDCOUT = ""
    
class LogStdcout(LogHanglerInterface):

    LOG_SYMBOLS: dict = {
        LogType.DEBUG       : '.',
        LogType.INFO        : '&',
        LogType.WARNING     : '*',
        LogType.ERROR       : '!',
        LogType.CRITICAL    : '!!',
        LogType.OK          : '#'
    }

    LOG_COLORS: dict = {
        LogType.DEBUG       : colorama.Fore.LIGHTCYAN_EX,
        LogType.INFO        : colorama.Fore.LIGHTWHITE_EX,
        LogType.WARNING     : colorama.Fore.LIGHTYELLOW_EX,
        LogType.ERROR       : colorama.Fore.RED,
        LogType.CRITICAL    : colorama.Fore.RED,
        LogType.OK          : colorama.Fore.LIGHTGREEN_EX
    }

    INDENTATION = "   o "


    def log(self, level: LogType, message: str) -> None:
        global LAST_IDENTIFIER_PRINTED_STDCOUT
        if self.loggingLevel.value > level.value: return

        lines = message.split('\n')

        # Information about caller
        caller_frame = inspect.currentframe().f_back                                        # type: ignore
        file_name = caller_frame.f_code.co_filename.split("Discord Selfbot\\")[1]           # type: ignore
        function_name = caller_frame.f_code.co_name                                         # type: ignore

        # Elements
        e_date          : str = str(datetime.now().time()).split('.')[0]
        e_id            : str = f"<{self.identifier}>"
        e_indentation   : str = self.INDENTATION * self.depth
        e_path          : str = f"{file_name}  {function_name}"
        e_symbol        : str = f"[{self.LOG_SYMBOLS[level]}]"

        # Color
        c_date              = colorama.Fore.LIGHTBLACK_EX
        c_id                = colorama.Fore.MAGENTA
        c_indentation       = colorama.Fore.LIGHTBLACK_EX
        c_path              = colorama.Fore.MAGENTA
        c_extra_data        = colorama.Fore.LIGHTBLACK_EX
      # c_extra_indentation = colorama.Fore.LIGHTBLACK_EX
        c_base              = self.LOG_COLORS[level]

        # Elements with color
        p_date          : str = f"{c_date       }{e_date       }"
        p_id            : str = f"{c_id         }{e_id         }"
        p_indentation   : str = f"{c_indentation}{e_indentation}"
        p_path          : str = f"{c_path       }{e_path       }"
        p_symbol        : str = f"{c_base       }{e_symbol     }"

        space = lambda string: ' '*len(string)
        
        # print(callers_path_identifier, callers_parent_path_identifier)
        
        # Log function name
        if not self.first_line_printed or LAST_IDENTIFIER_PRINTED_STDCOUT != self.identifier:
            print(f"{space(e_date)} {p_id if LAST_IDENTIFIER_PRINTED_STDCOUT != self.identifier else space(e_id)} {p_indentation} {p_path}")
            logger.log(logging.INFO, f"{space(e_date)} {e_id if LAST_IDENTIFIER_PRINTED_STDCOUT != self.identifier else space(e_id)} {e_indentation} {e_path}")      
            self.first_line_printed = True

        # Log main line
        print(f"{p_date} {space(e_id)} {p_indentation}{self.INDENTATION} {p_symbol} {c_base}{lines[0]}{colorama.Fore.RESET}")
        logger.log(logging.INFO, f"{e_date} {space(e_id)} {e_indentation}{self.INDENTATION} {e_symbol} {lines[0]}")

        # Log extra lines
        for line in lines[1:]:
            print(f"{space(f'{e_date} {space(e_id)}')} {p_indentation}{self.INDENTATION} {space(e_symbol)} {c_extra_data}{line}{colorama.Fore.RESET}")
            logger.log(logging.INFO, f"{space(f'{e_date} {space(e_id)}')} {e_indentation}{self.INDENTATION} {space(e_symbol)} {line}")

        LAST_IDENTIFIER_PRINTED_STDCOUT = self.identifier



class LogJsonFile(LogHanglerInterface):

    LOG_SYMBOLS: dict = {
        LogType.DEBUG       : '.',
        LogType.INFO        : '&',
        LogType.WARNING     : '*',
        LogType.ERROR       : '!',
        LogType.CRITICAL    : '!!',
        LogType.OK          : '#'
    }

    LOG_COLORS: dict = {
        LogType.DEBUG       : colorama.Fore.LIGHTCYAN_EX,
        LogType.INFO        : colorama.Fore.LIGHTWHITE_EX,
        LogType.WARNING     : colorama.Fore.LIGHTYELLOW_EX,
        LogType.ERROR       : colorama.Fore.RED,
        LogType.CRITICAL    : colorama.Fore.RED,
        LogType.OK          : colorama.Fore.LIGHTGREEN_EX
    }

    INDENTATION = "   o "

    def __init__(self, loggingLevel: LogType = LogType.INFO, identifier: str = "", depth: int = 0) -> None:
        create_json_file_if_not_exist(debug_terminal_json_file_path, [])
        super().__init__(loggingLevel, identifier, depth)


    def send_termination_signal(self):
        json_data: list

        with open(debug_terminal_json_file_path, encoding='utf-8') as file:
            json_data = json.load(file)

        json_data.append(debug_terminal_termination_signal)

        with open(debug_terminal_json_file_path, 'w', encoding='utf-8') as file:
            json.dump(json_data, file, ensure_ascii=False)


    def log(self, level: LogType, message: str) -> None:
        global LAST_IDENTIFIER_PRINTED_STDCOUT
        if self.loggingLevel.value > level.value: return

        lines = message.split('\n')

        # Information about caller
        caller_frame = inspect.currentframe().f_back                                        # type: ignore
        file_name = caller_frame.f_code.co_filename.split("Discord Selfbot\\")[1]           # type: ignore
        function_name = caller_frame.f_code.co_name                                         # type: ignore

        # Elements
        e_date          : str = str(datetime.now().time()).split('.')[0]
        e_id            : str = f"<{self.identifier}>".ljust(20)
        e_indentation   : str = self.INDENTATION * self.depth
        e_path          : str = f"{file_name}  {function_name}"
        e_symbol        : str = f"[{self.LOG_SYMBOLS[level]}]"

        # Color
        c_date              = colorama.Fore.LIGHTBLACK_EX
        c_id                = colorama.Fore.MAGENTA
        c_indentation       = colorama.Fore.LIGHTBLACK_EX
        c_path              = colorama.Fore.MAGENTA
        c_extra_data        = colorama.Fore.LIGHTBLACK_EX
      # c_extra_indentation = colorama.Fore.LIGHTBLACK_EX
        c_base              = self.LOG_COLORS[level]

        # Elements with color
        p_date          : str = f"{c_date       }{e_date       }"
        p_id            : str = f"{c_id         }{e_id         }"
        p_indentation   : str = f"{c_indentation}{e_indentation}"
        p_path          : str = f"{c_path       }{e_path       }"
        p_symbol        : str = f"{c_base       }{e_symbol     }"

        space = lambda string: ' '*len(string)

        json_data: list

        with open(debug_terminal_json_file_path, encoding='utf-8') as file:
            json_data = json.load(file)

            if not self.first_line_printed or LAST_IDENTIFIER_PRINTED_STDCOUT != self.identifier:
                json_data.append(f"{space(e_date)} {p_id if LAST_IDENTIFIER_PRINTED_STDCOUT != self.identifier else space(e_id)} {p_indentation} {p_path}")
                logger.log(logging.INFO, f"{space(e_date)} {e_id if LAST_IDENTIFIER_PRINTED_STDCOUT != self.identifier else space(e_id)} {e_indentation} {e_path}") 
                self.first_line_printed = True

            # Log main line
            json_data.append(f"{p_date} {space(e_id)} {p_indentation}{self.INDENTATION} {p_symbol} {c_base}{lines[0]}{colorama.Fore.RESET}")
            logger.log(logging.INFO, f"{e_date} {space(e_id)} {e_indentation}{self.INDENTATION} {e_symbol} {lines[0]}")

            # Log extra lines
            for line in lines[1:]:
                json_data.append(f"{space(f'{e_date} {space(e_id)}')} {p_indentation}{self.INDENTATION} {space(e_symbol)} {c_extra_data}{line}{colorama.Fore.RESET}")
                logger.log(logging.INFO, f"{space(f'{e_date} {space(e_id)}')} {e_indentation}{self.INDENTATION} {space(e_symbol)} {line}")

        with open(debug_terminal_json_file_path, 'w', encoding='utf-8') as file:
            json.dump(json_data, file, ensure_ascii=False)

        LAST_IDENTIFIER_PRINTED_STDCOUT = self.identifier




class LogNothing(LogHanglerInterface):
    def log(self, level: LogType, message: str) -> None:
        pass
    



if __name__ == "__main__":
    # Testing

    def func1(name: str, message: str, log: LogHanglerInterface=LogNothing()):
        log.log(LogType.INFO, f"Started func1...\nname   : {name}\nmessage: {message}")
        time.sleep(1)
        log.log(LogType.INFO, "Starting subprocess")
        func2(log.sub())
        log.log(LogType.OK, "func1 completed")
        log.log(LogType.CRITICAL, "CRITICAL ERROR OCCURED\nMight be a because of you...")


    def func2(log: LogHanglerInterface=LogNothing()):
        # log.log(LogType.DEBUG, "func2, debug, Hello!")
        for i in range(2):
            # print("WORKING...")
            time.sleep(1)
        # log.log(LogType.WARNING, "There might be a problem with the next function...")
        func3(log.sub())
        

    def func3(log: LogHanglerInterface=LogNothing()):
        log.log(LogType.INFO, "Text 1")
        log.log(LogType.INFO, "Text 2")
        log.log(LogType.ERROR, "Failed to compute!")


    cmd = f"python debug_terminal.py"
    process = subprocess.Popen(['start', 'cmd', '/k', cmd], shell=True, cwd=os.getcwd())


    log = LogJsonFile(LogType.INFO, "x_206346498103464981")
    func1("Bob1", "Freeman", log)

    time.sleep(4)

    log.send_termination_signal()

    # print((f"Created JSON object:\n"
    #                             f"id: {0}\n"
    #                             f"file path: {1}\n"
    #                             f"oldest memory: {2}\n"
    #                             f"newest memory: {3}"))
    # func1("Bob2", "Freeman", LogStdcout())
    # func1("Bob3", "Freeman")
    # func2("Sassy1", "Sal", None)
    # func2("Sassy2", "Sal", "Suss")
    # func3("Sassy3", "Sal")
    