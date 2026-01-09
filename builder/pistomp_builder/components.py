from .base import Component
from .pistomp import PiStomp, PiStompPedalboards
from .mod import ModUI, ModHost
from .dependencies import (
    Jack2,
    Hylia,
    BrowsePy,
    AmidiThru,
    TouchOsc2Midi,
    ModMidiMerger,
    ModTtyMidi,
    Lilv
)

COMPONENT_MAP = {
    "mod-ui": ModUI(),
    "mod-host": ModHost(),
    "jack2": Jack2(),
    "hylia": Hylia(),
    "browsepy": BrowsePy(),
    "amidithru": AmidiThru(),
    "touchosc2midi": TouchOsc2Midi(),
    "mod-midi-merger": ModMidiMerger(),
    "mod-ttymidi": ModTtyMidi(),
    "lilv": Lilv(),
    "pi-stomp": PiStomp(),
    "pi-stomp-pedalboards": PiStompPedalboards(),
}