from django.shortcuts import render

# Create your views here.


from django.shortcuts import render, redirect
from django.views.generic import ListView, CreateView
from django.urls import reverse_lazy
from django.contrib import messages

from .models import Story
from .forms import StoryForm
from .tasks import print_story_after_delay
from django.shortcuts import render, redirect
from django.views.generic import ListView, CreateView
from django.urls import reverse_lazy
from django.contrib import messages
from .models import Story
from .forms import StoryForm
from .tasks import print_story_after_delay

class StoryListView(ListView):
    model = Story
    template_name = 'tutorial/stories/story_list.html'
    context_object_name = 'stories'
    ordering = ['-created_at']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Process each story to calculate time components
        for story in context['stories']:
            total_seconds = int(story.publish_after.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            story.time_display = {
                'hours': hours,
                'minutes': minutes,
                'seconds': seconds
            }
        return context

class StoryCreateView(CreateView):
    model = Story
    form_class = StoryForm
    template_name = 'tutorial/stories/create_story.html'
    success_url = reverse_lazy('story-list')
    
    def form_valid(self, form):
        # Save the story to the database
        response = super().form_valid(form)
        story = self.object
        
        # Get the delay in seconds
        delay_seconds = story.publish_after.total_seconds()
        
        # Schedule the task
        print_story_after_delay.apply_async(
            args=[
                str(story.id),
                story.title,
                story.content,
                delay_seconds
            ],
        )
        
        messages.success(
            self.request, 
            f"Story scheduled to print after {delay_seconds} seconds!"
        )
        
        return response
    


from django.shortcuts import render, redirect
from django.views.generic import ListView, CreateView, DetailView
from django.urls import reverse_lazy
from django.contrib import messages
from .models import PDFDocument
from .forms import PDFDocumentForm
from .tasks import extract_text_from_pdf

class PDFDocumentListView(ListView):
    model = PDFDocument
    template_name = 'tutorial/stories/pdf/document_list.html'
    context_object_name = 'documents'
    ordering = ['-created_at']

class PDFDocumentCreateView(CreateView):
    model = PDFDocument
    form_class = PDFDocumentForm
    template_name = 'tutorial/stories/pdf/create_document.html'
    success_url = reverse_lazy('document-list')
    
    def form_valid(self, form):
        # Save the document to the database
        self.object = form.save()
        document = self.object
        
        # Get the delay in seconds
        delay_seconds = document.delay.total_seconds()
        
        # Schedule the extraction task with countdown instead of time.sleep
        # This allows the view to return immediately
        extract_text_from_pdf.apply_async(
            args=[
                str(document.id),
                document.file.path,
            ],
            countdown=int(delay_seconds)  # Use countdown parameter instead of sleeping in the task
        )
        
        messages.success(
            self.request, 
            f"PDF text extraction scheduled after {delay_seconds} seconds!"
        )
        
        return redirect(self.success_url)
    
class PDFDocumentDetailView(DetailView):
    model = PDFDocument
    template_name = 'tutorial/stories/pdf/document_detail.html'
    context_object_name = 'document'

from django.http import JsonResponse

def document_status(request, document_id):
    try:
        document = PDFDocument.objects.get(id=document_id)
        return JsonResponse({
            'status': document.extraction_status,
            'updated_at': document.created_at.isoformat()
        })
    except PDFDocument.DoesNotExist:
        return JsonResponse({'error': 'Document not found'}, status=404)
    