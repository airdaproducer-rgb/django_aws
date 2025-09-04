from celery import shared_task
import time
from datetime import datetime

@shared_task
def print_story_after_delay(story_id, story_title, story_content, delay_seconds):
    """
    Wait for the specified delay and then print the story to the terminal
    """
    time.sleep(delay_seconds)
    
    # Print to terminal
    print("\n" + "="*50)
    print(f"SCHEDULED STORY PRINT - {datetime.now()}")
    print(f"Story ID: {story_id}")
    print(f"Title: {story_title}")
    print("Content:")
    print("-"*50)
    print(story_content)
    print("="*50 + "\n")
    
    return f"Story '{story_title}' printed at {datetime.now()}"


from celery import shared_task
import time
from datetime import datetime
import httpx
import PyPDF2
import os

@shared_task
def extract_text_from_pdf(document_id, file_path):
    """
    Extract text from the PDF after the countdown expires
    """
    from .models import PDFDocument  # Import here to avoid circular import
    
    # Get the document
    try:
        document = PDFDocument.objects.get(id=document_id)
        document.extraction_status = "processing"
        document.save()
        
        # Extract text from PDF
        text = ""
        try:
            if os.path.exists(file_path):
                with open(file_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    for page_num in range(len(pdf_reader.pages)):
                        page = pdf_reader.pages[page_num]
                        text += page.extract_text() + "\n\n--- Page Break ---\n\n"
            
            # Save the extracted text
            document.extracted_text = text
            document.extraction_status = "completed"
            document.save()
            
            # Print to terminal
            print("\n" + "="*50)
            print(f"PDF TEXT EXTRACTION - {datetime.now()}")
            print(f"Document ID: {document_id}")
            print(f"File: {file_path}")
            print(f"Text Length: {len(text)} characters")
            print("="*50 + "\n")
            
            # Optional: Send data to external API using httpx
            try:
                response = httpx.post(
                    'https://api.example.com/process-text',
                    json={
                        'document_id': document_id,
                        'text': text[:1000],  # Send first 1000 chars as preview
                        'characters': len(text),
                        'processed_at': datetime.now().isoformat()
                    },
                    timeout=30.0
                )
                print(f"API Response: {response.status_code}")
            except Exception as e:
                print(f"API request failed: {str(e)}")
            
            return f"PDF text extracted at {datetime.now()}"
            
        except Exception as e:
            document.extraction_status = "failed"
            document.extracted_text = f"Error extracting text: {str(e)}"
            document.save()
            return f"Failed to extract text: {str(e)}"
            
    except PDFDocument.DoesNotExist:
        print(f"Document with ID {document_id} does not exist")
        return f"Document with ID {document_id} not found"