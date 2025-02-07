import os
import hashlib
import imagehash
from PIL import ImageChops, ImageDraw
from PIL import Image as PILImage
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.template.loader import get_template
from django.utils.dateparse import parse_date
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from .models import Case, Image, ActivityLog
from .forms import CaseForm, ImageUploadForm
from xhtml2pdf import pisa
import csv
from django.conf import settings
from django.db import IntegrityError

# Helper functions
def has_case_permission(user, case):
    """
    Check if the user has permission to manage the given case.
    """
    return user.is_superuser or user == case.investigator


def safe_parse_date(date_str):
    """
    Safely parse a date string into a date object.
    """
    from datetime import datetime
    try:
        return parse_date(date_str) or datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None


# Case Management Views
@login_required
def create_case(request):
    """
    Create a new case with optional tampering threshold.
    """
    if request.method == 'POST':
        form = CaseForm(request.POST)
        if form.is_valid():
            case = form.save(commit=False)
            case.investigator = request.user

            # Use a default tampering threshold if not provided
            if not case.tampering_threshold:
                case.tampering_threshold = 5  # Default value

            case.save()

            # Log the activity
            ActivityLog.objects.create(
                user=request.user,
                action=f"Created case: {case.name}",
                case=case,
            )

            messages.success(request, "Case created successfully.")
            return redirect('case_app:case_list')
        else:
            messages.error(request, "Error creating case. Please correct the form.")
    else:
        form = CaseForm()

    return render(request, 'case_app/create_case.html', {'form': form})

@login_required
def case_list(request):
    """
    Display a list of cases with search and filtering.
    """
    user = request.user
    cases = Case.objects.all() if user.is_superuser else Case.objects.filter(investigator=user)

    # Get search query and date filters safely
    search_query = request.GET.get('search', '')

    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    # ✅ Fix: Ensure `start_date` and `end_date` are valid strings before parsing
    start_date = str(start_date) if start_date else None
    end_date = str(end_date) if end_date else None

    if start_date:
        start_date = parse_date(start_date)  # Will safely parse or return None
    if end_date:
        end_date = parse_date(end_date)

    # Apply filters
    if search_query:
        cases = cases.filter(name__icontains=search_query)

    if start_date:
        cases = cases.filter(created_at__gte=start_date)

    if end_date:
        cases = cases.filter(created_at__lte=end_date)

    # Pagination
    paginator = Paginator(cases, 5)
    page_number = request.GET.get('page')
    cases_page = paginator.get_page(page_number)

    return render(request, 'case_app/case_list.html', {
        'cases': cases_page,
        'search_query': search_query,
        'start_date': request.GET.get('start_date', ''),  # Keep raw input for form
        'end_date': request.GET.get('end_date', ''),
    })

@login_required
def case_details(request, case_id):
    """
    Display details of a specific case, including its images.
    """
    case = get_object_or_404(Case, id=case_id)
    images = case.images.all()

    # Pagination
    paginator = Paginator(images, 5)  # Show 5 images per page
    page_number = request.GET.get('page')
    images_page = paginator.get_page(page_number)

    return render(request, 'case_app/case_details.html', {'case': case, 'images': images_page})


@login_required
def edit_case(request, case_id):
    """
    Edit an existing case.
    """
    case = get_object_or_404(Case, id=case_id)

    if not has_case_permission(request.user, case):
        messages.error(request, "You are not allowed to edit this case.")
        return redirect('case_app:case_details', case_id=case.id)

    if request.method == 'POST':
        form = CaseForm(request.POST, instance=case)
        if form.is_valid():
            form.save()
            messages.success(request, "Case updated successfully.")
            return redirect('case_app:case_details', case_id=case.id)
    else:
        form = CaseForm(instance=case)

    return render(request, 'case_app/edit_case.html', {'form': form, 'case': case})


@login_required
def delete_case(request, case_id):
    """
    Safely delete a case by first deleting all related logs and images, 
    with proper error handling to prevent IntegrityErrors.
    """
    case = get_object_or_404(Case, id=case_id)

    if not request.user.is_superuser:
        messages.error(request, "Only admins can delete cases.")
        return redirect('case_app:case_details', case_id=case.id)

    if request.method == 'POST':
        try:
            # Delete related logs and images before deleting the case
            ActivityLog.objects.filter(case=case).delete()
            Image.objects.filter(case=case).delete()

            # Now delete the case
            case.delete()
            messages.success(request, "Case deleted successfully.")
            return redirect('case_app:case_list')

        except IntegrityError as e:
            messages.error(request, f"Error: Unable to delete case due to database constraints. ({str(e)})")
            return redirect('case_app:case_details', case_id=case.id)

        except Exception as e:
            messages.error(request, f"Unexpected error occurred: {str(e)}")
            return redirect('case_app:case_details', case_id=case.id)

    return render(request, 'case_app/delete_case.html', {'case': case})


# Image Management Views
@login_required
def upload_image(request, case_id):
    """
    Upload images to a case.
    """
    case = get_object_or_404(Case, id=case_id)
    if request.method == 'POST':
        form = ImageUploadForm(request.POST, request.FILES)
        if form.is_valid():
            image = form.save(commit=False)
            image.case = case
            image.save()

            # Log the activity
            ActivityLog.objects.create(
                user=request.user,
                action=f"Uploaded image to case: {case.name}",
                case=case,
            )
            return redirect('case_app:case_details', case_id=case.id)
    else:
        form = ImageUploadForm()
    return render(request, 'case_app/upload_image.html', {'form': form, 'case': case})

@login_required
def delete_image(request, image_id):
    """
    Delete an image from a case.
    """
    image = get_object_or_404(Image, id=image_id)
    case_id = image.case.id  # Store case ID before deleting the image

    if not has_case_permission(request.user, image.case):
        messages.error(request, "You are not allowed to delete this image.")
        return redirect('case_app:case_details', case_id=case_id)

    if request.method == 'POST':
        try:
            #  Delete all associated activity logs safely
            ActivityLog.objects.filter(case=image.case, action__icontains="Uploaded image").delete()

            # Ensure image file exists before attempting to delete it
            if image.image and os.path.exists(image.image.path):
                os.remove(image.image.path)  # Delete image file from disk

            # Delete image record from the database
            image.delete()

            messages.success(request, "Image deleted successfully.")
        except Exception as e:
            messages.error(request, f"Error deleting image: {str(e)}")

        return redirect('case_app:case_details', case_id=case_id)

    return render(request, 'case_app/delete_image.html', {'image': image})

# Export and Tampering Detection Views
def export_case_pdf(request, case_id):
    """
    Export case details to a PDF.
    """
    case = get_object_or_404(Case, id=case_id)
    images = case.images.all()

    template = get_template('case_app/export_case_pdf.html')
    html = template.render({'case': case, 'images': images})

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="case_{case_id}.pdf"'

    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('Error generating PDF', status=500)
    return response


def export_case_csv(request, case_id):
    """
    Export case details to a CSV file.
    """
    case = get_object_or_404(Case, id=case_id)
    images = case.images.all()

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="case_{case_id}.csv"'

    writer = csv.writer(response)
    writer.writerow(['Field', 'Value'])
    writer.writerow(['Case Name', case.name])
    writer.writerow(['Description', case.description])
    writer.writerow(['Investigator', case.investigator.username])
    writer.writerow(['Created At', case.created_at])

    writer.writerow([])
    writer.writerow(['Uploaded Images'])
    writer.writerow(['Image Name', 'Image URL'])
    for image in images:
        writer.writerow([image.image.name, request.build_absolute_uri(image.image.url)])

    return response

@login_required
def detect_tampering(request, image_id):
    stored_image = get_object_or_404(Image, id=image_id)
    case = stored_image.case
    tampering_threshold = case.tampering_threshold

    if request.method == 'POST' and 'uploaded_image' in request.FILES:
        try:
            uploaded_image = request.FILES['uploaded_image']
            uploaded_pil = PILImage.open(uploaded_image)
            stored_pil = PILImage.open(stored_image.image.path)

            # Resize and convert images to the same mode
            uploaded_pil = uploaded_pil.resize(stored_pil.size).convert("RGB")
            stored_pil = stored_pil.convert("RGB")

            # Save the uploaded image temporarily
            uploaded_image_name = f"temp_{uploaded_image.name}"
            uploaded_image_path = os.path.join(settings.MEDIA_ROOT, "temp", uploaded_image_name)
            os.makedirs(os.path.dirname(uploaded_image_path), exist_ok=True)
            uploaded_pil.save(uploaded_image_path)

            # Generate difference image
            diff_image = ImageChops.difference(stored_pil, uploaded_pil)
            diff_image_path = os.path.join(settings.MEDIA_ROOT, "temp", "diff_image.png")
            diff_image.save(diff_image_path)

            # Compute perceptual hashes
            uploaded_phash = str(imagehash.phash(uploaded_pil))
            stored_phash = stored_image.perceptual_hash
            hamming_distance = imagehash.hex_to_hash(uploaded_phash) - imagehash.hex_to_hash(stored_phash)

            # Calculate similarity percentage
            similarity = max(0, 100 - (hamming_distance / tampering_threshold) * 100)

            # Determine tampering status
            diff_bbox = diff_image.getbbox()
            tampered = bool(diff_bbox)
            status = "Tampered" if tampered else "Original"

            # Log the action
            ActivityLog.objects.create(
                user=request.user,
                case=case,
                action="Tampering Detection Performed",
                details=f"""
                Uploaded Image: {uploaded_image.name}
                Stored Image ID: {stored_image.id}
                Perceptual Hashes - Stored: {stored_phash}, Uploaded: {uploaded_phash}
                Hamming Distance: {hamming_distance}
                Similarity: {similarity}%
                Threshold: {tampering_threshold}
                Status: {status}
                """
            )

            return render(request, "case_app/detect_tampering.html", {
                "stored_image": stored_image,
                "uploaded_image_url": f"/media/temp/{uploaded_image_name}",
                "diff_image_url": f"/media/temp/diff_image.png",
                "stored_phash": stored_phash,
                "uploaded_phash": uploaded_phash,
                "hamming_distance": hamming_distance,
                "similarity": round(similarity, 2),
                "tampered": tampered,
                "status": status,
                "threshold": tampering_threshold,
            })

        except Exception as e:
            return render(request, "case_app/detect_tampering.html", {
                "stored_image": stored_image,
                "error": f"Invalid image or processing error: {str(e)}"
            })

    return render(request, "case_app/detect_tampering.html", {
        "stored_image": stored_image,
        "error": "Please upload an image for testing.",
    })

@login_required
def case_logs(request, case_id):
    case = get_object_or_404(Case, id=case_id)
    logs = case.logs.all().order_by('-timestamp')
    paginator = Paginator(logs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'case_app/case_logs.html', {
        'logs': page_obj,
        'case': case
    })
