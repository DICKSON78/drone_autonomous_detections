#!/usr/bin/env python3
"""Object Detection Node — YOLO client with camera feed support."""

import os, sys, time, json, io, base64, argparse
import urllib.request
import numpy as np

GREEN = "\033[92m"; YELLOW = "\033[93m"; RED = "\033[91m"
CYAN = "\033[96m"; BOLD = "\033[1m"; RESET = "\033[0m"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False
    print(f"  {YELLOW}[WARN] OpenCV not available, running in log-only mode{RESET}")

class ObjectDetector:
    def __init__(self, yolo_url="http://localhost:8002", use_yolo=True):
        self.yolo_url = yolo_url
        self.use_yolo = use_yolo and self._check_yolo()
        self.frame_count = 0
        self.detection_history = []
        self.confidence_threshold = 0.5

    def _check_yolo(self):
        try:
            req = urllib.request.Request(f"{self.yolo_url}/health",
                                         method="GET")
            urllib.request.urlopen(req, timeout=2)
            print(f"  {GREEN}[DETECT] YOLO service found at {self.yolo_url}{RESET}")
            return True
        except:
            print(f"  {YELLOW}[DETECT] YOLO service unavailable (port 8002){RESET}")
            return False

    def detect_yolo(self, image):
        _, img_encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 85])
        img_bytes = io.BytesIO(img_encoded.tobytes())
        boundary = "----boundary123"
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="frame.jpg"\r\n'
            f"Content-Type: image/jpeg\r\n\r\n"
        ).encode() + img_bytes.getvalue() + f"\r\n--{boundary}--\r\n".encode()
        req = urllib.request.Request(
            f"{self.yolo_url}/detect",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
        try:
            resp = urllib.request.urlopen(req, timeout=5)
            result = json.loads(resp.read().decode())
            return result.get("detections", [])
        except:
            return []

    def detect_hsv(self, image):
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        detections = []
        ranges = [
            ("vehicle", 1, [(0, 100, 100), (10, 255, 255)], [(170, 100, 100), (180, 255, 255)]),
            ("obstacle", 2, [(35, 100, 100), (85, 255, 255)], None),
            ("building", 3, [(100, 100, 100), (130, 255, 255)], None),
        ]
        for name, cid, range1, range2 in ranges:
            mask = cv2.inRange(hsv, np.array(range1[0]), np.array(range1[1]))
            if range2:
                mask2 = cv2.inRange(hsv, np.array(range2[0]), np.array(range2[1]))
                mask = cv2.bitwise_or(mask, mask2)
            contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area > 500:
                    x, y, w, h = cv2.boundingRect(cnt)
                    confidence = min(1.0, area / 10000)
                    if confidence >= self.confidence_threshold:
                        detections.append({
                            "class_id": cid, "class_name": name,
                            "bbox": [int(x), int(y), int(w), int(h)],
                            "confidence": round(confidence, 2),
                        })
        return detections

    def draw_detections(self, image, detections):
        colors = {1: (0, 0, 255), 2: (0, 255, 0), 3: (255, 0, 0)}
        for d in detections:
            x, y, w, h = d["bbox"]
            color = colors.get(d["class_id"], (255, 255, 255))
            cv2.rectangle(image, (x, y), (x + w, y + h), color, 2)
            label = f"{d['class_name']} {d['confidence']:.2f}"
            cv2.putText(image, label, (x, y - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        cv2.putText(image, f"Frame: {self.frame_count}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(image, f"Detections: {len(detections)}", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        return image

    def generate_test_frame(self, width=640, height=480):
        img = np.zeros((height, width, 3), dtype=np.uint8)
        img[:] = (135, 206, 235)
        square_size = 40
        for i in range(0, height, square_size):
            for j in range(0, width, square_size):
                if ((i // square_size) + (j // square_size)) % 2 == 0:
                    img[i:i + square_size, j:j + square_size] = [100, 100, 100]
        centers = [(200, 240, "vehicle", (0, 0, 200)),
                   (450, 180, "building", (200, 0, 0)),
                   (320, 350, "obstacle", (0, 180, 0))]
        for cx, cy, label, color in centers:
            cv2.circle(img, (cx, cy), 30, color, -1)
            cv2.putText(img, label, (cx - 20, cy - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        cv2.putText(img, "Drone Camera Feed", (50, 100),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 2)
        return img

    def run_once(self, image=None):
        if image is None:
            image = self.generate_test_frame()
        self.frame_count += 1
        if self.use_yolo:
            detections = self.detect_yolo(image)
        else:
            detections = self.detect_hsv(image)
        self.detection_history.append({
            "frame": self.frame_count,
            "detections": len(detections),
            "timestamp": time.time(),
        })
        if len(self.detection_history) > 100:
            self.detection_history.pop(0)
        viz = self.draw_detections(image.copy(), detections)
        log_msg = f"Frame {self.frame_count}: {len(detections)} object(s)"
        if detections:
            log_msg += " [" + ", ".join(f"{d['class_name']}({d['confidence']:.2f})" for d in detections) + "]"
        print(f"  {CYAN}[DETECT]{RESET} {log_msg}")
        return detections, viz

    def run_continuous(self, interval=1.0, output_dir=None):
        print(f"  {GREEN}[DETECT] Starting continuous detection ({interval}s interval){RESET}")
        print(f"  {GREEN}[DETECT] {'YOLO API' if self.use_yolo else 'HSV fallback'} mode{RESET}")
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        try:
            while True:
                frame = self.generate_test_frame()
                detections, viz = self.run_once(frame)
                if HAS_CV2 and output_dir:
                    path = os.path.join(output_dir, f"frame_{self.frame_count:04d}.jpg")
                    cv2.imwrite(path, viz)
                time.sleep(interval)
        except KeyboardInterrupt:
            print(f"\n  {YELLOW}[DETECT] Stopped{RESET}")

def main():
    parser = argparse.ArgumentParser(description="Object Detection Node")
    parser.add_argument("--yolo-url", default="http://localhost:8002")
    parser.add_argument("--no-yolo", action="store_true", help="Force HSV mode")
    parser.add_argument("--interval", type=float, default=2.0)
    parser.add_argument("--output", default=None, help="Output directory for frames")
    parser.add_argument("--once", action="store_true", help="Single detection then exit")
    args = parser.parse_args()

    detector = ObjectDetector(args.yolo_url, use_yolo=not args.no_yolo)
    if args.once:
        frame = detector.generate_test_frame()
        dets, viz = detector.run_once(frame)
        if HAS_CV2 and args.output:
            path = os.path.join(args.output, f"detection_{int(time.time())}.jpg")
            cv2.imwrite(path, viz)
            print(f"  Saved to {path}")
    else:
        detector.run_continuous(args.interval, args.output)

if __name__ == "__main__":
    main()
