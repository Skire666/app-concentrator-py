"""Type stub for the part of miniaudio 1.73 Concentrator uses (the package ships no ``py.typed``, ADR-045).

Samples are 16-bit signed integers (``SampleFormat.SIGNED16``), so the arrays hold ``int``.
"""

import array
from collections.abc import Generator
from enum import Enum

class SampleFormat(Enum):
    UNKNOWN = 0
    UNSIGNED8 = 1
    SIGNED16 = 2
    SIGNED24 = 3
    SIGNED32 = 4
    FLOAT32 = 5

class MiniaudioError(Exception): ...
class DecodeError(MiniaudioError): ...

class SoundFileInfo:
    name: str
    nchannels: int
    sample_rate: int
    num_frames: int
    duration: float

def get_file_info(filename: str) -> SoundFileInfo: ...
def stream_file(
    filename: str,
    output_format: SampleFormat = ...,
    nchannels: int = ...,
    sample_rate: int = ...,
    frames_to_read: int = ...,
) -> Generator[array.array[int], int, None]: ...

class Devices:
    def __init__(self) -> None: ...
    def get_playbacks(self) -> list[dict[str, object]]: ...

class PlaybackDevice:
    def __init__(
        self,
        output_format: SampleFormat = ...,
        nchannels: int = ...,
        sample_rate: int = ...,
        buffersize_msec: int = ...,
        app_name: str = ...,
    ) -> None: ...
    def start(self, callback_generator: Generator[array.array[int], int, None]) -> None: ...
    def set_master_volume(self, volume: float) -> None: ...
    def close(self) -> None: ...
