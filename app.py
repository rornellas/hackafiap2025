from flask import Flask, render_template, request, redirect, url_for
import subprocess
import os
from datetime import datetime
from humanize import naturaltime
from threading import Thread, Lock
import time
import json

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'mp4', 'avi', 'mov'}

# Garante que os diretórios existam
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('static/results', exist_ok=True)
os.makedirs('processed', exist_ok=True)

# Dicionário para armazenar status dos processamentos
process_status = {}
status_lock = Lock()

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def index():
    return render_template('index.html')

def process_video_async(process_id, input_path, alert_dir):
    try:
        print(f"Iniciando processamento: {process_id}")
        # Executa o processamento
        result = subprocess.run([
            'python', 'security_system.py',
            '--input', input_path,
            '--alert_dir', alert_dir
        ], capture_output=True, text=True)
        
        with status_lock:
            if result.returncode == 0:
                process_status[process_id] = 'completed'
            else:
                process_status[process_id] = f'error: {result.stderr}'
                
        print(f"Processamento {process_id} completo")
        
    except Exception as e:
        with status_lock:
            process_status[process_id] = f'error: {str(e)}'

@app.route('/process', methods=['POST'])
def process_video():
    if 'file' not in request.files:
        return redirect(request.url)
    
    file = request.files['file']
    if file.filename == '':
        return redirect(request.url)
    
    if file and allowed_file(file.filename):
        # Cria diretório único para o processamento
        process_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        alert_dir = os.path.join('static', 'alerts', f"process_{process_id}")
        os.makedirs(alert_dir, exist_ok=True)
        
        # Salva o arquivo dentro do diretório de processamento
        input_path = os.path.join(alert_dir, "original_video.mp4")
        file.save(input_path)
        
        # Inicia a thread de processamento
        with status_lock:
            process_status[process_id] = 'processing'
        
        Thread(target=process_video_async, args=(process_id, input_path, alert_dir)).start()
        
        # Modificar a forma de armazenar processos ativos
        response = redirect(url_for('list_processes'))
        response.set_cookie('latest_process', process_id)  # Armazena apenas o último processo
        return response

    return redirect(request.url)

@app.route('/process', methods=['GET'])
def list_processes():
    processes = get_processes()  # Extrair lógica para função reutilizável
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('_process_table.html', processes=processes)
    
    return render_template('process_list.html', processes=processes)

def get_processes():
    processes = []
    process_dir = os.path.join('static', 'alerts')
    
    for entry in os.scandir(process_dir):
        if entry.is_dir() and entry.name.startswith('process_'):
            process_info = {
                'id': entry.name,
                'created_at': datetime.fromtimestamp(entry.stat().st_ctime),
                'alerts_count': len([f for f in os.listdir(entry.path) if f.startswith('alert_')]),
                'video_exists': os.path.exists(os.path.join(entry.path, 'processed_video.mp4')),
                'status': 'completed' if os.path.exists(os.path.join(entry.path, 'processed_video.mp4')) else 'processing'
            }
            processes.append(process_info)
    
    processes.sort(key=lambda x: x['created_at'], reverse=True)
    return processes

@app.route('/process/<process_id>')
def process_details(process_id):
    process_dir = os.path.join('static', 'alerts', process_id)
    
    if not os.path.exists(process_dir):
        return "Processamento não encontrado", 404
    
    # Lista e formata os alertas
    alerts = []
    for f in os.listdir(process_dir):
        if f.startswith('alert_') and f.endswith('.jpg'):
            # Extrai o timestamp do nome do arquivo
            timestamp_str = f.split('_')[1].split('.')[0]
            
            # Garante a conversão correta para float
            try:
                timestamp_ms = float(timestamp_str)
            except ValueError:
                continue
            
            # Calcula o tempo em segundos com precisão decimal
            alerts.append({
                'filename': f,
                'timestamp': f"{int(timestamp_ms//60000):02d}:{int((timestamp_ms%60000)//1000):02d}.{int(timestamp_ms%1000):03d}",
                'video_time': timestamp_ms / 1000.0  # Mantém precisão decimal
            })
    
    # Ordena por timestamp
    alerts.sort(key=lambda x: x['video_time'])
    
    return render_template('process_details.html',
                         process_id=process_id,
                         alerts=alerts,
                         video_exists=os.path.exists(os.path.join(process_dir, 'processed_video.mp4')))

@app.template_filter('naturaltime')
def natural_time_filter(dt):
    """Filtro para formatar datas usando humanize"""
    return naturaltime(dt)

@app.after_request
def add_headers(response):
    if response.mimetype == 'video/mp4':
        response.headers.add('Accept-Ranges', 'bytes')
    return response

@app.route('/check_status/<process_id>')
def check_status(process_id):
    print(f"Verificando status para: {process_id}")
    with status_lock:
        # Verifica diretamente no sistema de arquivos
        process_dir = os.path.join('static', 'alerts', process_id)
        if os.path.exists(os.path.join(process_dir, 'processed_video.mp4')):
            return {'status': 'completed'}
        return {'status': process_status.get(process_id, 'processing')}

@app.route('/processing/<process_id>')
def processing_status(process_id):
    return render_template('processing.html', process_id=process_id)

if __name__ == '__main__':
    app.run(debug=True) 