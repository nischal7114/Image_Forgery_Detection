from django.contrib import admin
from .models import Case, Image, ActivityLog

class ImageInline(admin.TabularInline):
    model = Image
    fields = ('thumbnail', 'uploaded_at')  # Show thumbnail
    readonly_fields = ('thumbnail', 'uploaded_at')
    extra = 1
    max_num = 5  # Limit to 5 images at a time

class ActivityLogInline(admin.TabularInline):
    model = ActivityLog
    fields = ('user', 'action', 'timestamp')
    readonly_fields = ('user', 'action', 'timestamp')
    extra = 0
    can_delete = False  # Prevent log deletion

@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'investigator', 'created_at', 'updated_at', 'tampering_threshold')
    search_fields = ('name', 'investigator__username')
    list_filter = ('created_at', 'updated_at')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')
    inlines = [ImageInline, ActivityLogInline]

@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    """
    Admin interface for managing uploaded images.
    """
    list_display = ('id', 'case', 'thumbnail', 'uploaded_at')  # Include thumbnail
    search_fields = ('case__name',)
    list_filter = ('uploaded_at',)
    ordering = ('-uploaded_at',)  # Order by newest uploads
    readonly_fields = ('uploaded_at', 'thumbnail')

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    """
    Admin interface for viewing activity logs.
    """
    list_display = ('id', 'user', 'case', 'action', 'timestamp')  # Include case in logs
    search_fields = ('user__username', 'action', 'case__name')
    list_filter = ('timestamp',)
    ordering = ('-timestamp',)
    readonly_fields = ('user', 'action', 'timestamp')
