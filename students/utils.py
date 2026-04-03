from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from .models import Student


FACE_SIZE = (200, 200)
CASCADE_PATH = Path(cv2.data.haarcascades) / 'haarcascade_frontalface_default.xml'


@dataclass(frozen=True)
class RecognitionResult:
    student: Student | None
    confidence: float | None
    faces_detected: int
    message: str


def _load_cascade() -> cv2.CascadeClassifier:
    cascade = cv2.CascadeClassifier(str(CASCADE_PATH))
    if cascade.empty():
        raise RuntimeError('OpenCV face cascade could not be loaded.')
    return cascade


def decode_upload_image(uploaded_file) -> np.ndarray:
    data = uploaded_file.read()
    if not data:
        raise ValueError('Empty image upload.')
    array = np.frombuffer(data, dtype=np.uint8)
    image = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError('Uploaded file is not a valid image.')
    return image


def detect_faces(image: np.ndarray) -> list[tuple[int, int, int, int]]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    cascade = _load_cascade()
    faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
    return [tuple(map(int, face)) for face in faces]


def _prepare_face_region(gray: np.ndarray, face_box: tuple[int, int, int, int]) -> np.ndarray:
    x, y, w, h = face_box
    face_region = gray[y : y + h, x : x + w]
    return cv2.resize(face_region, FACE_SIZE)


def _build_trainer() -> tuple[cv2.face.LBPHFaceRecognizer, dict[int, Student]]:
    if not hasattr(cv2, 'face') or not hasattr(cv2.face, 'LBPHFaceRecognizer_create'):
        raise RuntimeError('OpenCV contrib face recognizer is required for student matching.')

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    faces: list[np.ndarray] = []
    labels: list[int] = []
    label_map: dict[int, Student] = {}

    for student in Student.objects.exclude(face_image='').iterator():
        image_path = getattr(student.face_image, 'path', '')
        if not image_path:
            continue
        image = cv2.imread(image_path)
        if image is None:
            continue
        detected_faces = detect_faces(image)
        if not detected_faces:
            continue
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        face_region = _prepare_face_region(gray, detected_faces[0])
        faces.append(face_region)
        labels.append(student.pk)
        label_map[student.pk] = student

    if not faces:
        raise ValueError('At least one student face image is required for recognition.')

    recognizer.train(faces, np.array(labels, dtype=np.int32))
    return recognizer, label_map


def recognize_student_from_upload(uploaded_file, confidence_threshold: float = 75.0) -> RecognitionResult:
    image = decode_upload_image(uploaded_file)
    detected_faces = detect_faces(image)
    if not detected_faces:
        return RecognitionResult(
            student=None,
            confidence=None,
            faces_detected=0,
            message='No face detected in the uploaded image.',
        )

    recognizer, label_map = _build_trainer()
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    face_region = _prepare_face_region(gray, detected_faces[0])
    label, confidence = recognizer.predict(face_region)
    student = label_map.get(label)

    if student is None or confidence > confidence_threshold:
        return RecognitionResult(
            student=None,
            confidence=float(confidence),
            faces_detected=len(detected_faces),
            message='Face detected, but the student could not be matched confidently.',
        )

    return RecognitionResult(
        student=student,
        confidence=float(confidence),
        faces_detected=len(detected_faces),
        message='Student recognized successfully.',
    )

