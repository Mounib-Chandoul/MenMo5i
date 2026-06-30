from django.shortcuts import render

# Create your views here.
def landing_page_view(request):
    return render(request, 'core_store/landing.html')