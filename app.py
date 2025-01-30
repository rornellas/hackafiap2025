from flask import Flask, render_template, request, redirect, url_for
import subprocess
import os
from datetime import datetime
from humanize import naturaltime

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'mp4', 'avi', 'mov'}

# Garante que os diretórios existam
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('static/results', exist_ok=True)
os.makedirs('processed', exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def index():
    return render_template('index.html')

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
        
        # Executa o processamento
        subprocess.run([
            'python', 'security_system.py',
            '--input', input_path,
            '--alert_dir', alert_dir
        ])
        
        # Caminho relativo para o template
        output_path = os.path.join(alert_dir, "processed_video.mp4")
        
        return render_template('processing.html',
                             input_file=file.filename,
                             output_file=output_path.replace('static/', ''))

    return redirect(request.url)

@app.route('/process', methods=['GET'])
def list_processes():
    processes = []
    process_dir = os.path.join('static', 'alerts')  # Caminho corrigido
    
    # Lista todos os diretórios de processamento
    for entry in os.scandir(process_dir):
        if entry.is_dir() and entry.name.startswith('process_'):
            process_info = {
                'id': entry.name,
                'path': entry.path,
                'created_at': datetime.fromtimestamp(entry.stat().st_ctime),
                'alerts_count': len([f for f in os.listdir(entry.path) if f.startswith('alert_')]),
                'video_exists': os.path.exists(os.path.join(entry.path, 'processed_video.mp4'))
            }
            processes.append(process_info)
    
    # Ordena do mais recente para o mais antigo
    processes.sort(key=lambda x: x['created_at'], reverse=True)
    
    return render_template('process_list.html', processes=processes)

@app.route('/process/<process_id>')
def process_details(process_id):
    process_dir = os.path.join('static', 'alerts', process_id)
    
    if not os.path.exists(process_dir):
        return "Processamento não encontrado", 404
    
    # Lista e formata os alertas
    alerts = []
    for f in os.listdir(process_dir):
        if f.startswith('alert_') and f.endswith('.jpg'):
            timestamp_ms = int(f.split('_')[1].split('.')[0])
            minutes = timestamp_ms // 60000
            seconds = (timestamp_ms % 60000) // 1000
            milliseconds = timestamp_ms % 1000
            alerts.append({
                'filename': f,
                'timestamp': f"{minutes:02d}:{seconds:02d}.{milliseconds:03d}",
                'video_time': timestamp_ms / 1000
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

if __name__ == '__main__':
    app.run(debug=True) 