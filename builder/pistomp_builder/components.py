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
    Lilv,
)
from .effects import (
    ZynAddSubFX,
    Sfizz,
    LiquidSFZ,
)

# Note: serd, sord, sratom are provided by apt packages (liblilv dependencies)
# lilv is built from source for Python bindings only (static build, no shared libs)

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
    "sfizz": Sfizz(),
    "zynaddsubfx": ZynAddSubFX(),
    "liquidsfz": LiquidSFZ(),
    "pi-stomp": PiStomp(),
    "pi-stomp-pedalboards": PiStompPedalboards(),
}
