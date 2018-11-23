from __future__ import unicode_literals

from django.contrib import admin

from .models import Schedule


class ScheduleAdmin(admin.ModelAdmin):
    model = Schedule


admin.site.register(Schedule, ScheduleAdmin)
