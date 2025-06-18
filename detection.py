from ultralytics import YOLO
import cv2
import datetime
import os
import sqlite3

model = YOLO("models/yolov8n.pt")
record_writer = None

CLASSES = {
    0: "person",
    1: "helmet",
    2: "fire",
    3: "fall"
}

DB_NAME = "detection_logs.db"

def initialize_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    class TEXT,
                    timestamp TEXT
                 )''')
    conn.commit()
    conn.close()

def log_to_db(class_name):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO alerts (class, timestamp) VALUES (?, ?)",
              (class_name, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def get_latest_alerts(limit=5):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT class, timestamp FROM alerts ORDER BY id DESC LIMIT ?", (limit,))
    data = [{"class": row[0], "time": row[1]} for row in c.fetchall()]
    conn.close()
    return data

def get_alert_stats():
    stats = {"person": 0, "helmet": 0, "fire": 0, "fall": 0}
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    for key in stats.keys():
        c.execute("SELECT COUNT(*) FROM alerts WHERE class = ?", (key,))
        stats[key] = c.fetchone()[0]
    conn.close()
    return stats

def detect_objects(frame, record=False):
    global record_writer
    alerts = []
    results = model(frame, verbose=False)
    annotated = results[0].plot()

    for result in results:
        for box in result.boxes:
            cls_id = int(box.cls[0])
            name = CLASSES.get(cls_id, "unknown")
            if name in CLASSES.values():
                alerts.append(name)

    if record:
        if record_writer is None:
            now = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            os.makedirs("static/recordings", exist_ok=True)
            record_writer = cv2.VideoWriter(f"static/recordings/{now}.avi", cv2.VideoWriter_fourcc(*"XVID"), 20, (frame.shape[1], frame.shape[0]))
        record_writer.write(annotated)
    elif record_writer is not None:
        record_writer.release()
        record_writer = None

    return annotated, list(set(alerts))

def screenshot_frame(frame):
    os.makedirs("static/screenshots", exist_ok=True)
    now = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    cv2.imwrite(f"static/screenshots/screenshot_{now}.jpg", frame)

def toggle_recording(record):
    global record_writer
    if not record and record_writer is not None:
        record_writer.release()
        record_writer = None
