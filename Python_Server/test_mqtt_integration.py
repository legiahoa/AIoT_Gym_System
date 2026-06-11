import paho.mqtt.client as mqtt
import time
import json
from paho.mqtt.enums import CallbackAPIVersion

# ==========================================
# CẤU HÌNH KẾT NỐI MQTT
# ==========================================
# Lưu ý: Thay 'localhost' bằng địa chỉ IP LAN của máy tính 
# nếu bạn đang dùng điện thoại thật kết nối cùng Wi-Fi
BROKER_ADDRESS = "broker.emqx.io" 
PORT = 1883
TOPIC = "gym/squat/feedback"

def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print("✅ Đã kết nối thành công tới trạm trung chuyển MQTT!")
    else:
        print(f"❌ Kết nối thất bại, mã lỗi: {reason_code}")

# Khởi tạo Client và kết nối
client = mqtt.Client(CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.connect(BROKER_ADDRESS, PORT, 60)

client.loop_start()

print("\n🚀 --- BẮT ĐẦU CHẠY GIẢ LẬP TÍN HIỆU AI ---")
time.sleep(1) # Đợi 1 chút để đảm bảo kết nối ổn định

# ==========================================
# KỊCH BẢN 1: TẬP CHUẨN FORM (3 Reps)
# ==========================================
for i in range(1, 4):
    payload = {
        "status": "CORRECT",
        "rep_count": i,
        "message": "Form chuẩn, tiếp tục phát huy!"
    }
    client.publish(TOPIC, json.dumps(payload))
    print(f"[{time.strftime('%H:%M:%S')}] Đã gửi: Nhịp thứ {i} - CORRECT")
    time.sleep(2.5) # Giả lập thời gian hoàn thành 1 nhịp Squat

# ==========================================
# KỊCH BẢN 2: BẮT ĐẦU TẬP SAI CẦN CẢNH BÁO
# ==========================================
print("\n⚠️ [HỆ THỐNG] Phát hiện người dùng bắt đầu sai form...")
time.sleep(1)

# Lỗi 1: Cong lưng
payload_error_1 = {
    "status": "BACK_BENT",
    "rep_count": 3,
    "message": "CẢNH BÁO: Lưng đang bị cong, hãy siết cơ bụng và giữ thẳng lưng!"
}
client.publish(TOPIC, json.dumps(payload_error_1))
print(f"[{time.strftime('%H:%M:%S')}] Đã bắn tín hiệu lỗi - BACK_BENT")
time.sleep(3) # Đợi người dùng sửa dáng

# Lỗi 2: Xuống chưa đủ sâu
payload_error_2 = {
    "status": "INSUFFICIENT_DEPTH",
    "rep_count": 3,
    "message": "CẢNH BÁO: Squat chưa đủ biên độ, hãy xuống sâu thêm chút nữa!"
}
client.publish(TOPIC, json.dumps(payload_error_2))
print(f"[{time.strftime('%H:%M:%S')}] Đã bắn tín hiệu lỗi - INSUFFICIENT_DEPTH")

time.sleep(1)
client.loop_stop()
client.disconnect()
print("\n🏁 --- KẾT THÚC KỊCH BẢN KIỂM THỬ ---")