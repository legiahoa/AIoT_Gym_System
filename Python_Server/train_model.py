import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
import pickle
import os

# ==========================================
# CẤU HÌNH PIPELINE
# ==========================================
CSV_FILE = "squat_dataset_extracted.csv"
MODEL_FILE = "squat_model.pkl"

print(f"--- KHỞI ĐỘNG ĐƯỜNG ỐNG HUẤN LUYỆN ---")
print(f"1. Đang tải dữ liệu từ {CSV_FILE}...")

if not os.path.exists(CSV_FILE):
    print("LỖI: Không tìm thấy file dữ liệu. Hãy chạy data_extractor.py trước!")
    exit()

df = pd.read_csv(CSV_FILE)

# ==========================================
# TIỀN XỬ LÝ & PHÂN TÁCH DỮ LIỆU
# ==========================================
# X: Bỏ cột label đi, chỉ lấy tọa độ các điểm khớp (Features)
X = df.drop('label', axis=1)
# y: Chỉ lấy cột label (Target)
y = df['label']

# Chia dữ liệu theo tỷ lệ chuẩn: 80% để AI học, 20% để làm bài kiểm tra
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

print(f"2. Đã chia dữ liệu: {X_train.shape[0]} mẫu để học, {X_test.shape[0]} mẫu để test.")

# ==========================================
# KHỞI TẠO & HUẤN LUYỆN MÔ HÌNH
# ==========================================
print("3. Đang huấn luyện thuật toán Random Forest...")
# n_estimators=100 nghĩa là tạo ra 100 "cây quyết định" khác nhau để biểu quyết
model = RandomForestClassifier(n_estimators=100,class_weight='balanced', random_state=42)
model.fit(X_train, y_train)

# ==========================================
# ĐÁNH GIÁ KẾT QUẢ CỦA "HỌC SINH"
# ==========================================
print("4. Đang làm bài kiểm tra trên tập Test...")
y_pred = model.predict(X_test)

accuracy = accuracy_score(y_test, y_pred)
print(f"\n>>> ĐỘ CHÍNH XÁC (ACCURACY): {accuracy * 100:.2f}% <<<")
print("\nBÁO CÁO CHI TIẾT TỪNG NHÃN TƯ THẾ:")
print(classification_report(y_test, y_pred, zero_division=0))

# ==========================================
# XUẤT XƯỞNG MÔ HÌNH
# ==========================================
print("5. Đang đóng gói mô hình...")
with open(MODEL_FILE, 'wb') as f:
    pickle.dump(model, f)

print(f"HOÀN TẤT! File não bộ AI đã được lưu tại: {MODEL_FILE}")
print("---------------------------------------")