from dataclasses import dataclass
from typing import List, Tuple, Optional
import numpy as np
import os

YOLO_CLASSES = [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus",
    "train", "truck", "boat", "traffic light", "fire hydrant",
    "stop sign", "parking meter", "bench", "bird", "cat", "dog",
    "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe",
    "backpack", "umbrella", "handbag", "tie", "suitcase", "frisbee",
    "skis", "snowboard", "sports ball", "kite", "baseball bat",
    "baseball glove", "skateboard", "surfboard", "tennis racket",
    "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl",
    "banana", "apple", "sandwich", "orange", "broccoli", "carrot",
    "hot dog", "pizza", "donut", "cake", "chair", "couch",
    "potted plant", "bed", "dining table", "toilet", "tv", "laptop",
    "mouse", "remote", "keyboard", "cell phone", "microwave", "oven",
    "toaster", "sink", "refrigerator", "book", "clock", "vase",
    "scissors", "teddy bear", "hair drier", "toothbrush",
]

DRONE_RELEVANT = {0: "person", 1: "bicycle", 2: "car", 3: "motorcycle",
                  5: "bus", 7: "truck", 9: "traffic light",
                  11: "stop sign", 13: "bench", 14: "bird",
                  15: "cat", 16: "dog", 20: "umbrella",
                  24: "backpack", 56: "chair", 57: "couch",
                  58: "potted plant", 59: "bed", 60: "dining table",
                  63: "laptop", 64: "mouse", 67: "cell phone",
                  73: "book", 74: "clock", 75: "vase"}

OBSTACLE_TYPES = {0: "person", 2: "car", 3: "motorcycle", 5: "bus",
                  7: "truck", 14: "bird", 56: "chair",
                  58: "potted plant", 73: "book", 74: "clock"}

INFERENCE_SIZE = 640
MODEL_PATH = os.path.join(os.path.dirname(__file__), "yolov8n.onnx")


@dataclass
class ObstacleDetection:
    class_id: int
    confidence: float
    bbox: Tuple[int, int, int, int]
    center: Tuple[float, float]
    width: int
    height: int

    @property
    def class_name(self) -> str:
        return YOLO_CLASSES[self.class_id] if 0 <= self.class_id < len(YOLO_CLASSES) else "unknown"

    def is_obstacle(self) -> bool:
        return self.class_id in OBSTACLE_TYPES

    def estimate_distance(self, altitude: float, frame_h: int,
                          fov_v_deg: float = 50.0) -> float:
        if self.height < 2 or altitude <= 0:
            return 100.0
        assumed = {0: 1.8, 2: 1.5, 3: 1.2, 5: 3.0, 7: 2.5,
                   14: 0.3, 56: 0.8, 58: 0.6, 73: 0.3, 74: 0.3}
        h_obj = assumed.get(self.class_id, 2.0)
        bbox_ratio = self.height / frame_h
        if bbox_ratio < 0.001:
            return 100.0
        dist = (h_obj * frame_h) / (2 * self.height * np.tan(np.radians(fov_v_deg / 2)))
        return float(np.clip(dist, 0.5, 200.0))

    def bearing(self, frame_w: int, frame_h: int,
                fov_h_deg: float = 70.0) -> Tuple[float, float]:
        cx_n = (self.center[0] / frame_w) * 2 - 1
        cy_n = (self.center[1] / frame_h) * 2 - 1
        fov_h = np.radians(fov_h_deg)
        fov_v = fov_h * frame_h / frame_w
        return cx_n * fov_h / 2, cy_n * fov_v / 2


def _letterbox(img: np.ndarray, target: int) -> Tuple[np.ndarray, int, int, int, int]:
    h, w = img.shape[:2]
    scale = min(target / w, target / h)
    nw = int(w * scale)
    nh = int(h * scale)
    from PIL import Image
    pil = Image.fromarray(img)
    resized = np.array(pil.resize((nw, nh), Image.LANCZOS))
    dx = (target - nw) // 2
    dy = (target - nh) // 2
    canvas = np.full((target, target, 3), 114, dtype=np.uint8)
    canvas[dy:dy+nh, dx:dx+nw] = resized
    return canvas, dx, dy, scale


def _nms(boxes: np.ndarray, scores: np.ndarray, iou_thresh: float = 0.5) -> List[int]:
    x1 = boxes[:, 0]
    y1 = boxes[:, 1]
    x2 = boxes[:, 2]
    y2 = boxes[:, 3]
    areas = (x2 - x1) * (y2 - y1)
    order = scores.argsort()[::-1]
    keep = []
    while order.size > 0:
        i = order[0]
        keep.append(i)
        if order.size == 1:
            break
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])
        w = np.maximum(0, xx2 - xx1)
        h = np.maximum(0, yy2 - yy1)
        inter = w * h
        iou = inter / (areas[i] + areas[order[1:]] - inter)
        inds = np.where(iou <= iou_thresh)[0]
        order = order[inds + 1]
    return keep


class YOLODetector:
    def __init__(self, model_path: str = MODEL_PATH,
                 conf_threshold: float = 0.4,
                 iou_threshold: float = 0.5,
                 class_filter: Optional[set] = None):
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.class_filter = class_filter or set(DRONE_RELEVANT.keys())
        self.session = None
        self.input_name = None
        self.input_shape = None
        self._load_model(model_path)

    def _load_model(self, path: str):
        if not os.path.exists(path):
            print(f"[YOLO] Model {path} not found — will download on first inference")
            return
        try:
            import onnxruntime as ort
            self.session = ort.InferenceSession(
                path, providers=["CPUExecutionProvider"]
            )
            self.input_name = self.session.get_inputs()[0].name
            self.input_shape = self.session.get_inputs()[0].shape
            _ = self.session.get_outputs()[0].name
            print(f"[YOLO] ONNX model loaded ({os.path.getsize(path)//1024} KB)")
        except Exception as e:
            print(f"[YOLO] Failed to load ONNX model: {e}")
            self.session = None

    def _download_model(self):
        url = ("https://github.com/ultralytics/assets/releases/latest/download"
               "/yolov8n.onnx")
        dest = MODEL_PATH
        print(f"[YOLO] Downloading {url} ...")
        try:
            import urllib.request
            urllib.request.urlretrieve(url, dest)
            print(f"[YOLO] Model downloaded to {dest}")
            self._load_model(dest)
        except Exception as e:
            print(f"[YOLO] Download failed: {e}")

    def detect(self, image: np.ndarray) -> List[ObstacleDetection]:
        if self.session is None:
            self._download_model()
        if self.session is None:
            return []

        import onnxruntime as ort

        preprocessed, dx, dy, scale_inv = _letterbox(image, INFERENCE_SIZE)
        inp = preprocessed.astype(np.float32) / 255.0
        inp = np.transpose(inp, (2, 0, 1))[None, :, :, :]

        out = self.session.run(None, {self.input_name: inp})[0]
        out = out.squeeze(0)

        cls_ids = []
        confs = []
        boxes = []

        for i in range(out.shape[1]):
            scores = out[4:, i]
            max_cls = int(scores.argmax())
            max_score = float(scores[max_cls])
            if max_score < self.conf_threshold:
                continue
            if max_cls not in self.class_filter:
                continue

            cx, cy, w, h = out[:4, i]
            cx = (cx - dx) * scale_inv
            cy = (cy - dy) * scale_inv
            w = w * scale_inv
            h = h * scale_inv
            x1 = max(0, int(cx - w / 2))
            y1 = max(0, int(cy - h / 2))
            x2 = min(image.shape[1], int(cx + w / 2))
            y2 = min(image.shape[0], int(cy + h / 2))
            if x2 <= x1 or y2 <= y1:
                continue

            cls_ids.append(max_cls)
            confs.append(max_score)
            boxes.append([x1, y1, x2, y2])

        if not boxes:
            return []

        boxes_arr = np.array(boxes)
        confs_arr = np.array(confs)
        keep = _nms(boxes_arr, confs_arr, self.iou_threshold)

        detections: List[ObstacleDetection] = []
        for idx in keep:
            x1, y1, x2, y2 = boxes_arr[idx]
            w = x2 - x1
            h = y2 - y1
            detections.append(ObstacleDetection(
                class_id=cls_ids[idx],
                confidence=float(confs_arr[idx]),
                bbox=(x1, y1, x2, y2),
                center=((x1 + x2) / 2, (y1 + y2) / 2),
                width=w,
                height=h,
            ))

        detections.sort(key=lambda d: d.confidence, reverse=True)
        return detections

    def draw_annotations(self, image: np.ndarray,
                         detections: List[ObstacleDetection]) -> np.ndarray:
        from PIL import Image, ImageDraw
        pil = Image.fromarray(image)
        draw = ImageDraw.Draw(pil)
        for d in detections:
            color = "green" if d.is_obstacle() else "orange"
            draw.rectangle(d.bbox, outline=color, width=2)
            label = f"{d.class_name} {d.confidence:.2f}"
            draw.text((d.bbox[0], d.bbox[1] - 14), label, fill=color)
        return np.array(pil)


def detect_from_webots(camera_data: bytes, width: int, height: int,
                       detector: YOLODetector) -> List[ObstacleDetection]:
    arr = np.frombuffer(camera_data, dtype=np.uint8).reshape((height, width, 4))
    rgb = arr[:, :, [2, 1, 0]].copy()
    return detector.detect(rgb)


def draw_detections(width: int, height: int,
                    detections: List[ObstacleDetection]) -> bytes:
    buf = np.zeros((height, width, 4), dtype=np.uint8)
    for d in detections:
        x1, y1, x2, y2 = d.bbox
        color = (0, 200, 0, 255) if d.is_obstacle() else (200, 150, 0, 255)
        cv = np.array(color, dtype=np.uint8)
        buf[y1:y2, x1:x2] = cv * 0.3 + buf[y1:y2, x1:x2] * 0.7
        if y1 > 0:
            buf[y1, x1:x2] = cv
            buf[max(0, y2-1), x1:x2] = cv
        if x1 > 0:
            buf[y1:y2, x1] = cv
            buf[y1:y2, max(0, x2-1)] = cv
    return buf.tobytes()
