"""
Integration Examples Generator

This module generates comprehensive integration examples between Django and Vue.js,
including authentication patterns, API integration, deployment configurations,
and best practices.
"""

import logging
from datetime import datetime
from typing import Dict, List, Any
import json

logger = logging.getLogger(__name__)

class IntegrationExamplesGenerator:
    """Generates dynamic integration examples based on current best practices"""
    
    def __init__(self):
        self.django_version = "4.2+"
        self.vue_version = "3.x"
        self.drf_version = "3.14+"
        
    def generate_auth_integration(self) -> str:
        """Generate JWT authentication integration example"""
        return f"""# Django + Vue.js JWT Authentication Integration

**Last Updated**: {datetime.now().strftime('%Y-%m-%d')}
**Django Version**: {self.django_version}
**Vue Version**: {self.vue_version}
**DRF Version**: {self.drf_version}

## Backend Setup (Django + DRF)

### 1. Install Dependencies

```bash
pip install djangorestframework==3.14.0
pip install djangorestframework-simplejwt==5.3.0
pip install django-cors-headers==4.3.1
```

### 2. Django Settings Configuration

```python
# settings.py
from datetime import timedelta

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    
    # Local apps
    'accounts',
    'api',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# REST Framework configuration
REST_FRAMEWORK = {{
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20
}}

# JWT Configuration
SIMPLE_JWT = {{
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': False,
    
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    'JSON_ENCODER': None,
    'JWK_URL': None,
    'LEEWAY': 0,
    
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',
    
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'TOKEN_USER_CLASS': 'rest_framework_simplejwt.models.TokenUser',
    
    'JTI_CLAIM': 'jti',
}}

# CORS settings for Vue.js frontend
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",  # Vue dev server
    "http://127.0.0.1:3000",
    "http://localhost:5173",  # Vite dev server
    "http://127.0.0.1:5173",
]

CORS_ALLOW_CREDENTIALS = True
```

### 3. Custom JWT Views

```python
# views.py
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import get_user_model

User = get_user_model()

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        
        # Add custom claims
        token['username'] = user.username
        token['email'] = user.email
        token['is_staff'] = user.is_staff
        token['is_superuser'] = user.is_superuser
        
        return token

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    username = request.data.get('username')
    password = request.data.get('password')
    email = request.data.get('email')
    
    if not username or not password:
        return Response(
            {{'error': 'Username and password are required'}},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        user = User.objects.create_user(
            username=username,
            password=password,
            email=email
        )
        return Response(
            {{'message': 'User created successfully'}},
            status=status.HTTP_201_CREATED
        )
    except Exception as e:
        return Response(
            {{'error': str(e)}},
            status=status.HTTP_400_BAD_REQUEST
        )

@api_view(['GET'])
def get_user_profile(request):
    user = request.user
    return Response({{
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'is_staff': user.is_staff,
        'is_superuser': user.is_superuser,
        'date_joined': user.date_joined,
    }})
```

### 4. URL Configuration

```python
# urls.py
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenRefreshView,
    TokenVerifyView,
)
from .views import CustomTokenObtainPairView, register_user, get_user_profile

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('api/auth/register/', register_user, name='register'),
    path('api/user/profile/', get_user_profile, name='user_profile'),
]
```

## Frontend Setup (Vue.js 3 + Composition API)

### 1. Install Dependencies

```bash
npm install axios@1.5.0
npm install pinia@2.1.6
npm install @vueuse/core@10.4.1
```

### 2. Axios Configuration

```javascript
// src/plugins/axios.js
import axios from 'axios'
import {{ useAuthStore }} from '@/stores/auth'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({{
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {{
    'Content-Type': 'application/json',
  }},
}})

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {{
    const authStore = useAuthStore()
    const token = authStore.accessToken
    
    if (token) {{
      config.headers.Authorization = `Bearer ${{token}}`
    }}
    
    return config
  }},
  (error) => {{
    return Promise.reject(error)
  }}
)

// Response interceptor to handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {{
    const originalRequest = error.config
    
    if (error.response?.status === 401 && !originalRequest._retry) {{
      originalRequest._retry = true
      
      const authStore = useAuthStore()
      const refreshToken = authStore.refreshToken
      
      if (refreshToken) {{
        try {{
          const response = await axios.post(`${{API_BASE_URL}}/api/auth/refresh/`, {{
            refresh: refreshToken
          }})
          
          const {{ access }} = response.data
          authStore.setTokens(access, refreshToken)
          
          // Retry original request with new token
          originalRequest.headers.Authorization = `Bearer ${{access}}`
          return api(originalRequest)
        }} catch (refreshError) {{
          // Refresh failed, logout user
          authStore.logout()
          return Promise.reject(refreshError)
        }}
      }}
    }}
    
    return Promise.reject(error)
  }}
)

export default api
```

### 3. Authentication Store (Pinia)

```javascript
// src/stores/auth.js
import {{ defineStore }} from 'pinia'
import {{ computed, ref }} from 'vue'
import api from '@/plugins/axios'

export const useAuthStore = defineStore('auth', () => {{
  // State
  const accessToken = ref(localStorage.getItem('access_token'))
  const refreshToken = ref(localStorage.getItem('refresh_token'))
  const user = ref(null)
  const loading = ref(false)
  const error = ref(null)
  
  // Getters
  const isAuthenticated = computed(() => !!accessToken.value)
  const isStaff = computed(() => user.value?.is_staff || false)
  const isSuperuser = computed(() => user.value?.is_superuser || false)
  
  // Actions
  const setTokens = (access, refresh) => {{
    accessToken.value = access
    refreshToken.value = refresh
    localStorage.setItem('access_token', access)
    localStorage.setItem('refresh_token', refresh)
  }}
  
  const clearTokens = () => {{
    accessToken.value = null
    refreshToken.value = null
    user.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }}
  
  const login = async (credentials) => {{
    loading.value = true
    error.value = null
    
    try {{
      const response = await api.post('/api/auth/login/', credentials)
      const {{ access, refresh }} = response.data
      
      setTokens(access, refresh)
      await fetchUserProfile()
      
      return {{ success: true }}
    }} catch (err) {{
      error.value = err.response?.data?.detail || 'Login failed'
      return {{ success: false, error: error.value }}
    }} finally {{
      loading.value = false
    }}
  }}
  
  const register = async (userData) => {{
    loading.value = true
    error.value = null
    
    try {{
      await api.post('/api/auth/register/', userData)
      return {{ success: true }}
    }} catch (err) {{
      error.value = err.response?.data?.error || 'Registration failed'
      return {{ success: false, error: error.value }}
    }} finally {{
      loading.value = false
    }}
  }}
  
  const logout = () => {{
    clearTokens()
  }}
  
  const fetchUserProfile = async () => {{
    if (!accessToken.value) return
    
    try {{
      const response = await api.get('/api/user/profile/')
      user.value = response.data
    }} catch (err) {{
      console.error('Failed to fetch user profile:', err)
      if (err.response?.status === 401) {{
        logout()
      }}
    }}
  }}
  
  const verifyToken = async () => {{
    if (!accessToken.value) return false
    
    try {{
      await api.post('/api/auth/verify/', {{ token: accessToken.value }})
      return true
    }} catch (err) {{
      return false
    }}
  }}
  
  return {{
    // State
    accessToken,
    refreshToken,
    user,
    loading,
    error,
    
    // Getters
    isAuthenticated,
    isStaff,
    isSuperuser,
    
    // Actions
    login,
    register,
    logout,
    fetchUserProfile,
    verifyToken,
    setTokens,
    clearTokens,
  }}
}})
```

### 4. Authentication Composable

```javascript
// src/composables/useAuth.js
import {{ useAuthStore }} from '@/stores/auth'
import {{ useRouter }} from 'vue-router'
import {{ computed, onMounted }} from 'vue'

export function useAuth() {{
  const authStore = useAuthStore()
  const router = useRouter()
  
  const isAuthenticated = computed(() => authStore.isAuthenticated)
  const user = computed(() => authStore.user)
  const loading = computed(() => authStore.loading)
  const error = computed(() => authStore.error)
  
  const login = async (credentials) => {{
    const result = await authStore.login(credentials)
    if (result.success) {{
      router.push('/dashboard')
    }}
    return result
  }}
  
  const register = async (userData) => {{
    const result = await authStore.register(userData)
    if (result.success) {{
      router.push('/login')
    }}
    return result
  }}
  
  const logout = () => {{
    authStore.logout()
    router.push('/login')
  }}
  
  const requireAuth = () => {{
    if (!isAuthenticated.value) {{
      router.push('/login')
      return false
    }}
    return true
  }}
  
  // Initialize auth on mount
  onMounted(async () => {{
    if (authStore.accessToken) {{
      const isValid = await authStore.verifyToken()
      if (isValid) {{
        await authStore.fetchUserProfile()
      }} else {{
        authStore.logout()
      }}
    }}
  }})
  
  return {{
    isAuthenticated,
    user,
    loading,
    error,
    login,
    register,
    logout,
    requireAuth,
  }}
}}
```

### 5. Login Component Example

```vue
<!-- src/components/LoginForm.vue -->
<template>
  <div class="login-form">
    <form @submit.prevent="handleLogin" class="space-y-4">
      <div>
        <label for="username" class="block text-sm font-medium text-gray-700">
          Username
        </label>
        <input
          id="username"
          v-model="credentials.username"
          type="text"
          required
          class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
          :disabled="loading"
        />
      </div>
      
      <div>
        <label for="password" class="block text-sm font-medium text-gray-700">
          Password
        </label>
        <input
          id="password"
          v-model="credentials.password"
          type="password"
          required
          class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
          :disabled="loading"
        />
      </div>
      
      <div v-if="error" class="text-red-600 text-sm">
        {{ error }}
      </div>
      
      <button
        type="submit"
        :disabled="loading"
        class="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
      >
        <span v-if="loading">Logging in...</span>
        <span v-else>Log in</span>
      </button>
    </form>
  </div>
</template>

<script setup>
import {{ ref }} from 'vue'
import {{ useAuth }} from '@/composables/useAuth'

const {{ login, loading, error }} = useAuth()

const credentials = ref({{
  username: '',
  password: ''
}})

const handleLogin = async () => {{
  await login(credentials.value)
}}
</script>
```

### 6. Route Guards

```javascript
// src/router/guards.js
import {{ useAuthStore }} from '@/stores/auth'

export const authGuard = (to, from, next) => {{
  const authStore = useAuthStore()
  
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {{
    next('/login')
  }} else if (to.meta.requiresGuest && authStore.isAuthenticated) {{
    next('/dashboard')
  }} else if (to.meta.requiresStaff && !authStore.isStaff) {{
    next('/unauthorized')
  }} else {{
    next()
  }}
}}

// src/router/index.js
import {{ createRouter, createWebHistory }} from 'vue-router'
import {{ authGuard }} from './guards'

const routes = [
  {{
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: {{ requiresGuest: true }}
  }},
  {{
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('@/views/Dashboard.vue'),
    meta: {{ requiresAuth: true }}
  }},
  {{
    path: '/admin',
    name: 'Admin',
    component: () => import('@/views/Admin.vue'),
    meta: {{ requiresAuth: true, requiresStaff: true }}
  }}
]

const router = createRouter({{
  history: createWebHistory(),
  routes
}})

router.beforeEach(authGuard)

export default router
```

## Environment Configuration

### Backend (.env)
```bash
SECRET_KEY=your-very-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DATABASE_URL=sqlite:///db.sqlite3

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

### Frontend (.env)
```bash
VITE_API_URL=http://localhost:8000
VITE_APP_NAME=Django Vue App
```

## Testing the Integration

### Backend Tests
```python
# tests/test_auth.py
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

User = get_user_model()

class AuthenticationTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
    
    def test_login_success(self):
        response = self.client.post(reverse('token_obtain_pair'), {{
            'username': 'testuser',
            'password': 'testpass123'
        }})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
    
    def test_token_refresh(self):
        # First, get tokens
        login_response = self.client.post(reverse('token_obtain_pair'), {{
            'username': 'testuser',
            'password': 'testpass123'
        }})
        refresh_token = login_response.data['refresh']
        
        # Then, refresh
        refresh_response = self.client.post(reverse('token_refresh'), {{
            'refresh': refresh_token
        }})
        self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)
        self.assertIn('access', refresh_response.data)
```

### Frontend Tests
```javascript
// tests/auth.test.js
import {{ describe, it, expect, beforeEach, vi }} from 'vitest'
import {{ setActivePinia, createPinia }} from 'pinia'
import {{ useAuthStore }} from '@/stores/auth'

// Mock axios
vi.mock('@/plugins/axios', () => ({{
  default: {{
    post: vi.fn(),
    get: vi.fn(),
  }}
}}))

describe('Auth Store', () => {{
  beforeEach(() => {{
    setActivePinia(createPinia())
  }})
  
  it('should login successfully', async () => {{
    const authStore = useAuthStore()
    
    // Mock successful login response
    const mockApi = await import('@/plugins/axios')
    mockApi.default.post.mockResolvedValue({{
      data: {{
        access: 'fake-access-token',
        refresh: 'fake-refresh-token'
      }}
    }})
    
    const result = await authStore.login({{
      username: 'testuser',
      password: 'testpass'
    }})
    
    expect(result.success).toBe(true)
    expect(authStore.accessToken).toBe('fake-access-token')
    expect(authStore.isAuthenticated).toBe(true)
  }})
  
  it('should handle login failure', async () => {{
    const authStore = useAuthStore()
    
    const mockApi = await import('@/plugins/axios')
    mockApi.default.post.mockRejectedValue({{
      response: {{
        data: {{ detail: 'Invalid credentials' }}
      }}
    }})
    
    const result = await authStore.login({{
      username: 'wronguser',
      password: 'wrongpass'
    }})
    
    expect(result.success).toBe(false)
    expect(result.error).toBe('Invalid credentials')
    expect(authStore.isAuthenticated).toBe(false)
  }})
}})
```

## Security Best Practices

1. **Token Storage**: Store tokens in localStorage with proper error handling
2. **HTTPS Only**: Always use HTTPS in production
3. **Token Expiration**: Implement proper token refresh logic
4. **CORS Configuration**: Restrict CORS origins to your domains
5. **Rate Limiting**: Implement rate limiting on auth endpoints
6. **Input Validation**: Validate all inputs on both frontend and backend
7. **Error Handling**: Don't expose sensitive information in error messages

## Deployment Considerations

- Use environment variables for all configuration
- Set up proper logging for authentication events
- Implement monitoring for failed login attempts
- Use secure session storage in production
- Set up proper backup strategies for user data

This integration provides a robust, production-ready authentication system between Django and Vue.js using JWT tokens with automatic refresh capabilities.
"""
    
    def generate_api_integration(self) -> str:
        """Generate API integration example"""
        return f"""# Django + Vue.js API Integration

**Last Updated**: {datetime.now().strftime('%Y-%m-%d')}
**Focus**: RESTful API patterns, CRUD operations, and real-time features

## Backend API Structure (Django REST Framework)

### 1. Model and Serializer Setup

```python
# models.py
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "categories"
    
    def __str__(self):
        return self.name

class Product(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ]
    
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name

# serializers.py
from rest_framework import serializers
from .models import Category, Product

class CategorySerializer(serializers.ModelSerializer):
    product_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'product_count', 'created_at', 'updated_at']
    
    def get_product_count(self, obj):
        return obj.product_set.count()

class ProductListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'price', 'status', 'category', 'category_name',
            'created_by', 'created_by_username', 'created_at', 'updated_at'
        ]

class ProductDetailSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    category_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'price', 'status', 
            'category', 'category_id', 'created_by', 'created_at', 'updated_at'
        ]
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)
```

### 2. ViewSets with Advanced Features

```python
# views.py
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from .models import Category, Product
from .serializers import CategorySerializer, ProductListSerializer, ProductDetailSerializer

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    @action(detail=True, methods=['get'])
    def products(self, request, pk=None):
        {{\"\"\"Get all products in this category\"\"\"}}
        category = self.get_object()
        products = Product.objects.filter(category=category)
        serializer = ProductListSerializer(products, many=True)
        return Response(serializer.data)

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.select_related('category', 'created_by')
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'category', 'created_by']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'price', 'created_at']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action in ['list']:
            return ProductListSerializer
        return ProductDetailSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by price range
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def my_products(self, request):
        {{\"\"\"Get current user's products\"\"\"}}
        products = self.queryset.filter(created_by=request.user)
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        {{\"\"\"Publish a product\"\"\"}}
        product = self.get_object()
        product.status = 'published'
        product.save()
        return Response({{'message': 'Product published successfully'}})
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        {{\"\"\"Get product statistics\"\"\"}}
        total_products = self.queryset.count()
        published_products = self.queryset.filter(status='published').count()
        draft_products = self.queryset.filter(status='draft').count()
        
        return Response({{
            'total': total_products,
            'published': published_products,
            'draft': draft_products,
            'published_percentage': (published_products / total_products * 100) if total_products > 0 else 0
        }})

# urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'categories', views.CategoryViewSet)
router.register(r'products', views.ProductViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
]
```

## Frontend API Integration (Vue.js 3)

### 1. API Client Service

```javascript
// src/services/api.js
import axios from '@/plugins/axios'

class APIService {{
  constructor(endpoint) {{
    this.endpoint = endpoint
  }}
  
  // Generic CRUD methods
  async list(params = {{}}) {{
    const response = await axios.get(`/api/${{this.endpoint}}/`, {{ params }})
    return response.data
  }}
  
  async get(id) {{
    const response = await axios.get(`/api/${{this.endpoint}}/${{id}}/`)
    return response.data
  }}
  
  async create(data) {{
    const response = await axios.post(`/api/${{this.endpoint}}/`, data)
    return response.data
  }}
  
  async update(id, data) {{
    const response = await axios.put(`/api/${{this.endpoint}}/${{id}}/`, data)
    return response.data
  }}
  
  async patch(id, data) {{
    const response = await axios.patch(`/api/${{this.endpoint}}/${{id}}/`, data)
    return response.data
  }}
  
  async delete(id) {{
    await axios.delete(`/api/${{this.endpoint}}/${{id}}/`)
  }}
  
  // Custom action
  async action(id, actionName, data = {{}}) {{
    const url = id 
      ? `/api/${{this.endpoint}}/${{id}}/${{actionName}}/`
      : `/api/${{this.endpoint}}/${{actionName}}/`
    const response = await axios.post(url, data)
    return response.data
  }}
}}

// Specific API services
export const categoriesAPI = new APIService('categories')
export const productsAPI = new APIService('products')

// Extended product API with custom methods
export const productAPI = {{
  ...productsAPI,
  
  // Get products with advanced filtering
  async getFiltered(filters) {{
    const params = new URLSearchParams()
    
    Object.entries(filters).forEach(([key, value]) => {{
      if (value !== null && value !== undefined && value !== '') {{
        params.append(key, value)
      }}
    }})
    
    const response = await axios.get(`/api/products/?${{params}}`)
    return response.data
  }},
  
  // Get user's products
  async getMyProducts() {{
    const response = await axios.get('/api/products/my_products/')
    return response.data
  }},
  
  // Publish product
  async publish(id) {{
    const response = await axios.post(`/api/products/${{id}}/publish/`)
    return response.data
  }},
  
  // Get statistics
  async getStatistics() {{
    const response = await axios.get('/api/products/statistics/')
    return response.data
  }},
  
  // Bulk operations
  async bulkDelete(ids) {{
    const response = await axios.post('/api/products/bulk_delete/', {{ ids }})
    return response.data
  }},
  
  // Search products
  async search(query) {{
    const response = await axios.get('/api/products/', {{
      params: {{ search: query }}
    }})
    return response.data
  }}
}}
```

### 2. Pinia Store for State Management

```javascript
// src/stores/products.js
import {{ defineStore }} from 'pinia'
import {{ ref, computed }} from 'vue'
import {{ productAPI, categoriesAPI }} from '@/services/api'

export const useProductStore = defineStore('products', () => {{
  // State
  const products = ref([])
  const categories = ref([])
  const currentProduct = ref(null)
  const loading = ref(false)
  const error = ref(null)
  const pagination = ref({{
    page: 1,
    pageSize: 20,
    total: 0,
    totalPages: 0
  }})
  const filters = ref({{
    search: '',
    category: null,
    status: '',
    min_price: null,
    max_price: null,
    ordering: '-created_at'
  }})
  
  // Getters
  const publishedProducts = computed(() => 
    products.value.filter(p => p.status === 'published')
  )
  
  const draftProducts = computed(() => 
    products.value.filter(p => p.status === 'draft')
  )
  
  const productsByCategory = computed(() => {{
    const grouped = {{}}
    products.value.forEach(product => {{
      const categoryName = product.category_name
      if (!grouped[categoryName]) {{
        grouped[categoryName] = []
      }}
      grouped[categoryName].push(product)
    }})
    return grouped
  }})
  
  // Actions
  const fetchProducts = async (params = {{}}) => {{
    loading.value = true
    error.value = null
    
    try {{
      const queryParams = {{ ...filters.value, ...params }}
      const response = await productAPI.getFiltered(queryParams)
      
      products.value = response.results || response
      
      if (response.count !== undefined) {{
        pagination.value.total = response.count
        pagination.value.totalPages = Math.ceil(response.count / pagination.value.pageSize)
      }}
    }} catch (err) {{
      error.value = err.message || 'Failed to fetch products'
      console.error('Error fetching products:', err)
    }} finally {{
      loading.value = false
    }}
  }}
  
  const fetchProduct = async (id) => {{
    loading.value = true
    error.value = null
    
    try {{
      const product = await productAPI.get(id)
      currentProduct.value = product
      return product
    }} catch (err) {{
      error.value = err.message || 'Failed to fetch product'
      throw err
    }} finally {{
      loading.value = false
    }}
  }}
  
  const createProduct = async (productData) => {{
    loading.value = true
    error.value = null
    
    try {{
      const newProduct = await productAPI.create(productData)
      products.value.unshift(newProduct)
      return newProduct
    }} catch (err) {{
      error.value = err.message || 'Failed to create product'
      throw err
    }} finally {{
      loading.value = false
    }}
  }}
  
  const updateProduct = async (id, productData) => {{
    loading.value = true
    error.value = null
    
    try {{
      const updatedProduct = await productAPI.update(id, productData)
      const index = products.value.findIndex(p => p.id === id)
      if (index !== -1) {{
        products.value[index] = updatedProduct
      }}
      if (currentProduct.value?.id === id) {{
        currentProduct.value = updatedProduct
      }}
      return updatedProduct
    }} catch (err) {{
      error.value = err.message || 'Failed to update product'
      throw err
    }} finally {{
      loading.value = false
    }}
  }}
  
  const deleteProduct = async (id) => {{
    loading.value = true
    error.value = null
    
    try {{
      await productAPI.delete(id)
      products.value = products.value.filter(p => p.id !== id)
      if (currentProduct.value?.id === id) {{
        currentProduct.value = null
      }}
    }} catch (err) {{
      error.value = err.message || 'Failed to delete product'
      throw err
    }} finally {{
      loading.value = false
    }}
  }}
  
  const publishProduct = async (id) => {{
    try {{
      await productAPI.publish(id)
      const index = products.value.findIndex(p => p.id === id)
      if (index !== -1) {{
        products.value[index].status = 'published'
      }}
    }} catch (err) {{
      error.value = err.message || 'Failed to publish product'
      throw err
    }}
  }}
  
  const fetchCategories = async () => {{
    try {{
      categories.value = await categoriesAPI.list()
    }} catch (err) {{
      console.error('Error fetching categories:', err)
    }}
  }}
  
  const setFilter = (key, value) => {{
    filters.value[key] = value
    fetchProducts()
  }}
  
  const clearFilters = () => {{
    filters.value = {{
      search: '',
      category: null,
      status: '',
      min_price: null,
      max_price: null,
      ordering: '-created_at'
    }}
    fetchProducts()
  }}
  
  const setPage = (page) => {{
    pagination.value.page = page
    fetchProducts({{ page }})
  }}
  
  return {{
    // State
    products,
    categories,
    currentProduct,
    loading,
    error,
    pagination,
    filters,
    
    // Getters
    publishedProducts,
    draftProducts,
    productsByCategory,
    
    // Actions
    fetchProducts,
    fetchProduct,
    createProduct,
    updateProduct,
    deleteProduct,
    publishProduct,
    fetchCategories,
    setFilter,
    clearFilters,
    setPage,
  }}
}})
```

### 3. Vue Components

```vue
<!-- src/components/ProductList.vue -->
<template>
  <div class="product-list">
    <!-- Filters -->
    <div class="filters mb-6 p-4 bg-gray-50 rounded-lg">
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div>
          <label class="block text-sm font-medium text-gray-700">Search</label>
          <input
            v-model="searchQuery"
            @input="debouncedSearch"
            type="text"
            placeholder="Search products..."
            class="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
          />
        </div>
        
        <div>
          <label class="block text-sm font-medium text-gray-700">Category</label>
          <select
            v-model="selectedCategory"
            @change="handleCategoryChange"
            class="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
          >
            <option value="">All Categories</option>
            <option v-for="category in categories" :key="category.id" :value="category.id">
              {{ category.name }}
            </option>
          </select>
        </div>
        
        <div>
          <label class="block text-sm font-medium text-gray-700">Status</label>
          <select
            v-model="selectedStatus"
            @change="handleStatusChange"
            class="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
          >
            <option value="">All Status</option>
            <option value="published">Published</option>
            <option value="draft">Draft</option>
            <option value="archived">Archived</option>
          </select>
        </div>
        
        <div>
          <label class="block text-sm font-medium text-gray-700">Sort By</label>
          <select
            v-model="selectedOrdering"
            @change="handleOrderingChange"
            class="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
          >
            <option value="-created_at">Newest First</option>
            <option value="created_at">Oldest First</option>
            <option value="name">Name A-Z</option>
            <option value="-name">Name Z-A</option>
            <option value="price">Price Low-High</option>
            <option value="-price">Price High-Low</option>
          </select>
        </div>
      </div>
      
      <div class="mt-4 flex justify-between items-center">
        <button
          @click="clearAllFilters"
          class="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
        >
          Clear Filters
        </button>
        
        <div class="text-sm text-gray-600">
          {{ pagination.total }} products found
        </div>
      </div>
    </div>
    
    <!-- Loading State -->
    <div v-if="loading" class="text-center py-8">
      <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
      <p class="mt-2 text-gray-600">Loading products...</p>
    </div>
    
    <!-- Error State -->
    <div v-else-if="error" class="text-center py-8">
      <div class="text-red-600 mb-4">{{ error }}</div>
      <button
        @click="retryFetch"
        class="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700"
      >
        Retry
      </button>
    </div>
    
    <!-- Products Grid -->
    <div v-else-if="products.length > 0" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <div
        v-for="product in products"
        :key="product.id"
        class="bg-white rounded-lg shadow-md overflow-hidden hover:shadow-lg transition-shadow"
      >
        <div class="p-6">
          <div class="flex justify-between items-start mb-2">
            <h3 class="text-lg font-semibold text-gray-900">{{ product.name }}</h3>
            <span
              :class="getStatusClass(product.status)"
              class="px-2 py-1 text-xs rounded-full"
            >
              {{ product.status }}
            </span>
          </div>
          
          <p class="text-gray-600 text-sm mb-4">{{ product.category_name }}</p>
          
          <div class="flex justify-between items-center">
            <span class="text-2xl font-bold text-indigo-600">
              ${{ parseFloat(product.price).toFixed(2) }}
            </span>
            
            <div class="flex space-x-2">
              <button
                @click="viewProduct(product.id)"
                class="px-3 py-1 text-sm bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
              >
                View
              </button>
              <button
                @click="editProduct(product.id)"
                class="px-3 py-1 text-sm bg-indigo-100 text-indigo-700 rounded hover:bg-indigo-200"
              >
                Edit
              </button>
              <button
                v-if="product.status === 'draft'"
                @click="publishProduct(product.id)"
                class="px-3 py-1 text-sm bg-green-100 text-green-700 rounded hover:bg-green-200"
              >
                Publish
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Empty State -->
    <div v-else class="text-center py-12">
      <div class="text-gray-500 mb-4">No products found</div>
      <button
        @click="$router.push('/products/new')"
        class="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700"
      >
        Create First Product
      </button>
    </div>
    
    <!-- Pagination -->
    <div v-if="pagination.totalPages > 1" class="mt-8 flex justify-center">
      <nav class="flex items-center space-x-2">
        <button
          @click="goToPage(pagination.page - 1)"
          :disabled="pagination.page <= 1"
          class="px-3 py-2 text-sm bg-gray-100 text-gray-700 rounded disabled:opacity-50"
        >
          Previous
        </button>
        
        <span class="px-3 py-2 text-sm text-gray-700">
          Page {{ pagination.page }} of {{ pagination.totalPages }}
        </span>
        
        <button
          @click="goToPage(pagination.page + 1)"
          :disabled="pagination.page >= pagination.totalPages"
          class="px-3 py-2 text-sm bg-gray-100 text-gray-700 rounded disabled:opacity-50"
        >
          Next
        </button>
      </nav>
    </div>
  </div>
</template>

<script setup>
import {{ ref, computed, onMounted, watch }} from 'vue'
import {{ useRouter }} from 'vue-router'
import {{ useProductStore }} from '@/stores/products'
import {{ debounce }} from '@/utils/debounce'

const router = useRouter()
const productStore = useProductStore()

// Reactive references to store state
const {{ products, categories, loading, error, pagination }} = productStore
const searchQuery = ref('')
const selectedCategory = ref('')
const selectedStatus = ref('')
const selectedOrdering = ref('-created_at')

// Computed
const getStatusClass = (status) => {{
  const classes = {{
    'published': 'bg-green-100 text-green-800',
    'draft': 'bg-yellow-100 text-yellow-800',
    'archived': 'bg-gray-100 text-gray-800'
  }}
  return classes[status] || 'bg-gray-100 text-gray-800'
}}

// Methods
const debouncedSearch = debounce(() => {{
  productStore.setFilter('search', searchQuery.value)
}}, 300)

const handleCategoryChange = () => {{
  productStore.setFilter('category', selectedCategory.value || null)
}}

const handleStatusChange = () => {{
  productStore.setFilter('status', selectedStatus.value)
}}

const handleOrderingChange = () => {{
  productStore.setFilter('ordering', selectedOrdering.value)
}}

const clearAllFilters = () => {{
  searchQuery.value = ''
  selectedCategory.value = ''
  selectedStatus.value = ''
  selectedOrdering.value = '-created_at'
  productStore.clearFilters()
}}

const viewProduct = (id) => {{
  router.push(`/products/${{id}}`)
}}

const editProduct = (id) => {{
  router.push(`/products/${{id}}/edit`)
}}

const publishProduct = async (id) => {{
  try {{
    await productStore.publishProduct(id)
  }} catch (error) {{
    console.error('Failed to publish product:', error)
  }}
}}

const goToPage = (page) => {{
  productStore.setPage(page)
}}

const retryFetch = () => {{
  productStore.fetchProducts()
}}

// Lifecycle
onMounted(async () => {{
  await productStore.fetchCategories()
  await productStore.fetchProducts()
}})
</script>
```

## Real-time Features with WebSockets

### Backend WebSocket Setup
```python
# consumers.py (Django Channels)
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Product

class ProductConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add("products", self.channel_name)
        await self.accept()
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("products", self.channel_name)
    
    async def product_updated(self, event):
        await self.send(text_data=json.dumps({{
            'type': 'product_updated',
            'product': event['product']
        }}))
```

### Frontend WebSocket Integration
```javascript
// src/composables/useWebSocket.js
import {{ ref, onMounted, onUnmounted }} from 'vue'

export function useWebSocket(url) {{
  const socket = ref(null)
  const connected = ref(false)
  const messages = ref([])
  
  const connect = () => {{
    socket.value = new WebSocket(url)
    
    socket.value.onopen = () => {{
      connected.value = true
      console.log('WebSocket connected')
    }}
    
    socket.value.onmessage = (event) => {{
      const data = JSON.parse(event.data)
      messages.value.push(data)
    }}
    
    socket.value.onclose = () => {{
      connected.value = false
      console.log('WebSocket disconnected')
    }}
    
    socket.value.onerror = (error) => {{
      console.error('WebSocket error:', error)
    }}
  }}
  
  const disconnect = () => {{
    if (socket.value) {{
      socket.value.close()
    }}
  }}
  
  const sendMessage = (message) => {{
    if (socket.value && connected.value) {{
      socket.value.send(JSON.stringify(message))
    }}
  }}
  
  onMounted(connect)
  onUnmounted(disconnect)
  
  return {{
    connected,
    messages,
    sendMessage,
    connect,
    disconnect
  }}
}}
```

This comprehensive API integration example shows how to build a robust, scalable REST API with Django REST Framework and integrate it seamlessly with a Vue.js 3 frontend using modern patterns like Composition API, Pinia for state management, and real-time features.
"""

    def generate_deployment_integration(self) -> str:
        """Generate deployment configuration example"""
        return f"""# Django + Vue.js Production Deployment Guide

**Last Updated**: {datetime.now().strftime('%Y-%m-%d')}
**Focus**: Docker, Nginx, SSL, and cloud deployment strategies

## Docker-based Production Setup

### 1. Backend Dockerfile (Django)

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \\
    PYTHONUNBUFFERED=1 \\
    PYTHONPATH=/app

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \\
    && apt-get install -y --no-install-recommends \\
        build-essential \\
        libpq-dev \\
        curl \\
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser \\
    && chown -R appuser:appuser /app
USER appuser

# Collect static files
RUN python manage.py collectstatic --noinput

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:8000/health/ || exit 1

# Run gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--worker-class", "gevent", "project.wsgi:application"]
```

### 2. Frontend Dockerfile (Vue.js)

```dockerfile
# frontend/Dockerfile
# Build stage
FROM node:18-alpine as build-stage

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy source code
COPY . .

# Build for production
RUN npm run build

# Production stage
FROM nginx:alpine as production-stage

# Copy built assets from build stage
COPY --from=build-stage /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Add non-root user for security
RUN addgroup -g 1001 -S nodejs \\
    && adduser -S nextjs -u 1001

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:80 || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

### 3. Production Docker Compose

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  # Database
  postgres:
    image: postgres:15-alpine
    container_name: django_vue_postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data/
      - ./backups:/backups
    environment:
      - POSTGRES_DB=${{POSTGRES_DB}}
      - POSTGRES_USER=${{POSTGRES_USER}}
      - POSTGRES_PASSWORD=${{POSTGRES_PASSWORD}}
    restart: always
    networks:
      - app-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${{POSTGRES_USER}}"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Redis Cache
  redis:
    image: redis:7-alpine
    container_name: django_vue_redis
    volumes:
      - redis_data:/data
      - ./redis.conf:/usr/local/etc/redis/redis.conf
    command: redis-server /usr/local/etc/redis/redis.conf
    restart: always
    networks:
      - app-network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Django Backend
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: django_vue_backend
    volumes:
      - static_volume:/app/staticfiles
      - media_volume:/app/media
      - ./logs:/app/logs
    environment:
      - DEBUG=False
      - DATABASE_URL=postgresql://${{POSTGRES_USER}}:${{POSTGRES_PASSWORD}}@postgres:5432/${{POSTGRES_DB}}
      - REDIS_URL=redis://redis:6379
      - SECRET_KEY=${{SECRET_KEY}}
      - ALLOWED_HOSTS=${{ALLOWED_HOSTS}}
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: always
    networks:
      - app-network

  # Vue.js Frontend
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      args:
        - VITE_API_URL=${{VITE_API_URL}}
    container_name: django_vue_frontend
    restart: always
    networks:
      - app-network

  # Nginx Reverse Proxy
  nginx:
    image: nginx:alpine
    container_name: django_vue_nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/sites-available:/etc/nginx/sites-available
      - ./ssl:/etc/nginx/ssl
      - static_volume:/var/www/static
      - media_volume:/var/www/media
      - ./logs/nginx:/var/log/nginx
    depends_on:
      - backend
      - frontend
    restart: always
    networks:
      - app-network

  # Celery Worker
  celery:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: django_vue_celery
    command: celery -A project worker -l info
    volumes:
      - ./logs:/app/logs
    environment:
      - DATABASE_URL=postgresql://${{POSTGRES_USER}}:${{POSTGRES_PASSWORD}}@postgres:5432/${{POSTGRES_DB}}
      - REDIS_URL=redis://redis:6379
      - SECRET_KEY=${{SECRET_KEY}}
    depends_on:
      - postgres
      - redis
    restart: always
    networks:
      - app-network

  # Celery Beat Scheduler
  celery-beat:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: django_vue_celery_beat
    command: celery -A project beat -l info
    volumes:
      - ./logs:/app/logs
    environment:
      - DATABASE_URL=postgresql://${{POSTGRES_USER}}:${{POSTGRES_PASSWORD}}@postgres:5432/${{POSTGRES_DB}}
      - REDIS_URL=redis://redis:6379
      - SECRET_KEY=${{SECRET_KEY}}
    depends_on:
      - postgres
      - redis
    restart: always
    networks:
      - app-network

volumes:
  postgres_data:
  redis_data:
  static_volume:
  media_volume:

networks:
  app-network:
    driver: bridge
```

### 4. Nginx Configuration

```nginx
# nginx/nginx.conf
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {{
    worker_connections 1024;
    use epoll;
    multi_accept on;
}}

http {{
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    
    # Logging format
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';
    
    access_log /var/log/nginx/access.log main;
    
    # Performance settings
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    client_max_body_size 20M;
    
    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/json
        application/javascript
        application/xml+rss
        application/atom+xml
        image/svg+xml;
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=login:10m rate=1r/s;
    
    # SSL Configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;
    
    # Upstream servers
    upstream backend {{
        server backend:8000;
    }}
    
    upstream frontend {{
        server frontend:80;
    }}
    
    # HTTP redirect to HTTPS
    server {{
        listen 80;
        server_name yourdomain.com www.yourdomain.com;
        return 301 https://$server_name$request_uri;
    }}
    
    # HTTPS server
    server {{
        listen 443 ssl http2;
        server_name yourdomain.com www.yourdomain.com;
        
        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;
        
        # Static files
        location /static/ {{
            alias /var/www/static/;
            expires 1y;
            add_header Cache-Control "public, immutable";
        }}
        
        location /media/ {{
            alias /var/www/media/;
            expires 1y;
            add_header Cache-Control "public";
        }}
        
        # API endpoints
        location /api/ {{
            limit_req zone=api burst=20 nodelay;
            proxy_pass http://backend;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header Host $http_host;
            proxy_redirect off;
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }}
        
        # Admin panel
        location /admin/ {{
            limit_req zone=login burst=5 nodelay;
            proxy_pass http://backend;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header Host $http_host;
            proxy_redirect off;
        }}
        
        # WebSocket support
        location /ws/ {{
            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $http_host;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }}
        
        # Frontend (SPA)
        location / {{
            try_files $uri $uri/ @fallback;
            expires 1d;
            add_header Cache-Control "public";
        }}
        
        location @fallback {{
            proxy_pass http://frontend;
            proxy_set_header Host $http_host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }}
        
        # Health checks
        location /health/ {{
            access_log off;
            return 200 "healthy\\n";
            add_header Content-Type text/plain;
        }}
    }}
}}
```

### 5. Environment Configuration

```bash
# .env.production
# Database
POSTGRES_DB=django_vue_prod
POSTGRES_USER=django_user
POSTGRES_PASSWORD=your_secure_password

# Django
SECRET_KEY=your-very-secure-secret-key-here
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DATABASE_URL=postgresql://django_user:your_secure_password@postgres:5432/django_vue_prod

# Redis
REDIS_URL=redis://redis:6379

# Frontend
VITE_API_URL=https://yourdomain.com

# Email (using SendGrid)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=your_sendgrid_api_key

# Cloud Storage (AWS S3)
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_STORAGE_BUCKET_NAME=your_bucket_name
AWS_S3_REGION_NAME=us-east-1

# Monitoring
SENTRY_DSN=https://your_sentry_dsn@sentry.io/project_id
```

## Cloud Deployment Options

### 1. AWS ECS with Fargate

```yaml
# aws-ecs-task-definition.json
{{
  "family": "django-vue-app",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::account:role/ecsTaskRole",
  "containerDefinitions": [
    {{
      "name": "backend",
      "image": "your-account.dkr.ecr.region.amazonaws.com/django-vue-backend:latest",
      "portMappings": [
        {{
          "containerPort": 8000,
          "protocol": "tcp"
        }}
      ],
      "environment": [
        {{
          "name": "DATABASE_URL",
          "value": "postgresql://user:pass@rds-endpoint:5432/dbname"
        }}
      ],
      "logConfiguration": {{
        "logDriver": "awslogs",
        "options": {{
          "awslogs-group": "/ecs/django-vue-app",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }}
      }},
      "healthCheck": {{
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health/ || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3
      }}
    }},
    {{
      "name": "nginx",
      "image": "your-account.dkr.ecr.region.amazonaws.com/django-vue-nginx:latest",
      "portMappings": [
        {{
          "containerPort": 80,
          "protocol": "tcp"
        }}
      ],
      "dependsOn": [
        {{
          "containerName": "backend",
          "condition": "HEALTHY"
        }}
      ]
    }}
  ]
}}
```

### 2. Kubernetes Deployment

```yaml
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: django-vue-backend
  labels:
    app: django-vue-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: django-vue-backend
  template:
    metadata:
      labels:
        app: django-vue-backend
    spec:
      containers:
      - name: backend
        image: your-registry/django-vue-backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: django-secrets
              key: database-url
        - name: REDIS_URL
          value: "redis://redis-service:6379"
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health/
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5

---
apiVersion: v1
kind: Service
metadata:
  name: backend-service
spec:
  selector:
    app: django-vue-backend
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: ClusterIP

---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: django-vue-ingress
  annotations:
    kubernetes.io/ingress.class: "nginx"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/rate-limit: "100"
spec:
  tls:
  - hosts:
    - yourdomain.com
    secretName: django-vue-tls
  rules:
  - host: yourdomain.com
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: backend-service
            port:
              number: 80
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend-service
            port:
              number: 80
```

## CI/CD Pipeline

### GitHub Actions Workflow

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Set up Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '18'
    
    - name: Install Python dependencies
      run: |
        cd backend
        pip install -r requirements.txt
    
    - name: Install Node.js dependencies
      run: |
        cd frontend
        npm ci
    
    - name: Run backend tests
      run: |
        cd backend
        python manage.py test
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_db
        REDIS_URL: redis://localhost:6379
    
    - name: Run frontend tests
      run: |
        cd frontend
        npm run test:unit
        npm run test:e2e
    
    - name: Build frontend
      run: |
        cd frontend
        npm run build

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v2
      with:
        aws-access-key-id: ${{{{ secrets.AWS_ACCESS_KEY_ID }}}}
        aws-secret-access-key: ${{{{ secrets.AWS_SECRET_ACCESS_KEY }}}}
        aws-region: us-east-1
    
    - name: Login to Amazon ECR
      id: login-ecr
      uses: aws-actions/amazon-ecr-login@v1
    
    - name: Build and push backend image
      env:
        ECR_REGISTRY: ${{{{ steps.login-ecr.outputs.registry }}}}
        ECR_REPOSITORY: django-vue-backend
        IMAGE_TAG: ${{{{ github.sha }}}}
      run: |
        cd backend
        docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
        docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
    
    - name: Build and push frontend image
      env:
        ECR_REGISTRY: ${{{{ steps.login-ecr.outputs.registry }}}}
        ECR_REPOSITORY: django-vue-frontend
        IMAGE_TAG: ${{{{ github.sha }}}}
      run: |
        cd frontend
        docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
        docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
    
    - name: Deploy to ECS
      run: |
        aws ecs update-service --cluster production --service django-vue-app --force-new-deployment
```

## Monitoring and Logging

### 1. Django Logging Configuration

```python
# settings/production.py
LOGGING = {{
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {{
        'verbose': {{
            'format': '{{levelname}} {{asctime}} {{module}} {{process:d}} {{thread:d}} {{message}}',
            'style': '{{',
        }},
        'json': {{
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        }},
    }},
    'handlers': {{
        'file': {{
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/app/logs/django.log',
            'maxBytes': 1024*1024*10,  # 10MB
            'backupCount': 5,
            'formatter': 'json',
        }},
        'console': {{
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        }},
    }},
    'root': {{
        'level': 'INFO',
        'handlers': ['console', 'file'],
    }},
    'loggers': {{
        'django': {{
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        }},
        'django.request': {{
            'handlers': ['console', 'file'],
            'level': 'ERROR',
            'propagate': False,
        }},
    }},
}}
```

### 2. Health Check Endpoints

```python
# health/views.py
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
import redis
import time

def health_check(request):
    health_status = {{
        'status': 'healthy',
        'timestamp': time.time(),
        'services': {{}}
    }}
    
    # Database check
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        health_status['services']['database'] = 'healthy'
    except Exception as e:
        health_status['services']['database'] = f'unhealthy: {{str(e)}}'
        health_status['status'] = 'unhealthy'
    
    # Redis check
    try:
        cache.set('health_check', 'test', 1)
        cache.get('health_check')
        health_status['services']['redis'] = 'healthy'
    except Exception as e:
        health_status['services']['redis'] = f'unhealthy: {{str(e)}}'
        health_status['status'] = 'unhealthy'
    
    status_code = 200 if health_status['status'] == 'healthy' else 503
    return JsonResponse(health_status, status=status_code)
```

This comprehensive deployment guide provides everything needed to deploy a Django + Vue.js application to production with proper security, monitoring, and scalability considerations.
"""

    async def get_integration_example(self, integration_type: str) -> str:
        """Get integration examples between Django and Vue.js"""
        examples = {
            'django-vue-auth': self.generate_auth_integration(),
            'django-vue-api': self.generate_api_integration(),
            'django-vue-deployment': self.generate_deployment_integration()
        }
        
        return examples.get(integration_type, f"Integration example for {integration_type} not found.")
    
    def cleanup(self):
        """Clean up any resources if needed"""
        pass