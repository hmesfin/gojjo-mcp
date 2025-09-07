"""
Input Validation System

Provides input sanitization to prevent injection attacks, SSRF protection,
and HTML sanitization for the MCP documentation server.
"""

import ipaddress
import re
import socket
import urllib.parse
from typing import Dict, List, Optional, Set, Tuple, Union
from urllib.parse import urlparse

import html
import bleach
from pydantic import BaseModel, validator


class ValidationResult(BaseModel):
    """Input validation result"""
    is_valid: bool
    cleaned_value: Optional[str] = None
    errors: List[str] = []
    warnings: List[str] = []


class SecurityConfig:
    """Security configuration constants"""
    
    # Allowed URL schemes
    ALLOWED_SCHEMES = {'http', 'https'}
    
    # Blocked domains and IPs for SSRF protection
    BLOCKED_DOMAINS = {
        'localhost',
        '127.0.0.1',
        '0.0.0.0',
        'metadata.google.internal',
        '169.254.169.254',  # AWS metadata
        '100.100.100.200',  # Alibaba Cloud metadata
    }
    
    # Private IP ranges to block
    PRIVATE_IP_RANGES = [
        '10.0.0.0/8',
        '172.16.0.0/12', 
        '192.168.0.0/16',
        '127.0.0.0/8',
        '169.254.0.0/16',  # Link-local
        'fc00::/7',        # IPv6 private
        '::1/128',         # IPv6 loopback
    ]
    
    # Allowed domains for external API calls
    ALLOWED_API_DOMAINS = {
        'pypi.org',
        'registry.npmjs.org',
        'api.github.com',
        'github.com',
        'raw.githubusercontent.com',
        'docs.djangoproject.com',
        'vuejs.org',
        'nodejs.org',
        'www.python.org'
    }
    
    # Maximum input lengths
    MAX_URL_LENGTH = 2048
    MAX_PACKAGE_NAME_LENGTH = 214  # NPM limit
    MAX_DESCRIPTION_LENGTH = 1000
    MAX_API_KEY_LENGTH = 128
    
    # Regex patterns
    PACKAGE_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9._@/-]+$')
    API_KEY_PATTERN = re.compile(r'^[a-zA-Z0-9_-]+$')
    VERSION_PATTERN = re.compile(r'^[0-9]+(\.[0-9]+)*([a-zA-Z0-9.-]+)?$')
    
    # HTML sanitization
    ALLOWED_HTML_TAGS = [
        'p', 'br', 'strong', 'em', 'u', 'code', 'pre',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'ul', 'ol', 'li', 'blockquote'
    ]
    
    ALLOWED_HTML_ATTRIBUTES = {
        '*': ['class'],
        'code': ['class'],
        'pre': ['class']
    }


class URLValidator:
    """URL validation and SSRF protection"""
    
    @staticmethod
    def is_private_ip(ip_str: str) -> bool:
        """Check if IP address is private/internal"""
        try:
            ip = ipaddress.ip_address(ip_str)
            
            # Check against private ranges
            for range_str in SecurityConfig.PRIVATE_IP_RANGES:
                if ip in ipaddress.ip_network(range_str):
                    return True
            
            return False
        except ValueError:
            return False
    
    @staticmethod
    def resolve_domain(domain: str) -> List[str]:
        """Resolve domain to IP addresses"""
        try:
            result = socket.getaddrinfo(domain, None)
            ips = list(set([addr[4][0] for addr in result]))
            return ips
        except socket.gaierror:
            return []
    
    @classmethod
    def validate_url(cls, url: str, allow_private: bool = False) -> ValidationResult:
        """Validate URL for SSRF protection"""
        errors = []
        warnings = []
        
        # Basic length check
        if len(url) > SecurityConfig.MAX_URL_LENGTH:
            errors.append(f"URL too long (max {SecurityConfig.MAX_URL_LENGTH} characters)")
            return ValidationResult(is_valid=False, errors=errors)
        
        try:
            parsed = urlparse(url)
        except Exception as e:
            errors.append(f"Invalid URL format: {str(e)}")
            return ValidationResult(is_valid=False, errors=errors)
        
        # Scheme validation
        if parsed.scheme not in SecurityConfig.ALLOWED_SCHEMES:
            errors.append(f"URL scheme not allowed: {parsed.scheme}")
        
        # Domain validation
        domain = parsed.hostname
        if not domain:
            errors.append("URL must have a valid hostname")
            return ValidationResult(is_valid=False, errors=errors)
        
        # Check blocked domains
        if domain.lower() in SecurityConfig.BLOCKED_DOMAINS:
            errors.append(f"Domain is blocked: {domain}")
        
        # For external API calls, check if domain is in allowed list
        if domain.lower() not in SecurityConfig.ALLOWED_API_DOMAINS:
            warnings.append(f"Domain not in allowed API list: {domain}")
        
        # DNS resolution and IP checking (if not allowing private IPs)
        if not allow_private:
            try:
                resolved_ips = cls.resolve_domain(domain)
                for ip in resolved_ips:
                    if cls.is_private_ip(ip):
                        errors.append(f"Domain resolves to private IP: {domain} -> {ip}")
            except Exception as e:
                warnings.append(f"Could not resolve domain {domain}: {str(e)}")
        
        # Check for suspicious patterns
        suspicious_patterns = [
            r'localhost',
            r'127\.0\.0\.1',
            r'0\.0\.0\.0',
            r'metadata',
            r'169\.254\.',
            r'::1',
            r'0:0:0:0:0:0:0:1'
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                errors.append(f"URL contains suspicious pattern: {pattern}")
        
        # Clean the URL
        cleaned_url = url.strip()
        
        # Ensure proper encoding
        try:
            cleaned_url = urllib.parse.quote(url, safe=':/?#[]@!$&\'()*+,;=')
        except Exception:
            errors.append("URL contains invalid characters")
        
        is_valid = len(errors) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            cleaned_value=cleaned_url if is_valid else None,
            errors=errors,
            warnings=warnings
        )


class InputSanitizer:
    """General input sanitization"""
    
    @staticmethod
    def sanitize_package_name(name: str) -> ValidationResult:
        """Sanitize and validate package names"""
        errors = []
        warnings = []
        
        if not name:
            errors.append("Package name cannot be empty")
            return ValidationResult(is_valid=False, errors=errors)
        
        # Length check
        if len(name) > SecurityConfig.MAX_PACKAGE_NAME_LENGTH:
            errors.append(f"Package name too long (max {SecurityConfig.MAX_PACKAGE_NAME_LENGTH} characters)")
        
        # Pattern check
        if not SecurityConfig.PACKAGE_NAME_PATTERN.match(name):
            errors.append("Package name contains invalid characters")
        
        # Clean the name
        cleaned_name = name.strip().lower()
        
        # Check for suspicious patterns
        suspicious_patterns = ['..', '__', 'admin', 'root', 'system']
        for pattern in suspicious_patterns:
            if pattern in cleaned_name:
                warnings.append(f"Package name contains suspicious pattern: {pattern}")
        
        is_valid = len(errors) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            cleaned_value=cleaned_name if is_valid else None,
            errors=errors,
            warnings=warnings
        )
    
    @staticmethod
    def sanitize_version(version: str) -> ValidationResult:
        """Sanitize and validate version strings"""
        errors = []
        
        if not version:
            errors.append("Version cannot be empty")
            return ValidationResult(is_valid=False, errors=errors)
        
        # Pattern check
        if not SecurityConfig.VERSION_PATTERN.match(version):
            errors.append("Invalid version format")
        
        # Clean the version
        cleaned_version = version.strip()
        
        is_valid = len(errors) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            cleaned_value=cleaned_version if is_valid else None,
            errors=errors
        )
    
    @staticmethod
    def sanitize_api_key(api_key: str) -> ValidationResult:
        """Sanitize and validate API keys"""
        errors = []
        warnings = []
        
        if not api_key:
            errors.append("API key cannot be empty")
            return ValidationResult(is_valid=False, errors=errors)
        
        # Length check
        if len(api_key) > SecurityConfig.MAX_API_KEY_LENGTH:
            errors.append(f"API key too long (max {SecurityConfig.MAX_API_KEY_LENGTH} characters)")
        
        # Pattern check
        if not SecurityConfig.API_KEY_PATTERN.match(api_key):
            errors.append("API key contains invalid characters")
        
        # Check for obvious test/dummy keys
        dummy_patterns = ['test', 'demo', 'example', '123456', 'abcdef']
        api_key_lower = api_key.lower()
        for pattern in dummy_patterns:
            if pattern in api_key_lower:
                warnings.append(f"API key appears to be a test/demo key")
        
        cleaned_key = api_key.strip()
        is_valid = len(errors) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            cleaned_value=cleaned_key if is_valid else None,
            errors=errors,
            warnings=warnings
        )
    
    @staticmethod
    def sanitize_html(html_content: str) -> ValidationResult:
        """Sanitize HTML content"""
        errors = []
        warnings = []
        
        if not html_content:
            return ValidationResult(is_valid=True, cleaned_value="")
        
        try:
            # Use bleach to sanitize HTML
            cleaned_html = bleach.clean(
                html_content,
                tags=SecurityConfig.ALLOWED_HTML_TAGS,
                attributes=SecurityConfig.ALLOWED_HTML_ATTRIBUTES,
                strip=True
            )
            
            # Check if content was modified
            if cleaned_html != html_content:
                warnings.append("HTML content was sanitized")
            
            return ValidationResult(
                is_valid=True,
                cleaned_value=cleaned_html,
                warnings=warnings
            )
            
        except Exception as e:
            errors.append(f"HTML sanitization error: {str(e)}")
            return ValidationResult(is_valid=False, errors=errors)
    
    @staticmethod
    def sanitize_text(text: str, max_length: Optional[int] = None) -> ValidationResult:
        """Sanitize plain text content"""
        errors = []
        warnings = []
        
        if not text:
            return ValidationResult(is_valid=True, cleaned_value="")
        
        # Length check
        if max_length and len(text) > max_length:
            errors.append(f"Text too long (max {max_length} characters)")
            return ValidationResult(is_valid=False, errors=errors)
        
        # HTML escape
        cleaned_text = html.escape(text.strip())
        
        # Check for suspicious patterns
        suspicious_patterns = [
            r'<script',
            r'javascript:',
            r'data:',
            r'vbscript:',
            r'on\w+\s*='
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                warnings.append(f"Text contains suspicious pattern: {pattern}")
        
        return ValidationResult(
            is_valid=True,
            cleaned_value=cleaned_text,
            warnings=warnings
        )


class RequestValidator:
    """HTTP request validation"""
    
    @staticmethod
    def validate_headers(headers: Dict[str, str]) -> ValidationResult:
        """Validate HTTP headers"""
        errors = []
        warnings = []
        cleaned_headers = {}
        
        for key, value in headers.items():
            # Validate header name
            if not re.match(r'^[a-zA-Z0-9_-]+$', key):
                warnings.append(f"Invalid header name: {key}")
                continue
            
            # Validate header value
            if len(value) > 8192:  # Max header value length
                errors.append(f"Header value too long: {key}")
                continue
            
            # Sanitize value
            cleaned_value = value.strip()
            
            # Check for injection attempts
            if any(char in cleaned_value for char in ['\r', '\n', '\0']):
                errors.append(f"Header contains invalid characters: {key}")
                continue
            
            cleaned_headers[key] = cleaned_value
        
        is_valid = len(errors) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            cleaned_value=cleaned_headers if is_valid else None,
            errors=errors,
            warnings=warnings
        )
    
    @staticmethod
    def validate_query_params(params: Dict[str, Union[str, List[str]]]) -> ValidationResult:
        """Validate query parameters"""
        errors = []
        warnings = []
        cleaned_params = {}
        
        for key, value in params.items():
            # Validate parameter name
            if not re.match(r'^[a-zA-Z0-9_-]+$', key):
                warnings.append(f"Invalid parameter name: {key}")
                continue
            
            if isinstance(value, list):
                cleaned_values = []
                for v in value:
                    if len(v) > 1024:  # Max param value length
                        errors.append(f"Parameter value too long: {key}")
                        continue
                    cleaned_values.append(html.escape(v.strip()))
                cleaned_params[key] = cleaned_values
            else:
                if len(value) > 1024:
                    errors.append(f"Parameter value too long: {key}")
                    continue
                cleaned_params[key] = html.escape(value.strip())
        
        is_valid = len(errors) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            cleaned_value=cleaned_params if is_valid else None,
            errors=errors,
            warnings=warnings
        )


class SecurityValidator:
    """Main security validation class"""
    
    def __init__(self):
        self.url_validator = URLValidator()
        self.input_sanitizer = InputSanitizer()
        self.request_validator = RequestValidator()
    
    def validate_external_url(self, url: str) -> ValidationResult:
        """Validate external URL for API calls"""
        return self.url_validator.validate_url(url, allow_private=False)
    
    def validate_package_request(self, package_name: str, version: Optional[str] = None) -> Dict[str, ValidationResult]:
        """Validate package documentation request"""
        results = {
            'package_name': self.input_sanitizer.sanitize_package_name(package_name)
        }
        
        if version:
            results['version'] = self.input_sanitizer.sanitize_version(version)
        
        return results
    
    def validate_api_request(
        self,
        headers: Dict[str, str],
        params: Dict[str, Union[str, List[str]]],
        body: Optional[str] = None
    ) -> Dict[str, ValidationResult]:
        """Validate complete API request"""
        results = {
            'headers': self.request_validator.validate_headers(headers),
            'params': self.request_validator.validate_query_params(params)
        }
        
        if body:
            results['body'] = self.input_sanitizer.sanitize_text(
                body, 
                max_length=SecurityConfig.MAX_DESCRIPTION_LENGTH
            )
        
        return results
    
    def is_request_valid(self, validation_results: Dict[str, ValidationResult]) -> Tuple[bool, List[str]]:
        """Check if all validation results are valid"""
        all_errors = []
        
        for key, result in validation_results.items():
            if not result.is_valid:
                all_errors.extend([f"{key}: {error}" for error in result.errors])
        
        return len(all_errors) == 0, all_errors


# Utility functions
def validate_and_clean_url(url: str) -> str:
    """Quick URL validation and cleaning"""
    result = URLValidator.validate_url(url)
    if not result.is_valid:
        raise ValueError(f"Invalid URL: {', '.join(result.errors)}")
    return result.cleaned_value


def validate_package_name(name: str) -> str:
    """Quick package name validation"""
    result = InputSanitizer.sanitize_package_name(name)
    if not result.is_valid:
        raise ValueError(f"Invalid package name: {', '.join(result.errors)}")
    return result.cleaned_value


def create_security_headers() -> Dict[str, str]:
    """Create standard security headers"""
    return {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'Content-Security-Policy': "default-src 'self'; script-src 'none'; object-src 'none';",
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        'Permissions-Policy': 'geolocation=(), microphone=(), camera=()'
    }