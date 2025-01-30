import cv2
import smtplib
from datetime import datetime
from ultralytics import YOLO
from typing import Optional, List

class SecurityMonitor:
    def __init__(self, model_path: str = 'yolov8n.pt', alert_threshold: float = 0.5,
                 hand_padding: float = 0.3, hand_threshold_ratio: float = 0.3,
                 nearby_padding: float = 0.5, nearby_threshold_ratio: float = 0.7):
        self.model = YOLO(model_path)
        self.alert_threshold = alert_threshold
        self.classes_of_interest = [43, 72]  # COCO: 43=knife, 72=scissors
        self.last_alert_time = None
        
        # Parâmetros de zonas de detecção (corrigidos)
        self.hand_padding = hand_padding
        self.hand_threshold_ratio = hand_threshold_ratio
        self.nearby_padding = nearby_padding
        self.nearby_threshold_ratio = nearby_threshold_ratio

    def detect_objects(self, frame):
        """Processa um frame e retorna detecções relevantes"""
        results = self.model(frame, verbose=False)[0]
        
        # Separa pessoas e objetos de interesse primeiro
        people = [box for box in results.boxes if int(box.cls) == 0]
        objects = [box for box in results.boxes if int(box.cls) in self.classes_of_interest]
        
        relevant_objects = []
        
        for obj in objects:
            obj_conf = obj.conf.item()
            obj_class = int(obj.cls)
            obj_bbox = obj.xyxy[0].cpu().numpy()
            
            # Calcula centroide do objeto
            obj_center = ((obj_bbox[0] + obj_bbox[2])/2, (obj_bbox[1] + obj_bbox[3])/2)
            
            # Verifica proximidade com pessoas usando IOU e distância relativa
            for person in people:
                person_bbox = person.xyxy[0].cpu().numpy()
                
                # 1. Verifica se o centro do objeto está dentro da bbox da pessoa (com margem)
                expanded_person_bbox = [
                    person_bbox[0] - (person_bbox[2] - person_bbox[0]) * self.hand_padding,
                    person_bbox[1] - (person_bbox[3] - person_bbox[1]) * self.hand_padding,
                    person_bbox[2] + (person_bbox[2] - person_bbox[0]) * self.hand_padding,
                    person_bbox[3] + (person_bbox[3] - person_bbox[1]) * self.hand_padding
                ]
                
                # Verifica se o centro do objeto está dentro da área expandida da pessoa
                if (expanded_person_bbox[0] < obj_center[0] < expanded_person_bbox[2] and
                    expanded_person_bbox[1] < obj_center[1] < expanded_person_bbox[3]):
                    
                    # 2. Threshold dinâmico baseado na proximidade
                    proximity_threshold = self.alert_threshold * self.hand_threshold_ratio
                    
                    if obj_conf > proximity_threshold:
                        relevant_objects.append(obj)
                        break  # Para de verificar outras pessoas uma vez encontrado

        return relevant_objects, people

    def draw_annotations(self, frame, detections, people):
        """Desenha bounding boxes e labels no frame"""
        for obj in detections:
            box = obj.xyxy[0].cpu().numpy()
            # Converte o tensor para float antes de formatar
            conf = obj.conf.item()
            label = f"{self.model.names[int(obj.cls)]} {conf:.2f}"
            color = (0, 0, 255)  # Vermelho para alertas
            cv2.rectangle(frame, (int(box[0]), int(box[1])), (int(box[2]), int(box[3])), color, 2)
            cv2.putText(frame, label, (int(box[0]), int(box[1]-10)), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)

        # Desenha zonas de detecção
        for person in people:  # Adicione acesso às pessoas
            person_bbox = person.xyxy[0].cpu().numpy()
            # Zona da mão
            hand_bbox = self._expand_bbox(person_bbox, self.hand_padding)
            cv2.rectangle(frame, (int(hand_bbox[0]), int(hand_bbox[1])), 
                         (int(hand_bbox[2]), int(hand_bbox[3])), (0,255,0), 1)
            # Zona próxima
            nearby_bbox = self._expand_bbox(person_bbox, self.nearby_padding)
            cv2.rectangle(frame, (int(nearby_bbox[0]), int(nearby_bbox[1])), 
                         (int(nearby_bbox[2]), int(nearby_bbox[3])), (0,255,255), 1)
        return frame

    def _expand_bbox(self, bbox, padding):
        """Expande a bbox em porcentagem da dimensão original"""
        x1, y1, x2, y2 = bbox
        width = x2 - x1
        height = y2 - y1
        return [
            x1 - width * padding,
            y1 - height * padding,
            x2 + width * padding,
            y2 + height * padding
        ]

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
                cv2.putText(annotated_frame, "ALERTA ATIVADO!", (50, 50), 
                          cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)

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