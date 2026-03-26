
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django_otp import devices_for_user
from django_otp.plugins.otp_totp.models import TOTPDevice
from .forms import UserRegistrationForm, UserLoginForm, OTPLoginForm, SystemRegistrationForm
from .models import User
import base64
import io
import qrcode

def register_view(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registration successful!')
            return redirect('dashboard')
    else:
        form = UserRegistrationForm()
    return render(request, 'accounts/register.html', {'form': form})

def system_register_view(request):
    """Registration for Admin and Law Enforcement"""
    if request.method == 'POST':
        form = SystemRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'System registration successful!')
            if user.role == 'admin':
                return redirect('admin_dashboard')
            elif user.role == 'law_enforcement':
                return redirect('law_enforcement_dashboard')
            return redirect('dashboard')
    else:
        form = SystemRegistrationForm()
    return render(request, 'accounts/system_register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')

            # Try to authenticate with username first, then email
            user = authenticate(request, username=username, password=password)
            if not user:
                try:
                    user_obj = User.objects.get(email=username)
                    user = authenticate(request, username=user_obj.username, password=password)
                except User.DoesNotExist:
                    user = None

            if user is not None:
                # Login directly
                login(request, user)
                # Role-based redirect
                if user.role == 'admin':
                    return redirect('admin_dashboard')
                elif user.role == 'law_enforcement':
                    return redirect('law_enforcement_dashboard')
                else:
                    return redirect('dashboard')
            else:
                messages.error(request, 'Invalid username/email or password.')
        else:
            messages.error(request, 'Invalid form data.')
    else:
        form = UserLoginForm()
    return render(request, 'accounts/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('accounts:login')

@login_required
def profile_view(request):
    otp_devices = list(devices_for_user(request.user))
    otp_enabled = len(otp_devices) > 0

    context = {
        'user': request.user,
        'otp_enabled': otp_enabled,
        'otp_device_count': len(otp_devices),
    }
    return render(request, 'accounts/profile.html', context)

@login_required
def manage_2fa_view(request):
    """Manage 2FA devices"""
    otp_devices = list(devices_for_user(request.user))
    
    context = {
        'user': request.user,
        'otp_devices': otp_devices,
        'add_device_form': None,
    }
    return render(request, 'accounts/manage_2fa.html', context)

@login_required
def remove_2fa_device_view(request, device_id):
    """Remove a specific 2FA device"""
    if request.method == 'POST':
        try:
            device = TOTPDevice.objects.get(id=device_id, user=request.user)
            device.delete()
            messages.success(request, f'Device "{device.name}" has been removed successfully.')
        except TOTPDevice.DoesNotExist:
            messages.error(request, 'Device not found.')
    
    return redirect('accounts:manage_2fa')

@login_required
def disable_2fa_view(request):
    """Disable all 2FA devices"""
    if request.method == 'POST':
        devices = TOTPDevice.objects.filter(user=request.user)
        device_count = devices.count()
        devices.delete()
        messages.success(request, f'Two-factor authentication has been disabled. {device_count} device(s) removed.')
        return redirect('accounts:manage_2fa')
    
    return redirect('accounts:manage_2fa')

def otp_login_view(request):
    user_id = request.session.get('otp_user_id')
    if not user_id:
        messages.error(request, 'Session expired. Please login again.')
        return redirect('login')

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        messages.error(request, 'User not found.')
        return redirect('login')

    if request.method == 'POST':
        form = OTPLoginForm(request.POST)
        if form.is_valid():
            otp_token = form.cleaned_data['otp_token']
            devices = devices_for_user(user)
            for device in devices:
                if device.verify_token(otp_token):
                    # OTP verified, complete login
                    login(request, user)
                    del request.session['otp_user_id']  # Clear session
                    # Role-based redirect
                    if user.role == 'admin':
                        return redirect('admin_dashboard')
                    elif user.role == 'law_enforcement':
                        return redirect('law_enforcement_dashboard')
                    else:
                        return redirect('dashboard')
            messages.error(request, 'Invalid OTP token.')
        else:
            messages.error(request, 'Invalid form data.')
    else:
        form = OTPLoginForm()
    return render(request, 'accounts/otp_login.html', {'form': form})

@login_required
def setup_otp_view(request):
    device = TOTPDevice.objects.filter(user=request.user, name='default').first()

    if request.method == 'POST':
        if device is None:
            # Create new device if it doesn't exist
            device = TOTPDevice.objects.create(user=request.user, name='default')
        
        # Verify the token
        token = request.POST.get('token', '').strip()
        if token:
            if device.verify_token(token):
                # Token is valid, confirm the device
                device.confirmed = True
                device.save()
                messages.success(request, 'Two-Factor Authentication enabled successfully!')
                return redirect('accounts:manage_2fa')
            else:
                messages.error(request, 'Invalid code. Please try again.')
                # Don't delete device, let user retry
        else:
            if device is None:
                # First POST request - just create device
                device = TOTPDevice.objects.create(user=request.user, name='default')
            # Return same page with device to enter code

    qr_code_base64 = None
    if device is not None:
        qr = qrcode.QRCode(version=1, box_size=6, border=2)
        qr.add_data(device.config_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        qr_code_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    context = {
        'device': device,
        'qr_code_base64': qr_code_base64,
    }
    return render(request, 'accounts/setup_otp.html', context)
