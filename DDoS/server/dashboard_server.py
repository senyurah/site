import os, threading, time, shutil
from collections import deque
from flask import Flask, request, jsonify, render_template, send_from_directory, redirect, url_for
from werkzeug.utils import secure_filename
from PIL import Image

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

lock = threading.Lock()
total_uploads = 0
total_bytes = 0
logs = []                # [{filename, status, time, size_bytes}]
byte_events = deque()    # deque de (timestamp, bytes) para cálculo de taxa

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def bytes_to_human(n):
    for unit in ['B','KB','MB','GB','TB']:
        if n < 1024.0:
            return f"{n:.2f} {unit}"
        n /= 1024.0
    return f"{n:.2f} PB"

def calc_rate_mbps(window_secs=1):
    now = time.time()
    while byte_events and (now - byte_events[0][0]) > window_secs:
        byte_events.popleft()
    window_bytes = sum(b for _, b in byte_events)
    return (window_bytes / max(window_secs, 1)) * 8 / 1_000_000

@app.after_request
def add_cors(resp):
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
    resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return resp

@app.route('/upload', methods=['POST', 'OPTIONS'])
def upload_file():
    global total_uploads, total_bytes
    if request.method == 'OPTIONS':
        return ('', 204)
    if 'file' not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "Nome de arquivo vazio"}), 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        try:
            Image.open(filepath).verify()
            size_bytes = os.path.getsize(filepath)
            now_str = time.strftime("%H:%M:%S")
            with lock:
                global logs
                total_uploads += 1
                total_bytes += size_bytes
                logs.append({"filename": filename, "status": "OK", "time": now_str, "size_bytes": size_bytes})
                byte_events.append((time.time(), size_bytes))
        except Exception:
            if os.path.exists(filepath):
                os.remove(filepath)
            with lock:
                logs.append({"filename": filename, "status": "Inválido", "time": time.strftime("%H:%M:%S"), "size_bytes": 0})
            return jsonify({"error": "Arquivo não é imagem válida"}), 400
        return jsonify({"message": "Upload OK", "file": filename}), 200
    else:
        with lock:
            logs.append({"filename": file.filename, "status": "Extensão inválida", "time": time.strftime("%H:%M:%S"), "size_bytes": 0})
        return jsonify({"error": "Extensão não permitida"}), 400

@app.route('/clear_uploads', methods=['POST'])
def clear_uploads():
    with lock:
        for name in os.listdir(UPLOAD_FOLDER):
            try:
                os.remove(os.path.join(UPLOAD_FOLDER, name))
            except Exception:
                pass
        # não zera contadores históricos; apenas limpa arquivos
        # se quiser zerar tudo, descomente abaixo:
        # global total_uploads, total_bytes, logs, byte_events
        # total_uploads = 0
        # total_bytes = 0
        # logs = []
        # byte_events.clear()
    return redirect(url_for('dashboard'))

@app.route('/')
def dashboard():
    last_logs = list(reversed(logs[-10:]))
    rate_mbps = calc_rate_mbps(window_secs=1)
    return render_template(
        "dashboard.html",
        total=total_uploads,
        total_bytes_human=bytes_to_human(total_bytes),
        rate_mbps=f"{rate_mbps:.2f}",
        logs=last_logs
    )

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.errorhandler(500)
def internal_error(e):
    return render_template("error.html"), 500

@app.errorhandler(503)
def service_unavailable(e):
    return render_template("error.html"), 503

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
