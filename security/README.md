# 🔒 Security Package

Package ini berisi implementasi keamanan lengkap untuk pipeline.

## 📁 Struktur

```
security/
├── __init__.py          # Package initialization
├── security.py          # Security implementation
├── secrets/             # Direktori untuk encryption keys (GITIGNORED)
│   └── encryption.key   # Encryption key (auto-generated)
└── README.md
```

## 🔐 Fitur

### 1. Authentication (JWT)

```python
from security import AuthenticationManager

auth_manager = AuthenticationManager()

# Login
result = auth_manager.authenticate('admin', 'admin123')
if result['success']:
    token = result['token']
```

### 2. Authorization (RBAC)

```python
from security import AuthorizationManager

@AuthorizationManager.require_permission('write')
def send_data(token=None, user_info=None):
    # Only users with 'write' permission can execute
    pass
```

### 3. Encryption

```python
from security import DataEncryption

encryptor = DataEncryption()

# Encrypt
encrypted = encryptor.encrypt("sensitive_data")

# Decrypt
decrypted = encryptor.decrypt(encrypted)
```

### 4. Audit Logging

```python
from security import AuditLogger

audit = AuditLogger()
audit.log_authentication('admin', True, '192.168.1.1')
audit.log_data_access('user', 'weather_data', 'read')
```

## 👥 Default Users

| Username | Password | Role | Permissions |
|----------|----------|------|-------------|
| admin | admin123 | admin | read, write, train_model, view_logs |
| data_engineer | engineer123 | engineer | read, write, view_logs |
| viewer | viewer123 | viewer | read |
