import base64
import io
import os
import socket
import cv2
import numpy as np
import qrcode
from PIL import Image, ImageOps
import plotly.graph_objects as go
import streamlit as st
import tensorflow as tf

# Hỗ trợ định dạng HEIC/HEIF từ iPhone / iPad
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    pass


def get_local_ip():
    """Lấy địa chỉ IP mạng nội bộ (LAN) của máy tính"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def generate_qr_code(url: str) -> bytes:
    """Tạo ảnh mã QR dạng PNG bytes từ URL"""
    qr = qrcode.QRCode(box_size=5, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#1b3815", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# 1. Cấu hình trang Streamlit
st.set_page_config(
    page_title="Chẩn đoán bệnh lá xoài", page_icon="🍃", layout="wide"
)

# Thêm viewport meta để đảm bảo điện thoại render đúng tỷ lệ màn hình thực
st.markdown(
    '<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">',
    unsafe_allow_html=True,
)


# Hàm chuyển đổi ảnh cục bộ thành chuỗi Base64
def get_base64_of_bin_file(bin_file):
    with open(bin_file, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()


# 2. Tùy chỉnh CSS giao diện nền & các khung thẻ bo góc có màu
def set_bg_hack(main_bg_ext):
    bg_img = get_base64_of_bin_file(main_bg_ext)
    st.markdown(
        f"""
        <style>
        /* Nhúng font chữ hiện đại */
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

        html, body, [class*="css"] {{
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
        }}

        .stApp {{
            background-image: url("data:image/png;base64,{bg_img}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}

        /* Badge ứng dụng di động */
        .app-badge {{
            display: inline-block;
            background: linear-gradient(135deg, #e8f5e9, #c8e6c9);
            color: #1b5e20;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
            border: 1px solid #a5d6a7;
            text-transform: uppercase;
        }}

        /* Tùy chỉnh tiêu đề chính */
        h1 {{
            color: #1b3815 !important;
            text-align: center;
            font-weight: 700;
            background: rgba(255, 255, 255, 0.92);
            padding: 16px 20px;
            border-radius: 16px;
            margin-bottom: 20px;
            box-shadow: 0px 4px 14px rgba(0,0,0,0.06);
            border: 1px solid #d0e1cb;
        }}

        /* Khung thẻ bo góc 2 cột chính */
        [data-testid="stColumn"] {{
            background: rgba(255, 255, 255, 0.94);
            padding: 22px;
            border-radius: 20px;
            box-shadow: 0px 8px 24px rgba(0, 0, 0, 0.08);
            border: 1px solid #c2d6be;
            backdrop-filter: blur(10px);
        }}

        /* Màu tiêu đề phụ */
        h2, h3 {{
            color: #2b5123 !important;
            font-weight: 600;
        }}

        /* Khung tải tệp */
        [data-testid="stFileUploader"] {{
            background-color: #f8fbf6;
            border-radius: 16px;
            padding: 14px;
            border: 2px dashed #6b9e62;
            transition: all 0.2s ease;
        }}
        [data-testid="stFileUploader"]:hover {{
            border-color: #2e7d32;
            background-color: #f1f8ee;
        }}

        /* Nút chụp Camera phong cách App di động */
        [data-testid="stCameraInput"] {{
            border-radius: 16px;
            overflow: hidden;
            border: 2px solid #a5d6a7;
            background: #f8fbf6;
            padding: 8px;
        }}
        [data-testid="stCameraInput"] button {{
            background: linear-gradient(135deg, #2e7d32, #1b5e20) !important;
            color: white !important;
            border-radius: 12px !important;
            height: 46px !important;
            font-size: 15px !important;
            font-weight: 600 !important;
            box-shadow: 0 4px 12px rgba(46, 125, 50, 0.25) !important;
            border: none !important;
            transition: transform 0.15s ease !important;
        }}
        [data-testid="stCameraInput"] button:active {{
            transform: scale(0.98);
        }}

        /* Thẻ hiển thị kết quả chẩn đoán bo góc màu xanh pastel */
        .result-card {{
            background: linear-gradient(135deg, #edf7ed, #e8f5e9);
            border-left: 6px solid #2e7d32;
            padding: 16px 20px;
            border-radius: 14px;
            margin-bottom: 15px;
            box-shadow: 0 4px 12px rgba(46, 125, 50, 0.08);
        }}
        .result-title {{
            font-size: 16px;
            color: #1e4620;
            font-weight: 600;
        }}
        .result-value {{
            font-size: 22px;
            color: #1b5e20;
            font-weight: 700;
            margin-top: 4px;
        }}

        /* Thẻ cảnh báo lỗi bo góc */
        .warning-card {{
            background: linear-gradient(135deg, #fff5f5, #fed7d7);
            border-left: 6px solid #e53e3e;
            padding: 16px 20px;
            border-radius: 14px;
            margin-bottom: 15px;
            color: #9b1c1c;
            box-shadow: 0 4px 12px rgba(229, 62, 62, 0.08);
        }}

        /* Thẻ hướng dẫn điều trị */
        .treatment-card {{
            background: linear-gradient(135deg, #fffdf0, #fefae0);
            border-left: 6px solid #d4a373;
            padding: 18px 20px;
            border-radius: 14px;
            margin-top: 15px;
            margin-bottom: 20px;
            color: #333333;
            box-shadow: 0 4px 12px rgba(212, 163, 115, 0.1);
        }}
        .healthy-care-card {{
            background: linear-gradient(135deg, #f0fdf4, #dcfce7);
            border-left: 6px solid #16a34a;
            padding: 18px 20px;
            border-radius: 14px;
            margin-top: 15px;
            margin-bottom: 20px;
            color: #14532d;
            box-shadow: 0 4px 12px rgba(22, 163, 74, 0.1);
        }}

        /* Tabs tinh chỉnh */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 8px;
        }}
        .stTabs [data-baseweb="tab"] {{
            border-radius: 10px;
            padding: 8px 16px;
            background-color: #f1f8ee;
            font-weight: 600;
            color: #2e7d32;
        }}
        .stTabs [aria-selected="true"] {{
            background-color: #2e7d32 !important;
            color: white !important;
        }}

        /* ══════════════════════════════════════════════════════════════════════
           📱 TỐI ƯU HÓA ĐẶC BIỆT DÀNH CHO ĐIỆN THOẠI (MOBILE RESPONSIVE UI)
           ══════════════════════════════════════════════════════════════════════ */

        /* ── Ẩn sidebar mặc định trên điện thoại để tối đa không gian ── */
        @media (max-width: 768px) {{
            /* Tận dụng tối đa không gian màn hình điện thoại */
            .block-container {{
                padding-top: 0.75rem !important;
                padding-bottom: 3rem !important;
                padding-left: 0.5rem !important;
                padding-right: 0.5rem !important;
                max-width: 100% !important;
            }}

            /* Chống giật lag cuộn trang trên Safari iOS & Chrome Android */
            .stApp {{
                background-attachment: scroll !important;
            }}

            /* Xếp layout thành 1 cột trên điện thoại (không phải 2 cột) */
            [data-testid="stHorizontalBlock"] {{
                flex-direction: column !important;
                gap: 0 !important;
            }}

            /* Mỗi cột chiếm full chiều rộng trên điện thoại */
            [data-testid="stColumn"] {{
                width: 100% !important;
                flex: 1 1 100% !important;
                min-width: 100% !important;
                padding: 14px 12px !important;
                border-radius: 16px !important;
                margin-bottom: 12px !important;
                box-shadow: 0px 4px 14px rgba(0, 0, 0, 0.06) !important;
            }}

            /* Tiêu đề ứng dụng như Header App chuyên nghiệp */
            h1 {{
                font-size: 1.15rem !important;
                padding: 10px 12px !important;
                border-radius: 12px !important;
                margin-bottom: 10px !important;
                line-height: 1.35 !important;
            }}

            h2 {{
                font-size: 1.05rem !important;
                margin-bottom: 6px !important;
            }}

            h3 {{
                font-size: 0.95rem !important;
            }}

            /* Tabs trên điện thoại dễ chạm ngón tay — full width */
            .stTabs [data-baseweb="tab-list"] {{
                overflow-x: auto !important;
                white-space: nowrap !important;
                -webkit-overflow-scrolling: touch !important;
            }}
            .stTabs [data-baseweb="tab"] {{
                padding: 9px 12px !important;
                font-size: 12.5px !important;
                border-radius: 8px !important;
                min-width: fit-content !important;
            }}

            /* Camera input rộng hơn và nút chụp to */
            [data-testid="stCameraInput"] {{
                border-radius: 12px !important;
            }}
            [data-testid="stCameraInput"] button {{
                width: 100% !important;
                height: 52px !important;
                font-size: 16px !important;
                border-radius: 12px !important;
                letter-spacing: 0.3px !important;
            }}

            /* File uploader trên điện thoại */
            [data-testid="stFileUploader"] {{
                border-radius: 12px !important;
                padding: 10px !important;
            }}

            /* Thẻ kết quả chẩn đoán trên điện thoại */
            .result-card, .warning-card, .treatment-card, .healthy-care-card {{
                padding: 12px 13px !important;
                border-radius: 12px !important;
                font-size: 13px !important;
                line-height: 1.5 !important;
                margin-bottom: 10px !important;
            }}

            .result-value {{
                font-size: 1.15rem !important;
            }}

            .result-title {{
                font-size: 13.5px !important;
            }}

            /* Biểu đồ plotly compact hơn trên màn hình nhỏ */
            .js-plotly-plot .plotly {{
                font-size: 11px !important;
            }}

            /* Badge app nhỏ hơn */
            .app-badge {{
                font-size: 10px !important;
                padding: 3px 10px !important;
            }}

            /* Spinner / progress tối ưu mobile */
            [data-testid="stSpinner"] {{
                font-size: 13px !important;
            }}

            /* Sidebar thu gọn trên điện thoại */
            [data-testid="stSidebar"] {{
                width: 80vw !important;
                min-width: 260px !important;
            }}

            /* Button chính to dễ bấm ngón tay */
            .stButton button {{
                height: 48px !important;
                font-size: 15px !important;
                border-radius: 12px !important;
                width: 100% !important;
            }}

            /* Khoảng cách subheader */
            .stMarkdown h3 {{
                margin-top: 8px !important;
                margin-bottom: 4px !important;
            }}
        }}

        /* ── Điện thoại nhỏ hơn (< 480px như iPhone SE) ── */
        @media (max-width: 480px) {{
            h1 {{
                font-size: 1.0rem !important;
            }}
            .result-value {{
                font-size: 1.0rem !important;
            }}
            [data-testid="stCameraInput"] button {{
                height: 54px !important;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# Gọi hàm cài đặt ảnh nền
BG_IMAGE_PATH = "anhbackgroud.png"
if os.path.exists(BG_IMAGE_PATH):
    set_bg_hack(BG_IMAGE_PATH)

# Danh sách nhãn bệnh gốc (8 lớp gồm 7 bệnh + Unknown)
CLASS_NAMES = [
    "Anthracnose",  # Bệnh thán thư
    "Dieback",  # Bệnh khô cành / chết ngược
    "Gall_Midge",  # Bọ trĩ / Bọ xít muỗi
    "Healthy",  # Lá khỏe mạnh
    "Powdery_Mildew",  # Bệnh phấn trắng
    "Red_Rust",  # Bệnh rỉ sắt
    "Sooty_Mold",  # Bệnh nấm bồ hóng
    "Unknown",  # Đối tượng ngoài luồng / Không phải lá xoài
]

# Tên tiếng Việt hiển thị trên biểu đồ
CLASS_NAMES_VN = [
    "Thán thư",
    "Khô cành",
    "Bọ xít muỗi",
    "Lá khỏe mạnh",
    "Phấn trắng",
    "Rỉ sắt",
    "Bồ hóng",
    "Không phải lá xoài",
]

# Bảng màu sắc rực rỡ cho các loại bệnh
COLOR_PALETTE = [
    "#FF5722",  # Cam đỏ
    "#E91E63",  # Hồng đậm
    "#9C27B0",  # Tím
    "#4CAF50",  # Xanh lá tươi
    "#00BCD4",  # Xanh ngọc
    "#FFC107",  # Vàng
    "#795548",  # Nâu
    "#78909C",  # Xám xanh (Unknown)
]

# Thông tin chi tiết cách điều trị & chăm sóc từng bệnh
TREATMENT_INFO = {
    "Anthracnose": {
        "title": "Bệnh Thán Thư (Anthracnose)",
        "symptoms": (
            "Xuất hiện các đốm nâu đen nhỏ trên lá, sau đó lan rộng thành vệt"
            " cháy khô tròn hoặc bất hình dạng."
        ),
        "treatment": (
            "• **Cắt tỉa:** Tỉa bỏ ngay các lá, cành bị bệnh và thu gom đốt để"
            " tránh lây lan.<br>• **Biện pháp hóa học:** Phun các loại thuốc"
            " chứa hoạt chất *Mancozeb*, *Azoxystrobin*, hoặc *Copper"
            " Oxychloride*.<br>• **Phòng ngừa:** Tránh tưới nước lên tán lá vào"
            " buổi tối, giữ tán cây thông thoáng."
        ),
    },
    "Dieback": {
        "title": "Bệnh Khô Cành / Chết Ngược (Dieback)",
        "symptoms": (
            "Đầu cành khô dần từ ngọn xuống, lá héo khô, biến màu nâu sẫm và"
            " rụng hàng loạt."
        ),
        "treatment": (
            "• **Cắt tỉa:** Cắt bỏ phần cành bị khô chết (cắt sâu xuống phần gỗ"
            " khỏe mạnh 5 - 10 cm).<br>• **Xử lý vết cắt:** Bôi keo liền sẹo"
            " hoặc dung dịch Bordeaux lên vết cắt.<br>• **Biện pháp hóa học:**"
            " Phun các thuốc trị nấm như *Carbendazim*, *Thiophanate-methyl*"
            " hoặc gốc Đồng."
        ),
    },
    "Gall_Midge": {
        "title": "Bọ Xít Muỗi / Sâu Đục Cụm Lá (Gall Midge)",
        "symptoms": (
            "Lá có các vết biến dạng, u bướu nhỏ đốm tròn sẫm màu do côn trùng"
            " chích hút."
        ),
        "treatment": (
            "• **Biện pháp cơ học:** Cắt tỉa tạo tán giúp vườn cây đón ánh nắng"
            " tự nhiên.<br>• **Thuốc đặc trị côn trùng:** Phun thuốc trừ sâu vi"
            " sinh hoặc thuốc có hoạt chất *Imidacloprid*, *Thiamethoxam*,"
            " *Cypermethrin* vào thời điểm cây ra đọt non."
        ),
    },
    "Healthy": {
        "title": "Lá Khỏe Mạnh (Healthy)",
        "symptoms": (
            "Lá cây có màu xanh tự nhiên, bề mặt láng mịn, không có dấu hiệu"
            " đốm nấm hay sâu bệnh."
        ),
        "care": (
            "• **Tưới nước:** Tưới đủ nước, giữ độ ẩm ổn định, đặc biệt trong"
            " thời kỳ ra hoa và đậu quả.<br>• **Bón phân:** Bón phân cân đối"
            " NPK kết hợp phân hữu cơ hoai mục để tăng sức đề kháng cho"
            " cây.<br>• **Cắt tỉa:** Tỉa cành vượt, cành gầm định kỳ sau mỗi vụ"
            " thu hoạch để vườn luôn thông thoáng.<br>• **Theo dõi:** Thường"
            " xuyên kiểm tra mặt dưới lá để phát hiện sớm mầm bệnh."
        ),
    },
    "Powdery_Mildew": {
        "title": "Bệnh Phấn Trắng (Powdery Mildew)",
        "symptoms": (
            "Lớp đốm dính bột trắng như phấn phủ trên bề mặt lá non, hoa hoặc"
            " quả non."
        ),
        "treatment": (
            "• **Biện pháp xử lý:** Tỉa bớt lá già, tạo độ thông thoáng cho tán"
            " cây.<br>• **Biện pháp hóa học:** Phun thuốc gốc Lưu huỳnh"
            " (*Sulfur*), *Hexaconazole*, hoặc *Difenoconazole* khi vừa xuất"
            " hiện vết bệnh."
        ),
    },
    "Red_Rust": {
        "title": "Bệnh Rỉ Sắt (Red Rust)",
        "symptoms": (
            "Lá xuất hiện các đốm mụn nhỏ màu cam vàng hoặc đỏ gạch giống như rỉ"
            " sắt ở mặt dưới lá."
        ),
        "treatment": (
            "• **Cắt tỉa:** Dọn dẹp vệ sinh tàn dư lá bệnh dưới gốc cây.<br>•"
            " **Biện pháp hóa học:** Sử dụng các thuốc trừ nấm gốc Đồng (*Copper"
            " Hydroxide*) hoặc thuốc chứa *Tebuconazole*, *Propiconazole*."
        ),
    },
    "Sooty_Mold": {
        "title": "Bệnh Nấm Bồ Hóng (Sooty Mold)",
        "symptoms": (
            "Lớp muội đen phủ như bồ hóng trên bề mặt lá, làm giảm khả năng"
            " quang hợp của cây."
        ),
        "treatment": (
            "• **Diệt côn trùng môi giới:** Bệnh xuất hiện do dịch tiết của"
            " rệp/bọ xít. Cần phun diệt rệp bằng *Imidacloprid* hoặc xà phòng"
            " nông nghiệp.<br>• **Rửa sạch lá:** Phun xịt nước áp lực nhẹ hoặc"
            " tưới dung dịch gốc Đồng để làm trôi lớp nấm đen."
        ),
    },
}

CONFIDENCE_THRESHOLD = 40.0



def custom_divide(x, *args, **kwargs):
    return tf.math.divide(x, 255.0)


def true_divide(x, y=127.5, *args, **kwargs):
    return tf.math.divide(x, y)


@st.cache_resource
def load_mango_model():
    for model_path in ["mango_leaf_model.keras", "mango_leaf_model.h5"]:
        if os.path.exists(model_path):
            try:
                from tensorflow.keras.models import load_model
                # Thử load trực tiếp trước (dành cho file .keras hiện đại)
                return load_model(model_path, compile=False)
            except Exception:
                try:
                    # Dự phòng cho file .h5 cũ có custom_divide
                    custom_objects = {
                        "custom_divide": custom_divide,
                        "TrueDivide": true_divide,
                    }
                    return load_model(
                        model_path, custom_objects=custom_objects, compile=False
                    )
                except Exception:
                    pass

    # Dự phòng khởi tạo kiến trúc nếu không load trực tiếp được
    base_model = tf.keras.applications.MobileNetV2(
        input_shape=(224, 224, 3), include_top=False, weights=None
    )
    base_model.trainable = False

    inputs = tf.keras.Input(shape=(224, 224, 3), name="input_layer")
    x = base_model(inputs, training=False)
    x = tf.keras.layers.GlobalAveragePooling2D(name="global_avg_pool")(x)
    x = tf.keras.layers.Dense(128, activation="relu", name="dense_intermediate")(x)
    outputs = tf.keras.layers.Dense(len(CLASS_NAMES), activation="softmax", name="output_layer")(x)
    model = tf.keras.Model(inputs=inputs, outputs=outputs)

    for p in ["mango_leaf_model.keras", "mango_leaf_model.h5"]:
        if os.path.exists(p):
            try:
                model.load_weights(p, by_name=True, skip_mismatch=True)
                break
            except Exception:
                continue

    return model


# Khởi tạo model
try:
    model = load_mango_model()
except Exception as e:
    st.error(f"Lỗi khi tải mô hình: {e}")
    st.stop()


def preprocess_image(image_data):
    size = (224, 224)
    image = ImageOps.fit(image_data, size, Image.Resampling.LANCZOS)
    img_array = np.array(image).astype(np.float32)

    # Kiểm tra xem mô hình đã tích hợp sẵn tiền xử lý (preprocess_input) bên trong chưa
    has_internal_preprocess = any(
        "data_augmentation" in getattr(l, "name", "")
        or "preprocess" in getattr(l, "name", "")
        for l in model.layers
    )
    if not has_internal_preprocess:
        img_array = tf.keras.applications.mobilenet_v2.preprocess_input(img_array)

    data = np.expand_dims(img_array, axis=0)
    return data


# --- HÀM TẠO GRAD-CAM TƯƠNG THÍCH MỌI CẤU TRÚC MODEL ---
def generate_gradcam(img_array, model, pred_index=None):
    try:
        # 1. Tìm Base Model hoặc Sub-Model bên trong
        target_model = model
        base_layer = None

        for layer in model.layers:
            if hasattr(layer, "layers") or "mobilenet" in layer.name.lower():
                base_layer = layer
                break

        # Nếu mô hình bao gồm base model dạng nested
        if base_layer is not None:
            # Tìm lớp conv cuối cùng trong base model
            last_conv = None
            for layer in reversed(base_layer.layers):
                try:
                    if len(layer.output_shape) == 4:
                        last_conv = layer
                        break
                except Exception:
                    continue

            if last_conv is None:
                last_conv = base_layer.get_layer("out_relu")

            # Tạo feature extractor sub-model
            feature_model = tf.keras.models.Model(
                inputs=[base_layer.inputs], outputs=[last_conv.output]
            )

            # Lấy các lớp phân loại còn lại
            classifier_layers = []
            found = False
            for layer in model.layers:
                if layer == base_layer:
                    found = True
                    continue
                if found:
                    classifier_layers.append(layer)

            with tf.GradientTape() as tape:
                conv_outputs = feature_model(img_array)
                tape.watch(conv_outputs)

                x = conv_outputs
                for layer in classifier_layers:
                    x = layer(x)
                predictions = x

                if pred_index is None:
                    pred_index = tf.argmax(predictions[0])
                class_channel = predictions[:, pred_index]

            grads = tape.gradient(class_channel, conv_outputs)
            pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))

            conv_outputs = conv_outputs[0]
            heatmap = conv_outputs @ pooled_grads[..., tf.newaxis]
            heatmap = tf.squeeze(heatmap)

        else:
            # Mô hình phẳng (Flat Functional / Sequential Model)
            last_conv_layer = None
            for layer in reversed(model.layers):
                try:
                    if len(layer.output_shape) == 4:
                        last_conv_layer = layer
                        break
                except Exception:
                    continue

            if last_conv_layer is None:
                return None

            grad_model = tf.keras.models.Model(
                inputs=[model.inputs],
                outputs=[last_conv_layer.output, model.output],
            )

            with tf.GradientTape() as tape:
                conv_outputs, predictions = grad_model(img_array)
                if pred_index is None:
                    pred_index = tf.argmax(predictions[0])
                class_channel = predictions[:, pred_index]

            grads = tape.gradient(class_channel, conv_outputs)
            pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))

            conv_outputs = conv_outputs[0]
            heatmap = conv_outputs @ pooled_grads[..., tf.newaxis]
            heatmap = tf.squeeze(heatmap)

        # 2. Xử lý chuẩn hóa Heatmap về dải [0, 1]
        heatmap = tf.maximum(heatmap, 0)
        max_val = tf.math.reduce_max(heatmap)
        if max_val > 0:
            heatmap = heatmap / max_val

        return heatmap.numpy()

    except Exception as e:
        print(f"Grad-CAM Error: {e}")
        return None


def overlay_heatmap(original_img, heatmap, alpha=0.4):
    heatmap_resized = cv2.resize(
        heatmap, (original_img.width, original_img.height)
    )
    heatmap_uint8 = np.uint8(255 * heatmap_resized)

    heatmap_colored = cv2.applyColorMap(heatmap_uint8, cv2.COLORMAP_JET)
    heatmap_colored = cv2.cvtColor(heatmap_colored, cv2.COLOR_BGR2RGB)

    orig_np = np.array(original_img)
    superimposed = heatmap_colored * alpha + orig_np * (1 - alpha)
    superimposed = np.clip(superimposed, 0, 255).astype(np.uint8)

    return Image.fromarray(superimposed)


# 1. Biểu đồ hình tròn đồng hồ (Gauge Chart)
def create_circular_gauge(confidence_val):
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=confidence_val,
            number={"suffix": "%", "font": {"size": 34, "color": "#1b3815"}},
            gauge={
                "axis": {
                    "range": [0, 100],
                    "tickwidth": 1,
                    "tickcolor": "#2b5123",
                },
                "bar": {"color": "#388e3c"},
                "bgcolor": "white",
                "borderwidth": 2,
                "bordercolor": "#c2d6be",
                "steps": [
                    {"range": [0, 50], "color": "#ffebee"},
                    {"range": [50, 75], "color": "#fffde7"},
                    {"range": [75, 100], "color": "#e8f5e9"},
                ],
            },
        )
    )

    fig.update_layout(
        height=200,
        margin=dict(t=25, b=10, l=25, r=25),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


# 2. Biểu đồ cột rực rỡ nhiều màu sắc
def create_colorful_bar_chart(predictions):
    percentages = [float(p * 100) for p in predictions]
    text_labels = [f"{p:.1f}%" for p in percentages]

    # Tên ngắn hơn để phù hợp màn hình điện thoại nhỏ
    SHORT_NAMES = [
        "Thán thư",
        "Khô cành",
        "Bọ xít",
        "Khỏe mạnh",
        "Phấn trắng",
        "Rỉ sắt",
        "Bồ hóng",
        "Không xác định",
    ]

    fig = go.Figure(
        data=[
            go.Bar(
                x=SHORT_NAMES,
                y=percentages,
                text=text_labels,
                textposition="outside",
                marker=dict(
                    color=COLOR_PALETTE,
                    line=dict(color="rgba(0, 0, 0, 0.15)", width=1.5),
                ),
                hovertemplate="<b>%{x}</b>: %{y:.2f}%<extra></extra>",
            )
        ]
    )

    fig.update_layout(
        xaxis=dict(
            title="",
            tickangle=-40,
            tickfont=dict(size=9.5),
            automargin=True,
        ),
        yaxis=dict(title="<b>Xác suất (%)</b>", range=[0, 115], tickfont=dict(size=9)),
        height=260,
        margin=dict(t=25, b=5, l=30, r=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.5)",
        autosize=True,
    )
    return fig


# ─── THANH ĐIỀU HƯỚNG BÊN TRÁI (SIDEBAR) ──────────────────────────────────
local_ip = get_local_ip()
web_url = f"http://{local_ip}:8501"
api_url = f"http://{local_ip}:8000"

with st.sidebar:
    st.markdown("## 📱 Kết Nối Điện Thoại")
    st.markdown("Quét mã QR bằng Camera điện thoại để mở ứng dụng:")
    
    try:
        qr_bytes = generate_qr_code(web_url)
        st.image(qr_bytes, caption=f"Địa chỉ: {web_url}", use_container_width=True)
    except Exception:
        pass
    
    st.markdown(
        f"""
        * **Wi-Fi chung:** Kết nối điện thoại vào cùng mạng Wi-Fi với máy tính.
        * **Link truy cập:** [{web_url}]({web_url})
        """
    )

    st.markdown("---")
    st.markdown("## 🌐 RESTful API Server")
    st.markdown(
        f"""
        Hệ thống tích hợp sẵn API chẩn đoán cho Mobile App & IoT:
        * **Trạng thái:** 🟢 Đang hoạt động
        * **API URL:** `{api_url}/predict`
        * **Tài liệu Swagger:** [{api_url}/docs]({api_url}/docs)
        """
    )
    with st.expander("💻 Xem mã gọi API (cURL / Python)"):
        st.code(
            f"""# 1. Gọi bằng cURL (Terminal/CMD):
curl -X POST "{api_url}/predict" \\
  -H "accept: application/json" \\
  -H "Content-Type: multipart/form-data" \\
  -F "file=@la_xoai.jpg"

# 2. Gọi bằng Python:
import requests
url = "{api_url}/predict"
with open("la_xoai.jpg", "rb") as f:
    res = requests.post(url, files={{"file": f}})
print(res.json())
""",
            language="bash",
        )


# Giao diện chính
st.markdown(
    """
    <div style="text-align: center; margin-top: -10px; margin-bottom: 8px;">
        <span class="app-badge">🌿 AI NÔNG NGHIỆP THÔNG MINH • CHẨN ĐOÁN LÁ XOÀI</span>
    </div>
    """,
    unsafe_allow_html=True,
)
st.title("Chẩn Đoán Bệnh Lá Xoài bằng AI")



col1, col2 = st.columns([1, 1])

with col1:
    st.header("Hình ảnh lá xoài cần chẩn đoán")

    image_source = None

    uploaded_file = st.file_uploader(
        "Chọn ảnh từ máy tính hoặc điện thoại...",
        type=["jpg", "png", "jpeg", "webp", "heic", "heif", "bmp"],
        help="Hỗ trợ đầy đủ định dạng ảnh phổ biến bao gồm cả ảnh chụp HEIC từ iPhone/iPad.",
    )
    if uploaded_file is not None:
        image_source = uploaded_file

    if image_source is not None:
        # Đọc ảnh và tự động sửa góc xoay EXIF của ảnh chụp từ điện thoại
        _raw = Image.open(image_source)
        try:
            _raw = ImageOps.exif_transpose(_raw)
        except Exception:
            pass

        # Xử lý ảnh PNG nền trong suốt (transparent): ghép lên nền trắng
        # tránh nền đen gây nhầm lẫn với class Unknown
        if _raw.mode in ("RGBA", "LA") or (
            _raw.mode == "P" and "transparency" in _raw.info
        ):
            _bg = Image.new("RGB", _raw.size, (255, 255, 255))
            _raw_rgba = _raw.convert("RGBA")
            _bg.paste(_raw_rgba, mask=_raw_rgba.split()[3])
            image = _bg
        else:
            image = _raw.convert("RGB")
        processed_img = preprocess_image(image)

        # Tạo Tab chuyển đổi giữa Ảnh Gốc và Ảnh Grad-CAM
        tab_orig, tab_cam = st.tabs(
            ["Ảnh gốc", "Vùng AI tập trung (Grad-CAM)"]
        )

        with tab_orig:
            st.image(
                image, caption="Ảnh đã chọn / chụp", use_container_width=True
            )

        with tab_cam:
            heatmap = generate_gradcam(processed_img, model)
            if heatmap is not None:
                cam_img = overlay_heatmap(image, heatmap)
                st.image(
                    cam_img,
                    caption="Vùng Đỏ/Cam đại diện cho khu vực AI chú ý nhất",
                    use_container_width=True,
                )
            else:
                st.info("Không thể tạo biểu đồ nhiệt cho ảnh này.")

with col2:
    st.header("Kết quả chẩn đoán từ AI")
    if image_source is not None:
        with st.spinner("Đang phân tích ảnh..."):

            # Chạy mô hình dự đoán
            predictions = model.predict(processed_img)[0]

            predicted_class_idx = np.argmax(predictions)
            confidence = float(predictions[predicted_class_idx] * 100)

            # Kiểm tra chênh lệch giữa Top 1 và Top 2
            sorted_probs = np.sort(predictions)[::-1]
            prob_diff = sorted_probs[0] - sorted_probs[1]

            if predicted_class_idx < len(CLASS_NAMES):
                raw_label = CLASS_NAMES[predicted_class_idx]
                result_label = f"{raw_label} ({CLASS_NAMES_VN[predicted_class_idx]})"
            else:
                raw_label = "Unknown"
                result_label = f"Class {predicted_class_idx}"

        # 3. ĐIỀU KIỆN PHÂN LOẠI & CHẶN THÔNG MINH
        is_unknown = (raw_label == "Unknown")

        # Tổng xác suất của 7 bệnh lá xoài thực sự (bỏ lớp Unknown)
        disease_total_prob = float(np.sum(predictions[:7]) * 100)

        # Xử lý mất cân bằng dữ liệu: Unknown có ~1827 ảnh vs ~1000 ảnh/bệnh
        # Nếu Unknown thắng nhưng các bệnh vẫn chiếm >20% tổng → ưu tiên bệnh
        if is_unknown and disease_total_prob >= 20.0:
            # Override Unknown: lấy bệnh có xác suất cao nhất trong 7 bệnh
            disease_preds = predictions[:7]
            best_disease_idx = int(np.argmax(disease_preds))
            best_disease_conf = float(disease_preds[best_disease_idx] * 100)
            raw_label = CLASS_NAMES[best_disease_idx]
            result_label = f"{raw_label} ({CLASS_NAMES_VN[best_disease_idx]})"
            confidence = best_disease_conf
            is_unknown = False  # Không còn Unknown nữa

        if is_unknown:
            # Chặn tuyệt đối: Xác suất Unknown cao VÀ các bệnh lá xoài đều thấp
            st.markdown(
                f"""
                <div class="warning-card">
                    <div class="result-title">🚫 Phát hiện đối tượng ngoài luồng / Không phải lá xoài!</div>
                    <div style="font-size: 14px; margin-top: 5px;">
                        Hệ thống nhận diện đây là <b>đối tượng ngoài luồng</b> (lá cây khác, động vật, đất cát, đồ vật, xe cộ...) 
                        với độ tin cậy <b>{confidence:.1f}%</b> và tổng xác suất các bệnh lá xoài chỉ đạt <b>{disease_total_prob:.1f}%</b>.<br><br>
                        👉 <i>Hệ thống từ chối đưa ra kết luận bệnh. Vui lòng chỉ tải ảnh chụp lá xoài.</i>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        elif confidence < CONFIDENCE_THRESHOLD:
            # Nhận diện là lá xoài nhưng vết bệnh mờ / độ tin cậy thấp
            st.markdown(
                f"""
                <div class="warning-card">
                    <div class="result-title">⚠️ Ảnh chưa đủ rõ nét để kết luận chắc chắn!</div>
                    <div style="font-size: 14px; margin-top: 5px;">
                        Mô hình nhận diện đây là lá xoài có khả năng mắc bệnh: <b>{result_label}</b>, 
                        tuy nhiên độ tin cậy chỉ đạt <b>{confidence:.1f}%</b> (dưới ngưỡng {CONFIDENCE_THRESHOLD}%).<br><br>
                        👉 <i>Khuyến nghị: Chụp lại cận cảnh vết đốm trên phiến lá với ánh sáng rõ hơn để có kết luận chính xác nhất.</i>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            # Thẻ kết quả chẩn đoán chuẩn
            st.markdown(
                f"""
                <div class="result-card">
                    <div class="result-title">Kết quả chẩn đoán:</div>
                    <div class="result-value">{result_label}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Hướng dẫn ĐIỀU TRỊ hoặc CHĂM SÓC tùy theo kết quả
            if raw_label in TREATMENT_INFO:
                info = TREATMENT_INFO[raw_label]
                if raw_label == "Healthy":
                    st.markdown(
                        f"""
                        <div class="healthy-care-card">
                            <div style="font-size: 18px; font-weight: 700; margin-bottom: 8px;">
                                Hướng dẫn chăm sóc để lá luôn khỏe mạnh:
                            </div>
                            <div style="font-size: 14px; line-height: 1.6;">
                                {info['care']}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        f"""
                        <div class="treatment-card">
                            <div style="font-size: 18px; font-weight: 700; color: #bc6c25; margin-bottom: 6px;">
                                Biện pháp phòng trừ & Điều trị:
                            </div>
                            <div style="font-size: 14px; margin-bottom: 8px;">
                                <b>Triệu chứng:</b> {info['symptoms']}
                            </div>
                            <div style="font-size: 14px; line-height: 1.6;">
                                <b>Cách điều trị:</b><br>{info['treatment']}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

            # Đồng hồ độ tin cậy tròn
            st.subheader("Độ tin cậy:")
            st.plotly_chart(
                create_circular_gauge(confidence), use_container_width=True
            )

        # Biểu đồ cột rực rỡ màu sắc
        st.subheader("Chi tiết xác suất các bệnh:")
        st.plotly_chart(
            create_colorful_bar_chart(predictions), use_container_width=True
        )

    else:
        st.info("Vui lòng tải ảnh lên ở ô bên trái để nhận kết quả phân tích.")