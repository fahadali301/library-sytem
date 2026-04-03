import tempfile

import cv2
import numpy as np
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Student
from .utils import detect_faces
from books.models import Book, IssueRecord


class StudentModelTests(TestCase):
    def test_string_representation(self):
        student = Student(name='Ali', roll_number='S-001', books_issued=3)
        self.assertEqual(str(student), 'Ali (S-001)')


class FaceDetectionUtilityTests(TestCase):
    def test_blank_image_has_no_faces(self):
        image = np.zeros((240, 240, 3), dtype=np.uint8)
        self.assertEqual(detect_faces(image), [])


class FaceBookLookupViewTests(TestCase):
    def test_get_returns_help_message(self):
        response = self.client.get(reverse('face-book-lookup'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('POST an image file', response.json()['message'])

    def test_post_without_image_is_rejected(self):
        response = self.client.post(reverse('face-book-lookup'))
        self.assertEqual(response.status_code, 400)
        self.assertIn('image', response.json()['error'])

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_post_returns_student_books_when_recognition_succeeds(self):
        from . import views

        student = Student(id=1, name='Ali', roll_number='S-001', books_issued=7)
        image = np.zeros((50, 50, 3), dtype=np.uint8)
        ok, encoded = cv2.imencode('.jpg', image)
        self.assertTrue(ok)
        upload = SimpleUploadedFile('student.jpg', encoded.tobytes(), content_type='image/jpeg')

        class FakeResult:
            def __init__(self):
                self.student = student
                self.confidence = 12.5
                self.faces_detected = 1
                self.message = 'Student recognized successfully.'

        def fake_recognize(_uploaded_file):
            return FakeResult()

        original = views.recognize_student_from_upload
        views.recognize_student_from_upload = fake_recognize
        try:
            response = self.client.post(reverse('face-book-lookup'), data={'image': upload})
        finally:
            views.recognize_student_from_upload = original

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['student']['books_issued'], 0)
        self.assertEqual(payload['student']['name'], 'Ali')
        self.assertEqual(payload['faces_detected'], 1)
        self.assertEqual(payload['student']['active_books'], [])

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_api_includes_active_books_for_recognized_student(self):
        from . import views

        student = Student.objects.create(
            name='Sana',
            roll_number='S-900',
            books_issued=0,
            face_image='student_faces/sana.jpg',
        )
        book = Book.objects.create(
            title='Machine Learning',
            author='ML',
            isbn='ISBN-909',
            total_copies=1,
            available_copies=0,
        )
        IssueRecord.objects.create(student=student, book=book)

        class FakeResult:
            def __init__(self):
                self.student = student
                self.confidence = 22.2
                self.faces_detected = 1
                self.message = 'Student recognized successfully.'

        def fake_recognize(_uploaded_file):
            return FakeResult()

        image = np.zeros((40, 40, 3), dtype=np.uint8)
        ok, encoded = cv2.imencode('.jpg', image)
        self.assertTrue(ok)
        upload = SimpleUploadedFile('student.jpg', encoded.tobytes(), content_type='image/jpeg')

        original = views.recognize_student_from_upload
        views.recognize_student_from_upload = fake_recognize
        try:
            response = self.client.post(reverse('face-book-lookup'), data={'image': upload})
        finally:
            views.recognize_student_from_upload = original

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['student']['books_issued'], 1)
        self.assertEqual(payload['student']['active_books'][0]['title'], 'Machine Learning')
