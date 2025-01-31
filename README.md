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
- Python 3.10+ (recomendado)
- Gerenciador de pacotes: pip

## Instalação

1. Clone o repositório:
   ```bash
   git clone https://github.com/rornellas/hackafiap2025.git
   cd hackafiap2025
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

3. Faça upload de um vídeo para análise através da interface web

## Funcionalidades Principais

- Detecção em tempo real de objetos cortantes usando YOLOv8
- Sistema de alertas com cooldown para evitar notificações repetitivas
- Armazenamento organizado de resultados em diretórios específicos
- Interface web intuitiva para upload e visualização de vídeos
- Histórico completo de processamentos com detalhes
- Visualização detalhada do progresso de processamento

## Estrutura de Arquivos

```
.
├── app.py                 # Aplicação Flask principal
├── security_system.py     # Sistema de detecção de objetos
├── requirements.txt       # Dependências do projeto
├── static/               # Arquivos estáticos (CSS, JS)
├── templates/            # Templates HTML
├── uploads/             # Diretório para uploads de vídeos
├── processed/           # Diretório para vídeos processados
└── yolov8n.pt          # Modelo YOLOv8 pré-treinado
```

## Dependências Principais

- Flask 2.3.3 - Framework web
- PyTorch 2.0.1 - Framework de deep learning
- Ultralytics 8.0.200 - Framework YOLO para detecção de objetos
- OpenCV 4.5.5 - Processamento de imagens
- NumPy 1.23.5 - Computação numérica
- Humanize 4.7.0 - Formatação de datas

## Observações

- Certifique-se de ter espaço em disco suficiente para o processamento de vídeos
- O sistema mantém um histórico dos processamentos na interface web
- Os vídeos processados são organizados por data para fácil acesso 