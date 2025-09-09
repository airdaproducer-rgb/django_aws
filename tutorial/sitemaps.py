from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import YoutubeVideo

class YoutubeVideoSitemap(Sitemap):
    changefreq = "weekly"   # how often the page is likely to change
    priority = 0.8          # importance (0.0 - 1.0)

    def items(self):
        # Only include active videos
        return YoutubeVideo.objects.filter(is_active=True)

    def lastmod(self, obj):
        return obj.timestamp_modified

    def location(self, obj):
        # Assuming you have a detail view with a slug or id
        return reverse("youtube:detail", args=[obj.id])
