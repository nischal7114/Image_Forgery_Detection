from django import forms
from .models import Case, Image

class CaseForm(forms.ModelForm):
    """
    Form for creating and editing cases.
    """
    class Meta:
        model = Case
        fields = ['name', 'description', 'tampering_threshold']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter case name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Enter case description'}),
            'tampering_threshold': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter tampering threshold'}),
        }
        
class ImageUploadForm(forms.ModelForm):
    """
    Form for uploading images to a case.
    """
    class Meta:
        model = Image
        fields = ['image']
        widgets = {
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

class ImageVerificationForm(forms.Form):
    """
    Form for uploading an image to verify tampering.
    """
    uploaded_image = forms.ImageField(
        required=True,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )