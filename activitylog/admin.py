from django.contrib import admin
from .models import ActivityLog, ActivityLogEvent
from django.forms.widgets import Textarea
from django.db.models.fields import TextField


class ActivityLogEventAdminInline(admin.TabularInline):
    model = ActivityLogEvent


class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('name', 'format_str', 'format_args')
    list_editable = ('name', 'format_str', 'format_args')
    list_display_links = None
    formfield_overrides = {
        TextField: {'widget': Textarea(attrs={'rows': 1, 'cols': 100})},
    }
    inlines = (ActivityLogEventAdminInline,)


admin.site.register(ActivityLog, ActivityLogAdmin)