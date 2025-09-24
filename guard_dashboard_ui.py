import os
import time
from functools import partial
from database import get_connection, insert_feedback

from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QFrame, QTextEdit, QTableWidget, QTableWidgetItem, QSizePolicy,
    QSpacerItem, QComboBox, QFileDialog, QMessageBox, QHeaderView,
    QDialog, QScrollArea
)
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtCore import Qt, QTimer

from cctv_feed import CCTVFeed


class ImagePreviewDialog(QDialog):
    """Fullscreen preview of a detection snapshot."""
    def __init__(self, image_path: str, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setModal(True)

        layout = QVBoxLayout(self)
        container = QFrame()
        container.setStyleSheet("background-color: rgba(0,0,0,200); border-radius: 8px;")
        container_layout = QVBoxLayout(container)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(36, 36)
        close_btn.setStyleSheet("background: rgba(255,255,255,0.08); color: white; border-radius: 18px;")
        close_btn.clicked.connect(self.accept)
        top_row = QHBoxLayout()
        top_row.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum))
        top_row.addWidget(close_btn)
        container_layout.addLayout(top_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")
        self.image_holder = QLabel(alignment=Qt.AlignCenter)
        scroll.setWidget(self.image_holder)
        container_layout.addWidget(scroll, stretch=1)

        pixmap = QPixmap(image_path) if image_path and os.path.exists(image_path) else QPixmap(400, 400)
        if pixmap.isNull():
            pixmap.fill(Qt.gray)

        screen = parent.screen() if parent else self.screen()
        screen_size = screen.availableGeometry().size()
        scaled = pixmap.scaled(
            screen_size.width() * 0.9,
            screen_size.height() * 0.9,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.image_holder.setPixmap(scaled)
        self.resize(scaled.width() + 80, scaled.height() + 80)
        layout.addWidget(container)


class IncidentDialog(QDialog):
    """Dialog for logging incidents."""
    def __init__(self, detection_id, camera_id, confidence, timestamp, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Log Incident")
        self.resize(500, 320)
        layout = QVBoxLayout(self)

        info_label = QLabel(
            f"<b>Detection:</b> {detection_id} | <b>Camera:</b> {camera_id} | "
            f"<b>Confidence:</b> {confidence:.2f} | <b>Time:</b> {timestamp}"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        type_row = QHBoxLayout()
        type_row.addWidget(QLabel("Person Type:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Professor", "Guard", "Visitor", "Student"])
        type_row.addWidget(self.type_combo)
        layout.addLayout(type_row)

        self.note_edit = QTextEdit()
        self.note_edit.setPlaceholderText("Additional comments…")
        layout.addWidget(self.note_edit)

        btn_row = QHBoxLayout()
        cancel_btn = QPushButton("Cancel"); cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("Save Incident"); save_btn.clicked.connect(self.accept)
        btn_row.addWidget(cancel_btn); btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    def get_inputs(self):
        return self.type_combo.currentText(), self.note_edit.toPlainText().strip()


class GuardDashboardWindow(QWidget):
    """Main dashboard for guards."""
    def __init__(self, user_id, username):
        super().__init__()
        self.setWindowTitle(f"Guard Dashboard - {username}")
        self.showMaximized()

        self.user_id = user_id
        self.username = username
        self.dark_mode = False
        self.new_alerts_count = 0
        self.detection_notes = {}
        self.incidents = set()
        self.known_detections = set()

        self.cctv_feed = None
        self.cctv_label = None
        self.stats_label = None
        self.alerts_dropdown = None
        self._alerts_list = []

        self.setup_ui()

        # Auto-refresh timer for logs table
        self.auto_refresh_timer = QTimer()
        self.auto_refresh_timer.timeout.connect(self.auto_refresh_logs)
        self.auto_refresh_timer.start(5000)  # refresh every 5 seconds

    # ---------- UI Setup ----------
    def setup_ui(self):
        main_layout = QHBoxLayout(self)

        sidebar = QVBoxLayout()
        btn_style = ("QPushButton{padding:10px;border-radius:6px;background:#2D2D44;color:white;} "
                     "QPushButton:hover{background:#00A8E8;}")

        buttons = [("CCTV Live Feed", self.show_cctv),
                   ("Detection Logs", self.show_logs),
                   ("Export Logs", self.export_logs)]
        for text, slot in buttons:
            b = QPushButton(text); b.setStyleSheet(btn_style); b.clicked.connect(slot)
            sidebar.addWidget(b)

        self.theme_button = QPushButton("🌙 Dark Mode")
        self.theme_button.setStyleSheet(btn_style)
        self.theme_button.clicked.connect(self.toggle_theme)
        sidebar.addWidget(self.theme_button)
        sidebar.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding))
        main_layout.addLayout(sidebar, 1)

        self.content = QFrame()
        content_layout = QVBoxLayout(self.content)

        top_bar = QHBoxLayout()
        self.stats_label = QLabel("👤 Total: 0 | ✅ With ID: 0 | ❌ No ID: 0")
        self.stats_label.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        top_bar.addWidget(self.stats_label)
        top_bar.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum))

        self.bell_icon = QPushButton(f"🔔 {self.new_alerts_count}")
        self.bell_icon.setCursor(Qt.PointingHandCursor)
        self.bell_icon.setFixedSize(50, 40)
        self.bell_icon.setStyleSheet("""
            QPushButton {background-color:#2D2D44;color:#F1FAEE;font-size:16px;border-radius:8px;border:1px solid #00A8E8;}
            QPushButton:hover {background-color:#00A8E8;color:white;}
        """)
        self.bell_icon.clicked.connect(self.toggle_alerts_dropdown)
        top_bar.addWidget(self.bell_icon)

        content_layout.addLayout(top_bar)
        main_layout.addWidget(self.content, 4)

        self.show_cctv()

    # ---------- Pages ----------
    def clear_content(self):
        layout = self.content.layout()
        for i in reversed(range(layout.count())):
            w = layout.itemAt(i).widget()
            if w: w.setParent(None)

    def show_cctv(self):
        self.clear_content()
        layout = self.content.layout()
        title = QLabel("CCTV Live Feed", alignment=Qt.AlignCenter)
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        layout.addWidget(title)

        if not self.cctv_label:
            self.cctv_label = QLabel()
            self.cctv_label.setStyleSheet("background:black;")
            self.cctv_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.cctv_label, stretch=1)

        if not self.cctv_feed:
            try:
                self.cctv_feed = CCTVFeed(self.cctv_label, alert_callback=self.add_alert)
                self.cctv_feed.start_feed()
            except Exception as e:
                QMessageBox.warning(self, "CCTV Error", f"CCTV feed failed: {e}")

    def show_logs(self):
        self.clear_content()
        layout = self.content.layout()
        title = QLabel("Detection Logs", alignment=Qt.AlignCenter)
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        layout.addWidget(title)

        self.logs_table = QTableWidget()
        self.logs_table.setColumnCount(7)
        self.logs_table.setHorizontalHeaderLabels(
            ["Photo", "Detection ID", "Camera ID", "Confidence", "Timestamp", "AI Result", "Action"]
        )
        self.logs_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.logs_table.verticalHeader().setDefaultSectionSize(100)
        layout.addWidget(self.logs_table)

        self.populate_logs_table()

    # ---------- Populate Logs ----------
    def populate_logs_table(self):
        cnx = get_connection()
        cur = cnx.cursor(dictionary=True)
        cur.execute("""
            SELECT detection_id, camera_id, confidence_score, ai_result,
                   timestamp, image_path
            FROM detection
            ORDER BY detection_id ASC
        """)
        rows = cur.fetchall()
        cur.close(); cnx.close()

        total = with_id = no_id = 0
        existing_ids = set(self.known_detections)

        for d in rows:
            det_id = d["detection_id"]
            if det_id in existing_ids:
                continue  # skip already added
            self.known_detections.add(det_id)

            total += 1
            if d["ai_result"] == "person_with_id":
                with_id += 1
            else:
                no_id += 1

            row_index = self.logs_table.rowCount()
            self.logs_table.insertRow(row_index)

            thumb = QLabel(alignment=Qt.AlignCenter)
            pixmap = QPixmap(d["image_path"]) if d["image_path"] and os.path.exists(d["image_path"]) else QPixmap(100, 100)
            if pixmap.isNull():
                pixmap.fill(Qt.gray)
            thumb.setPixmap(pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            thumb.mousePressEvent = partial(self._on_thumb_click, d["image_path"])
            self.logs_table.setCellWidget(row_index, 0, thumb)

            self.logs_table.setItem(row_index, 1, self.center_item(str(d["detection_id"])))
            self.logs_table.setItem(row_index, 2, self.center_item(str(d["camera_id"])))
            self.logs_table.setItem(row_index, 3, self.center_item(f"{d['confidence_score']:.2f}"))
            self.logs_table.setItem(row_index, 4, self.center_item(str(d["timestamp"])))
            self.logs_table.setItem(row_index, 5, self.center_item(d["ai_result"]))

            btn = QPushButton("⚠ Incident")
            btn.setStyleSheet("background:#E63946;color:white;border-radius:6px;")
            btn.clicked.connect(partial(
                self._on_incident,
                row_index,
                d["detection_id"],
                d["camera_id"],
                d["confidence_score"],
                d["timestamp"],
                d["image_path"]
            ))
            self.logs_table.setCellWidget(row_index, 6, btn)

        # Update stats (cumulative)
        total_all = len(self.known_detections)
        with_id_all = sum(1 for d_id in self.known_detections if self.get_ai_result(d_id) == "person_with_id")
        no_id_all = total_all - with_id_all
        self.stats_label.setText(f"👤 Total: {total_all} | ✅ With ID: {with_id_all} | ❌ No ID: {no_id_all}")

    # ---------- Helper to get AI result by detection_id ----------
    def get_ai_result(self, detection_id):
        cnx = get_connection()
        cur = cnx.cursor(dictionary=True)
        cur.execute("SELECT ai_result FROM detection WHERE detection_id=%s", (detection_id,))
        row = cur.fetchone()
        cur.close(); cnx.close()
        return row["ai_result"] if row else ""

    # ---------- Actions ----------
    def _on_thumb_click(self, path, event):
        ImagePreviewDialog(path, parent=self).exec()

    def _on_incident(self, row, detection_id, camera_id, confidence, timestamp, path):
        dlg = IncidentDialog(detection_id, camera_id, confidence, timestamp, self)
        if dlg.exec() != QDialog.Accepted:
            return
        person_type, comment = dlg.get_inputs()
        try:
            insert_feedback(detection_id=int(detection_id), user_id=int(self.user_id),
                            category=person_type, notes=comment)
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Could not save feedback:\n{e}")
            return
        self.incidents.add(int(detection_id))
        if comment:
            self.detection_notes[int(detection_id)] = comment
        self.mark_row_incident(row)
        QMessageBox.information(self, "Saved", "Incident logged successfully.")

    def mark_row_incident(self, row):
        for col in range(self.logs_table.columnCount()):
            item = self.logs_table.item(row, col)
            if not item:
                item = QTableWidgetItem()
                self.logs_table.setItem(row, col, item)
            item.setBackground(Qt.green)
        btn = self.logs_table.cellWidget(row, 6)
        if isinstance(btn, QPushButton):
            btn.setText("✅ Logged")
            btn.setEnabled(False)
            btn.setStyleSheet("background:#4CAF50;color:white;border-radius:6px;")

    # ---------- Alerts ----------
    def add_alert(self, message):
        self.new_alerts_count += 1
        self.update_bell()
        self._alerts_list.append((time.time(), message))

    def toggle_alerts_dropdown(self):
        if not self.alerts_dropdown:
            self.alerts_dropdown = QFrame(self)
            self.alerts_dropdown.setFrameShape(QFrame.StyledPanel)
            self.alerts_dropdown.setStyleSheet(
                "background-color:#2D2D44;border:1px solid #00A8E8;border-radius:8px;"
            )
            self.alerts_dropdown.setLayout(QVBoxLayout())
            self.alerts_dropdown.setWindowFlags(Qt.Popup)
            self.alerts_dropdown.setMinimumWidth(300)
            self.alerts_dropdown.setMaximumHeight(300)

        if self.alerts_dropdown.isVisible():
            self.alerts_dropdown.hide()
        else:
            layout = self.alerts_dropdown.layout()
            while layout.count():
                item = layout.takeAt(0)
                if item.widget(): item.widget().deleteLater()
            for _, msg in sorted(self._alerts_list, key=lambda x: x[0], reverse=True)[:10]:
                lbl = QLabel(msg); lbl.setWordWrap(True)
                lbl.setStyleSheet("color:white;padding:4px;")
                layout.addWidget(lbl)
            layout.addStretch()
            pos = self.bell_icon.mapToGlobal(self.bell_icon.rect().bottomLeft())
            screen = QApplication.primaryScreen().availableGeometry()
            x = min(pos.x(), screen.right()-300)
            y = pos.y() if pos.y()+300 < screen.bottom() else pos.y()-300-self.bell_icon.height()
            self.alerts_dropdown.move(x, y)
            self.alerts_dropdown.show()
            self.new_alerts_count = 0
            self.update_bell()

    def update_bell(self):
        self.bell_icon.setText(f"🔔 {self.new_alerts_count}")

    # ---------- Auto-refresh ----------
    def auto_refresh_logs(self):
        if hasattr(self, "logs_table") and self.logs_table.isVisible():
            self.populate_logs_table()

    # ---------- Export ----------
    def export_logs(self):
        if not hasattr(self, "logs_table") or self.logs_table.rowCount() == 0:
            QMessageBox.warning(self, "Error", "No logs to export.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save Logs", "logs.csv", "CSV Files (*.csv)")
        if not path:
            return
        import csv
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["detection_id","camera_id","confidence","timestamp","note","incident","image_path"])
            for r in range(self.logs_table.rowCount()):
                det = self.logs_table.item(r, 1).text()
                cam = self.logs_table.item(r, 2).text()
                conf = self.logs_table.item(r, 3).text()
                ts  = self.logs_table.item(r, 4).text()
                note = self.detection_notes.get(int(det), "")
                inc  = "yes" if int(det) in self.incidents else "no"
                w.writerow([det, cam, conf, ts, note, inc, ""])
        QMessageBox.information(self, "Exported", f"Logs saved to {path}")

    # ---------- Utilities ----------
    def center_item(self, text):
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignCenter)
        return item

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        QApplication.instance().setStyleSheet(self.dark_qss() if self.dark_mode else self.light_qss())
        self.theme_button.setText("☀ Light Mode" if self.dark_mode else "🌙 Dark Mode")

    def dark_qss(self):
        return """
        QWidget { background-color:#1e1e2f;color:#f0f0f0; }
        QPushButton { background-color:#2D2D44;color:white;border-radius:6px;padding:6px; }
        QPushButton:hover { background-color:#00A8E8; }
        QTableWidget { background:#2b2b3d; gridline-color:#555; }
        QHeaderView::section { background:#2D2D44;color:white; }
        QTextEdit { background:#2b2b3d;color:white; }
        """

    def light_qss(self):
        return """
        QWidget { background-color: #f7f7f7; color: #202020; }
        QPushButton {
            background-color: #e0e0e0; color: #202020; border-radius:6px; padding:6px;
        }
        QPushButton:hover { background-color: #c0c0c0; }
        QTableWidget { background:white; gridline-color:#aaa; }
        QHeaderView::section { background:#e0e0e0; color:#202020; }
        QTextEdit { background:white; color:#202020; }
        """


if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    win = GuardDashboardWindow(user_id=1, username="guard1")
    win.show()
    sys.exit(app.exec())
