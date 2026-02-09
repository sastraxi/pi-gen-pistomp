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
    Serd,
    Sord,
    Sratom,
    Zix,
    Lilv,
)
from .effects import (
    ZynAddSubFX,
    Sfizz,
    LiquidSFZ,
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
    "serd": Serd(),
    "sord": Sord(),
    "sratom": Sratom(),
    "zix": Zix(),
    "lilv": Lilv(),
    "sfizz": Sfizz(),
    "zynaddsubfx": ZynAddSubFX(),
    "liquidsfz": LiquidSFZ(),
    "pi-stomp": PiStomp(),
    "pi-stomp-pedalboards": PiStompPedalboards(),
}
