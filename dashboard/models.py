from django.db import models

class PlatformMetrics(models.Model):
    """
    This is a dummy model that exists solely to enable
    custom admin dashboard views. No database table will be created.
    """
    class Meta:
        managed = False  # No database table creation
        verbose_name_plural = "Platform Metrics"
        app_label = 'dashboard'
