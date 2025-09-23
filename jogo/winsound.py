# winsound.py — shim cross‑platform
# Coloque este arquivo ao lado do seu `defesa-jogo.py` (ou dentro de `jogo/`).
# No Linux/macOS, fornece Beep/PlaySound básicos.
# No Windows, usa ctypes para chamar a API Beep do sistema.

import sys, os

if sys.platform.startswith('win'):
    import ctypes
    def Beep(freq=440, dur=200):
        ctypes.windll.kernel32.Beep(int(freq), int(dur))
    def PlaySound(sound, flags=0):
        # Stub simples; pode ser expandido conforme necessidade
        try:
            ctypes.windll.winmm.PlaySoundW(str(sound), 0, int(flags))
        except Exception:
            pass
    # Constantes comuns para compatibilidade
    SND_ASYNC = 0x0001
    SND_FILENAME = 0x00020000
else:
    def Beep(freq=440, dur=200):
        try:
            rc = os.system(f'beep -f {int(freq)} -l {int(dur)} 1>/dev/null 2>&1')
            if rc != 0:
                raise RuntimeError("beep not available")
        except Exception:
            # Fallback: bell do terminal
            print("\a", end="", flush=True)

    def PlaySound(sound, flags=0):
        # Tenta players comuns; se não, alerta simples
        cmd = f'paplay {sound} 1>/dev/null 2>&1 || aplay {sound} 1>/dev/null 2>&1 || afplay {sound} 1>/dev/null 2>&1'
        try:
            rc = os.system(cmd)
            if rc != 0:
                raise RuntimeError("no player")
        except Exception:
            print("\a", end="", flush=True)

    # Constantes para compatibilidade (valores não importam fora do Windows)
    SND_ASYNC = 1
    SND_FILENAME = 2
