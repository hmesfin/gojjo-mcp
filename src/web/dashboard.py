"""
Developer Dashboard with Usage Analytics and Rate Limit Displays
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import json

from auth.github_oauth import GitHubUser


class DashboardRenderer:
    """Renders comprehensive developer dashboard."""
    
    def __init__(self):
        pass
    
    def render_dashboard(
        self, 
        user: GitHubUser, 
        api_data: Dict[str, Any],
        base_url: str
    ) -> str:
        """Render complete developer dashboard."""
        
        keys = api_data.get('keys', [])
        usage = api_data.get('usage', {})
        current_usage = usage.get('current', {})
        historical_usage = usage.get('historical', [])
        
        # Get primary API key
        primary_key = keys[0] if keys else None
        
        # Calculate usage percentages
        role_limits = {
            'basic': 1000,
            'premium': 5000,
            'developer': 10000,
            'admin': 999999
        }
        
        current_role = primary_key['role'] if primary_key else 'basic'
        hourly_limit = role_limits.get(current_role, 1000)
        current_hourly = current_usage.get('per_hour', 0)
        usage_percentage = min(100, (current_hourly / hourly_limit) * 100)
        
        # Generate usage chart data
        chart_data = json.dumps([
            {'hour': item['hour'], 'requests': item['requests']} 
            for item in historical_usage[-12:]  # Last 12 hours
        ])
        
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Developer Dashboard - MCP Server</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f7fafc;
            min-height: 100vh;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 2rem 0;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 2rem;
        }}
        
        .header-content {{
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
        
        .user-info {{
            display: flex;
            align-items: center;
            gap: 1rem;
        }}
        
        .avatar {{
            width: 60px;
            height: 60px;
            border-radius: 50%;
            border: 3px solid rgba(255, 255, 255, 0.3);
        }}
        
        .user-details h1 {{
            font-size: 1.5rem;
            margin-bottom: 0.25rem;
        }}
        
        .user-details p {{
            opacity: 0.9;
            font-size: 0.9rem;
        }}
        
        .header-actions {{
            display: flex;
            gap: 1rem;
        }}
        
        .btn {{
            background: rgba(255, 255, 255, 0.2);
            color: white;
            border: 1px solid rgba(255, 255, 255, 0.3);
            border-radius: 6px;
            padding: 0.5rem 1rem;
            text-decoration: none;
            font-size: 0.9rem;
            transition: all 0.2s;
        }}
        
        .btn:hover {{
            background: rgba(255, 255, 255, 0.3);
        }}
        
        .main-content {{
            padding: 2rem 0;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }}
        
        .stat-card {{
            background: white;
            border-radius: 8px;
            padding: 1.5rem;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
            border-left: 4px solid #4299e1;
        }}
        
        .stat-header {{
            display: flex;
            align-items: center;
            justify-content: between;
            margin-bottom: 1rem;
        }}
        
        .stat-title {{
            font-size: 0.9rem;
            color: #718096;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .stat-value {{
            font-size: 2rem;
            font-weight: 700;
            color: #2d3748;
            margin-bottom: 0.5rem;
        }}
        
        .stat-subtitle {{
            font-size: 0.85rem;
            color: #718096;
        }}
        
        .usage-bar {{
            width: 100%;
            height: 8px;
            background: #e2e8f0;
            border-radius: 4px;
            overflow: hidden;
            margin: 0.5rem 0;
        }}
        
        .usage-fill {{
            height: 100%;
            background: linear-gradient(90deg, #48bb78, #38a169);
            border-radius: 4px;
            transition: width 0.3s ease;
        }}
        
        .usage-fill.warning {{
            background: linear-gradient(90deg, #ed8936, #dd6b20);
        }}
        
        .usage-fill.danger {{
            background: linear-gradient(90deg, #e53e3e, #c53030);
        }}
        
        .dashboard-section {{
            background: white;
            border-radius: 8px;
            padding: 1.5rem;
            margin-bottom: 2rem;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        }}
        
        .section-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 1.5rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid #e2e8f0;
        }}
        
        .section-title {{
            font-size: 1.2rem;
            font-weight: 700;
            color: #2d3748;
        }}
        
        .api-key-display {{
            background: #f7fafc;
            border: 1px solid #cbd5e0;
            border-radius: 6px;
            padding: 1rem;
            font-family: 'Monaco', 'Courier New', monospace;
            font-size: 0.9rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 1rem;
        }}
        
        .key-text {{
            color: #2d3748;
            word-break: break-all;
        }}
        
        .copy-btn {{
            background: #4299e1;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 0.5rem 1rem;
            font-size: 0.8rem;
            cursor: pointer;
            transition: background-color 0.2s;
            margin-left: 1rem;
            white-space: nowrap;
        }}
        
        .copy-btn:hover {{
            background: #3182ce;
        }}
        
        .key-info {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 1rem;
        }}
        
        .key-info-item {{
            display: flex;
            justify-content: space-between;
            padding: 0.5rem;
            background: #f7fafc;
            border-radius: 4px;
            font-size: 0.9rem;
        }}
        
        .key-info-label {{
            color: #718096;
            font-weight: 600;
        }}
        
        .key-info-value {{
            color: #2d3748;
        }}
        
        .chart-container {{
            height: 300px;
            margin: 1rem 0;
        }}
        
        .chart {{
            width: 100%;
            height: 100%;
        }}
        
        .role-badge {{
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .role-basic {{
            background: #bee3f8;
            color: #2b6cb0;
        }}
        
        .role-premium {{
            background: #fbb6ce;
            color: #b83280;
        }}
        
        .role-developer {{
            background: #c6f6d5;
            color: #2f855a;
        }}
        
        .role-admin {{
            background: #fed7d7;
            color: #c53030;
        }}
        
        .alert {{
            padding: 1rem;
            border-radius: 6px;
            margin-bottom: 1rem;
            border-left: 4px solid;
        }}
        
        .alert-warning {{
            background: #fefcbf;
            border-color: #d69e2e;
            color: #744210;
        }}
        
        .alert-info {{
            background: #bee3f8;
            border-color: #3182ce;
            color: #2c5282;
        }}
        
        .footer {{
            text-align: center;
            padding: 2rem;
            color: #718096;
            border-top: 1px solid #e2e8f0;
        }}
        
        .footer a {{
            color: #4299e1;
            text-decoration: none;
        }}
        
        .footer a:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <header class="header">
        <div class="container">
            <div class="header-content">
                <div class="user-info">
                    <img src="{user.avatar_url}" alt="Avatar" class="avatar">
                    <div class="user-details">
                        <h1>{user.name or user.login}</h1>
                        <p>@{user.login} • Developer Dashboard</p>
                    </div>
                </div>
                <div class="header-actions">
                    <a href="/docs" class="btn">📚 API Docs</a>
                    <a href="#" onclick="logout()" class="btn">🚪 Logout</a>
                </div>
            </div>
        </div>
    </header>
    
    <main class="main-content">
        <div class="container">
            <!-- Usage Statistics -->
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-header">
                        <span class="stat-title">Current Usage</span>
                    </div>
                    <div class="stat-value">{current_hourly:,}</div>
                    <div class="stat-subtitle">requests this hour</div>
                    <div class="usage-bar">
                        <div class="usage-fill {'warning' if usage_percentage > 70 else 'danger' if usage_percentage > 90 else ''}" 
                             style="width: {usage_percentage:.1f}%"></div>
                    </div>
                    <div class="stat-subtitle">{usage_percentage:.1f}% of {hourly_limit:,} hourly limit</div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-header">
                        <span class="stat-title">Total Requests</span>
                    </div>
                    <div class="stat-value">{usage.get('total_requests', 0):,}</div>
                    <div class="stat-subtitle">last 24 hours</div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-header">
                        <span class="stat-title">Access Level</span>
                    </div>
                    <div class="stat-value">
                        <span class="role-badge role-{current_role}">{current_role.title()}</span>
                    </div>
                    <div class="stat-subtitle">{hourly_limit:,} requests/hour limit</div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-header">
                        <span class="stat-title">API Keys</span>
                    </div>
                    <div class="stat-value">{len(keys)}</div>
                    <div class="stat-subtitle">active keys</div>
                </div>
            </div>
            
            {"<div class='alert alert-warning'><strong>Rate Limit Warning:</strong> You're using over 70% of your hourly rate limit. Consider upgrading or reducing usage.</div>" if usage_percentage > 70 else ""}
            
            <!-- API Key Management -->
            <div class="dashboard-section">
                <div class="section-header">
                    <h2 class="section-title">🔑 API Key Management</h2>
                </div>
                
                {self._render_api_key_section(primary_key) if primary_key else "<p>No API keys found. This shouldn't happen - please contact support.</p>"}
            </div>
            
            <!-- Usage Analytics -->
            <div class="dashboard-section">
                <div class="section-header">
                    <h2 class="section-title">📊 Usage Analytics</h2>
                </div>
                
                <div class="alert alert-info">
                    <strong>Usage tracked over the last 24 hours:</strong> Data is aggregated hourly and retained for analytical purposes.
                </div>
                
                <div class="chart-container">
                    <canvas id="usageChart" class="chart"></canvas>
                </div>
            </div>
            
            <!-- Integration Guide -->
            <div class="dashboard-section">
                <div class="section-header">
                    <h2 class="section-title">⚡ Quick Start Guide</h2>
                </div>
                
                <div style="margin-bottom: 1rem;">
                    <strong>1. Configure Your MCP Client</strong>
                </div>
                <div class="api-key-display">
                    <span class="key-text">export MCP_API_KEY="{primary_key['key'] if primary_key else 'YOUR_API_KEY'}"</span>
                    <button class="copy-btn" onclick="copyToClipboard('export MCP_API_KEY=\\"{primary_key['key'] if primary_key else 'YOUR_API_KEY'}\\"')">Copy</button>
                </div>
                
                <div style="margin-bottom: 1rem;">
                    <strong>2. Test API Access</strong>
                </div>
                <div class="api-key-display">
                    <span class="key-text">curl -H "X-API-Key: {primary_key['key'] if primary_key else 'YOUR_API_KEY'}" {base_url}/api/resources</span>
                    <button class="copy-btn" onclick="copyToClipboard('curl -H \\"X-API-Key: {primary_key['key'] if primary_key else 'YOUR_API_KEY'}\\" {base_url}/api/resources')">Copy</button>
                </div>
                
                <div style="margin-bottom: 1rem;">
                    <strong>3. Connect Claude Code</strong>
                </div>
                <div class="api-key-display">
                    <span class="key-text">python src/mcp_http_client.py</span>
                    <button class="copy-btn" onclick="copyToClipboard('python src/mcp_http_client.py')">Copy</button>
                </div>
            </div>
        </div>
    </main>
    
    <footer class="footer">
        <div class="container">
            <p>Django Vue MCP Documentation Server • 
               <a href="https://github.com/yourusername/django-vue-mcp-server">Source Code</a> • 
               <a href="/docs">API Documentation</a>
            </p>
        </div>
    </footer>
    
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
        // Usage Chart
        const chartData = {chart_data};
        const ctx = document.getElementById('usageChart').getContext('2d');
        
        new Chart(ctx, {{
            type: 'line',
            data: {{
                labels: chartData.map(item => {{
                    const date = new Date(item.hour);
                    return date.getHours() + ':00';
                }}),
                datasets: [{{
                    label: 'Requests',
                    data: chartData.map(item => item.requests),
                    borderColor: '#4299e1',
                    backgroundColor: 'rgba(66, 153, 225, 0.1)',
                    fill: true,
                    tension: 0.4
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    y: {{
                        beginAtZero: true,
                        grid: {{
                            color: 'rgba(0, 0, 0, 0.1)'
                        }}
                    }},
                    x: {{
                        grid: {{
                            color: 'rgba(0, 0, 0, 0.1)'
                        }}
                    }}
                }},
                plugins: {{
                    legend: {{
                        display: false
                    }},
                    tooltip: {{
                        mode: 'index',
                        intersect: false,
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        titleColor: 'white',
                        bodyColor: 'white',
                        cornerRadius: 6
                    }}
                }}
            }}
        }});
        
        // Utility functions
        function copyToClipboard(text) {{
            navigator.clipboard.writeText(text).then(() => {{
                // Visual feedback
                event.target.textContent = 'Copied!';
                event.target.style.background = '#48bb78';
                
                setTimeout(() => {{
                    event.target.textContent = 'Copy';
                    event.target.style.background = '#4299e1';
                }}, 2000);
            }});
        }}
        
        function logout() {{
            if (confirm('Are you sure you want to logout?')) {{
                fetch('/auth/logout', {{ method: 'POST' }})
                .then(() => {{
                    window.location.href = '/login';
                }});
            }}
        }}
        
        // Auto-refresh usage stats every 30 seconds
        setInterval(() => {{
            fetch('/dashboard/stats')
            .then(response => response.json())
            .then(data => {{
                // Update stats if needed
                console.log('Stats updated:', data);
            }})
            .catch(err => console.log('Stats update failed:', err));
        }}, 30000);
    </script>
</body>
</html>
        """
        
        return html
    
    def _render_api_key_section(self, key: Dict[str, Any]) -> str:
        """Render the API key management section."""
        return f"""
        <div class="api-key-display">
            <span class="key-text">{key['key']}</span>
            <button class="copy-btn" onclick="copyToClipboard('{key['key']}')">Copy Key</button>
        </div>
        
        <div class="key-info">
            <div class="key-info-item">
                <span class="key-info-label">Role</span>
                <span class="key-info-value role-badge role-{key['role']}">{key['role'].title()}</span>
            </div>
            <div class="key-info-item">
                <span class="key-info-label">Type</span>
                <span class="key-info-value">{key['type'].title()}</span>
            </div>
            <div class="key-info-item">
                <span class="key-info-label">Created</span>
                <span class="key-info-value">{datetime.fromisoformat(key['created_at']).strftime('%Y-%m-%d')}</span>
            </div>
            <div class="key-info-item">
                <span class="key-info-label">Last Used</span>
                <span class="key-info-value">
                    {datetime.fromisoformat(key['last_used']).strftime('%Y-%m-%d %H:%M') if key['last_used'] else 'Never'}
                </span>
            </div>
            <div class="key-info-item">
                <span class="key-info-label">Total Usage</span>
                <span class="key-info-value">{key['usage_count']:,} requests</span>
            </div>
            <div class="key-info-item">
                <span class="key-info-label">Status</span>
                <span class="key-info-value">{'Active' if key['is_active'] else 'Inactive'}</span>
            </div>
        </div>
        """