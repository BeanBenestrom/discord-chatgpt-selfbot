import json, time, colorama
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from typing import Any

from utility import create_json_file_if_not_exist

# Replace 'data.json' with the path to your JSON file
json_file_path = 'logs.json'
termination_signal = '123024 TERMINATEjdpsdh 324 99034234 12df *** 11'
run: bool = True


class JsonChangeHandler(FileSystemEventHandler):
    current_index: int = 0
    printing_lock: bool = False
    logs: list[str] = []

    def start_printing(self):
        global run
        if not self.printing_lock:
            self.printing_lock = True
            if self.current_index > len(self.logs): self.current_index = len(self.logs)
            while self.current_index < len(self.logs):
                if self.logs[self.current_index] == termination_signal:
                    run = False
                    return
                print(self.logs[self.current_index])
                self.current_index += 1
            self.printing_lock = False
            

    def on_modified(self, event):  
        if event.src_path == f".\\{json_file_path}":
            try:
                with open(json_file_path, encoding='utf-8') as file:
                    self.logs = json.load(file)
                self.start_printing()
            except Exception as e:
                pass


if __name__ == "__main__":
    colorama.init()
    with open(json_file_path, 'w', encoding='utf-8') as file:
        json.dump([], file, ensure_ascii=False)
    event_handler = JsonChangeHandler()
    observer = Observer()
    observer.schedule(event_handler, path='.', recursive=False)
    observer.start()

    try:
        while run:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    print("--- GAVE UP! ---")
    observer.stop()
    colorama.deinit()
