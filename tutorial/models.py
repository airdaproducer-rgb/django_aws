from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.urls import reverse


class YoutubeVideo(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField()
    youtube_link = models.URLField()
    is_active = models.BooleanField(default=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    timestamp_modified = models.DateTimeField(auto_now=True)
    password = models.CharField(max_length=128, blank=True, null=True)
    admin_notes = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return self.title

class ViewerHistory(models.Model):
    PAGE_CHOICES = (
        ('list', 'List Page'),
        ('detail', 'Detail Page'),
    )
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    video = models.ForeignKey(YoutubeVideo, on_delete=models.CASCADE)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    view_date = models.DateTimeField(auto_now_add=True)
    page_type = models.CharField(max_length=10, choices=PAGE_CHOICES, default='detail')
    
    class Meta:
        ordering = ['-view_date']
        verbose_name_plural = 'Viewer Histories'
    
    def __str__(self):
        return f"{self.video.title} viewed on {self.view_date}"

class SearchHistory(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    query = models.CharField(max_length=255)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    results_count = models.PositiveIntegerField(default=0)
    search_date = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-search_date']
        verbose_name_plural = 'Search Histories'
    
    def __str__(self):
        return f"Search: {self.query} ({self.search_date})"

class SearchResult(models.Model):
    search = models.ForeignKey(SearchHistory, on_delete=models.CASCADE, related_name='results')
    video = models.ForeignKey(YoutubeVideo, on_delete=models.CASCADE)
    position = models.PositiveIntegerField()
    
    class Meta:
        ordering = ['position']
    
    def __str__(self):
        return f"Result for {self.search.query}: {self.video.title}"

class Comment(models.Model):
    video = models.ForeignKey(YoutubeVideo, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=100, blank=True, null=True)
    content = models.TextField()
    is_anonymous = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        if self.user:
            return f"Comment by {self.user.username} on {self.video.title}"
        else:
            return f"Comment by {self.name or 'Anonymous'} on {self.video.title}"




from django.db import models
import uuid
from datetime import timedelta

class Story(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    content = models.TextField()
    publish_after = models.DurationField(help_text="Time delta after which to print the story (in seconds)")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.title
    
    class Meta:
        verbose_name_plural = "Stories"


from django.db import models
import uuid

class PDFDocument(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='pdfs/')
    delay = models.DurationField(default=30, help_text="Time delay before extraction (in seconds)")
    created_at = models.DateTimeField(auto_now_add=True)
    extraction_status = models.CharField(max_length=20, default="pending")
    extracted_text = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return self.title
    
    class Meta:
        verbose_name_plural = "PDF Documents"


