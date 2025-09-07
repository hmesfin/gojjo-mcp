"""
Authentication components for GitHub OAuth integration.
"""

from .github_oauth import GitHubOAuthManager, GitHubUser, OAuthSession

__all__ = ['GitHubOAuthManager', 'GitHubUser', 'OAuthSession']