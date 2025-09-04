# forms.py
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

from django import forms
from .models import Comment

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

from django import forms
from .models import Story
from datetime import timedelta

class StoryForm(forms.ModelForm):
    publish_after = forms.IntegerField(
        min_value=0,
        required=True,
        help_text="Time delay in seconds after which to print the story",
        label="Schedule to print after (seconds)"
    )
    
    class Meta:
        model = Story
        fields = ['title', 'content', 'publish_after']
    
    def clean_publish_after(self):
        seconds = self.cleaned_data['publish_after']
        if seconds <= 0:
            raise forms.ValidationError("Please specify a positive time delay in seconds")
        return timedelta(seconds=seconds)

from django import forms
from .models import PDFDocument
from datetime import timedelta

class PDFDocumentForm(forms.ModelForm):
    class Meta:
        model = PDFDocument
        fields = ['title', 'file', 'delay']
        widgets = {
            'delay': forms.NumberInput(attrs={'min': 5, 'max': 3600})
        }
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            if not file.name.endswith('.pdf'):
                raise forms.ValidationError("Only PDF files are allowed.")
            if file.size > 10 * 1024 * 1024:  # 10MB limit
                raise forms.ValidationError("File size must be under 10MB.")
        return file
    
    def clean_delay(self):
        delay = self.cleaned_data.get('delay')
        if not isinstance(delay, timedelta):
            delay = timedelta(seconds=int(delay))
        return delay