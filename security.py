"""
Security Module - Autentikasi, Autorisasi, dan Enkripsi Data
"""

import os
import jwt
import hashlib
import secrets
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from functools import wraps
import logging

logger = logging.getLogger(__name__)

# ==================== ENCRYPTION ====================

class DataEncryption:
    """Enkripsi/dekripsi data sensitif"""
    
    def __init__(self, key_file='secrets/encryption.key'):
        self.key_file = key_file
        self.cipher = None
        self._load_or_create_key()
    
    def _load_or_create_key(self):
        """Load atau generate encryption key"""
        os.makedirs(os.path.dirname(self.key_file), exist_ok=True)
        
        if os.path.exists(self.key_file):
            with open(self.key_file, 'rb') as f:
                key = f.read()
            logger.info("Encryption key loaded")
        else:
            key = Fernet.generate_key()
            with open(self.key_file, 'wb') as f:
                f.write(key)
            logger.info("New encryption key generated")
        
        self.cipher = Fernet(key)
    
    def encrypt(self, data: str) -> str:
        """Enkripsi data"""
        encrypted = self.cipher.encrypt(data.encode())
        return encrypted.decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """Dekripsi data"""
        decrypted = self.cipher.decrypt(encrypted_data.encode())
        return decrypted.decode()


# ==================== AUTHENTICATION ====================

class AuthenticationManager:
    """Manajemen autentikasi user dengan JWT"""
    
    def __init__(self, secret_key=None):
        self.secret_key = secret_key or os.getenv('JWT_SECRET', self._generate_secret())
        self.users_db = {}  # Simulasi database user
        self._init_default_users()
    
    def _generate_secret(self):
        """Generate random secret key"""
        return secrets.token_urlsafe(32)
    
    def _init_default_users(self):
        """Inisialisasi default users"""
        # Hash password: password123
        self.users_db = {
            'admin': {
                'password_hash': self._hash_password('admin123'),
                'role': 'admin',
                'permissions': ['read', 'write', 'train_model', 'view_logs']
            },
            'data_engineer': {
                'password_hash': self._hash_password('engineer123'),
                'role': 'engineer',
                'permissions': ['read', 'write', 'view_logs']
            },
            'viewer': {
                'password_hash': self._hash_password('viewer123'),
                'role': 'viewer',
                'permissions': ['read']
            }
        }
        logger.info(f"Initialized {len(self.users_db)} default users")
    
    def _hash_password(self, password: str) -> str:
        """Hash password dengan SHA-256 + salt"""
        salt = "weather_pipeline_salt"  # Dalam produksi, gunakan salt unik per user
        return hashlib.sha256(f"{password}{salt}".encode()).hexdigest()
    
    def authenticate(self, username: str, password: str) -> dict:
        """
        Autentikasi user dan generate JWT token
        Returns: {'success': bool, 'token': str, 'message': str}
        """
        if username not in self.users_db:
            logger.warning(f"Login attempt with invalid username: {username}")
            return {'success': False, 'message': 'Invalid credentials'}
        
        user = self.users_db[username]
        password_hash = self._hash_password(password)
        
        if password_hash != user['password_hash']:
            logger.warning(f"Failed login attempt for user: {username}")
            return {'success': False, 'message': 'Invalid credentials'}
        
        # Generate JWT token
        token = self._generate_token(username, user['role'], user['permissions'])
        
        logger.info(f"User {username} authenticated successfully")
        return {
            'success': True,
            'token': token,
            'role': user['role'],
            'message': 'Authentication successful'
        }
    
    def _generate_token(self, username: str, role: str, permissions: list) -> str:
        """Generate JWT token"""
        payload = {
            'username': username,
            'role': role,
            'permissions': permissions,
            'exp': datetime.utcnow() + timedelta(hours=24),
            'iat': datetime.utcnow()
        }
        token = jwt.encode(payload, self.secret_key, algorithm='HS256')
        return token
    
    def verify_token(self, token: str) -> dict:
        """
        Verify JWT token
        Returns: {'valid': bool, 'payload': dict, 'message': str}
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            return {'valid': True, 'payload': payload}
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return {'valid': False, 'message': 'Token expired'}
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {str(e)}")
            return {'valid': False, 'message': 'Invalid token'}


# ==================== AUTHORIZATION ====================

class AuthorizationManager:
    """Manajemen autorisasi dan permission checking"""
    
    @staticmethod
    def check_permission(user_permissions: list, required_permission: str) -> bool:
        """Check apakah user memiliki permission yang dibutuhkan"""
        return required_permission in user_permissions
    
    @staticmethod
    def require_permission(permission: str):
        """Decorator untuk require permission"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Ambil token dari kwargs atau context
                token = kwargs.get('token')
                if not token:
                    raise PermissionError("No authentication token provided")
                
                # Verify token
                auth_manager = AuthenticationManager()
                result = auth_manager.verify_token(token)
                
                if not result['valid']:
                    raise PermissionError(result['message'])
                
                # Check permission
                user_permissions = result['payload']['permissions']
                if not AuthorizationManager.check_permission(user_permissions, permission):
                    logger.warning(
                        f"Permission denied: {result['payload']['username']} "
                        f"needs '{permission}' permission"
                    )
                    raise PermissionError(
                        f"Permission denied: '{permission}' required"
                    )
                
                # Add user info to kwargs
                kwargs['user_info'] = result['payload']
                return func(*args, **kwargs)
            return wrapper
        return decorator


# ==================== DATA PROTECTION ====================

class DataProtection:
    """Data protection dan PII masking"""
    
    @staticmethod
    def mask_sensitive_data(data: dict, sensitive_fields: list = None) -> dict:
        """Mask field sensitif dalam data"""
        if sensitive_fields is None:
            sensitive_fields = ['password', 'token', 'secret', 'key', 'api_key']
        
        masked_data = data.copy()
        for field in sensitive_fields:
            if field in masked_data:
                masked_data[field] = '***MASKED***'
        
        return masked_data
    
    @staticmethod
    def sanitize_log_data(data: dict) -> dict:
        """Sanitize data sebelum logging untuk menghindari log injection"""
        sanitized = {}
        for key, value in data.items():
            # Remove newlines dan special chars yang bisa digunakan untuk log injection
            if isinstance(value, str):
                sanitized[key] = value.replace('\n', ' ').replace('\r', ' ')
            else:
                sanitized[key] = value
        return sanitized


# ==================== AUDIT LOGGING ====================

class AuditLogger:
    """Audit logging untuk tracking security events"""
    
    def __init__(self, log_file='logs/audit.log'):
        self.log_file = log_file
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        self.logger = logging.getLogger('audit')
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter(
            '%(asctime)s - AUDIT - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def log_authentication(self, username: str, success: bool, ip_address: str = None):
        """Log authentication attempt"""
        status = "SUCCESS" if success else "FAILED"
        self.logger.info(
            f"AUTH {status} - User: {username}, IP: {ip_address or 'unknown'}"
        )
    
    def log_authorization(self, username: str, action: str, resource: str, granted: bool):
        """Log authorization decision"""
        status = "GRANTED" if granted else "DENIED"
        self.logger.info(
            f"AUTHZ {status} - User: {username}, Action: {action}, Resource: {resource}"
        )
    
    def log_data_access(self, username: str, data_type: str, operation: str):
        """Log data access"""
        self.logger.info(
            f"DATA ACCESS - User: {username}, Type: {data_type}, Operation: {operation}"
        )


# ==================== USAGE EXAMPLE ====================

if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Test encryption
    print("\n=== TESTING ENCRYPTION ===")
    encryptor = DataEncryption()
    sensitive_data = "API_KEY_12345"
    encrypted = encryptor.encrypt(sensitive_data)
    decrypted = encryptor.decrypt(encrypted)
    print(f"Original: {sensitive_data}")
    print(f"Encrypted: {encrypted}")
    print(f"Decrypted: {decrypted}")
    
    # Test authentication
    print("\n=== TESTING AUTHENTICATION ===")
    auth_manager = AuthenticationManager()
    
    # Login admin
    result = auth_manager.authenticate('admin', 'admin123')
    if result['success']:
        print(f"Login successful! Token: {result['token'][:50]}...")
        
        # Verify token
        verify_result = auth_manager.verify_token(result['token'])
        print(f"Token valid: {verify_result['valid']}")
        print(f"User permissions: {verify_result['payload']['permissions']}")
    
    # Test failed login
    result = auth_manager.authenticate('admin', 'wrongpassword')
    print(f"Failed login result: {result['message']}")
    
    # Test authorization
    print("\n=== TESTING AUTHORIZATION ===")
    
    @AuthorizationManager.require_permission('train_model')
    def train_ml_model(token=None, user_info=None):
        print(f"Training model... (User: {user_info['username']})")
        return "Model trained successfully"
    
    try:
        # Admin has train_model permission
        admin_token = auth_manager.authenticate('admin', 'admin123')['token']
        result = train_ml_model(token=admin_token)
        print(result)
    except PermissionError as e:
        print(f"Permission error: {e}")
    
    try:
        # Viewer doesn't have train_model permission
        viewer_token = auth_manager.authenticate('viewer', 'viewer123')['token']
        result = train_ml_model(token=viewer_token)
        print(result)
    except PermissionError as e:
        print(f"Permission error: {e}")
    
    # Test audit logging
    print("\n=== TESTING AUDIT LOG ===")
    audit = AuditLogger()
    audit.log_authentication('admin', True, '192.168.1.1')
    audit.log_authorization('viewer', 'train_model', 'ml_model', False)
    audit.log_data_access('data_engineer', 'weather_data', 'read')
    print("Audit logs written to logs/audit.log")
