# probe_app/models.py

from django.db import models

class OrbitarToken(models.Model):
    access_token = models.CharField(max_length=255)
    refresh_token = models.CharField(max_length=255, blank=True, null=True)
    expires_at = models.DateTimeField()

    def __str__(self):
        return self.access_token # Добавление метода для лучшего отображения в админке.
