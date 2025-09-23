import requests
import threading
import time

URL = "http://127.0.0.1:8080/upload"
FILE_PATH = "minha_imagem.gif"
NUM_THREADS = 10
DELAY = 0.1

contador_global = 0
lock = threading.Lock()

with open(FILE_PATH, "rb") as f:
    imagem_base = f.read()

def enviar_imagem(thread_id):
    global contador_global
    while True:
        with lock:
            contador_global += 1
            numero = contador_global
        nome_virtual = f"{numero}.gif"
        files = {"file": (nome_virtual, imagem_base, "image/gif")}
        try:
            r = requests.post(URL, files=files, timeout=10)
            print(f"[Thread {thread_id}] Upload {numero}: {r.status_code}")
        except Exception as e:
            print(f"[Thread {thread_id}] Erro: {e}")
        time.sleep(DELAY)

threads = []
for t in range(NUM_THREADS):
    th = threading.Thread(target=enviar_imagem, args=(t+1,), daemon=True)
    threads.append(th)
    th.start()

print("Ataque iniciado.")
for th in threads:
    th.join()
