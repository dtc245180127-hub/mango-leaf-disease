"""
API Chẩn đoán Bệnh Lá Xoài bằng Trí tuệ Nhân tạo (FastAPI)
- Cung cấp RESTful API endpoint cho ứng dụng di động, web khác, hoặc hệ thống IoT
- Hỗ trợ mọi định dạng ảnh từ điện thoại: JPG, JPEG, PNG, WEBP, BMP, HEIC/HEIF (iPhone)
- Tự động xoay ảnh theo chiều chụp điện thoại (EXIF transpose)
- Tự động hòa trộn nền trong suốt của ảnh PNG lên nền trắng
"""

import io
import os
import sys
import numpy as np
import tensorflow as tf
from PIL import Image, ImageOps
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional

# Khắc phục lỗi font console Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Hỗ trợ định dạng HEIC/HEIF từ iPhone / iPad
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    pass

# ─── KHỞI TẠO FASTAPI APP ───────────────────────────────────────────────────
app = FastAPI(
    title="Mango Leaf Disease Classification API",
    description="API chẩn đoán bệnh lá xoài và nhận diện đối tượng ngoài luồng",
    version="2.0.0",
)

# Cho phép truy cập từ mọi thiết bị (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── DANH SÁCH LỚP PHÂN LOẠI ───────────────────────────────────────────────
CLASS_NAMES = [
    "Anthracnose",
    "Dieback",
    "Gall_Midge",
    "Healthy",
    "Powdery_Mildew",
    "Red_Rust",
    "Sooty_Mold",
    "Unknown",
]

CLASS_NAMES_VN = [
    "Bệnh thán thư",
    "Bệnh khô cành",
    "Bệnh bọ xít muỗi",
    "Lá khỏe mạnh",
    "Bệnh phấn trắng",
    "Bệnh rỉ sắt",
    "Bệnh bồ hóng",
    "Không phải lá xoài",
]

DISEASE_INFO = {
    "Anthracnose": {
        "symptoms": "Vết đốm đen hoặc nâu sẫm, viền vàng, xuất hiện khắp phiến lá, có thể gây thủng lá.",
        "prevention": "Cắt tỉa cành tạo độ thông thoáng, phun thuốc gốc đồng (Copper oxychloride) hoặc Mancozeb vào đầu mùa mưa.",
    },
    "Dieback": {
        "symptoms": "Chóp lá và mép lá khô cháy từ ngoài vào trong, cành non héo rũ từ ngọn xuống.",
        "prevention": "Cắt bỏ phần cành lá khô đem tiêu hủy, quét vôi hoặc Booc-đô lên vết cắt, bổ sung phân kali.",
    },
    "Gall_Midge": {
        "symptoms": "Lá nổi mụn cóc, mụn sần sùi dày đặc do ấu trùng bọ xít muỗi chích hút tạo u sưng.",
        "prevention": "Thu gom lá rụng tiêu hủy, dùng bẫy dính màu vàng, phun thuốc đặc trị rầy mềm/bọ xít muỗi khi cây ra đọt non.",
    },
    "Healthy": {
        "symptoms": "Lá xoài xanh mướt, phiến lá bóng bẩy, không có vết đốm sần hay đốm cháy.",
        "prevention": "Duy trì chế độ tưới nước, bón phân cân đối N-P-K theo từng thời kỳ sinh trưởng.",
    },
    "Powdery_Mildew": {
        "symptoms": "Lớp phấn trắng hoặc xám như bụi bột bao phủ mặt lá non và chùm hoa.",
        "prevention": "Phun thuốc có hoạt chất gốc lưu huỳnh hoặc Hexaconazole khi phát hiện mầm bệnh ban đầu.",
    },
    "Red_Rust": {
        "symptoms": "Vết đốm tròn màu gỉ sắt hoặc cam đỏ, bề mặt như nhung ở mặt trên của lá già.",
        "prevention": "Tăng cường ánh sáng cho tán cây, phun thuốc diệt tảo và thuốc trừ nấm gốc đồng.",
    },
    "Sooty_Mold": {
        "symptoms": "Mảng muội đen bồ hóng bám dày đặc trên bề mặt lá do nấm phát triển trên dịch ngọt của rệp.",
        "prevention": "Phun trừ rệp sáp, rầy mềm để cắt nguồn thức ăn của nấm, rửa tán lá bằng vòi nước áp lực.",
    },
    "Unknown": {
        "symptoms": "Đối tượng không thuộc lá xoài hoặc ngoài luồng dữ liệu của hệ thống.",
        "prevention": "Vui lòng chụp lại cận cảnh phiến lá xoài cần chẩn đoán.",
    },
}

# ─── NẠP MÔ HÌNH TENSORFLOW ────────────────────────────────────────────────
MODEL_PATH = "mango_leaf_model.keras"
model = None

try:
    if os.path.exists(MODEL_PATH):
        model = tf.keras.models.load_model(MODEL_PATH, compile=False)
        print(f"✅ [API] Đã nạp thành công mô hình từ: {MODEL_PATH}")
    else:
        print(f"⚠️ [API] Không tìm thấy file {MODEL_PATH}")
except Exception as e:
    print(f"❌ [API] Lỗi khi nạp mô hình: {e}")


def process_image_bytes(image_bytes: bytes) -> np.ndarray:
    """Xử lý ảnh từ bytes: hỗ trợ HEIC, JPG, PNG transparent, EXIF orientation"""
    raw = Image.open(io.BytesIO(image_bytes))

    # Tự động xoay ảnh theo EXIF orientation từ điện thoại
    try:
        raw = ImageOps.exif_transpose(raw)
    except Exception:
        pass

    # Xử lý PNG có nền trong suốt -> ghép lên nền trắng
    if raw.mode in ("RGBA", "LA") or (raw.mode == "P" and "transparency" in raw.info):
        bg = Image.new("RGB", raw.size, (255, 255, 255))
        raw_rgba = raw.convert("RGBA")
        bg.paste(raw_rgba, mask=raw_rgba.split()[3])
        image = bg
    else:
        image = raw.convert("RGB")

    # Resize theo chuẩn MobileNetV2
    size = (224, 224)
    image_resized = ImageOps.fit(image, size, Image.Resampling.LANCZOS)
    img_array = np.array(image_resized).astype(np.float32)

    # Mô hình fine-tuned đã có preprocess_input bên trong đồ thị, truyền raw [0, 255]
    has_internal_preprocess = any(
        "data_augmentation" in getattr(l, "name", "")
        or "preprocess" in getattr(l, "name", "")
        for l in model.layers
    )
    if not has_internal_preprocess:
        img_array = tf.keras.applications.mobilenet_v2.preprocess_input(img_array)

    return np.expand_dims(img_array, axis=0)


# ─── ENDPOINTS ─────────────────────────────────────────────────────────────
@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": "Mango Leaf Disease Classifier API",
        "version": "2.0.0",
        "docs_url": "/docs",
        "endpoints": {
            "predict": "POST /predict (Upload image file)",
            "classes": "GET /classes",
            "health": "GET /health",
        },
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "model_path": MODEL_PATH,
    }


@app.get("/classes")
def get_classes():
    return [
        {"id": i, "name": name, "vietnamese": vn}
        for i, (name, vn) in enumerate(zip(CLASS_NAMES, CLASS_NAMES_VN))
    ]


@app.post("/predict")
async def predict_leaf(file: UploadFile = File(...)):
    """
    Endpoint chẩn đoán bệnh lá xoài từ ảnh tải lên.
    Hỗ trợ: JPG, JPEG, PNG, WEBP, BMP, HEIC/HEIF (iPhone).
    """
    if model is None:
        raise HTTPException(status_code=503, detail="Mô hình AI chưa sẵn sàng.")

    try:
        content = await file.read()
        img_tensor = process_image_bytes(content)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Không thể đọc file ảnh: {str(e)}. Hãy chắc chắn file là ảnh hợp lệ.",
        )

    # Chạy dự đoán
    raw_preds = model.predict(img_tensor, verbose=0)[0]
    preds = [float(p) for p in raw_preds]

    predicted_idx = int(np.argmax(preds))
    confidence = float(preds[predicted_idx] * 100)
    raw_label = CLASS_NAMES[predicted_idx]

    # Tổng xác suất của 7 bệnh thực tế (trừ Unknown)
    disease_total_prob = float(np.sum(preds[:7]) * 100)

    # Cơ chế xử lý Unknown thông minh: nếu có dấu hiệu bệnh > 20% thì ưu tiên bệnh
    is_unknown = (raw_label == "Unknown")
    if is_unknown and disease_total_prob >= 20.0:
        best_disease_idx = int(np.argmax(preds[:7]))
        predicted_idx = best_disease_idx
        confidence = float(preds[predicted_idx] * 100)
        raw_label = CLASS_NAMES[predicted_idx]
        is_unknown = False

    result_vn = CLASS_NAMES_VN[predicted_idx]
    info = DISEASE_INFO.get(raw_label, {})

    # Tạo bảng xác suất chi tiết
    all_probabilities = {
        name: round(prob * 100, 2)
        for name, prob in zip(CLASS_NAMES, preds)
    }

    warning_msg = None
    if is_unknown:
        warning_msg = "Ảnh có khả năng cao là đối tượng ngoài luồng (không phải lá xoài)."
    elif confidence < 40.0:
        warning_msg = f"Độ tin cậy thấp ({confidence:.1f}%). Khuyến nghị chụp lại cận cảnh với ánh sáng tốt hơn."

    return {
        "success": True,
        "predicted_class": raw_label,
        "predicted_class_vn": result_vn,
        "confidence_percent": round(confidence, 2),
        "is_unknown": is_unknown,
        "disease_total_prob_percent": round(disease_total_prob, 2),
        "warning": warning_msg,
        "symptoms": info.get("symptoms"),
        "prevention": info.get("prevention"),
        "all_probabilities_percent": all_probabilities,
    }


if __name__ == "__main__":
    import uvicorn
    # Chạy trên mọi giao diện mạng (0.0.0.0) cổng 8000
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=False)
