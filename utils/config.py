from __future__ import annotations

import json
from dataclasses import dataclass

with open(r"config.json", "r") as f:
    config = json.load(f)


class Config:
    def __init__(self, **kwargs):
        self.__kwargs = kwargs
        self.__schema: str | None = None

    @property
    def cogs(self) -> list[str]:
        return [cog["path"] for cog in self.__kwargs["cogs"]]

    @property
    def database_file(self) -> str:
        return self.__kwargs["database_file"]

    @property
    def datbase_schema(self) -> str:
        if self.__schema is None:
            with open(self.__kwargs["database_schema"], "r") as f:
                self.__schema = f.read()
        return self.__schema

    @dataclass
    class Lavalink:
        host: str
        port: int
        password: str

    @property
    def lavalink(self) -> Lavalink:
        return Config.Lavalink(**self.__kwargs["lavalink"])

    @property
    def default_prefixes(self) -> list[str]:
        return self.__kwargs["default_prefixes"]


CONFIG = Config(**config)
