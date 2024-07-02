from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast
import requests

from hints import (
    GenerativeParametersType,
    GenerativeResponse,
    GenerativeResponseFinal,
    ModelInfo,
)

if TYPE_CHECKING:
    from typing_extensions import Generator, Unpack

GENERATE = "http://localhost:11434/api/generate"
LIST = "http://localhost:11434/api/ps"


class App:
    def __init__(self, model: str):
        self.model = model
        self.session = requests.Session()

    def generate_iter(
        self, **parameters: Unpack[GenerativeParametersType]
    ) -> Generator[GenerativeResponse, None, GenerativeResponseFinal | None]:
        parameters["stream"] = True
        parameters["model"] = self.model

        data = dict(parameters)

        response = self.session.post(GENERATE, json=data, stream=True)
        final_response = None

        for line in response.iter_lines():
            str_line = line.decode("UTF-8")
            json_line = json.loads(str_line)
            final_response = GenerativeResponseFinal.from_dict(json_line)

            if not final_response.done:
                yield cast(GenerativeResponse, final_response)

        return final_response

    def ps(self) -> list[ModelInfo]:
        response = self.session.get(LIST)

        models = response.json()

        return [ModelInfo(**data) for data in models["models"]]
