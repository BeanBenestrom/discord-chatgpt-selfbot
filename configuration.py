import os, json, asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from structure import channelConfiguration
from utility import create_json_file_if_not_exist

NAME = "configuration"
CONFIG: Any = None

@dataclass
class Configuration:
    channels: dict[str, channelConfiguration] = field(default_factory=dict)

    def from_json(self, json: dict) -> None:
        for id, value in json["channels"].items():
            self.channels[id] = channelConfiguration()
            self.channels[id].from_json(value)
            # print(self.channels[id])

    def to_json(self) -> dict[str, Any]:
        channelsJson = {}
        for id, value in self.channels.items():
            channelsJson[id] = value.to_json()
        return { 
            "channels": channelsJson
        }



def create_configuration_if_new() -> bool:
    return create_json_file_if_not_exist(f"{NAME}.json", Configuration().to_json())


def load():
    create_configuration_if_new()
    with open(f"{NAME}.json", encoding='utf-8') as file:
        CONFIG.from_json(json.load(file))

def save():
    with open(f"{NAME}.json", 'w', encoding="utf-8") as file:
        json.dump(CONFIG.to_json(), file, ensure_ascii=False)


# COMMANDS

def add_channel(channelId: int, channelConfig: channelConfiguration):
    CONFIG.channels[str(channelId)] = channelConfig
    save()


def toggle_blacklist_channel(channelId: int):
    if str(channelId) in CONFIG.channels:
        CONFIG.channels[str(channelId)].blacklisted = not CONFIG.channels[str(channelId)].blacklisted
        save()


def is_blacklist_channel(channelId: int):
    if str(channelId) in CONFIG.channels and CONFIG.channels[str(channelId)].blacklisted:
        return True
    return False


def is_channel_real(channelId: int):
    if str(channelId) in CONFIG.channels:
        return True
    return False


def get_channel_alias(channelId: int):
    if str(channelId) in CONFIG.channels:
        return CONFIG.channels[str(channelId)].alias
    return ""



if CONFIG is None:
    CONFIG = Configuration()
    load()



if __name__ == "__main__":

    async def main():
        load()
        add_channel(1, channelConfiguration("Bobk"))
        add_channel(2, channelConfiguration("dasdasdasdasdsadsd BAKA", blacklisted=True))
        save()
    

    asyncio.run(main())