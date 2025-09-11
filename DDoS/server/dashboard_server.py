import os, threading, time
from flask import Flask, request, jsonify, render_template, send_from_directory
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
logs = []

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def dashboard():
    last_logs = list(reversed(logs[-10:]))
    last20 = logs[-20:]
    times = [x['time'] for x in last20]
    counts = [i + 1 for i in range(len(last20))]
    return render_template("dashboard.html", total=total_uploads, logs=last_logs, times=times, counts=counts)

@app.route('/upload', methods=['POST'])
def upload_file():
    global total_uploads, logs
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
            with lock:
                total_uploads += 1
                logs.append({"filename": filename, "status": "OK", "time": time.strftime("%H:%M:%S")})
        except Exception:
            if os.path.exists(filepath):
                os.remove(filepath)
            with lock:
                logs.append({"filename": filename, "status": "Inválido", "time": time.strftime("%H:%M:%S")})
            return jsonify({"error": "Arquivo não é imagem válida"}), 400
        return jsonify({"message": "Upload OK", "file": filename}), 200
    else:
        with lock:
            logs.append({"filename": file.filename, "status": "Extensão inválida", "time": time.strftime("%H:%M:%S")})
        return jsonify({"error": "Extensão não permitida"}), 400

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
