import cv2
import mediapipe as mp
import csv
import os
import glob

# ==========================================
# CẤU HÌNH PIPELINE
# ==========================================
VIDEO_DIR = "raw_videos"
CSV_OUTPUT = "squat_dataset_extracted.csv"

mp_pose = mp.solutions.pose
pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)

# ==========================================
# KHỞI TẠO FILE CSV (Nếu chưa có)
# ==========================================
if not os.path.exists(CSV_OUTPUT):
    with open(CSV_OUTPUT, mode='w', newline='') as f:
        writer = csv.writer(f)
        header = ["label"] # Lưu ý: Cột đầu tiên giờ là 'label' do con người quy định, không phải 'math_label' nữa
        for i in range(33):
            header.extend([f"x_{i}", f"y_{i}", f"z_{i}", f"v_{i}"])
        writer.writerow(header)

# ==========================================
# TIẾN TRÌNH VẮT DỮ LIỆU TỰ ĐỘNG
# ==========================================
print(f"BẮT ĐẦU TRÍCH XUẤT DỮ LIỆU TỪ THƯ MỤC: {VIDEO_DIR}...")
total_frames_extracted = 0

# Duyệt qua các thư mục con (0, 1, 2 đại diện cho các nhãn)
for label_folder in os.listdir(VIDEO_DIR):
    folder_path = os.path.join(VIDEO_DIR, label_folder)
    
    # Bỏ qua nếu không phải là thư mục
    if not os.path.isdir(folder_path):
        continue
        
    try:
        # Ép tên thư mục thành số nguyên để làm nhãn (0, 1, 2)
        current_label = int(label_folder)
    except ValueError:
        print(f"Bỏ qua thư mục {label_folder} vì tên không phải là số (nhãn).")
        continue

    # Tìm tất cả các file video mp4 trong thư mục này
    video_files = glob.glob(os.path.join(folder_path, "*.mp4")) + glob.glob(os.path.join(folder_path, "*.avi"))
    
    for video_file in video_files:
        print(f"Đang xử lý: {video_file} (Nhãn: {current_label})...")
        cap = cv2.VideoCapture(video_file)
        frame_count = 0
        
        while cap.isOpened():
            success, frame = cap.read()
            if not success:
                break # Hết video
            
            # Xử lý MediaPipe
            image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = pose.process(image_rgb)
            
            if results.pose_landmarks:
                try:
                    row = [current_label]
                    for lm in results.pose_landmarks.landmark:
                        row.extend([lm.x, lm.y, lm.z, lm.visibility])
                    
                    # Ghi ngay vào CSV
                    with open(CSV_OUTPUT, mode='a', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerow(row)
                        
                    frame_count += 1
                    total_frames_extracted += 1
                except Exception as e:
                    pass
                    
        cap.release()
        print(f"  -> Xong! Thu được {frame_count} khung hình.")

print("==========================================")
print(f"HOÀN THÀNH! Tổng cộng đã trích xuất được {total_frames_extracted} khung hình dữ liệu.")
print(f"File kết quả được lưu tại: {CSV_OUTPUT}")