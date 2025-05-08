from django.shortcuts import render

def about_view(request):
    """View function for the About page"""
    return render(request, 'about.html')
