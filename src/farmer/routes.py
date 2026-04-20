"""Farmer portal routes for custom dashboards and OTP authentication."""

import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from src.config import settings
from src.farmer.auth import (
    request_login_otp,
    verify_login_otp,
    validate_farmer_session,
)
from src.farmer.models import (
    LoginRequestPayload,
    LoginVerifyPayload,
    LoginResponse,
)
from src.farmer.repository import FarmerRepository


router = APIRouter(prefix="/farmer", tags=["farmer"])

# Database session factory
_engine = None
_async_session_factory = None


async def get_db() -> AsyncSession:
    """Dependency: provide AsyncSession for routes."""
    global _engine, _async_session_factory

    if _engine is None:
        _engine = create_async_engine(settings.database_url, echo=False)
        _async_session_factory = sessionmaker(
            _engine, class_=AsyncSession, expire_on_commit=False
        )

    async with _async_session_factory() as session:
        yield session


# ============================================================================
# AUTHENTICATION DEPENDENCIES
# ============================================================================


async def get_farmer_id_from_token(request: Request, db: AsyncSession = Depends(get_db)) -> int:
    """Extract farmer_id from JWT token in Authorization header."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

    token = auth_header[7:]  # Remove "Bearer " prefix

    is_valid, farmer_id, message = await validate_farmer_session(db, token)
    if not is_valid:
        raise HTTPException(status_code=401, detail=message)

    return farmer_id


# ============================================================================
# LOGIN ENDPOINTS
# ============================================================================


@router.get("/login", response_class=HTMLResponse)
async def login_page():
    """Render farmer login page."""
    return LOGIN_HTML


@router.post("/api/login/request-otp", response_model=LoginResponse)
async def request_otp(
    payload: LoginRequestPayload,
    db: AsyncSession = Depends(get_db),
):
    """Request OTP for farmer login."""
    phone = payload.phone.strip()

    # Validate phone format (basic validation)
    if not phone.startswith("+91") or len(phone) != 13:
        raise HTTPException(status_code=400, detail="Invalid phone number format. Use +91XXXXXXXXXX")

    success, result = await request_login_otp(db, phone)

    if not success:
        raise HTTPException(status_code=400, detail=result)

    # In development, return OTP for testing
    # In production, don't expose the OTP
    return LoginResponse(
        success=True,
        message=f"OTP sent to {phone}",
        token=result,  # Development: return OTP; remove in production
    )


@router.post("/api/login/verify-otp", response_model=LoginResponse)
async def verify_otp(
    payload: LoginVerifyPayload,
    db: AsyncSession = Depends(get_db),
):
    """Verify OTP and return session token."""
    phone = payload.phone.strip()
    otp = payload.otp.strip()

    if len(otp) != 6 or not otp.isdigit():
        raise HTTPException(status_code=400, detail="OTP must be 6 digits")

    success, token, message = await verify_login_otp(db, phone, otp)

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return LoginResponse(
        success=True,
        message="Login successful",
        token=token,
    )


# ============================================================================
# DASHBOARD ENDPOINTS
# ============================================================================


@router.get("/dashboard", response_class=HTMLResponse)
async def farmer_dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Render farmer dashboard."""
    # Check if farmer is authenticated
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        # Redirect to login
        return HTMLResponse(
            content="<script>window.location.href='/farmer/login';</script>",
            status_code=401,
        )

    return DASHBOARD_HTML


@router.get("/api/dashboard", response_model=dict)
async def get_dashboard_data(
    farmer_id: int = Depends(get_farmer_id_from_token),
    db: AsyncSession = Depends(get_db),
):
    """Get farmer dashboard data."""
    try:
        repo = FarmerRepository(db)
        dashboard_data = await repo.get_farmer_dashboard_data(farmer_id)

        # Convert to JSON-serializable dict
        return {
            "farmer": dashboard_data.farmer.model_dump(),
            "crops": dashboard_data.crops,
            "prices": [p.model_dump() for p in dashboard_data.prices],
            "weather": dashboard_data.weather.model_dump(),
            "schemes": [s.model_dump() for s in dashboard_data.schemes],
            "advisories": [
                {**a.model_dump(), "advisory_date": a.advisory_date.isoformat(), "valid_until": a.valid_until.isoformat()}
                for a in dashboard_data.advisories
            ],
            "stats": dashboard_data.stats.model_dump(),
            "generated_at": dashboard_data.generated_at.isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading dashboard: {str(e)}")


@router.post("/api/advisories/{advisory_id}/dismiss")
async def dismiss_advisory(
    advisory_id: int,
    farmer_id: int = Depends(get_farmer_id_from_token),
    db: AsyncSession = Depends(get_db),
):
    """Dismiss an advisory card from the farmer dashboard."""
    from src.advisory.repository import AdvisoryRepository

    repo = AdvisoryRepository(db)
    ok = await repo.dismiss(advisory_id, farmer_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Advisory not found")
    return {"success": True}


# ============================================================================
# HTML TEMPLATES
# ============================================================================


LOGIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Kisan AI - Farmer Login</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
        }
        .login-card {
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
            max-width: 400px;
            width: 100%;
            padding: 40px;
        }
        .login-header {
            text-align: center;
            margin-bottom: 30px;
        }
        .login-header h1 {
            font-size: 32px;
            font-weight: 700;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }
        .login-header p {
            color: #666;
            font-size: 14px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        .form-label {
            font-weight: 500;
            color: #333;
            margin-bottom: 8px;
        }
        .form-control {
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 12px 16px;
            font-size: 16px;
        }
        .form-control:focus {
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        .btn-login {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
            color: white;
            font-weight: 600;
            padding: 12px 16px;
            border-radius: 8px;
            width: 100%;
            margin-top: 10px;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .btn-login:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
            color: white;
        }
        .btn-verify {
            background: #28a745;
            border: none;
            color: white;
            font-weight: 600;
            padding: 12px 16px;
            border-radius: 8px;
            width: 100%;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
            margin-top: 10px;
        }
        .btn-verify:hover {
            background: #218838;
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(40, 167, 69, 0.4);
            color: white;
        }
        .alert {
            border-radius: 8px;
            margin-bottom: 20px;
            font-size: 14px;
        }
        .step-indicator {
            display: flex;
            gap: 10px;
            margin-bottom: 30px;
            text-align: center;
        }
        .step {
            flex: 1;
            padding: 10px;
            border-radius: 8px;
            background: #f0f0f0;
            font-size: 12px;
            font-weight: 600;
            color: #666;
        }
        .step.active {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        #otp-input {
            letter-spacing: 8px;
            font-size: 20px;
            text-align: center;
            font-weight: 600;
        }
        .info-box {
            background: #f8f9fa;
            border-left: 4px solid #667eea;
            padding: 12px 16px;
            border-radius: 4px;
            margin-bottom: 20px;
            font-size: 14px;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="login-card">
        <div class="login-header">
            <h1>🌾 Kisan AI</h1>
            <p>Farmer Dashboard</p>
        </div>

        <div id="alert-container"></div>

        <div id="step1">
            <div class="step-indicator">
                <div class="step active">1. Phone</div>
                <div class="step">2. OTP</div>
            </div>

            <div class="info-box">
                📱 Enter your WhatsApp phone number to get started
            </div>

            <div class="form-group">
                <label class="form-label">Phone Number</label>
                <input
                    type="tel"
                    id="phone-input"
                    class="form-control"
                    placeholder="+91XXXXXXXXXX"
                    value="+91"
                >
            </div>

            <button class="btn-login" onclick="requestOTP()">
                Get OTP
            </button>
        </div>

        <div id="step2" style="display: none;">
            <div class="step-indicator">
                <div class="step">1. Phone</div>
                <div class="step active">2. OTP</div>
            </div>

            <div class="info-box">
                ✅ Check your WhatsApp for the 6-digit verification code
            </div>

            <div class="form-group">
                <label class="form-label">Verification Code</label>
                <input
                    type="text"
                    id="otp-input"
                    class="form-control"
                    placeholder="000000"
                    maxlength="6"
                    inputmode="numeric"
                >
            </div>

            <button class="btn-verify" onclick="verifyOTP()">
                Verify & Login
            </button>

            <button class="btn-login" onclick="goBackToPhone()" style="background: #6c757d; margin-top: 10px;">
                Back
            </button>
        </div>
    </div>

    <script>
        let phoneNumber = '';

        function showAlert(message, type = 'danger') {
            const alertContainer = document.getElementById('alert-container');
            const alertHTML = `
                <div class="alert alert-${type}" role="alert">
                    ${message}
                </div>
            `;
            alertContainer.innerHTML = alertHTML;
        }

        async function requestOTP() {
            phoneNumber = document.getElementById('phone-input').value.trim();

            if (!phoneNumber.startsWith('+91') || phoneNumber.length !== 13) {
                showAlert('Invalid phone number. Use format: +91XXXXXXXXXX');
                return;
            }

            try {
                const response = await fetch('/farmer/api/login/request-otp', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ phone: phoneNumber })
                });

                const data = await response.json();

                if (!response.ok) {
                    showAlert(data.detail || 'Error requesting OTP');
                    return;
                }

                // Development: Show OTP for testing
                if (data.token) {
                    showAlert(`Test OTP: ${data.token}`, 'info');
                }

                // Switch to OTP step
                document.getElementById('step1').style.display = 'none';
                document.getElementById('step2').style.display = 'block';
                document.getElementById('alert-container').innerHTML = '';
                document.getElementById('otp-input').focus();

            } catch (error) {
                showAlert('Network error: ' + error.message);
            }
        }

        async function verifyOTP() {
            const otp = document.getElementById('otp-input').value.trim();

            if (otp.length !== 6 || !/^\\d{6}$/.test(otp)) {
                showAlert('OTP must be 6 digits');
                return;
            }

            try {
                const response = await fetch('/farmer/api/login/verify-otp', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ phone: phoneNumber, otp: otp })
                });

                const data = await response.json();

                if (!response.ok) {
                    showAlert(data.detail || 'Invalid OTP');
                    return;
                }

                // Save token and redirect
                localStorage.setItem('farmerToken', data.token);
                window.location.href = '/farmer/dashboard';

            } catch (error) {
                showAlert('Network error: ' + error.message);
            }
        }

        function goBackToPhone() {
            document.getElementById('step2').style.display = 'none';
            document.getElementById('step1').style.display = 'block';
            document.getElementById('alert-container').innerHTML = '';
            document.getElementById('otp-input').value = '';
        }

        // Allow Enter key to submit
        document.addEventListener('keypress', function(event) {
            if (event.key === 'Enter') {
                const step2 = document.getElementById('step2');
                if (step2.style.display === 'none') {
                    requestOTP();
                } else {
                    verifyOTP();
                }
            }
        });

        // Auto-submit OTP when 6 digits entered
        document.getElementById('otp-input').addEventListener('input', function() {
            if (this.value.length === 6) {
                setTimeout(verifyOTP, 300);
            }
        });
    </script>
</body>
</html>
"""

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Kisan AI - Farmer Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {
            background: #f8f9fa;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
        }
        .navbar {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }
        .navbar-brand {
            font-size: 24px;
            font-weight: 700;
            color: white !important;
        }
        .navbar-text {
            color: rgba(255, 255, 255, 0.8);
        }
        .container-main {
            max-width: 1200px;
            padding: 30px 20px;
        }
        .welcome-header {
            color: #333;
            margin-bottom: 30px;
            padding: 20px;
            background: white;
            border-radius: 12px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
        }
        .welcome-header h1 {
            font-size: 28px;
            font-weight: 700;
            margin-bottom: 5px;
        }
        .welcome-header p {
            color: #666;
            margin: 0;
            font-size: 14px;
        }
        .card {
            border: none;
            border-radius: 12px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
            margin-bottom: 20px;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .card:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(0, 0, 0, 0.1);
        }
        .card-title {
            font-size: 18px;
            font-weight: 600;
            color: #333;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #f0f0f0;
        }
        .price-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 15px;
            text-align: center;
        }
        .price-crop {
            font-size: 14px;
            opacity: 0.9;
            margin-bottom: 5px;
        }
        .price-value {
            font-size: 28px;
            font-weight: 700;
            margin: 5px 0;
        }
        .price-msp {
            font-size: 12px;
            opacity: 0.8;
        }
        .price-trend {
            font-size: 14px;
            margin-top: 8px;
            padding-top: 8px;
            border-top: 1px solid rgba(255, 255, 255, 0.2);
        }
        .trend-up {
            color: #ffeb3b;
        }
        .trend-down {
            color: #ff9800;
        }
        .trend-stable {
            color: #4caf50;
        }
        .weather-day {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
            margin-right: 10px;
            flex: 0 0 auto;
        }
        .weather-day-name {
            font-size: 12px;
            color: #999;
            font-weight: 600;
        }
        .weather-icon {
            font-size: 28px;
            margin: 8px 0;
        }
        .weather-temp {
            font-size: 14px;
            font-weight: 600;
            color: #333;
        }
        .weather-precip {
            font-size: 11px;
            color: #666;
            margin-top: 5px;
        }
        .scheme-item {
            border-left: 4px solid #667eea;
            padding: 15px;
            margin-bottom: 12px;
            background: #f8f9fa;
            border-radius: 4px;
        }
        .scheme-name {
            font-weight: 600;
            color: #333;
            margin-bottom: 5px;
        }
        .scheme-desc {
            font-size: 13px;
            color: #666;
            margin-bottom: 5px;
        }
        .scheme-badge {
            display: inline-block;
            font-size: 11px;
            font-weight: 600;
            padding: 4px 10px;
            border-radius: 12px;
            background: #e8f5e9;
            color: #2e7d32;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
        }
        .stat-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }
        .stat-value {
            font-size: 24px;
            font-weight: 700;
            margin-bottom: 5px;
        }
        .stat-label {
            font-size: 13px;
            opacity: 0.9;
        }
        .loading {
            text-align: center;
            padding: 40px;
            color: #666;
        }
        .alert {
            border-radius: 8px;
            margin-bottom: 20px;
            font-size: 14px;
        }
        .btn-logout {
            background: #ff6b6b;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 6px;
            font-size: 14px;
            cursor: pointer;
            transition: background 0.2s;
        }
        .btn-logout:hover {
            background: #e63946;
        }
        @media (max-width: 768px) {
            .welcome-header h1 {
                font-size: 20px;
            }
            .stats-grid {
                grid-template-columns: 1fr;
            }
            .price-card {
                padding: 15px;
            }
            .weather-day {
                flex: 0 0 calc(50% - 5px);
            }
        }
    </style>
</head>
<body>
    <!-- Navbar -->
    <nav class="navbar">
        <div class="container-fluid">
            <a class="navbar-brand" href="/farmer/dashboard">🌾 Kisan AI</a>
            <button class="btn-logout" onclick="logout()">Logout</button>
        </div>
    </nav>

    <!-- Main Content -->
    <div class="container-main">
        <div id="alert-container"></div>
        <div id="dashboard-content" class="loading">
            Loading dashboard...
        </div>
    </div>

    <script>
        const token = localStorage.getItem('farmerToken');

        if (!token) {
            window.location.href = '/farmer/login';
        }

        function showAlert(message, type = 'danger') {
            const alertContainer = document.getElementById('alert-container');
            const alertHTML = `
                <div class="alert alert-${type}" role="alert">
                    ${message}
                </div>
            `;
            alertContainer.innerHTML = alertHTML;
        }

        async function loadDashboard() {
            try {
                const response = await fetch('/farmer/api/dashboard', {
                    headers: { 'Authorization': `Bearer ${token}` }
                });

                if (response.status === 401) {
                    localStorage.removeItem('farmerToken');
                    window.location.href = '/farmer/login';
                    return;
                }

                if (!response.ok) {
                    const error = await response.json();
                    showAlert(error.detail || 'Error loading dashboard');
                    return;
                }

                const data = await response.json();
                renderDashboard(data);

            } catch (error) {
                showAlert('Network error: ' + error.message);
            }
        }

        function renderDashboard(data) {
            const farmer = data.farmer;
            const crops = data.crops;
            const prices = data.prices;
            const weather = data.weather;
            const schemes = data.schemes;
            const stats = data.stats;

            let html = `
                <div class="welcome-header">
                    <h1>Welcome, ${farmer.name || 'Farmer'}! 🌾</h1>
                    <p>
                        ${farmer.district || 'Your District'} •
                        ${farmer.land_hectares || '–'} hectares •
                        ${farmer.plan_tier === 'free' ? '📱 Free Plan' : '⭐ Premium'}
                    </p>
                </div>

                <!-- Prices Section -->
                <div class="card">
                    <div class="card-title" style="padding: 20px 20px 10px;">
                        📊 Prices (Your Crops)
                    </div>
                    <div style="padding: 0 20px 20px;">
            `;

            if (prices.length === 0) {
                html += `<p style="color: #999; text-align: center;">No price data available</p>`;
            } else {
                html += `<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">`;
                for (const price of prices) {
                    const trendIcon = price.price_trend === 'up' ? '📈' : price.price_trend === 'down' ? '📉' : '→';
                    const trendClass = 'trend-' + price.price_trend;
                    const alertHTML = price.alert ? `<p style="margin-top: 10px; padding-top: 10px; border-top: 1px solid rgba(255,255,255,0.2); font-size: 12px; color: #ffeb3b;">⚠️ ${price.alert.message}</p>` : '';

                    html += `
                        <div class="price-card">
                            <div class="price-crop">${price.crop.toUpperCase()}</div>
                            <div class="price-value">₹${price.latest_price?.toFixed(0) || '–'}</div>
                            <div class="price-msp">MSP: ₹${price.msp?.toFixed(0) || '–'}</div>
                            <div class="price-trend ${trendClass}">
                                ${trendIcon} ${price.pct_change_7d > 0 ? '+' : ''}${price.pct_change_7d.toFixed(1)}% (7d)
                            </div>
                            ${alertHTML}
                        </div>
                    `;
                }
                html += `</div>`;
            }

            html += `</div></div>`;

            // Weather Section
            html += `
                <div class="card">
                    <div class="card-title" style="padding: 20px 20px 10px;">
                        ⛅ Weather (Next 5 Days)
                    </div>
                    <div style="padding: 0 20px 20px; overflow-x: auto;">
                        <div style="display: flex; gap: 10px; min-width: min-content;">
            `;

            for (const day of weather.forecast_5d) {
                const weatherEmoji = day.condition === 'Rainy' ? '🌧️' : day.condition === 'Cloudy' ? '⛅' : '☀️';
                html += `
                    <div class="weather-day">
                        <div class="weather-day-name">${day.day}</div>
                        <div class="weather-icon">${weatherEmoji}</div>
                        <div class="weather-temp">${day.high}°/${day.low}°</div>
                        <div class="weather-precip">${day.precipitation_mm}mm</div>
                    </div>
                `;
            }

            html += `</div></div></div>`;

            // Advisories Section (Phase 4 Step 3)
            const advisories = data.advisories || [];
            if (advisories.length > 0) {
                html += `
                    <div class="card">
                        <div class="card-title" style="padding: 20px 20px 10px;">
                            🌾 Your Farm Advisories
                        </div>
                        <div style="padding: 0 20px 20px;">
                `;
                const riskColors = { high: '#dc3545', medium: '#fd7e14', low: '#28a745' };
                const typeEmoji = { disease: '🦠', irrigation: '💧', weather: '⛈️', pest: '🐛' };
                for (const adv of advisories) {
                    const color = riskColors[adv.risk_level] || '#6c757d';
                    const emoji = typeEmoji[adv.advisory_type] || '📢';
                    const src = adv.source_citation ? `<div style="font-size:0.75rem;color:#999;margin-top:6px;">Source: ${adv.source_citation}</div>` : '';
                    const crop = adv.crop ? `<span style="background:#f0f0f0;padding:2px 8px;border-radius:10px;font-size:0.75rem;margin-left:8px;">${adv.crop}</span>` : '';
                    html += `
                        <div style="border-left:4px solid ${color};padding:12px 16px;margin-bottom:12px;background:#fafafa;border-radius:4px;position:relative;" data-advisory-id="${adv.id}">
                            <button onclick="dismissAdvisory(${adv.id}, this)" style="position:absolute;top:8px;right:8px;background:none;border:none;color:#999;cursor:pointer;font-size:18px;" title="Dismiss">×</button>
                            <div style="font-weight:600;color:${color};margin-bottom:4px;">
                                ${emoji} ${adv.title} ${crop}
                                <span style="font-size:0.7rem;background:${color};color:white;padding:2px 6px;border-radius:8px;margin-left:6px;text-transform:uppercase;">${adv.risk_level}</span>
                            </div>
                            <div style="color:#555;font-size:0.9rem;margin-bottom:6px;">${adv.message}</div>
                            <div style="color:#222;font-size:0.88rem;"><strong>👉 ${adv.action_hint}</strong></div>
                            ${src}
                        </div>
                    `;
                }
                html += `</div></div>`;
            }

            // Schemes Section
            html += `
                <div class="card">
                    <div class="card-title" style="padding: 20px 20px 10px;">
                        💡 Government Schemes (Eligible for You)
                    </div>
                    <div style="padding: 0 20px 20px;">
            `;

            if (schemes.length === 0) {
                html += `<p style="color: #999; text-align: center;">No eligible schemes found</p>`;
            } else {
                for (const scheme of schemes) {
                    const badge = scheme.eligible ? '<span class="scheme-badge">✓ Eligible</span>' : '';
                    html += `
                        <div class="scheme-item">
                            <div class="scheme-name">${scheme.name}</div>
                            <div class="scheme-desc">${scheme.description}</div>
                            ${badge}
                        </div>
                    `;
                }
            }

            html += `</div></div>`;

            // Stats Section
            html += `
                <div class="card">
                    <div class="card-title" style="padding: 20px 20px 10px;">
                        📈 Your Activity
                    </div>
                    <div style="padding: 0 20px 20px;">
                        <div class="stats-grid">
                            <div class="stat-card">
                                <div class="stat-value">${stats.queries_asked}</div>
                                <div class="stat-label">Queries Asked</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-value">${stats.messages_received}</div>
                                <div class="stat-label">Messages Received</div>
                            </div>
                        </div>
                    </div>
                </div>
            `;

            document.getElementById('dashboard-content').innerHTML = html;
        }

        function logout() {
            if (confirm('Are you sure you want to logout?')) {
                localStorage.removeItem('farmerToken');
                window.location.href = '/farmer/login';
            }
        }

        async function dismissAdvisory(id, btn) {
            const token = localStorage.getItem('farmerToken');
            try {
                const resp = await fetch(`/farmer/api/advisories/${id}/dismiss`, {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${token}` },
                });
                if (resp.ok) {
                    const card = btn.closest('[data-advisory-id]');
                    if (card) card.remove();
                }
            } catch (e) { console.error('Dismiss failed', e); }
        }

        // Load dashboard on page load
        loadDashboard();

        // Refresh every 15 minutes
        setInterval(loadDashboard, 15 * 60 * 1000);
    </script>
</body>
</html>
"""
