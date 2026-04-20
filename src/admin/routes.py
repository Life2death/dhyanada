"""Admin dashboard FastAPI routes."""
from __future__ import annotations

import logging
from typing import Optional
from datetime import datetime, timedelta
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import jwt

from src.admin.repository import AdminRepository
from src.admin.models import (
    DailyStats,
    CropStat,
    SubscriptionFunnel,
    MessageLogEntry,
    BroadcastHealth,
)
from src.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])

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


# ─────────────────────────────────────────────────────────────────
# JWT Authentication
# ─────────────────────────────────────────────────────────────────

async def get_admin_token(request: Request) -> dict:
    """Validate JWT token from Authorization header."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

    token = auth_header.split(" ")[1]

    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        if payload.get("type") != "admin":
            raise HTTPException(status_code=401, detail="Invalid token type")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired, please login again")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


@router.get("/login", response_class=HTMLResponse)
async def login_page():
    """Serve login form."""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Kisan AI — Admin Login</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .login-container {
                width: 100%;
                max-width: 400px;
                padding: 15px;
            }
            .login-card {
                border: none;
                border-radius: 12px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            }
            .login-card .card-body {
                padding: 40px;
            }
            .login-card h2 {
                text-align: center;
                color: #333;
                margin-bottom: 10px;
                font-weight: 700;
            }
            .login-card .text-muted {
                text-align: center;
                margin-bottom: 30px;
                font-size: 0.95em;
            }
            .btn-login {
                background: linear-gradient(90deg, #667eea, #764ba2);
                border: none;
                padding: 10px;
                font-weight: 600;
                margin-top: 20px;
            }
            .btn-login:hover {
                background: linear-gradient(90deg, #5568d3, #6a3d8f);
            }
            .alert {
                margin-bottom: 20px;
            }
        </style>
    </head>
    <body>
        <div class="login-container">
            <div class="card login-card">
                <div class="card-body">
                    <h2>🌾 Kisan AI</h2>
                    <p class="text-muted">Admin Dashboard</p>
                    <form id="loginForm">
                        <div class="mb-3">
                            <label for="username" class="form-label">Username</label>
                            <input type="text" class="form-control" id="username" name="username" placeholder="admin" required>
                        </div>
                        <div class="mb-3">
                            <label for="password" class="form-label">Password</label>
                            <input type="password" class="form-control" id="password" name="password" placeholder="••••••" required>
                        </div>
                        <div id="errorMessage" class="alert alert-danger d-none"></div>
                        <button type="submit" class="btn btn-primary btn-login w-100">Login</button>
                    </form>
                </div>
            </div>
        </div>
        <script>
            document.getElementById('loginForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                const username = document.getElementById('username').value;
                const password = document.getElementById('password').value;
                const errorDiv = document.getElementById('errorMessage');

                try {
                    const formData = new FormData();
                    formData.append('username', username);
                    formData.append('password', password);

                    const response = await fetch('/admin/login', {
                        method: 'POST',
                        body: formData
                    });

                    if (response.ok) {
                        const data = await response.json();
                        localStorage.setItem('adminToken', data.access_token);
                        window.location.href = '/admin/';
                    } else {
                        errorDiv.textContent = 'Invalid credentials. Please try again.';
                        errorDiv.classList.remove('d-none');
                    }
                } catch (err) {
                    errorDiv.textContent = 'Login failed. Please try again.';
                    errorDiv.classList.remove('d-none');
                }
            });
        </script>
    </body>
    </html>
    """


@router.post("/login")
async def admin_login(username: str = Form(...), password: str = Form(...)):
    """Generate JWT token for admin authentication."""
    if username == settings.admin_username and password == settings.admin_password:
        token = jwt.encode({
            "type": "admin",
            "username": username,
            "exp": datetime.utcnow() + timedelta(hours=settings.jwt_expiry_hours),
            "iat": datetime.utcnow()
        }, settings.jwt_secret, algorithm="HS256")
        return {"access_token": token, "token_type": "bearer"}
    raise HTTPException(status_code=401, detail="Invalid credentials")


# ─────────────────────────────────────────────────────────────────
# HTML Dashboard
# ─────────────────────────────────────────────────────────────────

HTML_DASHBOARD = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Kisan AI — Admin Dashboard</title>
    <!-- Bootstrap 5 CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            color: white;
        }

        .loading {
            text-align: center;
            padding: 40px;
            font-size: 1.2em;
            color: white;
        }

        .error {
            color: #ff6b6b;
            background: rgba(0,0,0,0.2);
            padding: 20px;
            border-radius: 8px;
            margin: 20px;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
        }

        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 40px;
            color: white;
            flex-wrap: wrap;
            gap: 20px;
        }

        .header-content {
            flex: 1;
        }

        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            margin: 0;
        }

        .header p {
            font-size: 1.1em;
            opacity: 0.9;
            margin: 0;
        }

        .logout-btn {
            background: rgba(255,255,255,0.2);
            border: 1px solid rgba(255,255,255,0.5);
            color: white;
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.95em;
            transition: background 0.2s;
        }

        .logout-btn:hover {
            background: rgba(255,255,255,0.3);
            color: white;
        }

        .dashboard {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }

        .card {
            background: white;
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            transition: transform 0.2s, box-shadow 0.2s;
        }

        .card:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 40px rgba(0,0,0,0.3);
        }

        .card-title {
            font-size: 0.95em;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 15px;
            font-weight: 600;
        }

        .card-value {
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 10px;
        }

        .card-meta {
            font-size: 0.9em;
            color: #999;
        }

        .chart-section {
            background: white;
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            margin-bottom: 20px;
        }

        .chart-title {
            font-size: 1.2em;
            font-weight: 600;
            margin-bottom: 20px;
            color: #333;
        }

        .top-crops {
            display: flex;
            flex-direction: column;
            gap: 15px;
        }

        .crop-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
        }

        .crop-name {
            font-weight: 600;
            color: #333;
        }

        .crop-bar {
            flex: 1;
            height: 8px;
            background: #e9ecef;
            border-radius: 4px;
            margin: 0 15px;
            overflow: hidden;
        }

        .crop-bar-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea, #764ba2);
        }

        .crop-count {
            font-weight: 600;
            color: #667eea;
            min-width: 40px;
            text-align: right;
        }

        .funnel {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }

        .funnel-step {
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }

        .funnel-label {
            font-size: 0.85em;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }

        .funnel-value {
            font-size: 1.8em;
            font-weight: bold;
            color: #667eea;
        }

        .messages-log {
            margin-top: 20px;
        }

        .message-item {
            padding: 12px;
            border-bottom: 1px solid #eee;
            font-size: 0.9em;
        }

        .message-item:last-child {
            border-bottom: none;
        }

        .message-phone {
            font-weight: 600;
            color: #667eea;
            margin-right: 10px;
        }

        .message-preview {
            color: #666;
            margin-top: 5px;
            font-style: italic;
        }

        .message-intent {
            display: inline-block;
            background: #e7f5ff;
            color: #667eea;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 0.8em;
            margin-top: 5px;
        }

        .broadcast-status {
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
            margin-top: 20px;
        }

        .broadcast-status.success {
            border-left: 4px solid #28a745;
        }

        .broadcast-status.partial {
            border-left: 4px solid #ffc107;
        }

        .broadcast-status.failure {
            border-left: 4px solid #dc3545;
        }

        .status-badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            font-weight: 600;
            margin-right: 10px;
        }

        .status-badge.success {
            background: #d4edda;
            color: #155724;
        }

        .status-badge.partial {
            background: #fff3cd;
            color: #856404;
        }

        .status-badge.failure {
            background: #f8d7da;
            color: #721c24;
        }

        .refresh-btn {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 8px;
            font-size: 1em;
            cursor: pointer;
            font-weight: 600;
            transition: transform 0.2s;
        }

        .refresh-btn:hover {
            transform: scale(1.05);
        }

        .timestamp {
            text-align: center;
            color: #999;
            font-size: 0.9em;
            margin-top: 20px;
        }

        @media (max-width: 768px) {
            .header h1 {
                font-size: 1.8em;
            }

            .dashboard {
                grid-template-columns: 1fr;
            }

            .card-value {
                font-size: 2em;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="header-content">
                <h1>🌾 Kisan AI Admin Dashboard</h1>
                <p>Real-time metrics for Maharashtra farmers</p>
            </div>
            <button class="logout-btn" onclick="logout()">🚪 Logout</button>
        </div>

        <!-- Tab Navigation -->
        <div style="display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap;">
            <button class="tab-btn active" onclick="switchTab('overview')" style="padding: 10px 20px; background: rgba(255,255,255,0.3); border: none; border-radius: 6px; color: white; cursor: pointer; font-weight: 600;">📊 Overview</button>
            <button class="tab-btn" onclick="switchTab('system-health')" style="padding: 10px 20px; background: rgba(255,255,255,0.1); border: none; border-radius: 6px; color: white; cursor: pointer; font-weight: 600;">🏥 System Health</button>
            <button class="tab-btn" onclick="switchTab('error-logs')" style="padding: 10px 20px; background: rgba(255,255,255,0.1); border: none; border-radius: 6px; color: white; cursor: pointer; font-weight: 600;">❌ Error Logs</button>
        </div>

        <div id="dashboard-content" style="opacity: 0.5;">
            <p style="text-align: center; color: white;">Loading dashboard...</p>
        </div>

        <div style="text-align: center; margin-top: 30px;">
            <button class="refresh-btn" onclick="location.reload()">🔄 Refresh Dashboard</button>
        </div>
    </div>

    <script>
        let currentTab = 'overview';

        function logout() {
            localStorage.removeItem('adminToken');
            window.location.href = '/admin/login';
        }

        function switchTab(tab) {
            currentTab = tab;

            // Update button styles
            document.querySelectorAll('.tab-btn').forEach(btn => {
                btn.style.background = 'rgba(255,255,255,0.1)';
            });
            event.target.style.background = 'rgba(255,255,255,0.3)';

            // Load appropriate content
            loadDashboard();
        }

        async function loadDashboard() {
            try {
                // Check for token
                const token = localStorage.getItem('adminToken');
                if (!token) {
                    window.location.href = '/admin/login';
                    return;
                }

                document.getElementById('dashboard-content').style.opacity = '0.5';

                if (currentTab === 'overview') {
                    // Load main dashboard
                    const response = await fetch('/admin/api/dashboard', {
                        headers: { 'Authorization': `Bearer ${token}` }
                    });
                    if (response.status === 401) {
                        localStorage.removeItem('adminToken');
                        window.location.href = '/admin/login';
                        return;
                    }
                    const data = await response.json();
                    const html = renderDashboard(data);
                    document.getElementById('dashboard-content').innerHTML = html;
                } else if (currentTab === 'system-health') {
                    // Load service health
                    const response = await fetch('/admin/api/service-health', {
                        headers: { 'Authorization': `Bearer ${token}` }
                    });
                    const health = await response.json();
                    const html = renderSystemHealth(health);
                    document.getElementById('dashboard-content').innerHTML = html;
                } else if (currentTab === 'error-logs') {
                    // Load error logs
                    const response = await fetch('/admin/api/errors', {
                        headers: { 'Authorization': `Bearer ${token}` }
                    });
                    const errors = await response.json();
                    const html = renderErrorLogs(errors);
                    document.getElementById('dashboard-content').innerHTML = html;
                }

                document.getElementById('dashboard-content').style.opacity = '1';
            } catch (error) {
                console.error('Failed to load dashboard:', error);
                document.getElementById('dashboard-content').innerHTML =
                    '<p style="color: white; text-align: center;">Failed to load content. Check console for details.</p>';
                document.getElementById('dashboard-content').style.opacity = '1';
            }
        }

        function renderDashboard(data) {
            const renderTopCrops = () => {
                const maxCount = Math.max(...data.top_crops.map(c => c.count), 1);
                return data.top_crops.map(crop => `
                    <div class="crop-item">
                        <span class="crop-name">${crop.commodity}</span>
                        <div class="crop-bar">
                            <div class="crop-bar-fill" style="width: ${(crop.count / maxCount) * 100}%"></div>
                        </div>
                        <span class="crop-count">${crop.count}</span>
                    </div>
                `).join('');
            };

            const renderFunnel = () => {
                const funnel = data.funnel;
                return `
                    <div class="funnel-step">
                        <div class="funnel-label">New Farmers</div>
                        <div class="funnel-value">${funnel.new}</div>
                    </div>
                    <div class="funnel-step">
                        <div class="funnel-label">Awaiting Consent</div>
                        <div class="funnel-value">${funnel.awaiting_consent}</div>
                    </div>
                    <div class="funnel-step">
                        <div class="funnel-label">Active</div>
                        <div class="funnel-value">${funnel.active}</div>
                    </div>
                    <div class="funnel-step">
                        <div class="funnel-label">Opted Out</div>
                        <div class="funnel-value">${funnel.opted_out}</div>
                    </div>
                `;
            };

            const renderMessages = () => {
                return data.recent_messages.slice(0, 10).map(msg => `
                    <div class="message-item">
                        <span class="message-phone">${msg.farmer_phone_masked}</span>
                        <span style="color: #999;">($${msg.direction})</span>
                        <div class="message-preview">"${msg.message_preview}..."</div>
                        ${msg.detected_intent ? `<span class="message-intent">${msg.detected_intent}</span>` : ''}
                    </div>
                `).join('');
            };

            const renderBroadcast = () => {
                if (!data.broadcast_health) return '<p style="color: #666;">No recent broadcasts</p>';

                const bh = data.broadcast_health;
                const statusClass = bh.status.replace('_', '-');
                const sentTotal = bh.sent_count + bh.failed_count;
                const successRate = sentTotal > 0 ? Math.round((bh.sent_count / sentTotal) * 100) : 0;

                return `
                    <div class="broadcast-status ${statusClass}">
                        <span class="status-badge ${statusClass}">${bh.status.toUpperCase()}</span>
                        <span>${bh.sent_count} sent, ${bh.failed_count} failed (${successRate}% success rate)</span>
                        <div style="margin-top: 10px; color: #666; font-size: 0.9em;">
                            Last run: ${new Date(bh.last_run_at).toLocaleString()}
                        </div>
                    </div>
                `;
            };

            return `
                <div class="dashboard">
                    <div class="card">
                        <div class="card-title">📊 DAU Today</div>
                        <div class="card-value">${data.dau_today}</div>
                        <div class="card-meta">daily active users</div>
                    </div>

                    <div class="card">
                        <div class="card-title">💬 Messages Today</div>
                        <div class="card-value">${data.messages_today}</div>
                        <div class="card-meta">inbound + outbound</div>
                    </div>

                    <div class="card">
                        <div class="card-title">👥 Total Farmers</div>
                        <div class="card-value">${data.total_farmers}</div>
                        <div class="card-meta">${data.active_farmers} active</div>
                    </div>
                </div>

                <div class="chart-section">
                    <div class="chart-title">🏆 Top Crops</div>
                    <div class="top-crops">
                        ${renderTopCrops()}
                    </div>
                </div>

                <div class="chart-section">
                    <div class="chart-title">📈 Subscription Funnel</div>
                    <div class="funnel">
                        ${renderFunnel()}
                    </div>
                </div>

                <div class="chart-section">
                    <div class="chart-title">📱 Recent Messages</div>
                    <div class="messages-log">
                        ${renderMessages()}
                    </div>
                </div>

                <div class="chart-section">
                    <div class="chart-title">📡 Broadcast Health</div>
                    ${renderBroadcast()}
                </div>

                <div class="timestamp">
                    Generated at: ${new Date(data.generated_at).toLocaleString()}
                </div>
            `;
        }

        function renderSystemHealth(health) {
            if (!health.services || health.services.length === 0) {
                return '<p style="color: white; text-align: center; padding: 40px;">No service health data available yet</p>';
            }

            const serviceCards = health.services.map(service => {
                const statusColor = service.healthy ? '#28a745' : '#dc3545';
                const statusText = service.healthy ? '✅ Healthy' : '❌ Unhealthy';
                return `
                    <div class="card" style="border-left: 4px solid ${statusColor};">
                        <div style="padding: 20px;">
                            <div style="font-size: 1.2em; font-weight: 600; margin-bottom: 10px;">${service.name}</div>
                            <div style="color: ${statusColor}; font-weight: 600; margin-bottom: 10px;">${statusText}</div>
                            <div style="font-size: 0.9em; color: #666;">
                                <div>📊 Error Rate (1h): ${service.error_rate_1h.toFixed(1)}%</div>
                                <div>📊 Error Rate (24h): ${service.error_rate_24h.toFixed(1)}%</div>
                                <div>⏱️  Latency: ${service.latency_ms.toFixed(0)}ms</div>
                                <div>🕐 Last Check: ${new Date(service.last_heartbeat).toLocaleString()}</div>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');

            return `
                <div style="margin-bottom: 20px;">
                    <h3 style="color: white; margin-bottom: 15px;">📡 Service Status Overview</h3>
                    <div class="dashboard">${serviceCards}</div>
                </div>
            `;
        }

        function renderErrorLogs(errorData) {
            if (!errorData.errors || errorData.errors.length === 0) {
                return '<p style="color: white; text-align: center; padding: 40px;">No errors logged</p>';
            }

            const errorRows = errorData.errors.map(error => `
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #eee; color: #666;">${new Date(error.created_at).toLocaleString()}</td>
                    <td style="padding: 10px; border-bottom: 1px solid #eee;"><span style="background: #e7f5ff; color: #667eea; padding: 2px 6px; border-radius: 3px; font-size: 0.85em;">${error.service}</span></td>
                    <td style="padding: 10px; border-bottom: 1px solid #eee;"><span style="background: #ffe7e7; color: #dc3545; padding: 2px 6px; border-radius: 3px; font-size: 0.85em;">${error.error_type}</span></td>
                    <td style="padding: 10px; border-bottom: 1px solid #eee; max-width: 300px; overflow: hidden; text-overflow: ellipsis; color: #666;">${error.message}</td>
                </tr>
            `).join('');

            return `
                <div style="margin-bottom: 20px;">
                    <h3 style="color: white; margin-bottom: 15px;">❌ Recent Errors (Last 50)</h3>
                    <div class="card">
                        <table style="width: 100%; border-collapse: collapse; font-size: 0.9em;">
                            <thead>
                                <tr style="background: #f8f9fa;">
                                    <th style="padding: 10px; text-align: left; color: #333; font-weight: 600;">Timestamp</th>
                                    <th style="padding: 10px; text-align: left; color: #333; font-weight: 600;">Service</th>
                                    <th style="padding: 10px; text-align: left; color: #333; font-weight: 600;">Type</th>
                                    <th style="padding: 10px; text-align: left; color: #333; font-weight: 600;">Message</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${errorRows}
                            </tbody>
                        </table>
                    </div>
                </div>
            `;
        }

        // Load on page load
        window.addEventListener('load', loadDashboard);

        // Auto-refresh every 5 minutes
        setInterval(loadDashboard, 5 * 60 * 1000);
    </script>
</body>
</html>
"""


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Serve admin dashboard HTML. Token validation happens in JavaScript via localStorage."""
    # Just return the dashboard HTML - JavaScript will check localStorage for token
    # If no token, JavaScript will redirect to login
    return HTML_DASHBOARD


# ─────────────────────────────────────────────────────────────────
# JSON API Endpoints
# ─────────────────────────────────────────────────────────────────

@router.get("/api/dashboard")
async def get_dashboard(session: AsyncSession = Depends(get_db), admin: dict = Depends(get_admin_token)):
    """Get complete dashboard snapshot."""
    repo = AdminRepository(session)
    data = await repo.get_dashboard_data()

    return {
        "dau_today": data.dau_today,
        "messages_today": data.messages_today,
        "total_farmers": data.total_farmers,
        "active_farmers": data.active_farmers,
        "daily_stats_7d": [
            {
                "date": s.date,
                "dau": s.dau,
                "messages_inbound": s.messages_inbound,
                "messages_outbound": s.messages_outbound,
                "top_intent": s.top_intent,
                "top_intent_count": s.top_intent_count,
            }
            for s in data.daily_stats_7d
        ],
        "top_crops": [{"commodity": c.commodity, "count": c.count} for c in data.top_crops],
        "funnel": {
            "new": data.funnel.new,
            "awaiting_consent": data.funnel.awaiting_consent,
            "active": data.funnel.active,
            "opted_out": data.funnel.opted_out,
            "total_farmers": data.funnel.total_farmers,
        },
        "recent_messages": [
            {
                "timestamp": m.timestamp.isoformat(),
                "farmer_phone_masked": m.farmer_phone_masked,
                "direction": m.direction,
                "message_preview": m.message_preview,
                "detected_intent": m.detected_intent,
                "detected_entities": m.detected_entities,
            }
            for m in data.recent_messages
        ],
        "broadcast_health": {
            "last_run_at": data.broadcast_health.last_run_at.isoformat() if data.broadcast_health else None,
            "status": data.broadcast_health.status if data.broadcast_health else None,
            "sent_count": data.broadcast_health.sent_count if data.broadcast_health else 0,
            "failed_count": data.broadcast_health.failed_count if data.broadcast_health else 0,
            "partial_failures": data.broadcast_health.partial_failures if data.broadcast_health else [],
        } if data.broadcast_health else None,
        "generated_at": data.generated_at.isoformat(),
    }


@router.get("/api/dau")
async def get_dau(session: AsyncSession = Depends(get_db), admin: dict = Depends(get_admin_token)):
    """Get daily active users."""
    repo = AdminRepository(session)
    dau = await repo.get_dau_today()
    return {"dau": dau}


@router.get("/api/messages")
async def get_messages(days: int = 7, session: AsyncSession = Depends(get_db), admin: dict = Depends(get_admin_token)):
    """Get message volume for last N days."""
    repo = AdminRepository(session)
    stats = await repo.get_daily_stats_7d()

    # Return only last N days
    stats_n = stats[-days:] if len(stats) >= days else stats

    return {
        "daily": [
            {
                "date": s.date,
                "inbound": s.messages_inbound,
                "outbound": s.messages_outbound,
                "total": s.messages_inbound + s.messages_outbound,
            }
            for s in stats_n
        ],
        "total": sum(s.messages_inbound + s.messages_outbound for s in stats_n),
    }


@router.get("/api/crops")
async def get_top_crops(limit: int = 5, session: AsyncSession = Depends(get_db), admin: dict = Depends(get_admin_token)):
    """Get top commodities by query count."""
    repo = AdminRepository(session)
    crops = await repo.get_top_crops(limit=limit)

    return {
        "top_crops": [{"commodity": c.commodity, "count": c.count} for c in crops]
    }


@router.get("/api/funnel")
async def get_funnel(session: AsyncSession = Depends(get_db), admin: dict = Depends(get_admin_token)):
    """Get subscription funnel breakdown."""
    repo = AdminRepository(session)
    funnel = await repo.get_subscription_funnel()

    return {
        "new": funnel.new,
        "awaiting_consent": funnel.awaiting_consent,
        "active": funnel.active,
        "opted_out": funnel.opted_out,
        "total": funnel.total_farmers,
    }


@router.get("/api/messages-log")
async def get_messages_log(limit: int = 50, session: AsyncSession = Depends(get_db), admin: dict = Depends(get_admin_token)):
    """Get recent conversation log with anonymization."""
    repo = AdminRepository(session)
    messages = await repo.get_recent_messages(limit=limit)

    return {
        "messages": [
            {
                "timestamp": m.timestamp.isoformat(),
                "farmer_phone_masked": m.farmer_phone_masked,
                "direction": m.direction,
                "message_preview": m.message_preview,
                "detected_intent": m.detected_intent,
                "detected_entities": m.detected_entities,
            }
            for m in messages
        ]
    }


@router.get("/api/broadcast-health")
async def get_broadcast_health(session: AsyncSession = Depends(get_db), admin: dict = Depends(get_admin_token)):
    """Get last broadcast task status."""
    repo = AdminRepository(session)
    health = await repo.get_broadcast_health()

    if not health:
        return {"status": "no_data", "message": "No recent broadcasts"}

    return {
        "last_run_at": health.last_run_at.isoformat() if health.last_run_at else None,
        "status": health.status,
        "sent_count": health.sent_count,
        "failed_count": health.failed_count,
        "partial_failures": health.partial_failures,
    }


# ─────────────────────────────────────────────────────────────────
# Phase 3 Step 3: Error Monitoring & Alerting APIs
# ─────────────────────────────────────────────────────────────────

@router.get("/api/errors")
async def get_errors(session: AsyncSession = Depends(get_db), admin: dict = Depends(get_admin_token)):
    """Get recent errors for error logs tab."""
    repo = AdminRepository(session)
    recent_errors = await repo.get_recent_errors(limit=50)

    return {
        "total": len(recent_errors),
        "errors": recent_errors,
    }


@router.get("/api/service-health")
async def get_service_health(session: AsyncSession = Depends(get_db), admin: dict = Depends(get_admin_token)):
    """Get current health status of all services."""
    repo = AdminRepository(session)
    health = await repo.get_service_health()

    return health


@router.get("/api/error-summary")
async def get_error_summary(session: AsyncSession = Depends(get_db), admin: dict = Depends(get_admin_token)):
    """Get error summary (counts by service and type)."""
    repo = AdminRepository(session)
    summary = await repo.get_error_summary(hours=24)

    return summary


@router.get("/api/error-timeline")
async def get_error_timeline(session: AsyncSession = Depends(get_db), admin: dict = Depends(get_admin_token)):
    """Get error timeline for graphing."""
    repo = AdminRepository(session)
    timeline = await repo.get_error_timeline(hours=24)

    return {
        "period_hours": 24,
        "data": timeline,
    }
