from django.db import models
from bomiot.server.core.models import CoreModel
from django.conf import settings

class AuthModel(CoreModel):
    community_key = models.CharField(max_length=255, verbose_name="COMMUNITY KEY")
    sponsor_key = models.CharField(max_length=255, verbose_name="SPONSOR KEY")
    expired = models.DateTimeField(blank=True, null=True, verbose_name="Expired Time")

    class Meta:
        db_table = settings.BASE_DB_TABLE + '_authmodel'
        verbose_name = settings.BASE_DB_TABLE + ' AuthModel'
        verbose_name_plural = verbose_name
        ordering = ['-id']