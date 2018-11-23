from django.contrib import admin

from errorlog.models import ErrorLog


class ErrorLogAdmin(admin.ModelAdmin):
    pass


admin.site.register(ErrorLog, ErrorLogAdmin)
