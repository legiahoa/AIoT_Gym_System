import cv2
import mediapipe as mp
import paho.mqtt.client as mqtt
from flask import Flask, Response, request, send_from_directory
import threading
import time
import os
import shutil
import pandas as pd
import pickle

# ==========================================
# 1. CẤU HÌNH MQTT & ĐƯỜNG DẪN MẠNG
# ==========================================
MQTT_BROKER = "broker.emqx.io" 
MQTT_PORT = 1883
TOPIC_COMMAND = "fitness/app/command" 
TOPIC_RESULT = "fitness/iot/result"   

# IP CỦA THIẾT BỊ IOT (Sửa lại IP máy tính của bạn nếu cần)
IP_PYTHON = "172.30.128.1" 

# ==========================================
# 2. BIẾN TOÀN CỤC & FLASK APP & AI MODEL
# ==========================================
app = Flask(__name__, static_folder='static')
output_frame = None
lock = threading.Lock()

is_recording = False
video_writer = None
temp_filename = "temp_set.mp4"
last_alert_time = 0  # Chống spam tin nhắn MQTT

mp_pose = mp.solutions.pose
pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)
mp_draw = mp.solutions.drawing_utils

# Biến dùng cho Logic đếm Rep hoàn toàn bằng AI kết hợp Hình học
squat_stage = "up" 
squat_counter = 0

# Nạp mô hình ML ngay khi khởi động
MODEL_FILE = "squat_model.pkl"
try:
    with open(MODEL_FILE, 'rb') as f:
        model = pickle.load(f)
    print(f"[AI CORE] Đã nạp thành công mô hình: {MODEL_FILE}")
except Exception as e:
    print(f"[AI CORE] Lỗi nạp mô hình: {e}. Vui lòng chạy train_model.py trước.")
    model = None

# ==========================================
# 3. CÁC HÀM XỬ LÝ CHÍNH
# ==========================================
def save_local_and_notify():
    """Luồng ngầm: Chuyển file mp4 vào thư mục static và gửi URL cho Android"""
    print("Đang xử lý file video nội bộ...")
    try:
        final_filename = f"exercise_{int(time.time())}.mp4"
        save_path = os.path.join("static", "videos", final_filename)
        
        # Đảm bảo thư mục tồn tại
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        shutil.move(temp_filename, save_path)
        
        video_url = f"http://{IP_PYTHON}:5000/videos/{final_filename}"
        print(f"Lưu thành công! URL: {video_url}")
        
        client.publish(TOPIC_RESULT, f"UPLOAD_SUCCESS|{video_url}")
    except Exception as e:
        print(f"Lỗi lưu file: {e}")
        client.publish(TOPIC_RESULT, "UPLOAD_FAILED")

def on_mqtt_message(client, userdata, msg):
    global is_recording, video_writer, squat_counter, squat_stage
    command = msg.payload.decode()
    print(f"Nhận được lệnh MQTT: {command}")
    
    if command == "START":
        if not is_recording:
            squat_counter = 0
            squat_stage = "up"
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            video_writer = cv2.VideoWriter(temp_filename, fourcc, 20.0, (640, 480))
            is_recording = True
            print("ĐÃ BẮT ĐẦU GHI HÌNH!")
            
    elif command == "STOP":
        if is_recording:
            is_recording = False
            if video_writer is not None:
                video_writer.release()
                video_writer = None
            print("ĐÃ KẾT THÚC GHI HÌNH!")
            threading.Thread(target=save_local_and_notify).start()

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
client.on_message = on_mqtt_message
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.subscribe(TOPIC_COMMAND)
client.loop_start()

# ==========================================
# 4. XỬ LÝ CAMERA & FLASK ROUTES
# ==========================================
@app.route('/videos/<filename>')
def play_video(filename):
    return send_from_directory(os.path.join(app.root_path, 'static', 'videos'), filename)

def generate_stream():
    global output_frame, lock
    while True:
        with lock:
            if output_frame is None:
                continue
            (flag, encodedImage) = cv2.imencode(".jpg", output_frame)
            if not flag:
                continue
        yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + bytearray(encodedImage) + b'\r\n')

@app.route("/video_feed")
def video_feed():
    return Response(generate_stream(), mimetype="multipart/x-mixed-replace; boundary=frame")

def process_camera():
    global output_frame, lock, is_recording, video_writer
    global squat_stage, squat_counter, last_alert_time 
    
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    # KHẮC PHỤC LỖI TÊN CỘT: Bỏ dấu gạch dưới để khớp 100% với file CSV huấn luyện
    feature_names = []
    for i in range(33):
        feature_names.extend([f"x{i}", f"y{i}", f"z{i}", f"v{i}"])

    while cap.isOpened():
        success, frame = cap.read()
        if not success: continue

        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(image_rgb)

        status_text = "DANG QUET..."
        color = (200, 200, 200)

        if results.pose_landmarks:
            mp_draw.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
            
            try:
                landmarks = results.pose_landmarks.landmark
                
                # --- THUẬT TOÁN HÌNH HỌC: XÁC ĐỊNH TRẠNG THÁI ĐỨNG ---
                left_hip_y = landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].y
                right_hip_y = landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].y
                left_knee_y = landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].y
                right_knee_y = landmarks[mp_pose.PoseLandmark.RIGHT_KNEE.value].y
                
                avg_hip_y = (left_hip_y + right_hip_y) / 2.0
                avg_knee_y = (left_knee_y + right_knee_y) / 2.0
                
                # Nếu hông cao hơn đầu gối 1 khoảng an toàn -> Đang đứng
                if avg_hip_y < avg_knee_y - 0.15:
                    status_text = "STATE: STANDING"
                    color = (255, 255, 255) # Trắng
                    squat_stage = "up"
                else:
                    # --- AI INFERENCE: KHI BẮT ĐẦU HẠ NGƯỜI SQUAT ---
                    if model is not None:
                        row = []
                        for lm in landmarks:
                            row.extend([lm.x, lm.y, lm.z, lm.visibility])
                        
                        X_input = pd.DataFrame([row], columns=feature_names)
                        prediction = model.predict(X_input)[0]

                        # AI quy ước: 0 = Chuẩn, 1 = Cong Lưng, 2 = Chưa đủ sâu
                        if prediction == 0:
                            status_text = "FORM: CHUAN"
                            color = (0, 255, 0)
                            if squat_stage == "up":
                                squat_counter += 1
                                squat_stage = "down"
                                
                        elif prediction == 1:
                            status_text = "FORM: SAI LUNG"
                            color = (0, 0, 255)
                            if squat_stage == "up":
                                squat_counter += 1
                                squat_stage = "down"
                                
                        elif prediction == 2:
                            status_text = "FORM: CHUA SAU"
                            color = (0, 165, 255)
                            if squat_stage == "up":
                                squat_counter += 1
                                squat_stage = "down"

                        # Bắn cảnh báo về Android (nếu sai tư thế 1 hoặc 2)
                        current_time = time.time()
                        if is_recording and (prediction in [1, 2]) and (current_time - last_alert_time > 3):
                            if prediction == 1:
                                client.publish(TOPIC_RESULT, "WARNING|Sai tư thế: Bạn đang gập/cong lưng!")
                            elif prediction == 2:
                                client.publish(TOPIC_RESULT, "WARNING|Sai tư thế: Bạn hạ người chưa đủ sâu!")
                            last_alert_time = current_time

            except Exception as e:
                pass 
            
        # UI: Ghi chú đang quay và đếm số Rep
        if is_recording:
            cv2.circle(frame, (30, 30), 10, (0, 0, 255), -1) 
            cv2.putText(frame, f"REC | Reps: {squat_counter}", (50, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            video_writer.write(frame)

        # Hiển thị Status Text lên frame
        cv2.putText(frame, status_text, (10, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        with lock:
            output_frame = frame.copy()

if __name__ == "__main__":
    t = threading.Thread(target=process_camera)
    t.daemon = True
    t.start()
    print("Khởi động server Stream tại cổng 5000...")
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True, use_reloader=False)