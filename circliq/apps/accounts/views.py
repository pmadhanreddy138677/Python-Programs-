from django.conf import settings
from django.contrib import messages
import json

from django.contrib.auth import logout
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.cache import cache
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.views import View

from apps.core.ratelimit import over_limit, rate_limit
from apps.institutions.models import Institution
from .forms import EmailLoginForm, RegistrationForm, ResendVerificationForm
from .models import User
from .tokens import make_token, read_token


def send_verification_email(request, user):
    link = request.build_absolute_uri(reverse("accounts:verify_email", args=[make_token(user)]))
    body = render_to_string("accounts/verify_email.txt", {"user": user, "link": link})
    send_mail("Verify your Circliq account", body, None, [user.email])


class RegisterView(View):
    template_name = "accounts/register.html"

    def _institution(self):
        return Institution.objects.filter(is_active=True).first()

    def get(self, request):
        if request.user.is_authenticated:
            return redirect("dashboard:home")
        inst = self._institution()
        if inst is None:
            return render(request, self.template_name, {"no_institution": True})
        return render(request, self.template_name, {"form": RegistrationForm(institution=inst), "institution": inst})

    def post(self, request):
        if over_limit(request, "register", 10, 3600, per="ip"):
            return render(request, "errors/429.html", status=429)
        inst = self._institution()
        if inst is None:
            return render(request, self.template_name, {"no_institution": True}, status=503)
        form = RegistrationForm(request.POST, institution=inst)
        if form.is_valid():
            user = form.save()
            send_verification_email(request, user)
            messages.success(request, "Account created! Check your email for a verification link.")
            return redirect("accounts:login")
        return render(request, self.template_name, {"form": form, "institution": inst})


class LoginView(auth_views.LoginView):
    template_name = "accounts/login.html"
    authentication_form = EmailLoginForm
    redirect_authenticated_user = True

    def _key(self, request):
        email = (request.POST.get("username") or "").strip().lower()
        ip = request.META.get("REMOTE_ADDR", "")
        return f"login-fail:{ip}:{email}"

    def post(self, request, *args, **kwargs):
        if over_limit(request, "login", 60, 600, per="ip") or cache.get(self._key(request), 0) >= settings.LOGIN_MAX_FAILED_ATTEMPTS:
            return render(request, "errors/429.html", status=429)
        return super().post(request, *args, **kwargs)

    def form_invalid(self, form):
        key = self._key(self.request)
        cache.set(key, cache.get(key, 0) + 1, settings.LOGIN_LOCKOUT_SECONDS)
        return super().form_invalid(form)

    def form_valid(self, form):
        cache.delete(self._key(self.request))
        response = super().form_valid(form)
        if not form.cleaned_data.get("remember_me"):
            self.request.session.set_expiry(0)  # expires when the browser closes
        return response


class LogoutView(auth_views.LogoutView):
    """POST-only logout (Django 5 default)."""


def verify_email(request, token):
    payload = read_token(token)
    user = User.objects.filter(pk=payload["uid"], email=payload["email"]).first() if payload else None
    if user is None:
        messages.error(request, "That verification link is invalid or has expired. Request a new one.")
        return redirect("accounts:resend_verification")
    if not user.is_email_verified:
        user.is_email_verified = True
        user.save(update_fields=["is_email_verified"])
    messages.success(request, "Email verified! You can log in now.")
    return redirect("accounts:login")


class ResendVerificationView(View):
    def get(self, request):
        return render(request, "accounts/simple_form.html", self._ctx(ResendVerificationForm()))

    def post(self, request):
        if over_limit(request, "resend", 5, 3600, per="ip"):
            return render(request, "errors/429.html", status=429)
        form = ResendVerificationForm(request.POST)
        if form.is_valid():
            user = User.objects.filter(email__iexact=form.cleaned_data["email"], is_email_verified=False).first()
            if user:
                send_verification_email(request, user)
            # Same message either way so emails can't be enumerated.
            messages.success(request, "If that account needs verification, a new link has been sent.")
            return redirect("accounts:login")
        return render(request, "accounts/simple_form.html", self._ctx(form))

    @staticmethod
    def _ctx(form):
        return {"form": form, "title": "Resend verification email", "subtitle": "Enter your email and we'll send a new link.", "button": "Send link"}


class PasswordResetView(SuccessMessageMixin, auth_views.PasswordResetView):
    template_name = "accounts/simple_form.html"

    def post(self, request, *args, **kwargs):
        if over_limit(request, "pwreset", 5, 3600, per="ip"):
            return render(request, "errors/429.html", status=429)
        return super().post(request, *args, **kwargs)

    email_template_name = "accounts/password_reset_email.txt"
    success_url = reverse_lazy("accounts:login")
    success_message = "If that email has an account, a reset link has been sent."
    extra_context = {"title": "Reset your password", "subtitle": "We'll email you a link to choose a new one.", "button": "Send reset link"}


class PasswordResetConfirmView(SuccessMessageMixin, auth_views.PasswordResetConfirmView):
    template_name = "accounts/simple_form.html"
    success_url = reverse_lazy("accounts:login")
    success_message = "Password updated. You can log in now."
    extra_context = {"title": "Choose a new password", "subtitle": "", "button": "Save password"}


class PasswordChangeView(LoginRequiredMixin, SuccessMessageMixin, auth_views.PasswordChangeView):
    template_name = "accounts/simple_form.html"
    success_url = reverse_lazy("dashboard:home")
    success_message = "Your password was changed."
    extra_context = {"title": "Change password", "subtitle": "", "button": "Update password", "in_app": True}


def error_403(request, exception=None):
    return render(request, "errors/403.html", status=403)

def error_404(request, exception=None):
    return render(request, "errors/404.html", status=404)

def error_500(request):
    return render(request, "errors/500.html", status=500)


# ---------------- account settings, deactivation, deletion, data export ----------------
@login_required
def account_settings(request):
    return render(request, "accounts/settings.html", {"can_delete": not (request.user.is_campus_admin or request.user.is_superuser)})


@login_required
@require_POST
def deactivate_account(request):
    user = request.user
    if not user.check_password(request.POST.get("password", "")):
        messages.error(request, "That password isn't correct.")
        return redirect("accounts:settings")
    if user.is_superuser:
        messages.error(request, "Administrator accounts can't be deactivated from here.")
        return redirect("accounts:settings")
    user.is_active, user.deactivated_at = False, timezone.now()
    user.save(update_fields=["is_active", "deactivated_at"])
    logout(request)
    messages.info(request, "Your account is deactivated and hidden. You can reactivate it any time from the login page.")
    return redirect("landing")


def reactivate_account(request):
    if request.method == "POST":
        if over_limit(request, "reactivate", 10, 3600, per="ip"):
            return render(request, "errors/429.html", status=429)
        email, password = (request.POST.get("email") or "").strip().lower(), request.POST.get("password", "")
        user = User.objects.filter(email__iexact=email).first()
        if user and not user.is_active and user.deactivated_at and not user.is_restricted and user.check_password(password):
            user.is_active, user.deactivated_at = True, None
            user.save(update_fields=["is_active", "deactivated_at"])
            messages.success(request, "Welcome back! Your account is active again. Log in to continue.")
            return redirect("accounts:login")
        messages.error(request, "We couldn't reactivate that account. Check your details, or contact an administrator.")
    return render(request, "accounts/reactivate.html")


def _blocking_ownerships(user):
    """Circles / projects the user runs that other people depend on."""
    from apps.circles.models import CircleMembership
    from apps.projects.models import ProjectMembership
    names = []
    for m in CircleMembership.objects.filter(user=user, role="owner", status="active").select_related("circle"):
        if CircleMembership.objects.filter(circle=m.circle, status="active").exclude(user=user).exists():
            names.append(f"circle “{m.circle.name}”")
    for m in ProjectMembership.objects.filter(user=user, role="lead").select_related("project"):
        if ProjectMembership.objects.filter(project=m.project).exclude(user=user).exists():
            names.append(f"project “{m.project.title}”")
    return names


@login_required
@require_POST
def delete_account(request):
    user = request.user
    if user.is_campus_admin or user.is_superuser:
        messages.error(request, "Administrator accounts must be removed by another administrator.")
        return redirect("accounts:settings")
    if not user.check_password(request.POST.get("password", "")) or request.POST.get("confirm", "").strip() != "DELETE":
        messages.error(request, "Enter your password and type DELETE to confirm.")
        return redirect("accounts:settings")
    blocking = _blocking_ownerships(user)
    if blocking:
        messages.error(request, "Before deleting your account, hand over or close: " + ", ".join(blocking) + ".")
        return redirect("accounts:settings")
    with transaction.atomic():
        user_pk = user.pk
        logout(request)
        User.objects.filter(pk=user_pk).delete()
    messages.info(request, "Your account and its content have been permanently deleted.")
    return redirect("landing")


@login_required
@rate_limit("export", 5, 3600, methods=("GET",))
def export_my_data(request):
    from .exporter import export_user_data
    resp = HttpResponse(json.dumps(export_user_data(request.user), indent=2, ensure_ascii=False), content_type="application/json")
    resp["Content-Disposition"] = 'attachment; filename="circliq-my-data.json"'
    return resp
