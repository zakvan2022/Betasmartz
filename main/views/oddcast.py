from django.shortcuts import render
from django.views.decorators.clickjacking import xframe_options_sameorigin

@xframe_options_sameorigin
def index(request):
    return render(request, 'client_app/oddcast.html')
