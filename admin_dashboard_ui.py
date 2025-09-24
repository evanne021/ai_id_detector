import sys, os, shutil, datetime
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QListWidget, QListWidgetItem, QFileDialog,
    QMessageBox, QStackedWidget, QTableWidget, QTableWidgetItem,
    QLineEdit, QFormLayout, QDialog, QDialogButtonBox, QHeaderView,
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QComboBox, QCalendarWidget,
    QFrame
)
from PySide6.QtGui import QFont, QPixmap, QImage, QTextCharFormat, QColor
from PySide6.QtCore import Qt, QDate
from database import insert_user, insert_feedback, insert_detection, get_connection


# ---------------- Dialogs ----------------
class UserDialog(QDialog):
    def __init__(self, parent=None, name="", role="", username="", password=""):
        super().__init__(parent)
        self.setWindowTitle("Add / Edit User")
        self.setFixedSize(320, 240)
        layout = QVBoxLayout()
        form = QFormLayout()

        self.name_input = QLineEdit(name)
        self.role_input = QLineEdit(role)
        self.username_input = QLineEdit(username)
        self.password_input = QLineEdit(password)
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)

        form.addRow("Name:", self.name_input)
        form.addRow("Role:", self.role_input)
        form.addRow("Username:", self.username_input)
        form.addRow("Password:", self.password_input)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def get_data(self):
        return (
            self.name_input.text().strip(),
            self.role_input.text().strip(),
            self.username_input.text().strip(),
            self.password_input.text().strip()
        )


class CameraDialog(QDialog):
    def __init__(self, location="", status="online"):
        super().__init__()
        self.setWindowTitle("Camera Settings")
        self.setFixedSize(360, 180)
        layout = QVBoxLayout()
        form = QFormLayout()
        self.location_input = QLineEdit(location)
        self.status_input = QLineEdit(status)
        form.addRow("Location:", self.location_input)
        form.addRow("Status:", self.status_input)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def get_data(self):
        return self.location_input.text().strip(), self.status_input.text().strip()


from PySide6.QtWidgets import QDialog, QVBoxLayout, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
from PySide6.QtGui import QPixmap, QImage, QPainter
from PySide6.QtCore import Qt

from PySide6.QtWidgets import QDialog, QVBoxLayout, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QApplication
from PySide6.QtGui import QPixmap, QImage, QPainter
from PySide6.QtCore import Qt

class SnapshotViewer(QDialog):
    def __init__(self, image_path):
        super().__init__()
        self.setWindowTitle("Snapshot Viewer")

        # Get screen size and set window to 70% of width and height
        screen = QApplication.primaryScreen()
        screen_size = screen.size()
        width = int(screen_size.width() * 0.7)
        height = int(screen_size.height() * 0.7)
        self.resize(width, height)

        layout = QVBoxLayout()
        view = QGraphicsView()
        scene = QGraphicsScene()

        img = QImage(image_path)
        pixmap = QPixmap.fromImage(img)

        # Scale pixmap to fit window while keeping aspect ratio
        scaled_pixmap = pixmap.scaled(width, height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        scene.addItem(QGraphicsPixmapItem(scaled_pixmap))
        view.setScene(scene)

        # Smooth rendering
        view.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)

        layout.addWidget(view)
        self.setLayout(layout)


# ---------------- Export Logs Dialog ----------------
class ExportLogsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Export Logs")
        self.setFixedSize(420, 400)
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Select export type:"))
        self.period_combo = QComboBox()
        self.period_combo.addItems(["Daily", "Weekly", "Monthly"])
        layout.addWidget(self.period_combo)

        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        layout.addWidget(self.calendar)

        self.month_combo = QComboBox()
        self.month_combo.addItems([
            "January","February","March","April","May","June",
            "July","August","September","October","November","December"
        ])
        layout.addWidget(self.month_combo)
        self.month_combo.hide()

        btn_layout = QHBoxLayout()
        self.btn_ok = QPushButton("OK")
        self.btn_cancel = QPushButton("Cancel")
        btn_layout.addWidget(self.btn_ok)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

        self.daily_selected_day = None
        self.weekly_start = None
        self.weekly_end = None

        self.period_combo.currentTextChanged.connect(self.update_period)
        self.calendar.clicked.connect(self.day_clicked)
        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)

        self.update_period(self.period_combo.currentText())

    def update_period(self, period):
        self.clear_calendar_selection()
        if period in ["Daily", "Weekly"]:
            self.calendar.show()
            self.month_combo.hide()
        else:
            self.calendar.hide()
            self.month_combo.show()

    def clear_calendar_selection(self):
        fmt = QTextCharFormat()
        year = self.calendar.yearShown()
        month = self.calendar.monthShown()
        for d in range(1, 32):
            date = QDate(year, month, d)
            if date.isValid():
                self.calendar.setDateTextFormat(date, fmt)

    def day_clicked(self, date):
        period = self.period_combo.currentText()
        if period == "Daily":
            self.clear_calendar_selection()
            fmt = QTextCharFormat()
            fmt.setBackground(QColor("#00BFA5"))
            self.calendar.setDateTextFormat(date, fmt)
            self.daily_selected_day = date
        elif period == "Weekly":
            if not self.weekly_start:
                self.weekly_start = date
            else:
                self.weekly_end = date
                self.highlight_week_range(self.weekly_start, self.weekly_end)

    def highlight_week_range(self, start, end):
        fmt = QTextCharFormat()
        fmt.setBackground(QColor("#00BFA5"))
        current = start
        while current <= end:
            self.calendar.setDateTextFormat(current, fmt)
            current = current.addDays(1)


# ---------------- Admin Dashboard ----------------
class AdminDashboardWindow(QMainWindow):
    def __init__(self, user: dict):
        super().__init__()
        self.user = user

        # FIXED SNAPSHOT FOLDER
        self.snapshots_folder = os.path.join(
            "C:\\Users\\evann\\OneDrive\\Documents\\AI_ID_DETECTOR\\desktop_app\\output",
            "admin_snapshots"
        )
        if not os.path.exists(self.snapshots_folder):
            os.makedirs(self.snapshots_folder)

        self.setWindowTitle(f"Admin Dashboard - {self.user['name']}")
        self.init_ui()
        self.load_users_from_db()
        self.load_cameras_from_db()
        self.load_snapshots()
        self.showMaximized()




    def init_ui(self):
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)

        # Sidebar
        sidebar = QVBoxLayout()
        sidebar.setContentsMargins(10, 10, 10, 10)
        sidebar.setSpacing(10)
        self.title_label = QLabel(f"ADMIN PANEL\nWelcome, {self.user['name']}")
        self.title_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.title_label.setAlignment(Qt.AlignCenter)
        sidebar.addWidget(self.title_label)

        self.btn_dashboard = QPushButton("📊 Dashboard")
        self.btn_snapshots = QPushButton("📁 Snapshots")
        self.btn_users = QPushButton("👥 User Management")
        self.btn_cameras = QPushButton("📷 Camera Settings")
        self.btn_export_logs = QPushButton("📤 Export Logs")
        self.btn_logout = QPushButton("🚪 Logout")

        for btn in [
            self.btn_dashboard, self.btn_snapshots, self.btn_users,
            self.btn_cameras, self.btn_export_logs, self.btn_logout
        ]:
            btn.setMinimumHeight(42)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #FFFFFF; color: #333333; border-radius: 6px; padding: 6px;
                    border: 1px solid #CCC;
                }
                QPushButton:hover { background-color: #E0E0E0; }
            """)
            sidebar.addWidget(btn)
        sidebar.addStretch()

        # Stacked Widget
        self.stacked_widget = QStackedWidget()
        self.page_dashboard = self.create_dashboard_page()
        self.page_snapshots = self.create_snapshots_page()
        self.page_users = self.create_users_page()
        self.page_cameras = self.create_cameras_page()
        for p in [self.page_dashboard, self.page_snapshots, self.page_users, self.page_cameras]:
            self.stacked_widget.addWidget(p)

        # Connections
        self.btn_dashboard.clicked.connect(lambda: self.switch_page(0))
        self.btn_snapshots.clicked.connect(lambda: self.switch_page(1))
        self.btn_users.clicked.connect(lambda: self.switch_page(2))
        self.btn_cameras.clicked.connect(lambda: self.switch_page(3))
        self.btn_export_logs.clicked.connect(self.export_logs_dialog)
        self.btn_logout.clicked.connect(self.logout)

        main_layout.addLayout(sidebar, 1)
        main_layout.addWidget(self.stacked_widget, 4)
        self.setCentralWidget(main_widget)

    # ---------------- Dashboard Page ----------------
    def create_dashboard_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        lbl = QLabel("📊 Real-time Monitoring")
        lbl.setFont(QFont("Segoe UI", 16, QFont.Bold))
        lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl)

        self.stats_frame = QFrame()
        self.stats_frame.setStyleSheet("""
            QFrame { background-color: #FFFFFF; border-radius: 8px; border: 1px solid #DDD; padding: 12px; }
            QLabel { color: #333333; font-family: 'Segoe UI'; font-size: 14px; }
        """)
        stats_layout = QVBoxLayout(self.stats_frame)
        self.stats = QLabel(
            "People Detected: 0\n"
            "Wearing ID: 0\n"
            "Not Wearing ID: 0\n"
            "Cameras Online: 0"
        )
        stats_layout.addWidget(self.stats)
        layout.addWidget(self.stats_frame)
        layout.addStretch()
        return page

    # ---------------- Snapshots Page ----------------
    def create_snapshots_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        lbl = QLabel("📁 Saved Snapshots")
        lbl.setFont(QFont("Segoe UI", 14, QFont.Bold))
        layout.addWidget(lbl)

        self.snapshot_list = QListWidget()
        self.snapshot_list.setAlternatingRowColors(True)
        layout.addWidget(self.snapshot_list)
        self.snapshot_list.itemDoubleClicked.connect(self.preview_snapshot_from_item)

        btn_layout = QHBoxLayout()
        for text, slot in [("🗑️ Delete", self.delete_snapshot), ("💾 Export", self.export_snapshot)]:
            b = QPushButton(text)
            b.clicked.connect(slot)
            b.setStyleSheet("padding:6px; border-radius:6px; background-color:#FFFFFF;")
            btn_layout.addWidget(b)
        layout.addLayout(btn_layout)
        return page

    def preview_snapshot_from_item(self, item):
        if not self.snapshots_folder or not item:
            return
        path = os.path.join(self.snapshots_folder, item.text())
        if os.path.exists(path):
            SnapshotViewer(path).exec()

    # ---------------- Snapshot Auto-Save ----------------
    def save_snapshot(self, image: QImage, filename: str = None):
        if not filename:
            filename = f"snapshot_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        path = os.path.join(self.snapshots_folder, filename)
        image.save(path)
        self.add_snapshot_to_list(filename)

    def add_snapshot_to_list(self, filename):
        for i in range(self.snapshot_list.count()):
            if self.snapshot_list.item(i).text() == filename:
                return
        self.snapshot_list.addItem(QListWidgetItem(filename))

    # ---------------- Load Snapshots ----------------
    def load_snapshots(self):
        self.snapshot_list.clear()
        if not os.path.exists(self.snapshots_folder):
            os.makedirs(self.snapshots_folder)
        for f in os.listdir(self.snapshots_folder):
            if f.lower().endswith((".jpg", ".jpeg", ".png")):
                self.snapshot_list.addItem(QListWidgetItem(f))


    # ---------------- Users Page ----------------
    def create_users_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 10, 10, 10)

        # Extra space at top for cleaner look
        layout.addSpacing(80)

        # Top row with search box on the right
        top_row = QHBoxLayout()
        top_row.addStretch()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search by Name")
        self.search_edit.setFixedWidth(280)   # wider
        self.search_edit.setFixedHeight(44)   # taller
        self.search_edit.setFont(QFont("Arial", 12))
        self.search_edit.setStyleSheet("padding-left:8px;")
        self.search_edit.textChanged.connect(self.filter_users)
        top_row.addWidget(self.search_edit)
        layout.addLayout(top_row)

        lbl = QLabel("👥 User Management")
        lbl.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(lbl)

        self.user_table = QTableWidget(0, 5)
        self.user_table.verticalHeader().setVisible(False)
        self.user_table.setHorizontalHeaderLabels(["#", "Name", "Role", "Username", "Action"])
        self.user_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # Table appearance
        table_font = QFont("Arial", 11)
        self.user_table.setFont(table_font)
        self.user_table.verticalHeader().setDefaultSectionSize(42)

        header = self.user_table.horizontalHeader()
        header.setFixedHeight(48)
        header_font = QFont("Arial", 13, QFont.Bold)
        header.setFont(header_font)
        header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.user_table.setStyleSheet("""
            QTableWidget::item {
                padding-left: 6px;
            }
        """)
        self.user_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.user_table.setSelectionMode(QTableWidget.SingleSelection)

        layout.addWidget(self.user_table)
        return page

    # ---------------- Users CRUD + Search ----------------
    def load_users_from_db(self):
        rows = self.db_query("SELECT user_id,name,role,username FROM user", fetch=True)
        self.all_users = rows
        self._populate_user_table(rows)

    def _populate_user_table(self, rows):
        self.user_table.setRowCount(0)
        for r in rows:
            row = self.user_table.rowCount()
            self.user_table.insertRow(row)
            for col, value in enumerate([r["user_id"], r["name"], r["role"], r["username"]]):
                item = QTableWidgetItem(str(value))
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                self.user_table.setItem(row, col, item)

            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(5, 0, 5, 0)
            btn_layout.setSpacing(8)

            btn_edit = QPushButton("✏️ Edit")
            btn_edit.setStyleSheet("background-color: skyblue; border-radius: 5px; padding:4px;")
            btn_edit.clicked.connect(lambda _, r=row: self.edit_user_by_row(r))

            btn_delete = QPushButton("🗑️ Delete")
            btn_delete.setStyleSheet("background-color: red; color:white; border-radius: 5px; padding:4px;")
            btn_delete.clicked.connect(lambda _, r=row: self.delete_user_by_row(r))

            btn_layout.addWidget(btn_edit)
            btn_layout.addWidget(btn_delete)
            btn_layout.addStretch()
            self.user_table.setCellWidget(row, 4, btn_widget)

    def filter_users(self):
        text = self.search_edit.text().strip().lower()
        if not text:
            self._populate_user_table(self.all_users)
            return
        filtered = [r for r in self.all_users if text in r["name"].lower()]
        self._populate_user_table(filtered)

    def edit_user_by_row(self, row):
        user_id = self.user_table.item(row, 0).text()
        dlg = UserDialog(
            self,
            name=self.user_table.item(row, 1).text(),
            role=self.user_table.item(row, 2).text(),
            username=self.user_table.item(row, 3).text(),
            password=""
        )
        if dlg.exec():
            name, role, username, password = dlg.get_data()
            if not name or not role or not username:
                self.centered_message_box("Missing Data", "Name, role, username required.")
                return
            conn = get_connection()
            try:
                cur = conn.cursor()
                if password:
                    import bcrypt
                    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
                    cur.execute(
                        "UPDATE user SET name=%s, role=%s, username=%s, password=%s WHERE user_id=%s",
                        (name, role, username, hashed, user_id)
                    )
                else:
                    cur.execute(
                        "UPDATE user SET name=%s, role=%s, username=%s WHERE user_id=%s",
                        (name, role, username, user_id)
                    )
                conn.commit()
            finally:
                conn.close()
            self.load_users_from_db()

    def delete_user_by_row(self, row):
        user_id = self.user_table.item(row, 0).text()
        reply = self.centered_message_box("Confirm", "Delete this user?")
        if reply == QMessageBox.Yes:
            self.db_query("DELETE FROM user WHERE user_id=%s", (user_id,))
            self.load_users_from_db()

    # ---------------- Cameras CRUD ----------------
    def create_cameras_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        lbl = QLabel("📷 Camera Settings")
        lbl.setFont(QFont("Arial", 14, QFont.Bold))
        layout.addWidget(lbl)

        self.camera_table = QTableWidget(0, 3)
        self.camera_table.verticalHeader().setVisible(False)
        self.camera_table.setHorizontalHeaderLabels(["ID", "Location", "Status"])
        self.camera_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.camera_table)

        btn_layout = QHBoxLayout()
        for text, slot in [("➕ Add Camera", self.add_camera), ("✏️ Edit Camera", self.edit_camera), ("🗑️ Delete Camera", self.delete_camera)]:
            b = QPushButton(text)
            b.clicked.connect(slot)
            b.setStyleSheet("padding:6px; border-radius:6px; background-color:#FFFFFF;")
            btn_layout.addWidget(b)
        layout.addLayout(btn_layout)
        return page

    def load_cameras_from_db(self):
        self.camera_table.setRowCount(0)
        rows = self.db_query("SELECT camera_id,location,status FROM camera", fetch=True)
        for r in rows:
            row = self.camera_table.rowCount()
            self.camera_table.insertRow(row)
            self.camera_table.setItem(row, 0, QTableWidgetItem(str(r["camera_id"])))
            self.camera_table.setItem(row, 1, QTableWidgetItem(r["location"]))
            self.camera_table.setItem(row, 2, QTableWidgetItem(r["status"]))

    def add_camera(self):
        dlg = CameraDialog()
        if dlg.exec():
            location, status = dlg.get_data()
            if not location or not status:
                self.centered_message_box("Missing Data", "All fields required.")
                return
            self.db_query("INSERT INTO camera (location,status) VALUES (%s,%s)", (location, status))
            self.load_cameras_from_db()

    def edit_camera(self):
        row = self.camera_table.currentRow()
        if row < 0:
            return
        camera_id = self.camera_table.item(row, 0).text()
        dlg = CameraDialog(
            location=self.camera_table.item(row, 1).text(),
            status=self.camera_table.item(row, 2).text()
        )
        if dlg.exec():
            location, status = dlg.get_data()
            self.db_query("UPDATE camera SET location=%s, status=%s WHERE camera_id=%s",
                          (location, status, camera_id))
            self.load_cameras_from_db()

    def delete_camera(self):
        row = self.camera_table.currentRow()
        if row < 0:
            return
        camera_id = self.camera_table.item(row, 0).text()
        reply = self.centered_message_box("Confirm", "Delete this camera?")
        if reply == QMessageBox.Yes:
            self.db_query("DELETE FROM camera WHERE camera_id=%s", (camera_id,))
            self.load_cameras_from_db()

    # ---------------- Snapshot Utilities ----------------
    def delete_snapshot(self):
        row = self.snapshot_list.currentRow()
        if row < 0 or not self.snapshots_folder:
            return
        path = os.path.join(self.snapshots_folder, self.snapshot_list.item(row).text())
        reply = self.centered_message_box("Delete?", f"Delete {os.path.basename(path)}?")
        if reply == QMessageBox.Yes:
            try:
                os.remove(path)
                self.snapshot_list.takeItem(row)
            except Exception as e:
                self.centered_message_box("Error", str(e))

    def export_snapshot(self):
        row = self.snapshot_list.currentRow()
        if row < 0 or not self.snapshots_folder:
            return
        path = os.path.join(self.snapshots_folder, self.snapshot_list.item(row).text())
        folder = QFileDialog.getExistingDirectory(self, "Select Export Folder")
        if folder:
            try:
                shutil.copy(path, folder)
                self.centered_message_box("Exported", f"{os.path.basename(path)} exported to {folder}")
            except Exception as e:
                self.centered_message_box("Error", str(e))

    # ---------------- Utilities ----------------
    def switch_page(self, idx):
        self.stacked_widget.setCurrentIndex(idx)

    def centered_message_box(self, title, text):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(text)
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg_box.setIcon(QMessageBox.Question)
        return msg_box.exec()

    def logout(self):
        reply = self.centered_message_box("Confirm Logout", "Are you sure you want to logout?")
        if reply == QMessageBox.Yes:
            self.close()

    # ---------------- Export Logs ----------------
    def export_logs_dialog(self):
        dlg = ExportLogsDialog(self)
        if dlg.exec():
            period = dlg.period_combo.currentText()
            conn = get_connection()
            try:
                cur = conn.cursor(dictionary=True)
                now = datetime.datetime.now()
                if period == "Daily" and dlg.daily_selected_day:
                    start_date = datetime.datetime(
                        dlg.daily_selected_day.year(),
                        dlg.daily_selected_day.month(),
                        dlg.daily_selected_day.day()
                    )
                    end_date = start_date + datetime.timedelta(days=1)
                elif period == "Weekly" and dlg.weekly_start and dlg.weekly_end:
                    start_date = datetime.datetime(
                        dlg.weekly_start.year(),
                        dlg.weekly_start.month(),
                        dlg.weekly_start.day()
                    )
                    end_date = datetime.datetime(
                        dlg.weekly_end.year(),
                        dlg.weekly_end.month(),
                        dlg.weekly_end.day(),
                        23, 59, 59
                    )
                elif period == "Monthly":
                    month = dlg.month_combo.currentIndex() + 1
                    start_date = datetime.datetime(now.year, month, 1)
                    next_month = month + 1 if month < 12 else 1
                    year = now.year if month < 12 else now.year + 1
                    end_date = datetime.datetime(year, next_month, 1)
                else:
                    return

                cur.execute("SELECT * FROM detection WHERE timestamp >= %s AND timestamp <= %s",
                            (start_date, end_date))
                logs = cur.fetchall()
            finally:
                conn.close()

            folder = QFileDialog.getExistingDirectory(self, "Select Export Folder")
            if folder:
                filename = f"{period.lower()}_logs.csv"
                path = os.path.join(folder, filename)
                try:
                    import csv
                    with open(path, "w", newline="", encoding="utf-8") as f:
                        if logs:
                            writer = csv.DictWriter(f, fieldnames=logs[0].keys())
                            writer.writeheader()
                            for row in logs:
                                writer.writerow(row)
                        else:
                            writer = csv.writer(f)
                            writer.writerow(["No data"])
                    self.centered_message_box("Exported", f"{filename} exported to {folder}")
                except Exception as e:
                    self.centered_message_box("Error", str(e))

    # ---------------- DB Helper ----------------
    def db_query(self, sql, params=None, fetch=False):
        conn = get_connection()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(sql, params or ())
            if fetch:
                return cur.fetchall()
            else:
                conn.commit()
        finally:
            conn.close()


# ---------------- Run ----------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    dummy_user = {"user_id": 1, "name": "Admin", "role": "admin", "username": "admin"}
    win = AdminDashboardWindow(dummy_user)
    win.showMaximized()
    sys.exit(app.exec())
