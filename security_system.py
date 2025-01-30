import cv2
import smtplib
from datetime import datetime
from ultralytics import YOLO
from typing import Optional, List
import os
import argparse
import subprocess

class SecurityMonitor:
    def __init__(self, model_path: str = 'yolov8n.pt', 
                 alert_threshold: float = 0.25,  # Limiar de confiança ajustado para maior sensibilidade
                 min_iou: float = 0.1,          # Mínima sobreposição aceita (10% da área)
                 iou_threshold_ratio: float = 0.8,
                 alert_cooldown: int = 5):  # Novo parâmetro: cooldown em segundos
        self.model = YOLO(model_path)  # Carrega o modelo YOLOv8 pré-treinado
        self.classes_of_interest = [43, 76]  # IDs do COCO dataset para facas e tesouras
        self.alert_threshold = alert_threshold
        self.last_alert_time = None
        
        # Parâmetros ajustados para balancear sensibilidade e falsos positivos
        self.min_iou = min_iou
        self.iou_threshold_ratio = iou_threshold_ratio
        self.alert_cooldown = alert_cooldown

    def detect_objects(self, frame):
        """Lógica principal de detecção:
        1. Executa inferência do YOLO
        2. Separta detecções em pessoas e objetos de interesse
        3. Verifica sobreposições usando IOU dinâmico
        4. Aplica threshold adaptativo baseado na sobreposição"""
        # Processamento otimizado com suppressão de logs (verbose=False)
        results = self.model(frame, verbose=False)[0]
        
        # Filtragem eficiente usando list comprehensions
        people = [box for box in results.boxes if int(box.cls) == 0]  # Classe 0 = pessoas no COCO
        objects = [box for box in results.boxes if int(box.cls) in self.classes_of_interest]
        
        relevant_objects = []
        
        # Lógica de sobreposição com threshold dinâmico
        for obj in objects:
            obj_conf = obj.conf.item()  # Confiança da detecção do objeto
            # Cálculo de IOU para cada par pessoa-objeto
            for person in people:
                iou = self._calculate_iou(obj.xyxy[0].cpu().numpy(), 
                                        person.xyxy[0].cpu().numpy())
                # Threshold reduz proporcionalmente à sobreposição
                dynamic_threshold = self.alert_threshold * (1 - self.iou_threshold_ratio * iou)
                
                # Condição combinada de sobreposição e confiança
                if (iou > self.min_iou and obj_conf > dynamic_threshold) or obj_conf > self.alert_threshold:
                    relevant_objects.append(obj)
                    break  # Otimização: para ao encontrar primeira sobreposição válida

        return relevant_objects, people

    def _calculate_iou(self, box1, box2):
        """Cálculo preciso de Intersection over Union:
        1. Determina coordenadas da área de interseção
        2. Calcula áreas individual e interseção
        3. Retorna razão interseção/união para medir sobreposição"""
        # Implementação otimizada sem uso de bibliotecas externas
        x_left = max(box1[0], box2[0])
        y_top = max(box1[1], box2[1])
        x_right = min(box1[2], box2[2])
        y_bottom = min(box1[3], box2[3])
        
        # Verifica se há interseção válida
        if x_right < x_left or y_bottom < y_top:
            return 0.0
        
        # Cálculo das áreas usando operações vetorizadas
        intersection_area = (x_right - x_left) * (y_bottom - y_top)
        box1_area = (box1[2] - box1[0]) * (box1[3] - box1[1])
        box2_area = (box2[2] - box2[0]) * (box2[3] - box2[1])
        
        # Prevenção contra divisão por zero
        union_area = box1_area + box2_area - intersection_area
        return intersection_area / union_area if union_area > 0 else 0.0

    def draw_annotations(self, frame, detections, people):
        """Destaca sobreposições pessoa-objeto"""
        # Desenha pessoas
        for person in people:
            box = person.xyxy[0].cpu().numpy()
            cv2.rectangle(frame, (int(box[0]), int(box[1])), (int(box[2]), int(box[3])), (255,0,0), 1)
        
        # Desenha objetos e sobreposições
        for obj in detections:
            box = obj.xyxy[0].cpu().numpy()
            conf = obj.conf.item()
            label = f"{self.model.names[int(obj.cls)]} {conf:.2f}"
            color = (0, 0, 255) if conf > self.alert_threshold else (0, 255, 255)
            cv2.rectangle(frame, (int(box[0]), int(box[1])), (int(box[2]), int(box[3])), color, 2)
            cv2.putText(frame, label, (int(box[0]), int(box[1]) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        
        return frame

    def should_alert(self) -> bool:
        """Verifica se pode enviar alerta baseado no cooldown"""
        if not self.last_alert_time:
            return True
            
        elapsed = (datetime.now() - self.last_alert_time).total_seconds()
        return elapsed >= self.alert_cooldown

    def update_alert_time(self):
        """Atualiza o timestamp do último alerta"""
        self.last_alert_time = datetime.now()

class AlertSystem:
    def __init__(self, sender_email: str, sender_password: str, receiver_email: str):
        self.sender = sender_email
        self.password = sender_password
        self.receiver = receiver_email
        self.server = smtplib.SMTP('smtp.gmail.com', 587)

    def connect(self):
        """Estabelece conexão com o servidor SMTP"""
        self.server.starttls()
        self.server.login(self.sender, self.password)

    def send_alert(self, frame: Optional[bytes] = None):
        """Sistema de notificação por e-mail:
        - Usa protocolo SMTP com TLS
        - Inclui timestamp preciso
        - Mensagem formatada para sistemas de monitoramento
        - Pode ser extendido para incluir anexos de imagem"""
        subject = "ALERTA: Objeto cortante detectado!"
        body = f"""\
        ALERTA DE SEGURANÇA

        Timestamp: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        Detecção confirmada pelo sistema VisionGuard.
        """
        msg = f'Subject: {subject}\n\n{body}'
        self.server.sendmail(self.sender, self.receiver, msg.encode('utf-8'))

def process_video(input_path: str, alert_dir: str) -> str:
    """
    Processa um vídeo para detecção de objetos perigosos.
    
    Args:
        input_path: Caminho do vídeo de entrada
        alert_dir: Diretório para salvar os alertas
        
    Returns:
        str: Caminho do vídeo processado
    """
    # Garante que o diretório existe
    os.makedirs(alert_dir, exist_ok=True)
    
    # Configurações
    monitor = SecurityMonitor()
    
    cap = cv2.VideoCapture(input_path)
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    # Configuração do FFmpeg
    output_path = os.path.join(alert_dir, "processed_video.mp4")
    command = [
        'ffmpeg',
        '-y',                    # Sobrescrever arquivo existente
        '-f', 'rawvideo',        # Formato de entrada: vídeo bruto
        '-vcodec', 'rawvideo',   # Codec de entrada: raw
        '-s', f'{frame_width}x{frame_height}',  # Resolução
        '-pix_fmt', 'bgr24',     # Formato de pixel OpenCV (BGR)
        '-r', str(fps),          # Taxa de quadros
        '-i', '-',               # Entrada via pipe
        '-c:v', 'libx264',       # Codec de saída H.264
        '-preset', 'fast',       # Balanceamento velocidade/qualidade
        '-crf', '22',            # Qualidade (0-51, menor=melhor)
        '-pix_fmt', 'yuv420p',   # Formato compatível com navegadores
        output_path
    ]
    
    # Inicia o processo FFmpeg
    writer = subprocess.Popen(command, stdin=subprocess.PIPE)
    
    try:
        while cap.isOpened():
            success, frame = cap.read()
            if not success:
                break

            frame_timestamp = cap.get(cv2.CAP_PROP_POS_MSEC)
            
            detections, people = monitor.detect_objects(frame)
            annotated_frame = monitor.draw_annotations(frame.copy(), detections, people)

            if detections:
                if monitor.should_alert():
                    monitor.update_alert_time()
                    
                    timestamp_str = f"{frame_timestamp:.0f}".zfill(10)
                    alert_filename = os.path.join(alert_dir, f"alert_{timestamp_str}.jpg")
                    cv2.imwrite(alert_filename, frame)
                    print(f"Alerta registrado: {alert_filename}")
                
                if monitor.last_alert_time:
                    cooldown_left = monitor.alert_cooldown - (datetime.now() - monitor.last_alert_time).total_seconds()
                    cooldown_text = f"Cooldown: {max(0, int(cooldown_left))}s"
                    text_x = frame_width - cv2.getTextSize(cooldown_text, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)[0][0] - 40
                    text_y = frame_height - 40
                    cv2.putText(annotated_frame, cooldown_text, (text_x, text_y - 40), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

            # Escreve o frame processado no FFmpeg
            writer.stdin.write(annotated_frame.tobytes())

    finally:
        cap.release()
        writer.stdin.close()
        writer.wait()
        print("Processamento concluído. Vídeo salvo em:", output_path)
        
    return output_path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, required=True)
    parser.add_argument('--alert_dir', type=str, required=True)
    args = parser.parse_args()
    
    # Garante que o diretório existe
    os.makedirs(args.alert_dir, exist_ok=True)
    
    # Processa o vídeo
    process_video(args.input, args.alert_dir)

if __name__ == "__main__":
    main()