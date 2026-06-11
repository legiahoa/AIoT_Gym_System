import os
import cv2
import mediapipe as mp
import pandas as pd
import csv

# ==========================================
# CẤU HÌNH MEDIAPIPE & ĐƯỜNG DẪN
# ==========================================
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(static_image_mode=True, min_detection_confidence=0.5)

# ĐƯỜNG DẪN ĐẾN THƯ MỤC TRAIN VÀ FILE CLASSES
DATASET_DIR = r"D:\UIT\HK6\DACN\Squat Posture Corrector.multiclass\train"
CLASSES_CSV_PATH = os.path.join(DATASET_DIR, "_classes.csv")
OUTPUT_CSV = "squat_dataset_extracted.csv"

# ==========================================
# KHỞI TẠO FILE CSV ĐẦU RA
# ==========================================
header = []
for i in range(33):
    header.extend([f'x{i}', f'y{i}', f'z{i}', f'v{i}'])
header.append('label')

with open(OUTPUT_CSV, mode='w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(header)

print("🚀 ĐANG ĐỌC FILE NHÃN _classes.csv...")

# ==========================================
# XỬ LÝ DỮ LIỆU
# ==========================================
try:
    # 1. Đọc file _classes.csv bằng pandas
    # Dùng list comprehension để làm sạch tên cột (loại bỏ khoảng trắng dư thừa)
    df = pd.read_csv(CLASSES_CSV_PATH)
    df.columns = [col.strip() for col in df.columns] 
    
    processed_count = 0
    print("⏳ BẮT ĐẦU TRÍCH XUẤT TỌA ĐỘ TỪNG ẢNH...")

    # 2. Duyệt qua từng dòng trong file CSV
    for index, row in df.iterrows():
        # Lấy tên file ảnh
        filename = str(row['filename']).strip()
        image_path = os.path.join(DATASET_DIR, filename)

        # Bỏ qua nếu file ảnh không tồn tại
        if not os.path.exists(image_path):
            continue

        # 3. Xác định nhãn (label) của ảnh hiện tại
        # Quy ước đồ án của bạn: 0 = Chuẩn, 1 = Cong lưng, 2 = Chưa đủ sâu
        label_id = -1
        
        # Kiểm tra giá trị ở các cột tương ứng trong file CSV (giá trị 1 nghĩa là có lỗi đó)
        if 'Good_Squat' in df.columns and row['Good_Squat'] == 1:
            label_id = 0
        elif 'Bent_Over_Squat' in df.columns and row['Bent_Over_Squat'] == 1:
            label_id = 1
        elif 'Shallow_Squat' in df.columns and row['Shallow_Squat'] == 1:
            label_id = 2
            
        # Nếu ảnh bị lỗi khác (nhón gót...) hoặc không xác định được, bỏ qua ảnh đó
        if label_id == -1:
            continue

        # 4. Đọc ảnh và trích xuất bằng MediaPipe
        image = cv2.imread(image_path)
        if image is None:
            continue

        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = pose.process(image_rgb)

        # 5. Ghi tọa độ nếu MediaPipe tìm thấy khung xương
        if results.pose_landmarks:
            row_data = []
            for landmark in results.pose_landmarks.landmark:
                row_data.extend([landmark.x, landmark.y, landmark.z, landmark.visibility])
            
            row_data.append(label_id)

            with open(OUTPUT_CSV, mode='a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(row_data)
            processed_count += 1
            
            # Cứ mỗi 20 ảnh in ra 1 lần để theo dõi tiến độ
            if processed_count % 20 == 0:
                print(f"  -> Đã xử lý {processed_count} ảnh...")

    print(f"\n✅ HOÀN TẤT! Đã trích xuất thành công {processed_count} bộ tọa độ.")
    print(f"File dữ liệu đã được lưu tại: {OUTPUT_CSV}")

except FileNotFoundError:
    print(f"❌ LỖI: Không tìm thấy file {CLASSES_CSV_PATH}. Bạn kiểm tra lại đường dẫn nhé!")
except Exception as e:
    print(f"❌ LỖI KHÔNG XÁC ĐỊNH: {e}")