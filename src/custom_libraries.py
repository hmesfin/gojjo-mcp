"""
Custom Library Documentation Handler

Handles documentation for custom libraries like aida-permissions
that aren't available in public registries.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional

import httpx

logger = logging.getLogger(__name__)

class CustomLibraryHandler:
    """Handler for custom library documentation with GitHub integration"""
    
    def __init__(self, github_token: Optional[str] = None):
        self.github_token = github_token
        self.client = httpx.AsyncClient(timeout=30.0)
        
        # Configure GitHub API headers
        self.github_headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'django-vue-mcp-server/1.0.0'
        }
        
        if self.github_token:
            self.github_headers['Authorization'] = f'token {self.github_token}'
        
        # Custom library configurations
        self.custom_libraries = {
            'aida-permissions': {
                'github_repo': 'hmesfin/aida-permissions',  # Replace with actual repo
                'description': 'Advanced RBAC system for Django applications',
                'category': 'Authentication & Authorization',
                'docs_url': 'https://github.com/hmesfin/aida-permissions/wiki',
                'installation_method': 'pip install aida-permissions'
            }
        }
    
    async def get_github_repo_info(self, repo_path: str) -> Dict[str, str]:
        """Fetch repository information from GitHub"""
        try:
            url = f"https://api.github.com/repos/{repo_path}"
            response = await self.client.get(url, headers=self.github_headers)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'stars': str(data.get('stargazers_count', 0)),
                    'forks': str(data.get('forks_count', 0)),
                    'issues': str(data.get('open_issues_count', 0)),
                    'last_updated': data.get('updated_at', '').split('T')[0],
                    'default_branch': data.get('default_branch', 'main'),
                    'language': data.get('language', 'Python'),
                    'license': data.get('license', {}).get('name', 'Unknown') if data.get('license') else 'Unknown'
                }
            else:
                return {}
        except Exception as e:
            logger.error(f"Error fetching GitHub repo info for {repo_path}: {e}")
            return {}

    async def get_aida_permissions_docs(self) -> str:
        """Get documentation for the aida-permissions library"""
        try:
            # Fetch GitHub repository information if available
            config = self.custom_libraries.get('aida-permissions', {})
            repo_info = await self.get_github_repo_info(config.get('github_repo', ''))
            
            # Format repository stats if available
            repo_stats = ""
            if repo_info:
                repo_stats = f"""
**Repository Stats**:
- ⭐ Stars: {repo_info.get('stars', 'N/A')}
- 🍴 Forks: {repo_info.get('forks', 'N/A')} 
- 🐛 Open Issues: {repo_info.get('issues', 'N/A')}
- 📅 Last Updated: {repo_info.get('last_updated', 'N/A')}
- ⚖️ License: {repo_info.get('license', 'N/A')}
"""

            content = f"""# aida-permissions

**Version**: Latest (Custom Library)
**Type**: Custom RBAC (Role-Based Access Control) Library
**Category**: Django Authentication & Authorization
**Last Updated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{repo_stats}

## Overview

The `aida-permissions` library provides a comprehensive Role-Based Access Control (RBAC) system for Django applications. It extends Django's built-in permission system with advanced features for complex permission hierarchies and multi-tenant applications.

## Key Features

- **Hierarchical Roles**: Support for role inheritance and nested permissions
- **Multi-tenant Support**: Permissions scoped to organizations/tenants
- **Dynamic Permissions**: Runtime permission assignment and checking
- **API Integration**: RESTful endpoints for permission management
- **Audit Logging**: Track permission changes and access attempts

## Installation

Since this is a custom library, installation typically involves:

```bash
# Install from private PyPI or git repository
pip install aida-permissions

# Or install from source
git clone https://github.com/hmesfin/aida-permissions.git
cd aida-permissions
pip install -e .
```

## Django Settings Configuration

```python
# settings.py
INSTALLED_APPS = [
    # ... other apps
    'aida_permissions',
    'rest_framework',
]

# RBAC Configuration
AIDA_PERMISSIONS = {{
    'ENABLE_MULTI_TENANT': True,
    'DEFAULT_ROLE_HIERARCHY': True,
    'AUDIT_PERMISSIONS': True,
    'CACHE_PERMISSIONS': True,
    'CACHE_TIMEOUT': 3600,  # 1 hour
}}

# REST Framework Integration
REST_FRAMEWORK = {{
    'DEFAULT_PERMISSION_CLASSES': [
        'aida_permissions.permissions.RoleBasedPermission',
    ],
}}
```

## Basic Usage

### 1. Define Roles and Permissions

```python
# models.py
from aida_permissions.models import Role, Permission, UserRole

# Create roles
admin_role = Role.objects.create(
    name='admin',
    description='Administrator role with full access'
)

editor_role = Role.objects.create(
    name='editor', 
    description='Content editor role',
    parent=admin_role  # Inherits admin permissions
)

# Create permissions
view_perm = Permission.objects.create(
    codename='view_content',
    name='Can view content'
)

edit_perm = Permission.objects.create(
    codename='edit_content',
    name='Can edit content'
)

# Assign permissions to roles
admin_role.permissions.add(view_perm, edit_perm)
editor_role.permissions.add(view_perm)
```

### 2. Assign Roles to Users

```python
from aida_permissions.services import PermissionService

# Assign role to user
PermissionService.assign_role(
    user=user,
    role='admin',
    scope='organization:123'  # Optional: scope to organization
)

# Check user permissions
has_permission = PermissionService.check_permission(
    user=user,
    permission='edit_content',
    scope='organization:123'
)
```

### 3. Django Views Integration

```python
# views.py
from aida_permissions.decorators import require_permission
from aida_permissions.mixins import PermissionRequiredMixin

# Function-based view
@require_permission('edit_content')
def edit_content(request):
    # View logic here
    pass

# Class-based view
class ContentEditView(PermissionRequiredMixin, UpdateView):
    permission_required = 'edit_content'
    model = Content
    template_name = 'content/edit.html'
```

### 4. DRF API Views Integration

```python
# api/views.py
from aida_permissions.permissions import RoleBasedPermission
from rest_framework.viewsets import ModelViewSet

class ContentViewSet(ModelViewSet):
    queryset = Content.objects.all()
    serializer_class = ContentSerializer
    permission_classes = [RoleBasedPermission]
    
    # Define required permissions for each action
    permission_map = {{
        'list': ['view_content'],
        'retrieve': ['view_content'],
        'create': ['add_content'],
        'update': ['edit_content'],
        'destroy': ['delete_content'],
    }}
```

## Advanced Features

### Multi-Tenant Permissions

```python
# Scope permissions to organizations
PermissionService.assign_role(
    user=user,
    role='manager',
    scope='organization:acme_corp'
)

# Check scoped permissions
has_access = PermissionService.check_permission(
    user=user,
    permission='manage_team',
    scope='organization:acme_corp'
)
```

### Dynamic Permission Assignment

```python
# Runtime permission management
from aida_permissions.models import DynamicPermission

# Grant temporary permission
DynamicPermission.objects.create(
    user=user,
    permission='temporary_access',
    expires_at=timezone.now() + timedelta(hours=24),
    scope='project:urgent_task'
)
```

### Permission Hierarchy

```python
# Define role hierarchy
ceo_role = Role.objects.create(name='ceo')
manager_role = Role.objects.create(name='manager', parent=ceo_role)
employee_role = Role.objects.create(name='employee', parent=manager_role)

# CEO inherits all manager and employee permissions
# Manager inherits all employee permissions
```

## API Endpoints

### REST API for Permission Management

```python
# urls.py
from aida_permissions.api.urls import urlpatterns as permission_urls

urlpatterns = [
    path('api/permissions/', include(permission_urls)),
]
```

**Available Endpoints:**

- `GET /api/permissions/roles/` - List all roles
- `POST /api/permissions/roles/` - Create new role
- `GET /api/permissions/roles/{id}/` - Get role details
- `PUT /api/permissions/roles/{id}/` - Update role
- `DELETE /api/permissions/roles/{id}/` - Delete role
- `POST /api/permissions/users/{id}/assign-role/` - Assign role to user
- `POST /api/permissions/users/{id}/revoke-role/` - Revoke role from user
- `GET /api/permissions/users/{id}/permissions/` - Get user permissions

## Frontend Integration (Vue.js)

### 1. API Service

```javascript
// api/permissions.js
export const permissionsAPI = {{
  getUserPermissions: (userId) => 
    axios.get(`/api/permissions/users/${{userId}}/permissions/`),
    
  assignRole: (userId, roleData) =>
    axios.post(`/api/permissions/users/${{userId}}/assign-role/`, roleData),
    
  checkPermission: (permission, scope = null) =>
    axios.post('/api/permissions/check/', {{ permission, scope }})
}}
```

### 2. Vue.js Permission Composable

```javascript
// composables/usePermissions.js
import {{ ref, computed }} from 'vue'
import {{ useAuthStore }} from '@/stores/auth'

export function usePermissions() {{
  const authStore = useAuthStore()
  const permissions = ref([])
  
  const hasPermission = (permission, scope = null) => {{
    return permissions.value.some(p => 
      p.codename === permission && 
      (!scope || p.scope === scope)
    )
  }}
  
  const canAccess = computed(() => (permission, scope) => {{
    return hasPermission(permission, scope)
  }})
  
  return {{
    permissions,
    hasPermission,
    canAccess
  }}
}}
```

### 3. Vue.js Permission Directive

```javascript
// directives/permission.js
export default {{
  mounted(el, binding) {{
    const {{ permission, scope }} = binding.value
    const hasPermission = checkUserPermission(permission, scope)
    
    if (!hasPermission) {{
      el.style.display = 'none'
    }}
  }}
}}
```

## Testing

### Unit Tests

```python
# tests/test_permissions.py
from django.test import TestCase
from aida_permissions.services import PermissionService
from aida_permissions.models import Role, Permission

class PermissionServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('testuser')
        self.role = Role.objects.create(name='test_role')
        self.permission = Permission.objects.create(
            codename='test_permission'
        )
        self.role.permissions.add(self.permission)
    
    def test_assign_role(self):
        PermissionService.assign_role(self.user, 'test_role')
        self.assertTrue(
            PermissionService.check_permission(
                self.user, 'test_permission'
            )
        )
```

## Migration Guide

### From Django's Built-in Permissions

```python
# Migration script
from django.contrib.auth.models import Permission as DjangoPermission
from aida_permissions.models import Permission, Role

def migrate_permissions():
    # Convert Django permissions to aida-permissions
    for django_perm in DjangoPermission.objects.all():
        Permission.objects.get_or_create(
            codename=django_perm.codename,
            name=django_perm.name,
            content_type=django_perm.content_type
        )
```

## Performance Optimization

### Caching Strategy

```python
# settings.py
CACHES = {{
    'default': {{
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {{
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }}
    }}
}}

# Enable permission caching
AIDA_PERMISSIONS['CACHE_PERMISSIONS'] = True
```

## Troubleshooting

### Common Issues

1. **Permission Not Found**: Ensure permissions are properly created and assigned
2. **Scope Mismatch**: Verify scope strings match exactly
3. **Cache Issues**: Clear permission cache after role changes
4. **Performance**: Use select_related/prefetch_related for permission queries

### Debug Commands

```bash
# Check user permissions
python manage.py check_user_permissions <username>

# List all roles and permissions
python manage.py list_permissions

# Clear permission cache
python manage.py clear_permission_cache
```

## Documentation Links

- **Internal Docs**: Check your organization's internal documentation
- **GitHub Repository**: [Private repository link]
- **API Reference**: `/api/permissions/docs/`
- **Support**: Contact your development team for assistance

---

**Note**: This is a custom library specific to your organization. 
For the most up-to-date documentation, refer to your internal documentation system.
"""
            
            return content
            
        except Exception as e:
            logger.error(f"Error getting aida-permissions documentation: {e}")
            return f"Error retrieving aida-permissions documentation: {str(e)}"
    
    async def get_custom_library_info(self, library_name: str) -> str:
        """Get information for any custom library"""
        if library_name == 'aida-permissions':
            return await self.get_aida_permissions_docs()
        else:
            return f"Custom library '{library_name}' documentation not available."
    
    async def cleanup(self):
        """Clean up resources"""
        await self.client.aclose()