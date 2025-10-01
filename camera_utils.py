import cv2
import threading
import time
import logging

logger = logging.getLogger(__name__)

class UsbCamera:
    def __init__(self, camera_id=0):
        self.camera_id = camera_id
        self.camera = None
        self.is_running = False
        self.thread = None
        self.frame = None
        self.lock = threading.Lock()
    
    def start(self):
        if self.is_running:
            return True
        
        # Ouvrir la caméra via V4L2
        self.camera = cv2.VideoCapture(f"/dev/video{self.camera_id}", cv2.CAP_V4L2)
        if not self.camera.isOpened():
            logger.error(f"[USB CAMERA] Impossible d'ouvrir la caméra {self.camera_id}")
            return False
        
        # Forcer MJPG
        self.camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 3840)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 2160)
        self.camera.set(cv2.CAP_PROP_FPS, 30)
        
        # Vérification
        actual_width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = self.camera.get(cv2.CAP_PROP_FPS)
        logger.info(f"[USB CAMERA] Caméra {self.camera_id} ouverte : {actual_width}x{actual_height}@{actual_fps:.1f}fps (MJPG)")

        self.is_running = True
        self.thread = threading.Thread(target=self._capture_loop)
        self.thread.daemon = True
        self.thread.start()
        return True
    
    def _capture_loop(self):
        while self.is_running:
            ret, frame = self.camera.read()
            if ret and frame is not None:
                _, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                with self.lock:
                    self.frame = jpeg.tobytes()
            time.sleep(0.01)
    
    def get_frame(self):
        with self.lock:
            return self.frame
    
    def stop(self):
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        if self.camera:
            self.camera.release()
        logger.info(f"[USB CAMERA] Caméra {self.camera_id} arrêtée")
