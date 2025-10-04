import cv2
import threading
import time
import logging

logger = logging.getLogger(__name__)


def detect_cameras():
    """Detect available USB cameras."""
    available_cameras = []
    logger.info("[CAMERA] Début de la détection des caméras USB...")

    for i in range(10):
        try:
            logger.info(f"[CAMERA] Test de la caméra ID {i}...")
            backends = [cv2.CAP_ANY, cv2.CAP_DSHOW, cv2.CAP_V4L2, cv2.CAP_GSTREAMER]
            cap = None
            for backend in backends:
                try:
                    cap = cv2.VideoCapture(i, backend)
                    if cap.isOpened():
                        resolutions_to_test = [
                            (1920, 1080),
                            (1280, 720),
                            (640, 480)
                        ]
                        best_resolution = None
                        best_fps = 0
                        for test_width, test_height in resolutions_to_test:
                            cap.set(cv2.CAP_PROP_FRAME_WIDTH, test_width)
                            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, test_height)
                            cap.set(cv2.CAP_PROP_FPS, 30)
                            actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                            actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                            actual_fps = cap.get(cv2.CAP_PROP_FPS)
                            ret, frame = cap.read()
                            if ret and frame is not None and frame.shape[1] >= test_width * 0.9 and frame.shape[0] >= test_height * 0.9:
                                best_resolution = (actual_width, actual_height)
                                best_fps = actual_fps
                                logger.info(f"[CAMERA] Résolution {actual_width}x{actual_height} supportée pour la caméra {i}")
                                break
                            else:
                                logger.info(f"[CAMERA] Résolution {test_width}x{test_height} non supportée pour la caméra {i}")
                        if best_resolution:
                            width, height = best_resolution
                            fps = best_fps
                            backend_name = {
                                cv2.CAP_ANY: "Auto",
                                cv2.CAP_DSHOW: "DirectShow",
                                cv2.CAP_V4L2: "V4L2",
                                cv2.CAP_GSTREAMER: "GStreamer",
                            }.get(backend, "Inconnu")
                            name = f"Caméra {i} ({backend_name}) - {width}x{height}@{fps:.1f}fps"
                            available_cameras.append((i, name))
                            logger.info(f"[CAMERA] ✓ Caméra fonctionnelle détectée: {name}")
                            break
                        else:
                            logger.info(f"[CAMERA] Caméra {i} ouverte mais ne peut pas lire de frame avec backend {backend_name}")
                    cap.release()
                except Exception as e:
                    if cap:
                        cap.release()
                    logger.info(f"[CAMERA] Backend {backend} échoué pour caméra {i}: {e}")
                    continue
            if not available_cameras or available_cameras[-1][0] != i:
                logger.info(f"[CAMERA] ✗ Caméra {i} non disponible ou non fonctionnelle")
        except Exception as e:
            logger.info(f"[CAMERA] Erreur générale lors de la détection de la caméra {i}: {e}")
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
        self.error = None

    def start(self):
        if self.is_running:
            return True
        return self._initialize_camera()

    def _initialize_camera(self):
        try:
            self.camera = cv2.VideoCapture(self.camera_id, cv2.CAP_V4L2)
            self.camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            self.camera.set(cv2.CAP_PROP_FPS, 30)
            ret, frame = self.camera.read()
            if not ret or frame is None:
                logger.info(f"[USB CAMERA] La caméra {self.camera_id} ne retourne pas d'image")
                self.camera.release()
                return False
            self.is_running = True
            self.thread = threading.Thread(target=self._capture_loop)
            self.thread.daemon = True
            self.thread.start()
            logger.info(f"[USB CAMERA] Caméra {self.camera_id} démarrée avec succès via V4L2/MJPG")
            return True
        except Exception as e:
            logger.info(f"[USB CAMERA] Erreur avec V4L2/MJPG: {e}")
            if self.camera:
                self.camera.release()
            return False

    def _reconnect(self):
        logger.info(f"[USB CAMERA] Tentative de reconnexion de la caméra {self.camera_id}...")
        if self.camera:
            self.camera.release()
        self.camera = None
        time.sleep(1)
        return self._initialize_camera()

    def _capture_loop(self):
        while self.is_running:
            ret, frame = self.camera.read()
            if ret:
                _, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                with self.lock:
                    self.frame = jpeg.tobytes()
            # Pas de sleep ici

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

    def capture_high_res_photo(self):
        """Capture une photo en résolution maximale (ex: 4K)"""
        was_running = self.is_running
        self.is_running = False
        if self.camera:
            self.camera.release()
        cap = cv2.VideoCapture(self.camera_id, cv2.CAP_V4L2)
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 3840)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 2160)
        cap.set(cv2.CAP_PROP_FPS, 30)
        time.sleep(0.5)
        ret, frame = cap.read()
        if ret and frame is not None:
            _, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
            cap.release()
            if was_running:
                self._initialize_camera()
            return jpeg.tobytes()
        else:
            cap.release()
            if was_running:
                self._initialize_camera()
            raise Exception("Capture haute résolution échouée")

