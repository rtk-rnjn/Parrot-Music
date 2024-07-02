from __future__ import annotations

from typing import TYPE_CHECKING, Literal, TypedDict

if TYPE_CHECKING:
    from typing_extensions import NotRequired, Unpack

import arrow


class GenerativeParametersType(TypedDict, total=False):
    model: str
    prompt: str
    images: NotRequired[list[str]]
    format: NotRequired[Literal["json"]]
    options: NotRequired[ModelFileType]
    system: NotRequired[str]
    template: NotRequired[str]
    context: NotRequired[str]
    stream: NotRequired[bool]
    raw: NotRequired[bool]


class ModelFileType(TypedDict):
    microstat: Literal[0, 1, 2]
    """Enable Mirostat sampling for controlling perplexity. 
    
    (default: 0, 0 = disabled, 1 = Mirostat, 2 = Mirostat 2.0)"""

    mirostat_eta: float
    """Influences how quickly the algorithm responds to feedback from the generated text. 
    
    A lower learning rate will result in slower adjustments, while a higher learning rate will make the algorithm more responsive. (Default: 0.1)"""

    mirostat_tau: float
    """Controls the balance between coherence and diversity of the output. 
    
    A lower value will result in more focused and coherent text. (Default: 5.0)"""

    num_ctx: int
    """Sets the size of the context window used to generate the next token. 
    
    (Default: 2048)"""

    repeat_last_n: int
    """Sets how far back for the model to look back to prevent repetition. 
    
    (Default: 64, 0 = disabled, -1 = num_ctx)"""

    repeat_penalty: float
    """Sets how strongly to penalize repetitions. 
    
    A higher value (e.g., 1.5) will penalize repetitions more strongly, while a lower value (e.g., 0.9) will be more lenient. 
    
    (Default: 1.1)"""

    temperature: float
    """The temperature of the model. Increasing the temperature will make the model answer more creatively. 
    
    (Default: 0.8)"""

    seed: int
    """Sets the random number seed to use for generation. 
    
    Setting this to a specific number will make the model generate the same text for the same prompt. 
    
    (Default: 0)"""

    stop: str
    """Sets the stop sequences to use. When this pattern is encountered the LLM will stop generating text and return. 
    
    Multiple stop patterns may be set by specifying multiple separate stop parameters in a modelfile."""

    tfs_z: float
    """Tail free sampling is used to reduce the impact of less probable tokens from the output. 
    
    A higher value (e.g., 2.0) will reduce the impact more, while a value of 1.0 disables this setting. (default: 1)"""

    num_predict: int
    """Maximum number of tokens to predict when generating text. 
    
    (Default: 128, -1 = infinite generation, -2 = fill context)"""

    top_k: int
    """Reduces the probability of generating nonsense. 
    
    A higher value (e.g. 100) will give more diverse answers, while a lower value (e.g. 10) will be more conservative. (Default: 40)"""

    top_p: float
    """Works together with top-k. 
    
    A higher value (e.g., 0.95) will lead to more diverse text, while a lower value (e.g., 0.5) will generate more focused and conservative text. 
    
    (Default: 0.9)"""


class ModelFile:
    __slots__ = (
        "microstat",
        "mirostat_eta",
        "mirostat_tau",
        "num_ctx",
        "repeat_last_n",
        "repeat_penalty",
        "temperature",
        "seed",
        "stop",
        "tfs_z",
        "num_predict",
        "top_k",
        "top_p",
    )

    def __init__(self, **kwargs: Unpack[ModelFileType]) -> None:
        for kw, value in kwargs.items():
            if value is not None and kw in self.__slots__:
                setattr(self, kw, value)

    @classmethod
    def from_dict(cls, data: ModelFileType) -> ModelFile:
        return cls(**data)


class GenerativeParameters:
    __slots__ = (
        "model",
        "prompt",
        "images",
        "format",
        "system",
        "template",
        "context",
        "stream",
        "raw",
    )

    def __init__(
        self,
        **kwargs: Unpack[GenerativeParametersType],
    ) -> None:
        images: list[str] = kwargs.pop("images", [])

        self.images = images

        for attr, value in kwargs.items():
            if value and attr in self.__slots__:
                setattr(self, attr, value)

    def __iter__(self):
        for attr in self.__slots__:
            if hasattr(self, attr):
                yield attr, getattr(self, attr)

    def __repr__(self) -> str:
        return f"GenerativeParameters(model={self.model!r}, prompt={self.prompt!r}, images={self.images!r})"

    def __str__(self) -> str:
        return repr(self)

    @classmethod
    def from_dict(cls, data: GenerativeParametersType) -> GenerativeParameters:
        return cls(**data)


class GenerativeResponseType(TypedDict):
    model: str
    created_at: str
    response: str
    done: bool


class GenerativeResponse:
    __slots__ = ("model", "created_at", "response", "done")

    def __init__(self, *, model: str, created_at: str, response: str, done: bool) -> None:
        self.model = model
        self.created_at = arrow.get(created_at)
        self.response = response
        self.done = done

    @classmethod
    def from_dict(cls, data: GenerativeResponseType) -> GenerativeResponse:
        return cls(**data)

    def __repr__(self) -> str:
        return f"GenerativeResponse(model={self.model!r}, created_at={self.created_at!r}, response={self.response!r}, done={self.done!r})"


class GenerativeResponseFinalType(TypedDict):
    model: str
    created_at: str
    response: str
    done: bool
    context: list[int]
    total_duration: float
    load_duration: float
    prompt_eval_count: int
    prompt_eval_duration: float
    eval_count: int
    eval_duration: float


class GenerativeResponseFinal(GenerativeResponse):
    __slots__ = (
        "model",
        "created_at",
        "response",
        "done",
        "context",
        "total_duration",
        "load_duration",
        "prompt_eval_count",
        "prompt_eval_duration",
        "eval_count",
        "eval_duration",
    )

    def __init__(
        self,
        **kwargs: Unpack[GenerativeResponseFinalType],
    ) -> None:
        super().__init__(
            model=kwargs.pop("model"),  # type: ignore
            created_at=kwargs.pop("created_at"),  # type: ignore
            response=kwargs.pop("response"),  # type: ignore
            done=kwargs.pop("done"),  # type: ignore
        )

        for k, value in kwargs.items():
            if value and k in self.__slots__:
                setattr(self, k, value)

    @classmethod
    def from_dict(cls, data: GenerativeResponseFinalType) -> GenerativeResponseFinal:
        return cls(**data)

    def __repr__(self) -> str:
        return f"GenerativeResponseFinal(model={self.model!r}, created_at={self.created_at!r}, response={self.response!r}, done={self.done!r})"


class DetailsType(TypedDict):
    parent_model: str
    format: str
    family: str
    families: list[str]
    parameter_size: str
    quantization_level: str


class ModelInfoType(TypedDict):
    name: str
    model: str
    size: int
    digest: str
    details: DetailsType
    expires_at: str
    size_vram: int


class ModelInfo:
    __slots__ = (
        "name",
        "model",
        "size",
        "digest",
        "expires_at",
        "size_vram",
        "parent_model",
        "format",
        "family",
        "families",
        "parameter_size",
        "quantization_level",
    )

    def __init__(self, **kwargs: Unpack[ModelInfoType]) -> None:
        for k, value in kwargs.items():
            if value:
                if isinstance(value, dict):
                    self.__init__(**value)
                else:
                    setattr(self, k, value)

        if hasattr(self, "expires_at"):
            self.expires_at = arrow.get(self.expires_at)

    def __repr__(self) -> str:
        return f"ModelInfo(model={self.model!r}, size={self.size!r}, digest={self.digest!r}, expires_at={self.expires_at!r})"

    @classmethod
    def from_dict(cls, data: ModelInfoType) -> ModelInfo:
        return cls(**data)
