from typing import Any, Literal
from pydantic import BaseModel, Field    # v2
from typing import Callable, Any
from dataclasses import dataclass

"""Schema for the server3 module 
   This module contains the data classes and models used in the server3 module.
   It includes the Packet class, which is used to represent packets of data sent
   between the server and clients, and the Task class, which is used to represent
   tasks that can be executed by worker threads.
"""


@dataclass
class Task:
    func: Callable[..., Any]
    args: tuple
    kwargs: dict
    result: Any = None
    error: Exception | None = None
    status: str = "pending"

class Packet(BaseModel):
    v: Literal[1]
    action: str
    data: Any
    tag: str
    token: str | None = None
    
