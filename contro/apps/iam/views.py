from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from contro.apps.iam.forms import LoginForm


@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect("iam:dashboard")

    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"]
        password = form.cleaned_data["password"]
        user = authenticate(request, username=email, password=password)
        if user:
            login(request, user)
            return redirect("iam:dashboard")
        messages.error(request, "Invalid email or password.")

    return render(request, "iam/login.html", {"form": form})


@login_required
@require_http_methods(["POST"])
def logout_view(request):
    logout(request)
    return redirect("iam:login")


@login_required
@require_http_methods(["GET"])
def dashboard_view(request):
    return render(request, "iam/dashboard.html")
