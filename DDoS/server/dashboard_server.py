# server_with_upload_and_maintenance.py
from flask import Flask, request, jsonify, Response, render_template_string
import time, threading, os, tempfile
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Config
UPLOAD_FOLDER = os.path.join(tempfile.gettempdir(), "demo_uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

BIND_HOST = '0.0.0.0'   # LOCAL ONLY
BIND_PORT = 8080

# Estado / métricas
metrics = {
    'total_uploads': 0
}
metrics_lock = threading.Lock()
MAINTENANCE_THRESHOLD = 1000  # ajuste para 1000 para demo real; reduzir p/ testes
# maintenance state
maintenance_mode = {
    'down': False,
    'since': None
}

# Página de manutenção (substitua este HTML pelo seu template se quiser)
MAINTENANCE_HTML = """
<!doctype html>
<html>
  <head><meta charset="utf-8"><title>Manutenção</title>
  <style>
    body { font-family: Arial, sans-serif; text-align:center; padding:60px; background:#f2f2f2; }
    .card { display:inline-block; padding:30px; background:white; border-radius:8px; box-shadow:0 6px 18px rgba(0,0,0,0.08); }
    h1 { color:#c0392b; }
  </style>
  </head>
  <body>
    <div class="card">
      <h1>Serviço temporariamente indisponível</h1>
      <p>O serviço entrou em modo de manutenção devido à alta carga (simulação).</p>
      <p><small>Demo local — ambiente controlado.</small></p>
    </div>
  </body>
</html>
"""

# Utilitários
def check_maintenance():
    with metrics_lock:
        return maintenance_mode['down']

def enter_maintenance():
    with metrics_lock:
        maintenance_mode['down'] = True
        maintenance_mode['since'] = time.time()

def reset_maintenance():
    with metrics_lock:
        maintenance_mode['down'] = False
        maintenance_mode['since'] = None
        metrics['total_uploads'] = 0

# Middleware: se em manutenção, retorna a página (exceto rotas admin)
@app.before_request
def before_all_requests():
    if request.path.startswith('/admin'):
        return None
    if check_maintenance():
        return Response(MAINTENANCE_HTML, status=503, mimetype='text/html')
    return None

# Root status
@app.route('/')
def index():
    with metrics_lock:
        return jsonify({
            'status': 'up' if not maintenance_mode['down'] else 'maintenance',
            'total_uploads': metrics['total_uploads'],
            'maintenance': maintenance_mode.copy()
        })

# Upload endpoint (multipart/form-data field 'file')
@app.route('/upload', methods=['POST'])
def upload():
    # Segurança: limitar a requests de localhost nesta demo
    remote = request.remote_addr
    if remote not in ('127.0.0.1', '::1', 'localhost'):
        return jsonify({'error': 'uploads permitidos apenas de localhost para esta demo'}), 403

    if 'file' not in request.files:
        return jsonify({'error': 'nenhum arquivo no campo "file"'}), 400

    f = request.files['file']
    filename = secure_filename(f.filename or f'upload_{int(time.time()*1000)}')
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    # salvando o arquivo (pode consumir espaço em disco; cuidado)
    f.save(save_path)

    # incrementar contador
    with metrics_lock:
        metrics['total_uploads'] += 1
        current = metrics['total_uploads']

    # checar threshold
    if current >= MAINTENANCE_THRESHOLD and not check_maintenance():
        enter_maintenance()

    return jsonify({
        'ok': True,
        'filename': filename,
        'total_uploads': current,
        'maintenance_now': check_maintenance()
    })

# Admin: reset (token simples)
ADMIN_TOKEN = "tioomB5bxY30y52XE69A6Sg6Ezjw_fg-njLu4K3YT80"  # troque antes de apresentar

@app.route('/admin/reset', methods=['POST'])
def admin_reset():
    token = request.args.get('token') or request.headers.get('X-ADMIN-TOKEN')
    if token != ADMIN_TOKEN:
        return jsonify({'error': 'token inválido'}), 403
    reset_maintenance()
    return jsonify({'ok': True, 'message': 'contador resetado e site fora de manutenção'})

@app.route('/admin/status', methods=['GET'])
def admin_status():
    token = request.args.get('token') or request.headers.get('X-ADMIN-TOKEN')
    if token != ADMIN_TOKEN:
        return jsonify({'error': 'token inválido'}), 403
    with metrics_lock:
        return jsonify({
            'total_uploads': metrics['total_uploads'],
            'maintenance': maintenance_mode.copy()
        })

if __name__ == '__main__':
    print("Upload folder:", app.config['UPLOAD_FOLDER'])
    print(f"Rodando em http://{BIND_HOST}:{BIND_PORT} — demo LOCAL apenas.")
    app.run(host=BIND_HOST, port=BIND_PORT, threaded=True)
