from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.http import JsonResponse
import subprocess
from .models import CodeFile
from pyflakes.api import check
from pyflakes.reporter import Reporter
from io import StringIO

@login_required
def home(request):
     # Fetch all code files for the logged-in user
    files = CodeFile.objects.filter(user=request.user).order_by('-created_at')

    if request.method == 'POST':
        # Save a new code file
        name = request.POST.get('name', 'Untitled')
        content = request.POST.get('content', '')
        CodeFile.objects.create(user=request.user, name=name, content=content)
        return redirect('home')

    return render(request, 'ide/home.html', {'files': files})

@login_required
def profile(request):
    return render(request, 'ide/profile.html', {'username': request.user.username})

def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Account created successfully! Please log in.')
            return redirect('login')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserCreationForm()
    
    return render(request, 'registration/signup.html', {'form': form})

@login_required
def delete_file(request, pk):
    if request.method == 'POST':
        print("Expected CSRF Token:", request.META.get("CSRF_COOKIE"))
        print("Received CSRF Token:", request.headers.get("X-CSRFToken"))

        code_file = get_object_or_404(CodeFile, pk=pk, user=request.user)
        code_file.delete()
    return redirect('/ide')

@login_required
def code_file_detail(request, pk):
    code_file = get_object_or_404(CodeFile, pk=pk, user=request.user)

    if request.method == 'POST':
        code = request.POST.get('content', '')
        action = request.POST.get('action')

        if action == 'auto_save':
            # Save the code file contents to the database
            code_file.content = code
            code_file.save()
            return JsonResponse({'status': 'success', 'message': 'File auto-saved successfully.'})

        elif action == 'run':
            # Handle running the code
            buffer = StringIO()
            reporter = Reporter(buffer, buffer)
            check(code, reporter)
            linting_errors = buffer.getvalue()

            if linting_errors.strip():
                return JsonResponse({'output': f"Linting Issues:\n{linting_errors}", 'status': 'error'})

            try:
                result = subprocess.run(
                    ['python3', '-c', code],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                output = result.stdout or result.stderr
            except Exception as e:
                output = f"Runtime Error: {str(e)}"
                return JsonResponse({'output': output, 'status': 'error'})

            return JsonResponse({'output': output, 'status': 'success'})

    return render(request, 'ide/code_file_detail.html', {'code_file': code_file})