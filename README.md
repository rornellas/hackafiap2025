# VisionGuard - Sistema de Detecção de Objetos Perigosos

Sistema de monitoramento de segurança que detecta objetos cortantes em tempo real usando visão computacional e deep learning.

## Pré-requisitos

### Sistema Operacional
- Ubuntu 20.04+ (recomendado)
- Dependências do sistema:
  ```bash
  sudo apt-get update && sudo apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgl1-mesa-glx
  ```

### Python
- Python 3.8+
- Gerenciador de pacotes: pip

## Instalação

1. Clone o repositório:
   ```bash
   git clone https://github.com/seu-usuario/visionguard.git
   cd visionguard
   ```

2. Crie e ative um ambiente virtual (recomendado):
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

4. Baixe o modelo YOLOv8 pré-treinado:
   ```bash
   wget https://github.com/ultralytics/assets/releases/download/v8.0.0/yolov8n.pt -O yolov8n.pt
   ```

## Execução

1. Inicie o servidor web:
   ```bash
   python app.py
   ```

2. Acesse a interface no navegador:
   ```
   http://localhost:5000
   ```

3. Faça upload de um vídeo para análise

## Funcionalidades Principais

- Detecção em tempo real de objetos cortantes
- Sistema de alertas com cooldown
- Armazenamento organizado de resultados
- Interface web intuitiva
- Histórico de processamentos

## Estrutura de Arquivos 