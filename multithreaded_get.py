import atexit
from dataclasses import dataclass
from queue import Queue
from threading import Event, Thread
from typing import Callable, Protocol

import requests


_OnCompletionCallable = Callable[[bytes, ...], None] | Callable[[bytes], None]


@dataclass
class _Packet:
    url: str
    on_completion: _OnCompletionCallable
    args: tuple
    kwargs: dict


_URL_QUEUE: Queue[_Packet] = Queue()
_STOP_FLAG = Event()
atexit.register(_STOP_FLAG.set)


def _thread_work():
    while not _STOP_FLAG.is_set():
        packet = _URL_QUEUE.get()
        response = requests.get(packet.url)
        packet.on_completion(response.content, *packet.args, **packet.kwargs)


_THREADS = [
    Thread(target=_thread_work)
]
for _thread in _THREADS:
    _thread.start()


def multithreaded_get(url: str, on_completion: _OnCompletionCallable, *args, **kwargs):
    _URL_QUEUE.put(_Packet(url, on_completion, args, kwargs))
