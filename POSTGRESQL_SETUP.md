# PostgreSQL Integration Guide

## Current Status
The system **currently uses SQLite by default**. This is fine for single-user desktop applications and stores data in:
```
~/.quality_system/quality_system.db
```

## To Use PostgreSQL Instead

### 1. Install PostgreSQL Driver

```bash
pip install psycopg2-binary
```

Or add to `requirements.txt`:
```
psycopg2-binary>=2.9.0
```

### 2. Update `database.py`

Replace the `__init__` method in the `DatabaseManager` class to accept a database URL:

```python
def __init__(self, db_url=None, db_path=None):
    """
    Initialize database manager
    
    Args:
        db_url: Full database URL (e.g., 'postgresql://user:pass@localhost/dbname')
        db_path: Path to SQLite database file (only used if db_url is None).
    """
    # Check for environment variable first
    if db_url is None:
        db_url = os.environ.get('QMS_DATABASE_URL')
    
    # Determine database type
    if db_url:
        self.db_url = db_url
        self.db_type = self._detect_db_type(db_url)
        self.db_path = None
    else:
        # Default to SQLite
        if db_path is None:
            app_dir = Path.home() / '.quality_system'
            app_dir.mkdir(parents=True, exist_ok=True)
            db_path = app_dir / 'quality_system.db'
        
        self.db_path = Path(db_path)
        self.db_url = f'sqlite:///{self.db_path}'
        self.db_type = 'sqlite'
    
    # Create engine with database-specific settings
    self.engine = self._create_engine()
    self.Session = scoped_session(sessionmaker(bind=self.engine))

def _detect_db_type(self, db_url):
    """Detect database type from URL"""
    if db_url.startswith('postgresql'):
        return 'postgresql'
    elif db_url.startswith('mysql'):
        return 'mysql'
    elif db_url.startswith('sqlite'):
        return 'sqlite'
    else:
        return 'unknown'

def _create_engine(self):
    """Create SQLAlchemy engine with database-specific configuration"""
    if self.db_type == 'sqlite':
        engine = create_engine(
            self.db_url,
            echo=False,
            connect_args={'check_same_thread': False, 'timeout': 30},
            poolclass=StaticPool
        )
        
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()
    
    elif self.db_type == 'postgresql':
        from sqlalchemy.pool import QueuePool
        engine = create_engine(
            self.db_url,
            echo=False,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=3600,
            poolclass=QueuePool
        )
    
    return engine
```

### 3. Update `init_database` function

Change the signature to accept `db_url`:

```python
def init_database(db_url=None, db_path=None, create_tables=True, init_data=True):
    global db_manager
    db_manager = DatabaseManager(db_url=db_url, db_path=db_path)
    # ... rest of the function
```

### 4. Set Up PostgreSQL Database

#### Create Database:
```bash
# Login to PostgreSQL
psql -U postgres

# Create database and user
CREATE DATABASE quality_system;
CREATE USER qms_user WITH ENCRYPTED PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE quality_system TO qms_user;

# Exit psql
\q
```

### 5. Configure the Application

#### Option A: Environment Variable (Recommended)
```bash
export QMS_DATABASE_URL='postgresql://qms_user:your_secure_password@localhost:5432/quality_system'
python main.py
```

#### Option B: Direct Code Modification
In `main.py`, find where `init_database()` is called and add the URL:

```python
# Replace this:
db_manager, was_new = init_database()

# With this:
db_url = 'postgresql://qms_user:your_secure_password@localhost:5432/quality_system'
db_manager, was_new = init_database(db_url=db_url)
```

### 6. Required Changes Summary

| Component | Changes Needed |
|-----------|----------------|
| **requirements.txt** | Add `psycopg2-binary>=2.9.0` |
| **database.py** | Update `__init__`, add `_detect_db_type()`, add `_create_engine()` |
| **main.py** | Pass `db_url` to `init_database()` (or use env variable) |
| **PostgreSQL Server** | Create database and user |

## Connection String Formats

### PostgreSQL
```
postgresql://username:password@host:port/database
postgresql://qms_user:password123@localhost:5432/quality_system
postgresql://user@localhost/dbname  # Uses local auth
```

### SQLite (default if no URL provided)
```
sqlite:///path/to/database.db
sqlite:////absolute/path/to/database.db
```

### MySQL (if needed in future)
```
mysql+pymysql://username:password@host:port/database
```

## Advantages of PostgreSQL

1. **Multi-user support**: Multiple users can access simultaneously
2. **Network access**: Can be hosted on a server
3. **Better concurrency**: Handles concurrent writes better
4. **ACID compliance**: Stronger data integrity guarantees
5. **Advanced features**: Full-text search, JSON support, etc.
6. **Scalability**: Handles larger datasets better

## Advantages of SQLite (Current)

1. **Zero configuration**: No server setup required
2. **Single file**: Easy to backup and move
3. **Perfect for desktop apps**: Ideal for single-user scenarios
4. **No dependencies**: No database server needed
5. **Fast for small datasets**: Excellent performance for typical use

## Migration Path

### From SQLite to PostgreSQL:

1. **Backup SQLite data**:
   ```bash
   cp ~/.quality_system/quality_system.db backup.db
   ```

2. **Export to SQL**:
   ```bash
   sqlite3 ~/.quality_system/quality_system.db .dump > dump.sql
   ```

3. **Clean up SQL file** (remove SQLite-specific commands):
   ```bash
   sed -i '/PRAGMA/d' dump.sql
   sed -i '/BEGIN TRANSACTION/d' dump.sql
   sed -i '/COMMIT/d' dump.sql
   ```

4. **Import to PostgreSQL**:
   ```bash
   psql -U qms_user -d quality_system < dump.sql
   ```

5. **Verify data and switch connection string**

## Docker PostgreSQL (Quick Setup)

```bash
docker run -d \
  --name qms-postgres \
  -e POSTGRES_PASSWORD=your_password \
  -e POSTGRES_USER=qms_user \
  -e POSTGRES_DB=quality_system \
  -p 5432:5432 \
  -v qms_data:/var/lib/postgresql/data \
  postgres:16

# Connection string:
# postgresql://qms_user:your_password@localhost:5432/quality_system
```

## Testing the Connection

```python
from sqlalchemy import create_engine

# Test connection
engine = create_engine('postgresql://qms_user:password@localhost:5432/quality_system')
with engine.connect() as conn:
    result = conn.execute("SELECT version();")
    print(result.fetchone())
```

## Troubleshooting

### psycopg2 installation issues
```bash
# On Ubuntu/Debian:
sudo apt-get install libpq-dev python3-dev
pip install psycopg2

# Or use binary version (no compilation needed):
pip install psycopg2-binary
```

### Connection refused
- Check PostgreSQL is running: `systemctl status postgresql`
- Check port: `sudo netstat -plnt | grep 5432`
- Check pg_hba.conf for authentication settings

### Permission denied
- Ensure user has correct privileges: `GRANT ALL PRIVILEGES ON DATABASE quality_system TO qms_user;`
- For all tables: `GRANT ALL ON ALL TABLES IN SCHEMA public TO qms_user;`
