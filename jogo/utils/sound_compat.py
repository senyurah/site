# jogo/utils/sound_compat.py
import sys, os

def _beep_system(freq=440, dur=200):
    try:
        rc = os.system(f'beep -f {int(freq)} -l {int(dur)} 1>/dev/null 2>&1')
        if rc == 0:
            return True
    except Exception:
        pass
    try:
        print("\a", end="", flush=True)
        return True
    except Exception:
        return False

try:
    if sys.platform.startswith("win"):
        import winsound  # type: ignore
        def beep(freq=440, dur=200):
            winsound.Beep(int(freq), int(dur))
    else:
        def beep(freq=440, dur=200):
            _beep_system(freq, dur)
except Exception:
    def beep(freq=440, dur=200):
        _beep_system(freq, dur)

def beep_ok():
    beep(880, 120)
def beep_err():
    beep(220, 250)
