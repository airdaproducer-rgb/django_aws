from django import forms
from .models import YoutubeVideo, Comment

class YoutubeVideoForm(forms.ModelForm):
    class Meta:
        model = YoutubeVideo
        fields = ['title', 'description', 'youtube_link', 'is_active', 'password', 'admin_notes']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'admin_notes': forms.Textarea(attrs={'rows': 3}),
            'password': forms.PasswordInput(),
        }

class CommentForm(forms.ModelForm):
    name = forms.CharField(max_length=100, required=False)
    is_anonymous = forms.BooleanField(required=False)
    
    class Meta:
        model = Comment
        fields = ['content', 'name', 'is_anonymous']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Share your thoughts about this video...'}),
            'name': forms.TextInput(attrs={'placeholder': 'Your name (optional)'}),
        }
        
class SearchForm(forms.Form):
    query = forms.CharField(max_length=255, required=False, widget=forms.TextInput(attrs={
        'placeholder': 'Search videos...',
        'class': 'search-input'
    }))
