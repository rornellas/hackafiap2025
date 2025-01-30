from flask import Flask, render_template, request, redirect, url_for
import subprocess
import os
from datetime import datetime

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'mp4', 'avi', 'mov'}

# Garante que os diretórios existam
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('static/results', exist_ok=True)

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

if __name__ == '__main__':
    app.run(debug=True) 