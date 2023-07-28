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

import configuration


class TerminalText():
    text_elements: list[tuple[str, str]]
    target : FormattedTextControl
    spacing: int

    def __init__(self, spacing: int=0, target: FormattedTextControl | None=None) -> None:
        self.text_elements = []
        self.spacing = spacing+1
        if target is None: self.target = FormattedTextControl()
        else:              self.target = target

    def remove_lines(self, amount: int):
        self.text_elements = self.text_elements[amount:]
        self.target.text = FormattedText(self.text_elements)
        get_app().invalidate()

    def clear(self):
        self.text_elements = []
        self.target.text = FormattedText(self.text_elements)
        get_app().invalidate()

    def write(self, row: int, text: str, cls: str=''):
        text = str(text)+'\n'*self.spacing
        if row > 0:
            while len(self.text_elements) < row:
                self.text_elements.append(('', '\n'*self.spacing))
            self.text_elements[row-1] = (f"class:{cls}", text)
            self.target.text = FormattedText(self.text_elements)
        get_app().invalidate()

    def append(self, text: str, cls: str=''):
        text = str(text)+'\n'*self.spacing
        self.text_elements.append((f"class:{cls}", text))
        self.target.text = FormattedText(self.text_elements)
        get_app().invalidate()

    def append_no_newline(self, text: str, cls: str=''):
        text = str(text)
        self.text_elements.append((f"class:{cls}", text))
        self.target.text = FormattedText(self.text_elements)
        get_app().invalidate()


def print_channels(terminal: TerminalText) -> None:
    config: configuration.Configuration = configuration.CONFIG

    terminal.clear()
    terminal.append(f"{'alias':30} {'id':18} ")
    for id, channelConfig in config.channels.items():
        terminal.text_elements.append(('', f"{channelConfig.alias[:30]:30} {id:18} "))
        terminal.text_elements.append(('class:error', f"{'blacklisted' if channelConfig.blacklisted else '' }\n"))

    terminal.append("")
    terminal.append("")
    terminal.append("v + [CHANNEL ID]  -  Start a virtual conversation with user", "deseleted")
    terminal.append("b + [CHANNEL ID]  -  Blacklist user", "deseleted")
    terminal.append("")
    terminal.append("alt+q             -  quit program", "deseleted")

    #Update
    terminal.target.text = FormattedText(terminal.text_elements)
    get_app().invalidate()