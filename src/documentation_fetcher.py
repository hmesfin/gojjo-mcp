"""
Advanced Documentation Fetching System

This module provides enhanced documentation fetching capabilities including:
- Release history and changelogs
- GitHub integration for source code analysis
- Official documentation parsing
- Version comparison and recommendations
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urlparse, urljoin
import re

import httpx
from bs4 import BeautifulSoup
import yaml

logger = logging.getLogger(__name__)

class ReleaseInfo:
    """Information about a specific release"""
    def __init__(self, version: str, release_date: str, notes: str = "", 
                 is_prerelease: bool = False, download_count: int = 0):
        self.version = version
        self.release_date = release_date
        self.notes = notes
        self.is_prerelease = is_prerelease
        self.download_count = download_count

class DocumentationFetcher:
    """Advanced documentation fetching with GitHub and release info integration"""
    
    def __init__(self, github_token: Optional[str] = None):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.github_token = github_token
        
        # GitHub API headers
        self.github_headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'django-vue-mcp-server/1.0.0'
        }
        
        if self.github_token:
            self.github_headers['Authorization'] = f'token {self.github_token}'
    
    async def get_pypi_package_details(self, package_name: str) -> Dict[str, Any]:
        """Get comprehensive PyPI package information including release history"""
        try:
            url = f"https://pypi.org/pypi/{package_name}/json"
            response = await self.client.get(url)
            
            if response.status_code != 200:
                return {"error": f"Failed to fetch from PyPI: HTTP {response.status_code}"}
            
            data = response.json()
            info = data.get('info', {})
            releases = data.get('releases', {})
            
            # Get release history (last 10 releases)
            release_history = []
            sorted_versions = sorted(
                releases.keys(), 
                key=lambda v: self._parse_version(v), 
                reverse=True
            )[:10]
            
            for version in sorted_versions:
                version_data = releases[version]
                if version_data:  # Skip empty releases
                    release_date = version_data[0].get('upload_time', '').split('T')[0]
                    total_downloads = sum(file_info.get('size', 0) for file_info in version_data)
                    
                    release_history.append({
                        'version': version,
                        'release_date': release_date,
                        'files_count': len(version_data),
                        'total_size': total_downloads
                    })
            
            # Parse project URLs for additional info
            project_urls = info.get('project_urls', {})
            github_url = self._extract_github_url(project_urls, info.get('home_page', ''))
            
            return {
                'name': package_name,
                'version': info.get('version', 'unknown'),
                'summary': info.get('summary', ''),
                'description': info.get('description', ''),
                'author': info.get('author', ''),
                'author_email': info.get('author_email', ''),
                'license': info.get('license', ''),
                'homepage': info.get('home_page', ''),
                'documentation_url': project_urls.get('Documentation', ''),
                'source_url': project_urls.get('Source', project_urls.get('Homepage', '')),
                'bug_tracker': project_urls.get('Bug Tracker', ''),
                'github_url': github_url,
                'classifiers': info.get('classifiers', []),
                'keywords': info.get('keywords', ''),
                'requires_python': info.get('requires_python', ''),
                'dependencies': info.get('requires_dist', []),
                'release_history': release_history,
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error fetching PyPI details for {package_name}: {e}")
            return {"error": f"Failed to fetch PyPI details: {str(e)}"}
    
    async def get_npm_package_details(self, package_name: str) -> Dict[str, Any]:
        """Get comprehensive NPM package information including release history"""
        try:
            url = f"https://registry.npmjs.org/{package_name}"
            response = await self.client.get(url)
            
            if response.status_code != 200:
                return {"error": f"Failed to fetch from NPM: HTTP {response.status_code}"}
            
            data = response.json()
            
            # Get latest version info
            latest_version = data.get('dist-tags', {}).get('latest', 'unknown')
            version_data = data.get('versions', {}).get(latest_version, {})
            
            # Get release history (last 10 versions)
            versions = data.get('versions', {})
            times = data.get('time', {})
            
            release_history = []
            sorted_versions = sorted(
                versions.keys(),
                key=lambda v: self._parse_version(v),
                reverse=True
            )[:10]
            
            for version in sorted_versions:
                release_date = times.get(version, '').split('T')[0]
                version_info = versions[version]
                
                release_history.append({
                    'version': version,
                    'release_date': release_date,
                    'description': version_info.get('description', ''),
                    'dependencies_count': len(version_info.get('dependencies', {}))
                })
            
            # Extract GitHub URL
            repository = data.get('repository', {})
            github_url = self._extract_github_url_from_npm(repository)
            
            return {
                'name': package_name,
                'version': latest_version,
                'description': data.get('description', ''),
                'author': self._format_npm_author(data.get('author', {})),
                'license': data.get('license', ''),
                'homepage': data.get('homepage', ''),
                'repository_url': repository.get('url', '') if isinstance(repository, dict) else repository,
                'github_url': github_url,
                'keywords': data.get('keywords', []),
                'dependencies': version_data.get('dependencies', {}),
                'dev_dependencies': version_data.get('devDependencies', {}),
                'peer_dependencies': version_data.get('peerDependencies', {}),
                'engines': version_data.get('engines', {}),
                'scripts': version_data.get('scripts', {}),
                'release_history': release_history,
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error fetching NPM details for {package_name}: {e}")
            return {"error": f"Failed to fetch NPM details: {str(e)}"}
    
    async def get_github_releases(self, github_url: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Fetch GitHub releases and changelog information"""
        try:
            # Parse GitHub URL to get owner and repo
            owner, repo = self._parse_github_url(github_url)
            if not owner or not repo:
                return []
            
            # Fetch releases from GitHub API
            url = f"https://api.github.com/repos/{owner}/{repo}/releases"
            params = {'per_page': limit}
            
            response = await self.client.get(url, headers=self.github_headers, params=params)
            
            if response.status_code != 200:
                logger.warning(f"Failed to fetch GitHub releases for {owner}/{repo}: HTTP {response.status_code}")
                return []
            
            releases = response.json()
            
            formatted_releases = []
            for release in releases:
                formatted_releases.append({
                    'tag_name': release.get('tag_name', ''),
                    'name': release.get('name', ''),
                    'body': release.get('body', ''),
                    'published_at': release.get('published_at', '').split('T')[0],
                    'prerelease': release.get('prerelease', False),
                    'draft': release.get('draft', False),
                    'html_url': release.get('html_url', ''),
                    'download_count': sum(asset.get('download_count', 0) for asset in release.get('assets', []))
                })
            
            return formatted_releases
            
        except Exception as e:
            logger.error(f"Error fetching GitHub releases for {github_url}: {e}")
            return []
    
    async def get_documentation_urls(self, package_name: str, package_type: str = 'pypi') -> Dict[str, str]:
        """Get official documentation URLs for a package"""
        docs_urls = {}
        
        try:
            if package_type == 'pypi':
                # Common Python documentation patterns
                common_docs = [
                    f"https://{package_name}.readthedocs.io/",
                    f"https://{package_name.replace('-', '')}.readthedocs.io/",
                    f"https://docs.{package_name}.org/",
                    f"https://www.{package_name}.org/",
                ]
                
                for url in common_docs:
                    if await self._check_url_exists(url):
                        docs_urls['official'] = url
                        break
                        
            elif package_type == 'npm':
                # Common JS documentation patterns
                common_docs = [
                    f"https://{package_name}.js.org/",
                    f"https://docs.{package_name}.com/",
                    f"https://www.{package_name}.com/",
                ]
                
                for url in common_docs:
                    if await self._check_url_exists(url):
                        docs_urls['official'] = url
                        break
            
            return docs_urls
            
        except Exception as e:
            logger.error(f"Error finding documentation URLs for {package_name}: {e}")
            return {}
    
    async def parse_documentation_content(self, doc_url: str) -> Dict[str, Any]:
        """Parse and extract key information from documentation pages"""
        try:
            response = await self.client.get(doc_url)
            if response.status_code != 200:
                return {"error": f"Failed to fetch documentation: HTTP {response.status_code}"}
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract key sections
            content = {
                'title': soup.title.text if soup.title else '',
                'description': '',
                'installation': '',
                'quick_start': '',
                'examples': []
            }
            
            # Look for common documentation patterns
            for section in soup.find_all(['h1', 'h2', 'h3']):
                section_text = section.get_text().lower()
                
                if 'install' in section_text:
                    content['installation'] = self._extract_section_content(section)
                elif any(word in section_text for word in ['quick', 'start', 'getting started']):
                    content['quick_start'] = self._extract_section_content(section)
                elif 'example' in section_text:
                    content['examples'].append(self._extract_section_content(section))
            
            # Extract meta description
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc:
                content['description'] = meta_desc.get('content', '')
            
            return content
            
        except Exception as e:
            logger.error(f"Error parsing documentation from {doc_url}: {e}")
            return {"error": f"Failed to parse documentation: {str(e)}"}
    
    def _parse_version(self, version_str: str) -> Tuple[int, ...]:
        """Parse version string for comparison"""
        try:
            # Remove prefixes like 'v' and suffixes like '-beta'
            version_clean = re.sub(r'^v?', '', version_str)
            version_clean = re.split(r'[-+]', version_clean)[0]
            
            # Split into numeric parts
            parts = []
            for part in version_clean.split('.'):
                try:
                    parts.append(int(part))
                except ValueError:
                    # Handle non-numeric parts
                    parts.append(0)
            
            return tuple(parts)
        except:
            return (0,)
    
    def _extract_github_url(self, project_urls: Dict[str, str], homepage: str) -> str:
        """Extract GitHub URL from project URLs or homepage"""
        github_patterns = [
            'Source', 'Repository', 'Homepage', 'Source Code', 'GitHub'
        ]
        
        for pattern in github_patterns:
            url = project_urls.get(pattern, '')
            if 'github.com' in url:
                return url
        
        if 'github.com' in homepage:
            return homepage
        
        return ''
    
    def _extract_github_url_from_npm(self, repository: Any) -> str:
        """Extract GitHub URL from NPM repository field"""
        if isinstance(repository, dict):
            url = repository.get('url', '')
        elif isinstance(repository, str):
            url = repository
        else:
            return ''
        
        # Clean up git+ prefix and .git suffix
        url = re.sub(r'^git\+', '', url)
        url = re.sub(r'\.git$', '', url)
        
        if 'github.com' in url:
            return url
        
        return ''
    
    def _parse_github_url(self, github_url: str) -> Tuple[str, str]:
        """Parse GitHub URL to extract owner and repo"""
        try:
            # Clean up URL
            url = github_url.replace('git+', '').replace('.git', '')
            parsed = urlparse(url)
            
            if parsed.hostname != 'github.com':
                return '', ''
            
            path_parts = parsed.path.strip('/').split('/')
            if len(path_parts) >= 2:
                return path_parts[0], path_parts[1]
            
            return '', ''
        except:
            return '', ''
    
    def _format_npm_author(self, author: Any) -> str:
        """Format NPM author field"""
        if isinstance(author, dict):
            name = author.get('name', '')
            email = author.get('email', '')
            return f"{name} <{email}>" if email else name
        elif isinstance(author, str):
            return author
        return ''
    
    async def _check_url_exists(self, url: str) -> bool:
        """Check if a URL exists and is accessible"""
        try:
            response = await self.client.head(url)
            return response.status_code == 200
        except:
            return False
    
    def _extract_section_content(self, section_element) -> str:
        """Extract content following a section header"""
        content = []
        current = section_element.next_sibling
        
        while current and current.name not in ['h1', 'h2', 'h3']:
            if hasattr(current, 'get_text'):
                text = current.get_text().strip()
                if text:
                    content.append(text)
            current = current.next_sibling
            
            if len(content) > 5:  # Limit content length
                break
        
        return '\n'.join(content[:3])  # Return first 3 paragraphs
    
    async def cleanup(self):
        """Clean up resources"""
        await self.client.aclose()