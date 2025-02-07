from django.urls import path
from .views import (
    create_case, upload_image, case_details, case_list, edit_case, delete_case,
    delete_image, export_case_pdf, export_case_csv, case_logs, detect_tampering,
)

app_name = 'case_app'

urlpatterns = [
    # Case Management
    path('create/', create_case, name='create_case'),
    path('<int:case_id>/', case_details, name='case_details'),
    path('<int:case_id>/edit/', edit_case, name='edit_case'),
    path('<int:case_id>/delete/', delete_case, name='delete_case'),
    path('<int:case_id>/logs/', case_logs, name='case_logs'),
    path('', case_list, name='case_list'),

    # Image Management
    path('<int:case_id>/upload/', upload_image, name='upload_image'),
    path('image/<int:image_id>/delete/', delete_image, name='delete_image'),
    path('image/<int:image_id>/detect/', detect_tampering, name='detect_tampering'),
  
    # Exporting Case Data
    path('<int:case_id>/export/pdf/', export_case_pdf, name='export_case_pdf'),
    path('<int:case_id>/export/csv/', export_case_csv, name='export_case_csv'),
]
