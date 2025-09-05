from django import forms
from .models import YoutubeVideo, Comment,CommentResponse

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



class CommentForm(forms.ModelForm):
    name = forms.CharField(max_length=100, required=False)
    is_anonymous = forms.BooleanField(required=False)
    
    class Meta:
        model = Comment
        fields = ['content', 'name', 'is_anonymous']
        widgets = {
            'content': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Share your thoughts...'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your name'})
        }

class CommentResponseForm(forms.ModelForm):
    name = forms.CharField(max_length=100, required=False)
    is_anonymous = forms.BooleanField(required=False)
    
    class Meta:
        model = CommentResponse
        fields = ['content', 'name', 'is_anonymous']
        widgets = {
            'content': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Write your response...'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your name'})
        }