import cv2
import threading
import time
import logging

logger = logging.getLogger(__name__)

def detect_cameras():
    """Retourne la caméra fixe configurée en dur (3840x2160@30fps MJPG)."""
    camera_id = 0  # ID de la caméra à utiliser
    available_cameras = []

    logger.info("[CAMERA] Début de la détection de la caméra en dur...")
    cap = cv2.VideoCapture(f"/dev/video{camera_id}", cv2.CAP_V4L2)
    if not cap.isOpened():
        logger.error(f"[CAMERA] Impossible d'ouvrir la caméra {camera_id}")
        return available_cameras

    # Forcer MJPG et résolution max
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
    cap.set(cv2.CAP_PROP_FPS, 30)

    actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    actual_fps = cap.get(cv2.CAP_PROP_FPS)

    ret, frame = cap.read()
    if ret and frame is not None:
        name = f"Caméra {camera_id} (V4L2) - {actual_width}x{actual_height}@{actual_fps:.1f}fps"
        available_cameras.append((camera_id, name))
        logger.info(f"[CAMERA] ✓ Caméra fonctionnelle détectée : {name}")
    else:
        logger.error(f"[CAMERA] Caméra {camera_id} ouverte mais ne retourne pas d'image valide")

    cap.release()
    logger.info(f"[CAMERA] Détection terminée. {len(available_cameras)} caméra(s) fonctionnelle(s) trouvée(s)")
    return available_cameras

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
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
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
