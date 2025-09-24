import sys
from PySide6.QtWidgets import QApplication
from login import LoginWindow
from database import insert_detection, insert_feedback, get_recent_detections

# Example: logging a detection
insert_detection(camera_id=1, ai_result="ID worn", confidence_score=97.5, image_path="images/img1.jpg")

# Example: logging feedback
insert_feedback(detection_id=1, user_id=1, category="ID missing", notes="Student forgot ID today")

# Example: getting recent detections
detections = get_recent_detections(5)
for d in detections:
    print(d)



if __name__ == "__main__":
    app = QApplication(sys.argv)
    login_window = LoginWindow()
    login_window.show()
    sys.exit(app.exec())
