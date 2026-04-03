from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from .utils import recognize_student_from_upload


@require_http_methods(["GET", "POST"])
def face_book_lookup(request):
    if request.method == 'GET':
        return JsonResponse(
            {
                'message': 'POST an image file as multipart/form-data with the key `image`.'
            }
        )

    uploaded_file = request.FILES.get('image')
    if uploaded_file is None:
        return JsonResponse({'error': 'Please upload an image using the `image` field.'}, status=400)

    try:
        result = recognize_student_from_upload(uploaded_file)
    except (ValueError, RuntimeError) as exc:
        return JsonResponse({'error': str(exc)}, status=400)

    payload = {
        'message': result.message,
        'faces_detected': result.faces_detected,
        'confidence': result.confidence,
    }
    if result.student is not None:
        student_payload = {
            'id': result.student.pk,
            'name': result.student.name,
            'roll_number': result.student.roll_number,
            'books_issued': result.student.books_issued,
        }

        try:
            from books.models import IssueRecord

            active_records = IssueRecord.objects.filter(
                student=result.student,
                returned_at__isnull=True,
            ).select_related('book')
            student_payload['books_issued'] = active_records.count()
            student_payload['active_books'] = [
                {
                    'title': record.book.title,
                    'isbn': record.book.isbn,
                    'issued_at': record.issued_at.isoformat(),
                    'due_date': record.due_date.isoformat() if record.due_date else None,
                }
                for record in active_records
            ]
        except Exception:
            student_payload['active_books'] = []

        payload['student'] = student_payload

    return JsonResponse(payload)
