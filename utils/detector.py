from pathlib import Path

import cv2


PRETRAINED_MODE = "YOLOv8n pretrained - Cell phone only"
CUSTOM_MODE = "Custom YOLOv8m - models/best.pt"
CUSTOM_MODEL_MISSING_MESSAGE = (
    "Khong tim thay models/best.pt. Hay dung YOLOv8n pretrained hoac them model custom."
)
PHONE_LABELS = {"phone", "cell phone"}
COCO_CELL_PHONE_ID = 67


class PhoneDetector:
    """Tai YOLO that va ve bounding box bang OpenCV."""

    def __init__(self, model_mode, custom_model_path="models/best.pt", conf_threshold=0.5):
        self.model_mode = model_mode
        self.custom_model_path = Path(custom_model_path)
        self.conf_threshold = float(conf_threshold)
        self.model = None
        self.model_ready = False
        self.load_error = ""
        self._load_model()

    def _load_model(self):
        """Tai YOLOv8n hoac custom best.pt."""
        if self.model_mode == CUSTOM_MODE and not self.custom_model_path.exists():
            self.load_error = CUSTOM_MODEL_MISSING_MESSAGE
            return

        try:
            from ultralytics import YOLO

            model_path = "yolov8n.pt" if self.model_mode == PRETRAINED_MODE else str(self.custom_model_path)
            self.model = YOLO(model_path)
            self.model_ready = True
        except Exception as exc:
            self.model = None
            self.model_ready = False
            self.load_error = f"Khong the tai model: {exc}"

    def detect_image(self, frame):
        """Tra ve frame annotate, detections va trang thai co phone."""
        if not self.model_ready or self.model is None:
            return frame.copy(), [], False

        if self.model_mode == PRETRAINED_MODE:
            results = self.model(
                frame,
                conf=self.conf_threshold,
                classes=[COCO_CELL_PHONE_ID],
                verbose=False,
            )
            return self._parse_results(frame, results[0], only_cell_phone=True)

        results = self.model(frame, conf=self.conf_threshold, verbose=False)
        return self._parse_results(frame, results[0], only_cell_phone=False)

    def _parse_results(self, frame, result, only_cell_phone):
        """Chuyen YOLO results thanh frame va bang detection."""
        annotated_frame = frame.copy()
        detections = []
        phone_detected = False
        names = result.names or {}

        for box in result.boxes:
            cls_id = int(box.cls[0].item())
            if only_cell_phone and cls_id != COCO_CELL_PHONE_ID:
                continue

            confidence = float(box.conf[0].item())
            label = "cell phone" if only_cell_phone else str(names.get(cls_id, cls_id)).lower()
            is_phone = label in PHONE_LABELS or (only_cell_phone and cls_id == COCO_CELL_PHONE_ID)
            phone_detected = phone_detected or is_phone
            x1, y1, x2, y2 = [float(value) for value in box.xyxy[0].tolist()]

            self._draw_box(annotated_frame, x1, y1, x2, y2, label, confidence)
            detections.append(
                {
                    "label": label,
                    "confidence": round(confidence, 3),
                    "x1": round(x1, 1),
                    "y1": round(y1, 1),
                    "x2": round(x2, 1),
                    "y2": round(y2, 1),
                    "is_phone": is_phone,
                    "class_id": cls_id,
                }
            )

        return annotated_frame, detections, phone_detected

    @staticmethod
    def _draw_box(frame, x1, y1, x2, y2, label, confidence):
        """Ve bounding box bang OpenCV."""
        p1 = (int(x1), int(y1))
        p2 = (int(x2), int(y2))
        color = (0, 220, 255)
        text = f"{label} {confidence:.2f}"

        cv2.rectangle(frame, p1, p2, color, 2)
        text_size, _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.65, 2)
        text_w, text_h = text_size
        text_y = max(p1[1] - 10, text_h + 10)
        cv2.rectangle(
            frame,
            (p1[0], text_y - text_h - 8),
            (p1[0] + text_w + 10, text_y + 4),
            color,
            -1,
        )
        cv2.putText(
            frame,
            text,
            (p1[0] + 5, text_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (8, 13, 25),
            2,
            cv2.LINE_AA,
        )
