from django import forms
from .models import YoutubeVideo

class YoutubeVideoForm(forms.ModelForm):
    class Meta:
        model = YoutubeVideo
        fields = ['title', 'description', 'youtube_link', 'is_active', 'password', 'admin_notes']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'admin_notes': forms.Textarea(attrs={'rows': 3}),
            'password': forms.PasswordInput(),
        }

class SearchForm(forms.Form):
    query = forms.CharField(max_length=255, required=False, widget=forms.TextInput(attrs={
        'placeholder': 'Search videos...',
        'class': 'search-input'
    }))