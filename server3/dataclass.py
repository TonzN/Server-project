from typing import Any, Literal
from pydantic import BaseModel, Field    # v2
from typing import Callable, Any
from dataclasses import dataclass

@dataclass
class Task:
    func: Callable[..., Any]
    args: tuple
    kwargs: dict

class Packet(BaseModel):
    v: Literal[1]
    action: str
    data: Any
    tag: str
    token: str | None = None
    
