import os, time, threading
from datetime import datetime
import cv2
from PySide6.QtCore import QTimer, Qt, Signal, QObject
from PySide6.QtGui import QImage, QPixmap
from ultralytics import YOLO
from database import insert_detection

MODEL_PATH = os.path.join("model", "bestt.pt")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FOLDER = os.path.join(BASE_DIR, "output")
CCTV_URL = "rtsp://evanne:evanne123@192.168.1.33:554/stream1"
NO_ID_COOLDOWN = 5

os.makedirs(os.path.join(OUTPUT_FOLDER, "person_with_id"), exist_ok=True)
os.makedirs(os.path.join(OUTPUT_FOLDER, "person_without_id"), exist_ok=True)
os.makedirs(os.path.join(OUTPUT_FOLDER, "admin_snapshots"), exist_ok=True)
os.makedirs(os.path.join(OUTPUT_FOLDER, "guard_snapshots"), exist_ok=True)

LABEL_MAP = {
    "id": "person_with_id",
    "with_id": "person_with_id",
    "withid": "person_with_id",
    "wearing_id": "person_with_id",
    "person_with_id": "person_with_id",
    "no_id": "person_without_id",
    "noid": "person_without_id",
    "without_id": "person_without_id",
    "person_without_id": "person_without_id",
}

model = YOLO(MODEL_PATH)
print("Model classes:", model.names)


class AlertSignal(QObject):
    alert = Signal(str, str)  # message, ai_result


class CCTVFeed:
    def __init__(self, display_label, alert_callback=None):
        self.label = display_label
        self.alert_callback = alert_callback
        self.alert_signal = AlertSignal()
        if self.alert_callback:
            self.alert_signal.alert.connect(self.alert_callback)

        self.cap = None
        self.running = False
        self.latest_frame = None
        self.processed_frame = None
        self.last_no_id_time = 0
        self.camera_id = 1
        self.detection_counter = 0

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_gui)

    def start_feed(self):
        self.cap = cv2.VideoCapture(CCTV_URL)
        if not self.cap.isOpened():
            print("[ERROR] Cannot open CCTV stream")
            return

        self.running = True
        threading.Thread(target=self.capture_frames, daemon=True).start()
        threading.Thread(target=self.run_inference, daemon=True).start()
        self.timer.start(33)

    def stop_feed(self):
        self.running = False
        if self.cap:
            self.cap.release()

    def capture_frames(self):
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                self.latest_frame = cv2.resize(frame, (640, 384))

    def run_inference(self):
        while self.running:
            if self.latest_frame is None:
                continue

            frame = self.latest_frame.copy()
            self.latest_frame = None
            results = model.predict(source=frame, imgsz=384, show=False, save=False, verbose=False)
            annotated_frame = frame.copy()

            for r in results:
                if hasattr(r, "boxes") and r.boxes is not None and len(r.boxes) > 0:
                    annotated_frame = r.plot()
                    for box in r.boxes:
                        cls_id = int(box.cls[0])
                        raw_label = str(model.names[cls_id]).lower().strip()
                        mapped_label = LABEL_MAP.get(raw_label, "person_with_id")
                        confidence = float(box.conf[0])

                        # Increment detection counter
                        self.detection_counter += 1

                        # Save snapshots and insert into DB
                        detection_id = self.save_snapshot(frame, confidence, mapped_label)
                        self.save_admin_snapshot(frame, confidence)
                        self.save_guard_snapshot(frame, confidence)

                        # Emit alert with mapped label
                        if self.alert_callback:
                            self.alert_signal.alert.emit(
                                f"{mapped_label.upper()} detected | Camera: {self.camera_id} | Det: {self.detection_counter}",
                                mapped_label
                            )

            self.processed_frame = annotated_frame

    def update_gui(self):
        if self.processed_frame is not None:
            rgb_image = cv2.cvtColor(self.processed_frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_image).scaled(
                self.label.width(), self.label.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.label.setPixmap(pixmap)

    def save_snapshot(self, frame, confidence, mapped_label):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        filename = f"cam{self.camera_id}_det{self.detection_counter}_conf{confidence:.2f}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        path = os.path.join(OUTPUT_FOLDER, mapped_label, filename)
        cv2.imwrite(path, frame)

        try:
            detection_id = insert_detection(
                camera_id=self.camera_id,
                confidence_score=confidence,
                ai_result=mapped_label,
                image_path=path,
                timestamp=timestamp
            )
            return detection_id
        except Exception as e:
            print(f"⚠ Failed to insert detection: {e}")
            return 0

    def save_admin_snapshot(self, frame, confidence):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"cam{self.camera_id}_admin_det{self.detection_counter}_conf{confidence:.2f}_{timestamp}.jpg"
        path = os.path.join(OUTPUT_FOLDER, "admin_snapshots", filename)
        cv2.imwrite(path, frame)

    def save_guard_snapshot(self, frame, confidence):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"cam{self.camera_id}_guard_det{self.detection_counter}_conf{confidence:.2f}_{timestamp}.jpg"
        path = os.path.join(OUTPUT_FOLDER, "guard_snapshots", filename)
        cv2.imwrite(path, frame)
