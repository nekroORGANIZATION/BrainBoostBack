from django.db import models


class Story(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField(blank=True, null=True)   # на майбутнє
    cover = models.ImageField(upload_to="stories/covers/", blank=True, null=True)
    published_at = models.DateTimeField()
    author_name = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        ordering = ["-published_at"]

    def __str__(self):
        return self.title
