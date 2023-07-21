import logging, inspect, typing, time, colorama
from enum import Enum
from abc import ABC, abstractmethod
from datetime import datetime

def init():
    colorama.init()

def deinit():
    colorama.deinit()
# logger = logging.getLogger('simple_example')
# logger.setLevel(logging.DEBUG)
# # create file handler which logs even debug messages
# fh = logging.FileHandler('logs.log')
# fh.setLevel(logging.DEBUG)
# # create console handler with a higher log level
# ch = logging.StreamHandler()
# ch.setLevel(logging.INFO)
# # create formatter and add it to the handlers
# formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# ch.setFormatter(formatter)
# fh.setFormatter(formatter)
# # add the handlers to logger
# logger.addHandler(ch)
# logger.addHandler(fh)


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



class LogHanglerInterface():
    loggingLevel: LogType
    identifier: str
    depth: int

    def __init__(self, loggingLevel: LogType=LogType.INFO, identifier: str="", depth: int=0) -> None:
        self.loggingLevel = loggingLevel
        self.identifier = identifier
        self.depth = depth

    @classmethod
    def _newInstance(cls, loggingLevel, identifier, depth) -> 'LogHanglerInterface':
        return cls(loggingLevel, identifier, depth)

    def sub(self) -> 'LogHanglerInterface':
        return self._newInstance(self.loggingLevel, self.identifier, self.depth + 1)

    @abstractmethod
    def log(self, level: LogType, message: str) -> None:
        ...


    
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
        LogType.ERROR       : colorama.Fore.LIGHTRED_EX,
        LogType.CRITICAL    : colorama.Fore.LIGHTRED_EX,
        LogType.OK          : colorama.Fore.LIGHTGREEN_EX
    }

    def log(self, level: LogType, message: str) -> None:
        if self.loggingLevel.value > level.value: return
        lines = message.split('\n')
        info_before_message: str = f"{'    '*self.depth}<{self.identifier}> [{self.LOG_SYMBOLS[level]}] {__name__} - {str(datetime.now().time()).split('.')[0]} - "
        print(f"{self.LOG_COLORS[level]}{info_before_message}{lines[0]}{colorama.Fore.RESET}")
        for line in lines[1:]:
            print(f"{colorama.Fore.LIGHTBLACK_EX}{' '*len(info_before_message)}{line}{colorama.Fore.RESET}")



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
        log.log(LogType.DEBUG, "func2, debug, Hello!")
        for i in range(5):
            print("WORKING...")
            time.sleep(1)
        log.log(LogType.WARNING, "There might be a problem with the next function...")
        func3(log.sub())
        

    def func3(log: LogHanglerInterface=LogNothing()):
        log.log(LogType.ERROR, "Failed to compute!")


    func1("Bob1", "Freeman", LogStdcout(LogType.INFO, "12345"))
    # func1("Bob2", "Freeman", LogStdcout())
    # func1("Bob3", "Freeman")
    # func2("Sassy1", "Sal", None)
    # func2("Sassy2", "Sal", "Suss")
    # func3("Sassy3", "Sal")
    