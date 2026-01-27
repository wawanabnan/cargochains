from django.shortcuts import render

def error_403(request, exception=None):
    return render(request, "errors/403.html", status=403)

def error_404(request, exception):
    return render(request, "erros/404.html", status=404)
