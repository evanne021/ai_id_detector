import sys
from PySide6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout,
    QMessageBox, QSpacerItem, QSizePolicy, QFrame, QApplication
)
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt

from admin_dashboard_ui import AdminDashboardWindow
from guard_dashboard_ui import GuardDashboardWindow
from database import get_user_by_credentials


class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI ID Detection - Login")
        self.showMaximized()  # Fullscreen
        self.setStyleSheet("background-color: #1E1E2F; color: #FFFFFF;")
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Spacer top
        main_layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # Login panel
        panel = QFrame()
        panel.setFixedSize(400, 400)
        panel.setStyleSheet("""
            QFrame {
                background-color: #2D2D44;
                border-radius: 15px;
            }
            QLabel {
                font-size: 16px;
            }
            QLineEdit {
                font-size: 14px;
                padding: 8px;
                border: 1px solid #555;
                border-radius: 8px;
                background-color: #3E3E5E;
                color: #FFF;
            }
            QPushButton {
                font-size: 16px;
                padding: 10px;
                border-radius: 10px;
                background-color: #00A8E8;
                color: #FFF;
            }
            QPushButton:hover {
                background-color: #0077B6;
            }
        """)

        panel_layout = QVBoxLayout()
        panel_layout.setContentsMargins(40, 40, 40, 40)
        panel_layout.setSpacing(20)

        # Title
        title = QLabel("AI ID Detection System")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        panel_layout.addWidget(title)

        # Username
        panel_layout.addWidget(QLabel("Username:"))
        self.username_input = QLineEdit()
        panel_layout.addWidget(self.username_input)
        self.username_input.returnPressed.connect(self.check_login)

        # Password
        panel_layout.addWidget(QLabel("Password:"))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        panel_layout.addWidget(self.password_input)
        self.password_input.returnPressed.connect(self.check_login)

        # Login button
        self.login_button = QPushButton("Login")
        self.login_button.clicked.connect(self.check_login)
        panel_layout.addWidget(self.login_button)

        panel.setLayout(panel_layout)

        # Center panel horizontally
        h_layout = QHBoxLayout()
        h_layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum))
        h_layout.addWidget(panel)
        h_layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum))

        main_layout.addLayout(h_layout)

        # Spacer bottom
        main_layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding))

        self.setLayout(main_layout)

    def check_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "Login Failed", "Please enter both username and password")
            return

        # Query the database for credentials
        user = get_user_by_credentials(username, password)

        if user:
            role = user["role"]
            if role == "admin":
                self.dashboard = AdminDashboardWindow(user)  # <-- pass full user dict
            else:
                self.dashboard = GuardDashboardWindow(user)  # <-- pass full user dict
            self.dashboard.show()
            self.close()
        else:
            QMessageBox.warning(self, "Login Failed", "Invalid username or password")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    login_window = LoginWindow()
    login_window.show()
    sys.exit(app.exec())
