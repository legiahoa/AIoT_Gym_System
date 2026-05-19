import cv2
import mediapipe as mp
import paho.mqtt.client as mqtt
from flask import Flask, Response, request, send_from_directory
import threading
import time
import os
import shutil
import numpy as np

# ==========================================

# 1. CẤU HÌNH MQTT & ĐƯỜNG DẪN MẠNG
MQTT_BROKER = "broker.emqx.io" 
MQTT_PORT = 1883
TOPIC_COMMAND = "fitness/app/command" 
TOPIC_RESULT = "fitness/iot/result"   

# IP CUA THIET BI IOT
IP_PYTHON = "192.168.1.15" 

# ==========================================

# 2. BIẾN TOÀN CỤC & FLASK APP
app = Flask(__name__, static_folder='static')
output_frame = None
lock = threading.Lock()

is_recording = False
video_writer = None
temp_filename = "temp_set.mp4"

mp_pose = mp.solutions.pose
pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)
mp_draw = mp.solutions.drawing_utils

# ==========================================

# 3. CÁC HÀM XỬ LÝ CHÍNH

def save_local_and_notify():
    """Luồng ngầm: Chuyển file mp4 vào thư mục static và gửi URL cho Android"""
    print("Đang xử lý file video nội bộ...")
    try:
        # Tạo tên file duy nhất dựa trên thời gian
        final_filename = f"exercise_{int(time.time())}.mp4"
        save_path = os.path.join("static", "videos", final_filename)
        
        # Di chuyển file từ thư mục tạm vào thư mục static/videos
        shutil.move(temp_filename, save_path)
        
        # Tạo đường link nội bộ để Android có thể truy cập
        video_url = f"http://{IP_PYTHON}:5000/videos/{final_filename}"
        print(f"Lưu thành công! URL: {video_url}")
        
        # Bắn URL về cho Android qua MQTT
        client.publish(TOPIC_RESULT, f"UPLOAD_SUCCESS|{video_url}")
            
    except Exception as e:
        print(f"Lỗi lưu file: {e}")
        client.publish(TOPIC_RESULT, "UPLOAD_FAILED")

def on_mqtt_message(client, userdata, msg):
    global is_recording, video_writer
    command = msg.payload.decode()
    print(f"Nhận được lệnh MQTT: {command}")
    
    if command == "START":
        if not is_recording:
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

# API mới: Cho phép Android truy cập file MP4
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

# Thêm hàm tính góc vào trước hàm process_camera
def calculate_angle(a, b, c):
    """Tính góc giữa 3 điểm a, b, c (b là đỉnh góc)"""
    a = np.array(a) # Điểm đầu
    b = np.array(b) # Đỉnh góc (VD: Đầu gối)
    c = np.array(c) # Điểm cuối
    
    radians = np.arctan2(c[1]-b[1], c[0]-b[0]) - np.arctan2(a[1]-b[1], a[0]-b[0])
    angle = np.abs(radians*180.0/np.pi)
    
    if angle > 180.0:
        angle = 360 - angle
        
    return angle

# Biến toàn cục đếm số rep tập
squat_stage = None 
squat_counter = 0

def process_camera():
    global output_frame, lock, is_recording, video_writer
    global squat_stage, squat_counter # Lấy biến toàn cục
    
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    while cap.isOpened():
        success, frame = cap.read()
        if not success: continue

        # Nếu bạn đã xoay dọc camera thực tế, hãy bỏ comment dòng dưới đây
        # frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)

        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(image_rgb)

        if results.pose_landmarks:
            mp_draw.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
            
            # TRÍCH XUẤT TỌA ĐỘ VÀ TÍNH TOÁN (Logic cho bài SQUAT)
            try:
                landmarks = results.pose_landmarks.landmark
                
                # Lấy tọa độ Vai, Hông, Đầu gối, Cổ chân (bên phải)
                shoulder = [landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].x, landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].y]
                hip = [landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].x, landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].y]
                knee = [landmarks[mp_pose.PoseLandmark.RIGHT_KNEE.value].x, landmarks[mp_pose.PoseLandmark.RIGHT_KNEE.value].y]
                ankle = [landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE.value].x, landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE.value].y]
                
                # 1. Tính góc Đầu gối (Đánh giá độ sâu của Squat)
                knee_angle = calculate_angle(hip, knee, ankle)
                
                # 2. Tính góc Lưng so với phương thẳng đứng (Đánh giá lỗi gập lưng)
                # Tạo một điểm tham chiếu thẳng đứng từ hông dóng lên trên
                vertical_ref = [hip[0], 0] 
                back_angle = calculate_angle(shoulder, hip, vertical_ref)

                # Hiển thị góc đầu gối lên màn hình video để dễ debug
                cv2.putText(frame, f"Knee: {int(knee_angle)}", (10, 80), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                cv2.putText(frame, f"Back: {int(back_angle)}", (10, 110), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

                # --- LOGIC ĐÁNH GIÁ ĐÚNG SAI ---
                if is_recording:
                    # Lỗi 1: Gập lưng quá sâu về phía trước (Góc lưng > 45 độ)
                    if back_angle > 45:
                        client.publish(TOPIC_RESULT, "WARNING|Lưng gập quá thấp!")
                    
                    # Bộ đếm Rep & Đánh giá độ sâu
                    if knee_angle > 160: # Trạng thái đứng thẳng
                        squat_stage = "up"
                    
                    if knee_angle < 90 and squat_stage == 'up': # Trạng thái ngồi xổm (đúng chuẩn)
                        squat_stage = "down"
                        squat_counter += 1
                    elif 90 <= knee_angle <= 130 and squat_stage == 'up':
                        # Cảnh báo nếu hạ người chưa đủ sâu mà đã đứng lên
                        # client.publish(TOPIC_RESULT, "WARNING|Xuống chưa đủ sâu!")
                        pass

            except Exception as e:
                pass # Bỏ qua frame nếu thuật toán mất dấu điểm khớp
            
        # UI: Ghi chú đang quay và đếm số Rep
        if is_recording:
            cv2.circle(frame, (30, 30), 10, (0, 0, 255), -1) 
            cv2.putText(frame, f"REC | Reps: {squat_counter}", (50, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            video_writer.write(frame)

        with lock:
            output_frame = frame.copy()

if __name__ == "__main__":
    t = threading.Thread(target=process_camera)
    t.daemon = True
    t.start()
    print("Khởi động server Stream tại cổng 5000...")
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True, use_reloader=False)