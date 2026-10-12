from typing import Any, Literal
from pydantic import BaseModel, Field    # v2
from typing import Callable, Any
from dataclasses import dataclass
from loads import json

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
    """Packet schema for server communication.
    \n version: 1
    \n action: The action to be performed.
    \n data: The data to be sent.
    \n tag: A tag for the packet.
    \n token: Optional authentication token."""
    v: Literal[1] = Field(default=1, description="Version of the packet")
    action: str = Field(..., description="Action to be performed")
    data: Any = Field(..., description="Data to be sent")
    tag: str = Field(..., description="Tag for the packet")
    token: str | None = Field(None, description="Token for authentication")

class ResponsePacket(BaseModel):
    v: Literal[1] = 1
    data: list[Any] = Field(..., description="Data to be sent, 0: data, 1: tag")


def validate_packet(data, packet_type) -> Packet:
    try:
        return Packet(**json.loads(data.strip()))
    except Exception as e:
        print(f"validate_packet->Error validating packet: {e}")
        return False