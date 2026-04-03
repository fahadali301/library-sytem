import cv2
import numpy as np
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from books.models import Book, IssueRecord
from students.models import Student


def _test_image_file(name='face.png'):
    image = np.zeros((20, 20, 3), dtype=np.uint8)
    ok, encoded = cv2.imencode('.png', image)
    if not ok:
        raise RuntimeError('Could not create test image.')
    return SimpleUploadedFile(name, encoded.tobytes(), content_type='image/png')


class BookIssueFlowTests(TestCase):
    def setUp(self):
        self.student = Student.objects.create(
            name='Ayesha',
            roll_number='S-100',
            books_issued=0,
            face_image='student_faces/test.jpg',
        )
        self.book = Book.objects.create(
            title='Python Basics',
            author='PS',
            isbn='ISBN-001',
            total_copies=2,
            available_copies=2,
        )

    def test_issue_book_reduces_available_count(self):
        response = self.client.post(
            reverse('book-issue'),
            data={'student': self.student.id, 'book': self.book.id, 'due_date': ''},
        )
        self.assertEqual(response.status_code, 302)
        self.book.refresh_from_db()
        self.student.refresh_from_db()
        self.assertEqual(self.book.available_copies, 1)
        self.assertEqual(self.student.books_issued, 1)
        self.assertEqual(IssueRecord.objects.filter(student=self.student, returned_at__isnull=True).count(), 1)

    def test_return_book_increases_available_count(self):
        issue = IssueRecord.objects.create(student=self.student, book=self.book)
        self.book.available_copies = 1
        self.book.save(update_fields=['available_copies'])
        self.student.books_issued = 1
        self.student.save(update_fields=['books_issued'])

        response = self.client.post(reverse('book-return', args=[issue.id]))
        self.assertEqual(response.status_code, 302)
        issue.refresh_from_db()
        self.book.refresh_from_db()
        self.student.refresh_from_db()
        self.assertIsNotNone(issue.returned_at)
        self.assertEqual(self.book.available_copies, 2)
        self.assertEqual(self.student.books_issued, 0)


class DashboardViewTests(TestCase):
    def test_dashboard_shows_quick_actions(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Add Student')
        self.assertContains(response, 'Overdue Issues')


class StudentAddTests(TestCase):
    def test_add_student_page_get(self):
        response = self.client.get(reverse('student-add'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Add Student')

    def test_add_student_page_post_creates_student(self):
        response = self.client.post(
            reverse('student-add'),
            data={
                'name': 'Nida',
                'roll_number': 'S-501',
                'face_image': _test_image_file(),
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Student.objects.filter(roll_number='S-501').exists())


class FaceLookupPageTests(TestCase):
    def test_face_lookup_page_get(self):
        response = self.client.get(reverse('face-lookup-page'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Face Lookup')

    def test_face_lookup_without_file_shows_error(self):
        response = self.client.post(reverse('face-lookup-page'), data={})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please upload an image.')

    def test_face_lookup_post_with_mocked_recognition(self):
        from books import views

        student = Student.objects.create(
            name='Ali',
            roll_number='S-200',
            books_issued=0,
            face_image='student_faces/ali.jpg',
        )
        book = Book.objects.create(
            title='Django Guide',
            author='DJ',
            isbn='ISBN-555',
            total_copies=1,
            available_copies=0,
        )
        IssueRecord.objects.create(student=student, book=book)

        class FakeResult:
            def __init__(self):
                self.student = student
                self.confidence = 18.0
                self.faces_detected = 1
                self.message = 'Student recognized successfully.'

        def fake_recognize(_uploaded_file):
            return FakeResult()

        original = views.recognize_student_from_upload
        views.recognize_student_from_upload = fake_recognize
        try:
            image = SimpleUploadedFile('student.jpg', b'abc', content_type='image/jpeg')
            response = self.client.post(reverse('face-lookup-page'), data={'image': image})
        finally:
            views.recognize_student_from_upload = original

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Django Guide')
        self.assertContains(response, 'Active Books')
