# AI Exam Monitoring

A Flask web app that detects suspected **cell phone usage during exams** using **Ultralytics YOLOv8** and **OpenCV**. Operators can analyze a single image, an uploaded video, or a live webcam feed, review annotated evidence, and receive **Telegram alerts**.

> Vietnamese-first UI (Tiếng Việt) · Built as a university AI project.

## Features

- **Three input sources, one workflow**: image upload, video upload (frame-by-frame), and real-time camera stream (MJPEG via `/video_feed`).
- **YOLOv8n (COCO)** restricted to the `cell phone` class (ID 67), or a **custom YOLOv8 model** via `models/best.pt`.
- **Temporal alert logic**: a `NORMAL → LOW → HIGH` state machine based on consecutive frames with a phone, which reduces false alarms from single-frame detections.
- **Evidence capture**: `HIGH` alert frames are saved with bounding box, label, confidence, and timestamp.
- **Telegram notifications** with cooldown to prevent spam, plus chat registration via `/start`, an allow-list, or a registration code.
- **Security hardening**: upload whitelist (extension + MIME + magic bytes + size limit), `safe_join` against path traversal, token-protected admin routes, rate limiting, and security headers (CSP, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`, optional HSTS).
- **Tests** for the security layer and Telegram flow (`unittest`).

## Tech stack

Python · Flask · Ultralytics YOLOv8 · OpenCV · NumPy · Telegram Bot API · HTML/CSS/JS (GSAP)

## Project structure

```text
app.py                  # Flask routes, security, streaming
utils/
  detector.py           # YOLO loading + bounding-box drawing
  alert_logic.py        # NORMAL / LOW / HIGH alert state machine
  telegram_notifier.py  # Telegram sending, polling, webhook
templates/              # Jinja2 pages (home, image, video, camera)
static/                 # CSS, JS, images
tests/test_security.py
```

## Getting started

```bash
git clone https://github.com/<your-username>/proctoring-phone-detector.git
cd proctoring-phone-detector
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # Windows: copy .env.example .env
python app.py
```

Open <http://127.0.0.1:5000>. The `yolov8n.pt` weights are downloaded automatically by Ultralytics on first run.

### Custom model (optional)

Put your trained weights at `models/best.pt` (or set `CUSTOM_MODEL_PATH` in `.env`), then choose the custom model in the UI. If the file is missing, the app shows a warning and does not crash.

### Telegram alerts (optional)

1. Create a bot with [@BotFather](https://t.me/BotFather) and copy the token.
2. In `.env`:
   ```env
   TELEGRAM_ENABLED=true
   TELEGRAM_BOT_TOKEN=<your_bot_token>
   ALERT_COOLDOWN_SECONDS=30
   ```
3. Run the app and send `/start` to your bot; the app saves your chat ID automatically via polling.
4. To restrict who can subscribe, set `TELEGRAM_ALLOWED_USER_IDS` or `TELEGRAM_REGISTRATION_CODE`.

`ADMIN_API_TOKEN` is generated automatically on first run if left empty. Admin routes require the `X-Admin-Token` header.

## Run tests

```bash
python -m unittest tests.test_security
```

## Limitations & future work

- Pretrained COCO `cell phone` detection can miss phones that are small, occluded, or at odd angles; a model fine-tuned on exam-room data would improve recall.
- Detection is per-frame; adding tracking (e.g. ByteTrack) would make alert logic more robust.
- Flask's dev server is for local use; use a production WSGI server (gunicorn/waitress) and HTTPS when deploying.

## License

MIT
