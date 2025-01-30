import cv2
import smtplib
from datetime import datetime
from ultralytics import YOLO
from typing import Optional, List

class SecurityMonitor:
    def __init__(self, model_path: str = 'yolov8n.pt', alert_threshold: float = 0.4,
                 min_iou: float = 0.2, iou_threshold_ratio: float = 0.5):
        self.model = YOLO(model_path)
        self.alert_threshold = alert_threshold
        self.classes_of_interest = [43, 72]  # COCO: 43=knife, 72=scissors
        self.last_alert_time = None
        
        # Parâmetros de sobreposição
        self.min_iou = min_iou  # Mínimo de 20% de sobreposição
        self.iou_threshold_ratio = iou_threshold_ratio  # Redução do threshold para objetos sobrepostos

    def detect_objects(self, frame):
        """Detecta objetos cortantes sobrepostos com pessoas"""
        results = self.model(frame, verbose=False)[0]
        
        people = [box for box in results.boxes if int(box.cls) == 0]
        objects = [box for box in results.boxes if int(box.cls) in self.classes_of_interest]
        
        relevant_objects = []
        
        for obj in objects:
            obj_conf = obj.conf.item()
            obj_bbox = obj.xyxy[0].cpu().numpy()
            
            for person in people:
                person_bbox = person.xyxy[0].cpu().numpy()
                
                # Calcula IOU (Intersection over Union)
                iou = self._calculate_iou(obj_bbox, person_bbox)
                
                # Threshold dinâmico baseado na sobreposição
                dynamic_threshold = self.alert_threshold * (1 - self.iou_threshold_ratio * iou)
                
                if iou > self.min_iou and obj_conf > dynamic_threshold:
                    relevant_objects.append(obj)
                    break

        return relevant_objects, people

    def _calculate_iou(self, box1, box2):
        """Calcula a porcentagem de sobreposição entre duas bounding boxes"""
        # Coordenadas da interseção
        x_left = max(box1[0], box2[0])
        y_top = max(box1[1], box2[1])
        x_right = min(box1[2], box2[2])
        y_bottom = min(box1[3], box2[3])
        
        if x_right < x_left or y_bottom < y_top:
            return 0.0
        
        intersection_area = (x_right - x_left) * (y_bottom - y_top)
        box1_area = (box1[2] - box1[0]) * (box1[3] - box1[1])
        box2_area = (box2[2] - box2[0]) * (box2[3] - box2[1])
        
        return intersection_area / (box1_area + box2_area - intersection_area)

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
            cv2.putText(frame, label, (int(box[0]), int(box[1]-10)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        
        return frame

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
        """Envia alerta por e-mail com timestamp"""
        subject = "ALERTA: Objeto cortante detectado!"
        body = f"""\
        ALERTA DE SEGURANÇA

        Timestamp: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        Detecção confirmada pelo sistema VisionGuard.
        """
        
        msg = f'Subject: {subject}\n\n{body}'
        self.server.sendmail(self.sender, self.receiver, msg.encode('utf-8'))

def main(video_path: str = 0, output_path: str = 'output.mp4'):
    # Configurações
    monitor = SecurityMonitor()
#    alert_system = AlertSystem(
#        sender_email="seu_email@gmail.com",
#        sender_password="sua_senha_app",  # Usar senha de app do Google
#        receiver_email="central@seguranca.com"
#    )
#    alert_system.connect()

    cap = cv2.VideoCapture(video_path)
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    # Configuração do vídeo de saída
    writer = cv2.VideoWriter(output_path, 
                           cv2.VideoWriter_fourcc(*'mp4v'), 
                           fps, 
                           (frame_width, frame_height))

    try:
        while cap.isOpened():
            success, frame = cap.read()
            if not success:
                break

            # Processamento do frame
            detections, people = monitor.detect_objects(frame)
            annotated_frame = monitor.draw_annotations(frame.copy(), detections, people)

            # Sistema de alerta
            if detections:
                #alert_system.send_alert()
                # Posicionamento no canto inferior direito
                text = "ALERTA ATIVADO!"
                text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1.5, 3)[0]
                text_x = frame_width - text_size[0] - 40  # 40px da borda direita
                text_y = frame_height - 40  # 40px da borda inferior
                cv2.putText(annotated_frame, text, (text_x, text_y), 
                          cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3, cv2.LINE_AA)

            writer.write(annotated_frame)

    finally:
        cap.release()
        writer.release()
        #alert_system.server.quit()
        print("Processamento concluído. Vídeo salvo em:", output_path)

if __name__ == "__main__":
    # Para webcam: main(video_path=0)
    # Para arquivo: main(video_path="input.mp4")
    main(video_path="/home/rodrigo/Downloads/teste-hacka.mp4")