"""
IntruderLens - Face Recognition & Whitelist Subsystem
Powered by OpenCV YuNet (Ultra-fast Face Detection) & SFace (Face Recognition ONNX).
Zero external heavy dependencies required: 100% offline, local, and hardware-accelerated.
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import List, Tuple, Dict, Optional
import numpy as np
import cv2

try:
    import config
except ImportError:
    from . import config

logger = logging.getLogger("IntruderLens")


class FaceRecognitionEngine:
    """
    Local, offline face recognition engine supporting multi-user enrollment and matching.
    """

    COSINE_THRESHOLD = 0.363  # SFace recommended threshold for cosine similarity
    L2_THRESHOLD = 1.128      # SFace recommended threshold for L2 norm

    def __init__(self,
                 yunet_model_path: Optional[Path] = None,
                 sface_model_path: Optional[Path] = None,
                 whitelist_dir: Optional[Path] = None):
        self.yunet_path = Path(yunet_model_path or getattr(config, "YUNET_MODEL_PATH", config.PROJECT_DIR / "models" / "face_detection_yunet_2023mar.onnx"))
        self.sface_path = Path(sface_model_path or getattr(config, "SFACE_MODEL_PATH", config.PROJECT_DIR / "models" / "face_recognition_sface_2021dec.onnx"))
        self.whitelist_dir = Path(whitelist_dir or getattr(config, "WHITELIST_DIR", config.PROJECT_DIR / "trusted_faces"))
        self.embeddings_file = self.whitelist_dir / "embeddings.json"

        self.detector = None
        self.recognizer = None
        self.known_profiles: Dict[str, List[np.ndarray]] = {}  # name -> list of feature vectors

        self._initialize_models()
        self.load_known_profiles()

    def _initialize_models(self):
        """Loads the ONNX models into OpenCV DNN."""
        if not self.yunet_path.exists() or not self.sface_path.exists():
            logger.warning(
                f"Face recognition models not found at {self.yunet_path} or {self.sface_path}. "
                "Face recognition will be disabled until models are downloaded."
            )
            return

        try:
            # FaceDetectorYN: input_size set initially to (320, 320), dynamically updated per image
            self.detector = cv2.FaceDetectorYN.create(
                str(self.yunet_path),
                "",
                (320, 320),
                score_threshold=0.55,
                nms_threshold=0.3,
                top_k=5000
            )
            self.recognizer = cv2.FaceRecognizerSF.create(str(self.sface_path), "")
            logger.info("FaceDetectorYN (YuNet) and FaceRecognizerSF (SFace) loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load OpenCV face recognition models: {e}")

    @property
    def is_ready(self) -> bool:
        return self.detector is not None and self.recognizer is not None

    def detect_faces(self, image: np.ndarray) -> Optional[np.ndarray]:
        """
        Detects faces in an image using YuNet.
        Returns faces array of shape (N, 15) or None.
        Each face row has: [x, y, w, h, x_re, y_re, x_le, y_le, x_nt, y_nt, x_rcm, y_rcm, x_lcm, y_lcm, score]
        """
        if not self.is_ready or image is None:
            return None

        h, w = image.shape[:2]
        self.detector.setInputSize((w, h))
        _, faces = self.detector.detect(image)
        return faces

    def extract_features(self, image: np.ndarray, face_box: np.ndarray) -> Optional[np.ndarray]:
        """Aligns and crops a detected face, then computes its 128D SFace feature embedding."""
        if not self.is_ready:
            return None
        try:
            aligned_face = self.recognizer.alignCrop(image, face_box)
            feature = self.recognizer.feature(aligned_face)
            return feature
        except Exception as e:
            logger.debug(f"Failed to extract face features: {e}")
            return None

    def enroll_face_from_image(self, person_name: str, image_path: Path) -> bool:
        """Enrolls a trusted face from an existing image file on disk."""
        person_name = person_name.strip()
        if not person_name:
            print("[ERROR] Person name cannot be empty.")
            return False

        if not Path(image_path).exists():
            print(f"[ERROR] Image path does not exist: {image_path}")
            return False

        img = cv2.imread(str(image_path))
        if img is None:
            print(f"[ERROR] Failed to load image: {image_path}")
            return False

        faces = self.detect_faces(img)
        if faces is None or len(faces) == 0:
            print(f"[ERROR] No face detected in {image_path}. Please use a clear, well-lit photo.")
            return False

        # Pick the largest/most confident face
        primary_face = faces[0]
        feature = self.extract_features(img, primary_face)
        if feature is None:
            print("[ERROR] Could not extract face feature vector.")
            return False

        # Save photo into user's folder
        user_dir = self.whitelist_dir / person_name
        user_dir.mkdir(parents=True, exist_ok=True)
        target_img_name = f"ref_{len(list(user_dir.glob('*.jpg'))) + 1}.jpg"
        target_path = user_dir / target_img_name
        cv2.imwrite(str(target_path), img)

        # Store in profiles
        if person_name not in self.known_profiles:
            self.known_profiles[person_name] = []
        self.known_profiles[person_name].append(feature)

        self.save_known_profiles()
        print(f"[SUCCESS] Successfully enrolled '{person_name}' from {image_path}!")
        return True

    def enroll_face_from_webcam(self, person_name: str, num_samples: int = 5) -> bool:
        """
        Interactively captures multiple facial samples from the webcam
        to capture different slight angles and lighting conditions for robust matching.
        """
        person_name = person_name.strip()
        if not person_name:
            print("[ERROR] Person name cannot be empty.")
            return False

        if not self.is_ready:
            print("[ERROR] Face recognition engine is not initialized.")
            return False

        user_dir = self.whitelist_dir / person_name
        user_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n=======================================================")
        print(f" Enrolling Trusted Face for: '{person_name}'")
        print(f" Please look directly at the webcam...")
        print(f" Capturing {num_samples} high-confidence facial angles.")
        print(f"=======================================================\n")

        cap = cv2.VideoCapture(config.CAMERA_INDEX, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(config.CAMERA_INDEX)

        if not cap.isOpened():
            print("[ERROR] Could not open webcam.")
            return False

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        # Sensor warmup
        for _ in range(10):
            cap.read()

        collected_features = []
        sample_count = 0
        attempts = 0
        max_attempts = 60

        import time

        while sample_count < num_samples and attempts < max_attempts:
            attempts += 1
            ret, frame = cap.read()
            if not ret or frame is None:
                time.sleep(0.1)
                continue

            faces = self.detect_faces(frame)
            if faces is not None and len(faces) > 0:
                score = faces[0][-1]
                if score >= 0.70:  # High confidence face
                    feat = self.extract_features(frame, faces[0])
                    if feat is not None:
                        sample_count += 1
                        collected_features.append(feat)
                        save_path = user_dir / f"sample_{sample_count}.jpg"
                        cv2.imwrite(str(save_path), frame)
                        print(f" -> Captured sample {sample_count}/{num_samples} (Confidence: {score:.1%})")
                        time.sleep(0.4)  # Slight pause for varied expression/angle
            time.sleep(0.1)

        cap.release()

        if sample_count == 0:
            print("[FAILED] Could not capture any clear face samples. Please ensure good lighting and look straight at the webcam.")
            return False

        if person_name not in self.known_profiles:
            self.known_profiles[person_name] = []
        self.known_profiles[person_name].extend(collected_features)

        self.save_known_profiles()
        print(f"\n[SUCCESS] '{person_name}' enrolled with {sample_count} trusted face samples!")
        return True

    def save_known_profiles(self):
        """Serializes feature embeddings to disk for instant boot-up matching."""
        self.whitelist_dir.mkdir(parents=True, exist_ok=True)
        serializable = {}
        for name, feats in self.known_profiles.items():
            serializable[name] = [f.tolist() for f in feats]

        try:
            with open(self.embeddings_file, "w", encoding="utf-8") as f:
                json.dump(serializable, f)
            logger.info(f"Saved {len(self.known_profiles)} profiles to {self.embeddings_file}")
        except Exception as e:
            logger.error(f"Failed to save embeddings: {e}")

    def load_known_profiles(self):
        """Loads feature embeddings from disk or re-indexes photos in trusted_faces/."""
        self.known_profiles.clear()

        # Try fast load from JSON cache
        if self.embeddings_file.exists():
            try:
                with open(self.embeddings_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for name, feat_list in data.items():
                    self.known_profiles[name] = [np.array(f, dtype=np.float32) for f in feat_list]
                logger.info(f"Loaded {len(self.known_profiles)} trusted face profiles from cache.")
                return
            except Exception as e:
                logger.warning(f"Could not load cached embeddings, re-indexing photos: {e}")

        # Fallback: scan directories in trusted_faces/
        if self.whitelist_dir.exists() and self.is_ready:
            for user_folder in self.whitelist_dir.iterdir():
                if user_folder.is_dir():
                    name = user_folder.name
                    self.known_profiles[name] = []
                    for img_file in user_folder.glob("*.jpg"):
                        img = cv2.imread(str(img_file))
                        if img is not None:
                            faces = self.detect_faces(img)
                            if faces is not None and len(faces) > 0:
                                feat = self.extract_features(img, faces[0])
                                if feat is not None:
                                    self.known_profiles[name].append(feat)
            if self.known_profiles:
                self.save_known_profiles()

    def identify_face(self, frame: np.ndarray, tolerance: Optional[float] = None) -> Tuple[bool, Optional[str], float, Optional[np.ndarray]]:
        """
        Analyzes a captured frame:
        1. Detects face(s).
        2. Compares against all enrolled profiles in the whitelist.
        3. Returns (is_whitelisted, matched_name, best_score, primary_face_box).

        :param tolerance: Cosine similarity threshold (defaults to COSINE_THRESHOLD = 0.363).
        :return: (is_whitelisted: bool, matched_name: str or None, best_score: float, face_box: np.ndarray or None)
        """
        if not self.is_ready:
            # If models not loaded, treat as unknown / not whitelisted
            return False, None, 0.0, None

        threshold = tolerance if tolerance is not None else getattr(config, "FACE_MATCH_THRESHOLD", self.COSINE_THRESHOLD)

        faces = self.detect_faces(frame)
        if faces is None or len(faces) == 0:
            logger.info("Face recognition: No face detected in frame.")
            return False, None, 0.0, None

        # Sort faces by detection score and area to check the primary person
        primary_face = faces[0]
        test_feature = self.extract_features(frame, primary_face)
        if test_feature is None:
            return False, None, 0.0, primary_face

        best_match_name = None
        best_score = -1.0

        for name, enrolled_feats in self.known_profiles.items():
            for ref_feat in enrolled_feats:
                # SFace cosine similarity match
                score = self.recognizer.match(test_feature, ref_feat, cv2.FaceRecognizerSF_FR_COSINE)
                if score > best_score:
                    best_score = score
                    if score >= threshold:
                        best_match_name = name

        is_whitelisted = best_match_name is not None
        if is_whitelisted:
            logger.info(f"✅ FACE MATCHED! Authorized Person: '{best_match_name}' (Score: {best_score:.4f} >= {threshold:.4f})")
        else:
            logger.warning(f"🚨 UNRECOGNIZED FACE / INTRUDER DETECTED! (Highest score was {best_score:.4f} < {threshold:.4f})")

        return is_whitelisted, best_match_name, best_score, primary_face

    def list_enrolled_profiles(self) -> Dict[str, int]:
        """Returns dict of enrolled names and their number of samples."""
        return {name: len(feats) for name, feats in self.known_profiles.items()}

    def remove_profile(self, person_name: str) -> bool:
        """Removes a trusted person from the whitelist."""
        if person_name in self.known_profiles:
            del self.known_profiles[person_name]
            self.save_known_profiles()
            # Delete image directory if exists
            user_dir = self.whitelist_dir / person_name
            if user_dir.exists():
                import shutil
                shutil.rmtree(user_dir, ignore_errors=True)
            print(f"[SUCCESS] Removed '{person_name}' from trusted face whitelist.")
            return True
        else:
            print(f"[ERROR] '{person_name}' is not in the trusted profiles list.")
            return False

