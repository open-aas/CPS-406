from typing import List, Union
from asyncua import Node
from asyncua.ua import NodeId
from enum import Enum, auto

import asyncio


class EdgeType(Enum):
    RISING = auto()
    FALLING = auto()
    BOTH = auto()


class State(Enum):
    LOW = 0
    HIGH = 1


class EdgeDetector:
    def __init__(self, node_id: NodeId, trigger_on=EdgeType.RISING, enable=True):
        self.node_id = node_id
        self.state = State.LOW
        self.trigger_on = trigger_on
        self.event_trigger = asyncio.Event()
        self.enable = enable

    def update(self, signal_value: int, name: str):
        if not self.enable:
            return

        new_state = State.HIGH if signal_value else State.LOW

        if self.state == State.LOW and new_state == State.HIGH:
            edge = EdgeType.RISING
            print(edge, name)
        
        elif self.state == State.HIGH and new_state == State.LOW:
            edge = EdgeType.FALLING
            print(edge, name)

        else:
            edge = None

        self.state = new_state

        if edge and (self.trigger_on == EdgeType.BOTH or self.trigger_on == edge):
            self.event_trigger.set()

    def set_trigger(self, trigger_on: EdgeType):
        self.trigger_on = trigger_on

    def set_enable(self, value: bool):
        self.enable = value

    def clear(self):
        self.event_trigger.clear()

    async def wait(self):
        await self.event_trigger.wait()
        self.event_trigger.clear()


class SensorEventHandler:
    def __init__(self, edge_detectors: Union[EdgeDetector, List[EdgeDetector]]):
        # bug fix: isinstance check was wrong in original (isinstance(list, tuple))
        self.edge_detectors = edge_detectors if isinstance(edge_detectors, (list, tuple)) else [edge_detectors]

    async def datachange_notification(self, node: Node, val, data):
        name = str(node.nodeid)
        value = int(val)

        for detector in self.edge_detectors:
            if node.nodeid == detector.node_id:
                print(f"Data change detected on {name}: {value}")
                detector.update(value, name)

    async def event_notification(self, event):
        pass

    def add_detect(self, detectors: Union[EdgeDetector, List[EdgeDetector]]):
        if not isinstance(detectors, (list, tuple)):
            detectors = [detectors]
        self.edge_detectors.extend(detectors)

    def clear(self):
        self.edge_detectors.clear()
