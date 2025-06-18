from flask import Flask, render_template, Response, request, redirect, url_for, session, jsonify, send_file
import cv2
from detection import detect_objects, screenshot_frame, toggle_recording, log_to_db, get_latest_alerts, get_alert_stats
import os
from database import initialize_user_db, register_user, validate_user

app = Flask(__name__)
app.secret_key = 'supersecretkey'
camera = cv2.VideoCapture(0)

recording = [False]
current_frame = [None]

# Live feed generator
def generate():
    while True:
        success, frame = camera.read()
        if not success:
            break
        frame, alerts = detect_objects(frame, recording[0])
        current_frame[0] = frame
        if alerts:
            for alert in alerts:
                log_to_db(alert)
        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/')
def login_page():
    return render_template('login.html')

@app.route('/login', methods=['GET'])
def login_get():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def do_login():
    username = request.form['username']
    password = request.form['password']
    if validate_user(username, password):
        session['logged_in'] = True
        return redirect(url_for('dashboard'))
    return "Login Failed", 401

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        print(f"Register attempt: {username}")
        if register_user(username, password):
            print("Registration successful")
            return redirect(url_for('login_get'))
        else:
            print("User already exists")
            return "User already exists", 409
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login_page'))

@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login_page'))
    return render_template('index.html')

@app.route('/video')
def video():
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/screenshot', methods=['POST'])
def take_screenshot():
    if current_frame[0] is not None:
        screenshot_frame(current_frame[0])
    return ('', 204)

@app.route('/record', methods=['POST'])
def toggle_record():
    recording[0] = not recording[0]
    toggle_recording(recording[0])
    return ('', 204)

@app.route('/download_screenshot')
def download_screenshot():
    folder = "static/screenshots"
    files = sorted([f for f in os.listdir(folder) if f.endswith(".jpg")])
    if files:
        return send_file(os.path.join(folder, files[-1]), as_attachment=True)
    return "No screenshots found", 404

@app.route('/download_video')
def download_video():
    folder = "static/recordings"
    files = sorted([f for f in os.listdir(folder) if f.endswith(".avi")])
    if files:
        return send_file(os.path.join(folder, files[-1]), as_attachment=True)
    return "No recordings found", 404

@app.route('/latest_alerts')
def latest_alerts():
    return jsonify(get_latest_alerts(5))

@app.route('/alert_stats')
def alert_stats():
    return jsonify(get_alert_stats())

if __name__ == "__main__":
    from detection import initialize_db
    initialize_db()
    initialize_user_db()
    app.run(debug=True)
