from __future__ import annotations

import re
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Concatenate, Literal, ParamSpec, TypeVar

if TYPE_CHECKING:
    from core import Bot

SELECT_REGEX = re.compile(r"(SELECT) ([A-Z_]*) FROM (GUILDS|USERS) WHERE ID = (\?)")
UPDATE_REGEX = re.compile(
    r"""(UPDATE) (GUILDS|USERS) SET ([A-Z_]*) = ([a-zA-Z0-9_'" \?]*) WHERE ID = (\?)"""
)
INSERT_REGEX = re.compile(
    r"""(INSERT) INTO (GUILDS|USERS) \(([A-Z_ (,)?]*)\) VALUES \(([a-zA-Z0-9_'" (,)?\?]*)\)"""
)

SP = ParamSpec("SP")
TR = TypeVar("TR")
TS = TypeVar("TS")


def copy_method_signature(
    f: Callable[Concatenate[Any, SP], Any],
) -> Callable[[Callable[Concatenate[TS, ...], TR]], Callable[Concatenate[TS, SP], TR]]:
    return lambda _: _  # type: ignore[return-value]


class Cache:
    def __init__(self, bot: Bot):
        self.cache: dict[tuple[str, int], Any] = {}
        self.bot = bot

        self.__conn = self.bot.sql

    def __getitem__(self, key: tuple[str, int]) -> Any:
        """Get a value from the cache.

        >>> cache = Cache()
        >>> cache[("GUILDS.BOT_PREFIX", 123)]
        """
        return self.cache[key]

    def __setitem__(self, key: tuple[str, int], value: Any) -> None:
        """Set a value in the cache.

        >>> cache = Cache()
        >>> cache[("GUILDS.BOT_PREFIX", 123)] = "!"
        """
        self.cache[key] = value

    def __delitem__(self, key: tuple[str, int]) -> None:
        del self.cache[key]

    async def get(self, query: str, args: tuple) -> Any:
        match = SELECT_REGEX.match(query)
        assert match is not None

        operation, column, table, _ = match.groups()  # type: ignore

        if TYPE_CHECKING:
            operation: Literal["SELECT", "UPDATE"]
            column: str
            table: Literal["GUILDS", "USERS"]

        identifier = args[0]

        assert operation == "SELECT"

        try:
            return self.__getitem__((f"{table}.{column}", identifier))
        except KeyError:
            pass

        async with self.__conn.execute(query, args) as cursor:
            row = await cursor.fetchone()

        self.bot.need_commit = True

        if row is None:
            return None

        value = row[0]
        self.__setitem__((f"{table}.{column}", identifier), value)

        return value

    async def set(self, query: str, args: tuple) -> None:
        match = UPDATE_REGEX.match(query)
        assert match is not None

        operation, table, column, _, identifier = match.groups()  # type: ignore

        if TYPE_CHECKING:
            column: str
            table: Literal["GUILDS", "USERS"]

        assert operation == "UPDATE"

        identifier = args[-1]

        assert operation == "UPDATE"

        await self.__conn.execute(query, args)
        self.bot.need_commit = True

        self.__setitem__((f"{table}.{column}", identifier), args[0])

    async def put(self, query: str, args: tuple) -> None:
        match = INSERT_REGEX.match(query)
        assert match is not None

        operation, table, columns, _ = match.groups()  # type: ignore

        if TYPE_CHECKING:
            operation: Literal["INSERT"]
            table: Literal["GUILDS", "USERS"]
            columns: str

        cols_iter = map(lambda s: s.strip(), columns.split(","))

        assert operation == "INSERT"

        await self.__conn.execute(query, args)
        self.bot.need_commit = True

        index = 0

        for i, column in enumerate(cols_iter):
            if column == "ID":
                index = i
                break

        for column, value in zip(columns, args):
            self.__setitem__((f"{table}.{column}", args[index]), value)

    @copy_method_signature(get)
    async def select(self, *args, **kwargs):
        return await self.get(*args, **kwargs)

    @copy_method_signature(set)
    async def update(self, *args, **kwargs):
        return await self.set(*args, **kwargs)

    @copy_method_signature(put)
    async def insert(self, *args, **kwargs):
        return await self.put(*args, **kwargs)
