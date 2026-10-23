from datetime import datetime
from collections import defaultdict, deque
from functools import wraps
import hmac
import ipaddress
import os
from pathlib import Path
import secrets
from threading import Thread
from time import sleep, time
from uuid import uuid4
from urllib.parse import urlparse

import cv2
import numpy as np
from flask import Flask, Response, abort, jsonify, render_template, request, send_from_directory, url_for
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename

from utils.alert_logic import AlertManager
from utils.detector import (
    CUSTOM_MODE,
    CUSTOM_MODEL_MISSING_MESSAGE,
    PRETRAINED_MODE,
    PhoneDetector,
)
from utils.telegram_notifier import TelegramNotifier


app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
ALERT_DIR = BASE_DIR / "alerts"
CUSTOM_MODEL_PATH = Path(
    os.getenv("CUSTOM_MODEL_PATH", str(BASE_DIR / "models" / "best.pt"))
).expanduser().resolve()

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov"}
IMAGE_MIME_TYPES = {"image/jpeg", "image/png"}
VIDEO_MIME_TYPES = {"video/mp4", "video/quicktime", "video/x-msvideo"}
MODEL_OPTIONS = [PRETRAINED_MODE, CUSTOM_MODE]

for directory in (UPLOAD_DIR, OUTPUT_DIR, ALERT_DIR):
    directory.mkdir(parents=True, exist_ok=True)

_detector_cache = {}
_rate_buckets = defaultdict(deque)
_telegram_polling_started = False
telegram_notifier = TelegramNotifier()
app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("APP_MAX_UPLOAD_MB", "200")) * 1024 * 1024
app.config["ALLOW_ADMIN_TOKEN_IN_QUERY"] = os.getenv("ALLOW_ADMIN_TOKEN_IN_QUERY", "false").lower() == "true"


def ensure_admin_token():
    """Tao ADMIN_API_TOKEN neu .env chua co."""
    token = os.getenv("ADMIN_API_TOKEN", "").strip()
    if token:
        return token
    token = secrets.token_urlsafe(32)
    telegram_notifier.set_env_value("ADMIN_API_TOKEN", token)
    return token


ADMIN_API_TOKEN = ensure_admin_token()


def admin_authorized():
    """Kiem tra token cho route quan tri."""
    provided = request.headers.get("X-Admin-Token", "")
    if not provided and app.config["ALLOW_ADMIN_TOKEN_IN_QUERY"]:
        provided = request.args.get("admin_token", "")
    return bool(provided) and hmac.compare_digest(provided, ADMIN_API_TOKEN)


def require_admin(handler):
    """Decorator bao ve route quan tri."""
    @wraps(handler)
    def wrapped(*args, **kwargs):
        if not admin_authorized():
            return jsonify({"ok": False, "error": "Unauthorized admin route"}), 401
        return handler(*args, **kwargs)

    return wrapped


def rate_limit(max_calls, window_seconds, methods=None):
    """Rate limit don gian theo IP va endpoint."""
    limited_methods = {method.upper() for method in methods} if methods else None

    def decorator(handler):
        @wraps(handler)
        def wrapped(*args, **kwargs):
            if limited_methods and request.method.upper() not in limited_methods:
                return handler(*args, **kwargs)
            now = time()
            key = (request.remote_addr or "unknown", request.endpoint or handler.__name__)
            bucket = _rate_buckets[key]
            while bucket and now - bucket[0] > window_seconds:
                bucket.popleft()
            if len(bucket) >= max_calls:
                retry_after = max(1, int(window_seconds - (now - bucket[0])))
                response = jsonify(
                    {
                        "ok": False,
                        "error": "Too many requests",
                        "retry_after_seconds": retry_after,
                    }
                )
                response.headers["Retry-After"] = str(retry_after)
                return response, 429
            bucket.append(now)
            return handler(*args, **kwargs)

        return wrapped

    return decorator


@app.after_request
def add_security_headers(response):
    """Them header bao ve co ban."""
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    camera_policy = "camera=(self)" if request.endpoint in {"camera", "video_feed"} else "camera=()"
    response.headers["Permissions-Policy"] = f"{camera_policy}, microphone=(), geolocation=(), payment=(), usb=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "img-src 'self' data:; "
        "media-src 'self'; "
        "style-src 'self' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "script-src 'self' https://cdnjs.cloudflare.com https://unpkg.com; "
        "connect-src 'self'; "
        "object-src 'none'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    if request.is_secure or os.getenv("FORCE_HSTS", "false").lower() == "true":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    if request.endpoint in {
        "camera",
        "video_feed",
        "uploaded_media",
        "output_media",
        "test_telegram",
        "telegram_sync",
        "telegram_webhook",
        "telegram_set_webhook",
        "telegram_status",
    }:
        response.headers["Cache-Control"] = "no-store, max-age=0"
        response.headers["Pragma"] = "no-cache"
    return response


@app.errorhandler(RequestEntityTooLarge)
def upload_too_large(_error):
    """Tra loi ro rang khi file upload qua lon."""
    return (
        jsonify(
            {
                "ok": False,
                "error": f"File qua lon. Gioi han hien tai: {app.config['MAX_CONTENT_LENGTH'] // (1024 * 1024)} MB.",
            }
        ),
        413,
    )


@app.errorhandler(404)
def not_found(_error):
    """Thong bao 404 an toan."""
    return jsonify({"ok": False, "error": "Not found"}), 404


@app.errorhandler(429)
def too_many_requests(_error):
    """Thong bao rate limit an toan."""
    return jsonify({"ok": False, "error": "Too many requests"}), 429


@app.errorhandler(500)
def internal_error(_error):
    """Khong lo stack trace cho client."""
    return jsonify({"ok": False, "error": "Internal server error"}), 500


def get_detector(model_mode, conf_threshold):
    """Tai model mot lan cho moi cau hinh."""
    cache_key = (model_mode, round(float(conf_threshold), 2))
    if cache_key not in _detector_cache:
        _detector_cache[cache_key] = PhoneDetector(
            model_mode=model_mode,
            custom_model_path=str(CUSTOM_MODEL_PATH),
            conf_threshold=float(conf_threshold),
        )
    return _detector_cache[cache_key]


def get_model_settings():
    """Doc model va confidence tu form/query string."""
    model_mode = request.values.get("model_mode", PRETRAINED_MODE)
    if model_mode not in MODEL_OPTIONS:
        model_mode = PRETRAINED_MODE

    try:
        conf_threshold = float(request.values.get("conf_threshold", 0.5))
    except ValueError:
        conf_threshold = 0.5

    return model_mode, min(max(conf_threshold, 0.1), 0.9)


def is_public_https_url(raw_url):
    """Chi cho phep webhook URL HTTPS public."""
    parsed = urlparse(raw_url)
    if parsed.scheme != "https" or not parsed.hostname:
        return False

    hostname = parsed.hostname.lower()
    if hostname in {"localhost", "127.0.0.1"} or hostname.endswith(".local"):
        return False

    try:
        ip = ipaddress.ip_address(hostname)
        return not (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved)
    except ValueError:
        return True


def model_context(active_page, load_detector=False):
    """Context chung, chi tai YOLO khi xu ly du lieu."""
    model_mode, conf_threshold = get_model_settings()
    detector = None
    model_warning = ""

    if model_mode == CUSTOM_MODE and not CUSTOM_MODEL_PATH.exists():
        model_warning = CUSTOM_MODEL_MISSING_MESSAGE
    elif load_detector:
        detector = get_detector(model_mode, conf_threshold)
        model_warning = detector.load_error

    return {
        "active_page": active_page,
        "model_options": MODEL_OPTIONS,
        "model_mode": model_mode,
        "conf_threshold": conf_threshold,
        "detector": detector,
        "model_warning": model_warning,
    }


def allowed_file(filename, extensions):
    """Kiem tra duoi file upload."""
    return Path(filename).suffix.lower() in extensions


def file_signature(file_storage, size=16):
    """Doc magic bytes va dua stream ve dau."""
    file_storage.stream.seek(0)
    head = file_storage.stream.read(size)
    file_storage.stream.seek(0)
    return head


def valid_image_signature(file_storage):
    """Xac minh JPG/PNG bang magic bytes."""
    head = file_signature(file_storage)
    return head.startswith(b"\xff\xd8\xff") or head.startswith(b"\x89PNG\r\n\x1a\n")


def valid_video_signature(file_storage):
    """Xac minh MP4/MOV/AVI bang magic bytes co ban."""
    head = file_signature(file_storage, size=32)
    is_mp4_or_mov = len(head) >= 12 and head[4:8] == b"ftyp"
    is_avi = head.startswith(b"RIFF") and head[8:12] == b"AVI "
    return is_mp4_or_mov or is_avi


def validate_upload(file_storage, extensions, mime_types, signature_validator):
    """Validate filename, MIME type va file signature."""
    if not file_storage or file_storage.filename == "":
        return False, "Vui long chon file de upload."
    if not allowed_file(file_storage.filename, extensions):
        return False, "Dinh dang file khong duoc ho tro."
    if file_storage.mimetype not in mime_types:
        return False, "MIME type khong hop le."
    if not signature_validator(file_storage):
        return False, "Noi dung file khong khop dinh dang khai bao."
    return True, ""


def unique_filename(filename):
    """Tao ten file an toan va tranh ghi de."""
    safe_name = secure_filename(filename)
    suffix = Path(safe_name).suffix.lower()
    stem = Path(safe_name).stem or "upload"
    return f"{stem}_{uuid4().hex[:10]}{suffix}"


def media_response(directory, filename):
    """Serve file da tao, chan path traversal."""
    safe_name = Path(filename).name
    if safe_name != filename:
        abort(404)
    return send_from_directory(directory, safe_name, as_attachment=False)


def draw_alert_overlay(frame, alert_level):
    """Ve trang thai canh bao len frame."""
    overlays = {
        "HIGH": ("HIGH ALERT: SUSPECTED PHONE USAGE", (0, 0, 255)),
        "LOW": ("PHONE DETECTED", (0, 165, 255)),
    }
    if alert_level not in overlays:
        return frame

    text, color = overlays[alert_level]
    cv2.putText(
        frame,
        text,
        (30, 52),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        color,
        3,
        cv2.LINE_AA,
    )
    return frame


def handle_high_alert(annotated_frame):
    """Luu anh vi pham va gui Telegram theo cooldown."""
    if not telegram_notifier.can_send():
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    image_name = f"alert_{timestamp}.jpg"
    image_path = ALERT_DIR / image_name
    display_path = f"alerts/{image_name}"

    saved = cv2.imwrite(str(image_path), annotated_frame)
    evidence_path = display_path if saved else "Khong luu duoc anh bang chung"
    message = (
        "CANH BAO VI PHAM\n"
        "Phat hien nghi ngo su dung dien thoai trong gio kiem tra.\n"
        f"Thoi gian: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}\n"
        f"Anh bang chung: {evidence_path}"
    )

    telegram_notifier.send_alert(message, image_path=str(image_path) if saved else None)


def warning_frame(message):
    """Tao frame thong bao khi camera/model chua san sang."""
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    frame[:] = (7, 10, 18)
    cv2.putText(
        frame,
        message[:78],
        (52, 360),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.9,
        (0, 220, 255),
        2,
        cv2.LINE_AA,
    )
    return frame


def encode_mjpeg(frame):
    """Encode frame thanh chunk MJPEG."""
    ok, buffer = cv2.imencode(".jpg", frame)
    if not ok:
        return None
    return b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"


@app.route("/")
def index():
    return render_template("index.html", **model_context("home"))


@app.route("/media/uploads/<path:filename>")
def uploaded_media(filename):
    return media_response(UPLOAD_DIR, filename)


@app.route("/media/outputs/<path:filename>")
def output_media(filename):
    return media_response(OUTPUT_DIR, filename)


@app.route("/image", methods=["GET", "POST"])
@rate_limit(max_calls=20, window_seconds=300, methods={"POST"})
def image():
    context = model_context("image", load_detector=request.method == "POST")
    original_url = None
    output_url = None
    detections = []
    message = ""

    if request.method == "POST":
        file = request.files.get("image_file")
        valid, message = validate_upload(
            file,
            IMAGE_EXTENSIONS,
            IMAGE_MIME_TYPES,
            valid_image_signature,
        )
        if not valid:
            message = message or "Chi ho tro .jpg, .jpeg, .png."
        else:
            filename = unique_filename(file.filename)
            input_path = UPLOAD_DIR / filename
            output_name = f"detected_{Path(filename).stem}.jpg"
            output_path = OUTPUT_DIR / output_name
            file.save(input_path)

            frame = cv2.imread(str(input_path))
            if frame is None:
                message = "Khong the doc anh da upload."
            else:
                annotated_frame, detections, _ = context["detector"].detect_image(frame)
                cv2.imwrite(str(output_path), annotated_frame)
                original_url = url_for("uploaded_media", filename=filename)
                output_url = url_for("output_media", filename=output_name)
                message = context["model_warning"] or ""

    return render_template(
        "image.html",
        **context,
        original_url=original_url,
        output_url=output_url,
        detections=detections,
        message=message,
    )


@app.route("/video", methods=["GET", "POST"])
@rate_limit(max_calls=10, window_seconds=600, methods={"POST"})
def video():
    context = model_context("video", load_detector=request.method == "POST")
    input_url = None
    output_url = None
    message = ""

    if request.method == "POST":
        file = request.files.get("video_file")
        valid, message = validate_upload(
            file,
            VIDEO_EXTENSIONS,
            VIDEO_MIME_TYPES,
            valid_video_signature,
        )
        if not valid:
            message = message or "Chi ho tro .mp4, .avi, .mov."
        else:
            filename = unique_filename(file.filename)
            input_path = UPLOAD_DIR / filename
            output_name = f"detected_{Path(filename).stem}.mp4"
            output_path = OUTPUT_DIR / output_name
            file.save(input_path)

            processed, message = process_video_file(
                input_path,
                output_path,
                context["detector"],
            )
            input_url = url_for("uploaded_media", filename=filename)
            if processed:
                output_url = url_for("output_media", filename=output_name)
            message = context["model_warning"] or message

    return render_template(
        "video.html",
        **context,
        input_url=input_url,
        output_url=output_url,
        message=message,
    )


def process_video_file(input_path, output_path, detector):
    """Xu ly video tung frame bang OpenCV."""
    cap = cv2.VideoCapture(str(input_path))
    if not cap.isOpened():
        return False, "Khong the mo video."

    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 1280)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 720)
    writer = cv2.VideoWriter(
        str(output_path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (width, height),
    )
    alert_manager = AlertManager(warning_seconds=2)

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            annotated_frame, _, phone_detected = detector.detect_image(frame)
            alert_level, _ = alert_manager.update(phone_detected=phone_detected, fps=fps)
            writer.write(draw_alert_overlay(annotated_frame, alert_level))
    finally:
        cap.release()
        writer.release()

    return True, "Da xu ly video xong."


@app.route("/camera")
def camera():
    return render_template("camera.html", **model_context("camera"))


@app.route("/video_feed")
@rate_limit(max_calls=120, window_seconds=60)
def video_feed():
    model_mode, conf_threshold = get_model_settings()
    return Response(
        generate_frames(model_mode, conf_threshold),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@app.route("/test_telegram")
@require_admin
@rate_limit(max_calls=10, window_seconds=300)
def test_telegram():
    """Gui tin nhan test Telegram neu da cau hinh token."""
    if request.args.get("force") == "1":
        telegram_notifier.last_sent = 0

    message = (
        "AI Exam Monitoring test\n"
        f"Thoi gian: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}"
    )
    sent = telegram_notifier.send_alert(message)
    return jsonify(
        {
            "sent": sent,
            "enabled": telegram_notifier.enabled,
            "has_token": bool(telegram_notifier.token),
            "has_chat_id": bool(telegram_notifier.chat_id),
            "chat_id": telegram_notifier.chat_id,
            "last_status": telegram_notifier.last_status,
            "last_error": telegram_notifier.last_error,
            "last_response": telegram_notifier.last_response,
        }
    )


@app.route("/telegram_sync")
@require_admin
@rate_limit(max_calls=10, window_seconds=300)
def telegram_sync():
    """Lay chat id tu getUpdates sau khi user bam /start."""
    result = telegram_notifier.sync_chat_id_from_updates()
    return jsonify(result)


@app.route("/telegram_poll_once")
@require_admin
@rate_limit(max_calls=30, window_seconds=300)
def telegram_poll_once():
    """Kiem tra /start moi mot lan de debug polling."""
    return jsonify(telegram_notifier.poll_registration_once())


@app.route("/telegram_webhook", methods=["GET", "POST"])
@rate_limit(max_calls=60, window_seconds=60)
def telegram_webhook():
    """Nhan update Telegram va tu luu chat id khi user /start."""
    if request.method == "GET":
        return jsonify({"ok": True, "message": "Telegram webhook is ready"})

    telegram_notifier.refresh_config()
    expected_secret = telegram_notifier.webhook_secret
    provided_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if not expected_secret or not hmac.compare_digest(provided_secret, expected_secret):
        return jsonify({"ok": False, "error": "Invalid Telegram webhook secret"}), 403

    update = request.get_json(silent=True) or {}
    chat_info = telegram_notifier.extract_chat_from_update(update)
    text = (chat_info.get("text") or "").strip()

    saved = False
    denied_reason = ""
    if chat_info.get("chat_id") and text.startswith("/start"):
        allowed, denied_reason = telegram_notifier.can_register_chat(chat_info)
        if allowed:
            saved = telegram_notifier.update_chat_id(chat_info["chat_id"])
            telegram_notifier.last_sent = 0
            telegram_notifier.send_alert(
                "Da ket noi AI Exam Monitoring.\n"
                f"Telegram chat id: {chat_info['chat_id']}"
            )

    return jsonify({"ok": True, "saved": saved, "denied_reason": denied_reason, **chat_info})


@app.route("/telegram_set_webhook")
@require_admin
@rate_limit(max_calls=5, window_seconds=300)
def telegram_set_webhook():
    """Dang ky webhook Telegram voi public URL, vi du ngrok."""
    public_url = request.args.get("url", "")
    if not public_url:
        return jsonify({"ok": False, "error": "Thieu tham so url=https://..."})
    if len(public_url) > 300 or not is_public_https_url(public_url):
        return jsonify({"ok": False, "error": "Webhook URL phai la HTTPS public hop le"}), 400
    return jsonify(telegram_notifier.set_webhook(public_url))


@app.route("/telegram_status")
@require_admin
@rate_limit(max_calls=120, window_seconds=300)
def telegram_status():
    """Xem trang thai Telegram ma khong lo token."""
    telegram_notifier.refresh_config()
    return jsonify(
        {
            "enabled": telegram_notifier.enabled,
            "has_token": bool(telegram_notifier.token),
            "has_chat_id": bool(telegram_notifier.chat_id),
            "chat_id": telegram_notifier.chat_id,
            "auto_polling": telegram_notifier.auto_polling,
            "poll_interval_seconds": telegram_notifier.poll_interval,
            "update_offset": telegram_notifier.update_offset,
            "cooldown_seconds": telegram_notifier.cooldown,
            "last_status": telegram_notifier.last_status,
            "last_error": telegram_notifier.last_error,
            "last_response": telegram_notifier.last_response,
        }
    )


def generate_frames(model_mode=PRETRAINED_MODE, conf_threshold=0.5):
    """Stream webcam thanh MJPEG cho trinh duyet."""
    detector = get_detector(model_mode, conf_threshold)
    if detector.load_error:
        frame = warning_frame(detector.load_error)
        while True:
            chunk = encode_mjpeg(frame)
            if chunk:
                yield chunk

    cap = cv2.VideoCapture(0)
    alert_manager = AlertManager(warning_seconds=2)
    last_time = time()
    fps = 30

    if not cap.isOpened():
        chunk = encode_mjpeg(warning_frame("Khong the mo webcam. Hay kiem tra camera index 0."))
        if chunk:
            yield chunk
        return

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            now = time()
            fps = 1 / max(now - last_time, 0.001)
            last_time = now

            annotated_frame, _, phone_detected = detector.detect_image(frame)
            alert_level, _ = alert_manager.update(phone_detected=phone_detected, fps=fps)
            annotated_frame = draw_alert_overlay(annotated_frame, alert_level)
            if alert_level == "HIGH":
                handle_high_alert(annotated_frame)

            cv2.putText(
                annotated_frame,
                f"FPS {fps:.1f}",
                (30, annotated_frame.shape[0] - 28),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )

            chunk = encode_mjpeg(annotated_frame)
            if chunk:
                yield chunk
    finally:
        cap.release()


def telegram_polling_loop():
    """Theo doi /start moi neu app khong dung webhook public."""
    while True:
        telegram_notifier.refresh_config()
        if telegram_notifier.auto_polling:
            result = telegram_notifier.poll_registration_once()
            if result.get("saved"):
                print("[TELEGRAM POLL] updated chat id", result.get("chat"))
        sleep(telegram_notifier.poll_interval)


def start_telegram_polling():
    """Khoi dong polling nen mot lan."""
    global _telegram_polling_started
    if _telegram_polling_started:
        return
    _telegram_polling_started = True
    Thread(target=telegram_polling_loop, daemon=True).start()


def should_start_telegram_polling_in_wsgi():
    """Chi bat polling khi WSGI server duoc cau hinh ro rang."""
    return os.getenv("START_TELEGRAM_POLLING", "false").lower() == "true"


if __name__ == "__main__":
    start_telegram_polling()
    app.run(host=os.getenv("APP_HOST", "127.0.0.1"), port=int(os.getenv("PORT", "5000")), debug=False)
elif should_start_telegram_polling_in_wsgi():
    # Render chay app qua Gunicorn nen can khoi dong polling o nhanh nay.
    start_telegram_polling()
