"""
Web interface components for OAuth authentication and dashboard.
"""

from .oauth_handler import OAuthWebHandler
from .dashboard import DashboardRenderer

__all__ = ['OAuthWebHandler', 'DashboardRenderer']