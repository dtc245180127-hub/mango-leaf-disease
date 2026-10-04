# 🌿 HỆ THỐNG NHẬN DIỆN & CHẨN ĐOÁN BỆNH LÁ XOÀI BẰNG TRÍ TUỆ NHÂN TẠO (AI)

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://meks6shbxyo4ers7qrrzwm.streamlit.app)
[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11-blue.svg)](https://www.python.org/)
[![TensorFlow](https://img.shields.io/badge/TensorFlow-2.18-orange.svg)](https://www.tensorflow.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **Đồ án môn học / Dự án nghiên cứu ứng dụng AI trong Nông nghiệp thông minh.**  
> Ứng dụng mô hình Deep Learning (Transfer Learning với MobileNetV2) nhằm phát hiện sớm và chẩn đoán chính xác các bệnh thường gặp trên lá xoài, đồng thời đưa ra phác đồ điều trị và biện pháp chăm sóc kịp thời cho nhà vườn.

---

## 🌐 Trải Nghiệm Trực Tuyến

Bạn có thể truy cập và sử dụng trực tiếp ứng dụng tại:  
👉 **[https://meks6shbxyo4ers7qrrzwm.streamlit.app](https://meks6shbxyo4ers7qrrzwm.streamlit.app)**  
*(Tương thích mượt mà trên cả trình duyệt máy tính và điện thoại di động).*

---

## ✨ Tính Năng Nổi Bật

1. **Phân Loại Đa Lớp Chuẩn Xác (8 Lớp):**
   - Chẩn đoán 7 loại bệnh phổ biến hại lá xoài và nhận diện lá khỏe mạnh:
     - 🍂 **Anthracnose** (*Bệnh thán thư*)
     - 🥀 **Dieback** (*Bệnh khô cành / chết ngược*)
     - 🦟 **Gall Midge** (*Bọ xít muỗi / Bọ trĩ tạo u*)
     - 🍃 **Healthy** (*Lá khỏe mạnh*)
     - ⚪ **Powdery Mildew** (*Bệnh phấn trắng*)
     - 🔴 **Red Rust** (*Bệnh rỉ sắt*)
     - 🌑 **Sooty Mold** (*Bệnh nấm bồ hóng*)
     - 🚫 **Unknown** (*Chặn đối tượng ngoài luồng: lá cây khác, đất cát, đồ vật, động vật...*)
2. **Giao Diện Hiện Đại & Tối Ưu Cho Thiết Bị Di Động:**
   - Thiết kế giao diện thân thiện, chuẩn thẩm mỹ, tự động co giãn linh hoạt trên mọi kích thước màn hình điện thoại.
   - Trực quan hóa dữ liệu qua **Đồng hồ đo độ tin cậy** và **Biểu đồ cột phân bố xác suất** trực quan.
3. **Cơ Chế Tiền Xử Lý Ảnh Thông Minh:**
   - Tự động sửa góc xoay ảnh chụp từ điện thoại thông qua metadata EXIF.
   - Hỗ trợ ảnh trong suốt (PNG Transparent) tự động ghép lên nền trắng chuẩn.
   - Hỗ trợ đa dạng định dạng: JPG, JPEG, PNG, WEBP, BMP, HEIC/HEIF (ảnh chụp iPhone).
4. **Cung Cấp Phác Đồ Điều Trị & Chăm Sóc:**
   - Mỗi kết quả chẩn đoán đi kèm mô tả triệu chứng chi tiết và biện pháp sinh học, hóa học cụ thể để người trồng xử lý kịp thời.
5. **Tích Hợp Sẵn RESTful API (FastAPI):**
   - Cung cấp các endpoint chuẩn JSON phục vụ kết nối với Mobile App (iOS / Android), hệ thống nhúng IoT hoặc thiết bị bay nông nghiệp (Drone).

---

## 📁 Cấu Trúc Thư Mục Dự Án

```text
├── .streamlit/
│   └── config.toml          # Cấu hình máy chủ Streamlit (giới hạn dung lượng tải ảnh, giao diện)
├── anhbackgroud.png         # Hình nền giao diện web
├── api.py                   # RESTful API Server xây dựng bằng FastAPI
├── app.py                   # Giao diện Web tương tác xây dựng bằng Streamlit
├── mango_leaf_model.keras   # Trọng số mô hình AI đã qua huấn luyện (MobileNetV2 Fine-tuned)
├── requirements.txt         # Danh sách các thư viện cần cài đặt
├── train.py                 # File mã nguồn phục vụ việc huấn luyện & fine-tuning mô hình
└── README.md                # Tài liệu hướng dẫn sử dụng dự án
```

---

## 🛠️ Hướng Dẫn Cài Đặt & Chạy Cục Bộ (Local)

### 1. Yêu Cầu Môi Trường
- Python 3.10 hoặc 3.11
- Git

### 2. Tải Mã Nguồn Về Máy
```bash
git clone https://github.com/dtc245180127-hub/mango-leaf-disease.git
cd mango-leaf-disease
```

### 3. Cài Đặt Các Thư Viện Cần Thiết
Khuyến nghị tạo môi trường ảo (Virtualenv / Conda) trước khi cài đặt:
```bash
# Tạo môi trường ảo
python -m venv venv

# Kích hoạt trên Windows:
.\venv\Scripts\activate

# Kích hoạt trên Linux/macOS:
source venv/bin/activate

# Cài đặt thư viện:
pip install -r requirements.txt
```

---

## 🚀 Khởi Chạy Ứng Dụng

### Cách 1: Chạy Ứng Dụng Web Streamlit
Mở terminal tại thư mục dự án và chạy lệnh:
```bash
streamlit run app.py
```
Sau đó truy cập trình duyệt tại địa chỉ: `http://localhost:8501`.

---

### Cách 2: Khởi Chạy RESTful API Server (FastAPI)
Mở terminal và khởi động server API:
```bash
python api.py
```
*(Hoặc chạy lệnh: `uvicorn api:app --host 0.0.0.0 --port 8000 --reload`)*

- **Trang tài liệu tương tác Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Kiểm tra trạng thái (Health Check):** [http://localhost:8000/health](http://localhost:8000/health)

#### Ví Dụ Gọi API Bằng cURL:
```bash
curl -X POST "http://localhost:8000/predict" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@duong_dan_anh_la_xoai.jpg"
```

#### Ví Dụ Gọi API Bằng Python:
```python
import requests

url = "http://localhost:8000/predict"
with open("la_xoai.jpg", "rb") as f:
    response = requests.post(url, files={"file": f})

print(response.json())
```

---

## 🧠 Kiến Trúc Mô Hình & Huấn Luyện

- **Kiến trúc cốt lõi:** `MobileNetV2` (Pre-trained trên tập dữ liệu ImageNet).
- **Kích thước đầu vào:** `(224, 224, 3)`.
- **Kỹ thuật tối ưu:**
  - Transfer Learning kết hợp Fine-Tuning các tầng Convolution cuối.
  - Kỹ thuật Data Augmentation (xoay, lật, thay đổi độ tương phản, zoom ngẫu nhiên) giúp chống overfitting.
  - Bổ sung lớp `Unknown` để phát hiện và ngăn chặn các vật thể nằm ngoài dữ liệu lá xoài.

---

## 👥 Nhóm Thực Hiện
- **Dự án:** Phân loại và chẩn đoán bệnh lá xoài bằng Trí tuệ nhân tạo.
- **Mã nguồn:** [https://github.com/dtc245180127-hub/mango-leaf-disease](https://github.com/dtc245180127-hub/mango-leaf-disease)
