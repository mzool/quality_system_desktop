"""
Database Configuration and Session Management
"""
import os
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import StaticPool
from models import Base
import hashlib


class DatabaseManager:
    """Manages database connection and sessions"""
    
    def __init__(self, db_path=None):
        """
        Initialize database manager
        
        Args:
            db_path: Path to SQLite database file. If None, uses default location.
        """
        if db_path is None:
            # Default to user's home directory
            app_dir = Path.home() / '.quality_system'
            app_dir.mkdir(parents=True, exist_ok=True)
            db_path = app_dir / 'quality_system.db'
        
        self.db_path = Path(db_path)
        self.db_url = f'sqlite:///{self.db_path}'
        
        # Create engine with appropriate settings for SQLite
        self.engine = create_engine(
            self.db_url,
            echo=False,  # Set to True for SQL query debugging
            connect_args={
                'check_same_thread': False,  # Allow multi-threading
                'timeout': 30  # Connection timeout in seconds
            },
            poolclass=StaticPool  # Use static pool for SQLite
        )
        
        # Enable foreign keys in SQLite
        @event.listens_for(self.engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging for better concurrency
            cursor.close()
        
        # Create session factory
        self.Session = scoped_session(sessionmaker(bind=self.engine))
        
    def create_all_tables(self):
        """Create all tables in the database"""
        # Check if tables already exist
        from sqlalchemy import inspect
        inspector = inspect(self.engine)
        existing_tables = inspector.get_table_names()
        
        Base.metadata.create_all(self.engine)
        
        # Return True if tables were created (didn't exist before)
        tables_created = len(existing_tables) == 0
        if tables_created:
            print(f"Database created at: {self.db_path}")
        return tables_created
        
    def drop_all_tables(self):
        """Drop all tables (use with caution!)"""
        Base.metadata.drop_all(self.engine)
        print("All tables dropped!")
        
    def get_session(self):
        """Get a new database session"""
        return self.Session()
    
    def close_session(self):
        """Close the current session"""
        self.Session.remove()
    
    def backup_database(self, backup_path=None):
        """
        Create a backup of the database
        
        Args:
            backup_path: Where to save the backup. If None, creates timestamped backup.
        """
        import shutil
        from datetime import datetime
        
        if backup_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_dir = self.db_path.parent / 'backups'
            backup_dir.mkdir(exist_ok=True)
            backup_path = backup_dir / f'quality_system_backup_{timestamp}.db'
        
        # Close all connections before backup
        self.close_session()
        
        # Copy database file
        shutil.copy2(self.db_path, backup_path)
        print(f"Database backed up to: {backup_path}")
        return backup_path
    
    def initialize_default_data(self):
        """Initialize database with default data"""
        from models import Role, User
        
        session = self.get_session()
        
        try:
            # Check if roles already exist
            if session.query(Role).count() > 0:
                print("Database already initialized with data")
                return False
            
            # Create default roles
            roles_data = [
                {
                    'name': 'Admin',
                    'description': 'System Administrator with full access',
                    'permissions': {
                        'can_create_records': True,
                        'can_approve': True,
                        'can_close_nc': True,
                        'can_edit_templates': True,
                        'can_manage_users': True,
                        'can_manage_standards': True,
                        'can_view_all': True
                    }
                },
                {
                    'name': 'QA Manager',
                    'description': 'Quality Assurance Manager',
                    'permissions': {
                        'can_create_records': True,
                        'can_approve': True,
                        'can_close_nc': True,
                        'can_edit_templates': True,
                        'can_manage_users': False,
                        'can_manage_standards': True,
                        'can_view_all': True
                    }
                },
                {
                    'name': 'Quality Inspector',
                    'description': 'Quality Inspector',
                    'permissions': {
                        'can_create_records': True,
                        'can_approve': False,
                        'can_close_nc': False,
                        'can_edit_templates': False,
                        'can_manage_users': False,
                        'can_manage_standards': False,
                        'can_view_all': False
                    }
                },
                {
                    'name': 'Auditor',
                    'description': 'Internal/External Auditor',
                    'permissions': {
                        'can_create_records': True,
                        'can_approve': False,
                        'can_close_nc': False,
                        'can_edit_templates': False,
                        'can_manage_users': False,
                        'can_manage_standards': False,
                        'can_view_all': True
                    }
                },
                {
                    'name': 'Viewer',
                    'description': 'Read-only access',
                    'permissions': {
                        'can_create_records': False,
                        'can_approve': False,
                        'can_close_nc': False,
                        'can_edit_templates': False,
                        'can_manage_users': False,
                        'can_manage_standards': False,
                        'can_view_all': False
                    }
                }
            ]
            
            roles = {}
            for role_data in roles_data:
                role = Role(**role_data)
                session.add(role)
                roles[role_data['name']] = role
            
            session.flush()  # Flush to get role IDs
            
            # Create default admin user
            admin_password = 'admin123'  # Should be changed immediately
            password_hash = hashlib.sha256(admin_password.encode()).hexdigest()
            
            admin_user = User(
                username='admin',
                full_name='System Administrator',
                email='admin@qualitysystem.local',
                password_hash=password_hash,
                role_id=roles['Admin'].id,
                department='IT',
                is_active=True
            )
            session.add(admin_user)
            
            session.commit()
            print("Default data initialized successfully!")
            print("Default admin user created:")
            print("  Username: admin")
            print("  Password: admin123")
            print("  **PLEASE CHANGE THIS PASSWORD IMMEDIATELY**")
            return True
            
        except Exception as e:
            session.rollback()
            print(f"Error initializing default data: {e}")
            raise
        finally:
            session.close()


# Global database manager instance
db_manager = None


def init_database(db_path=None, create_tables=True, init_data=True):
    """
    Initialize the global database manager
    
    Args:
        db_path: Path to database file
        create_tables: Whether to create tables
        init_data: Whether to initialize default data
    
    Returns:
        Tuple of (DatabaseManager instance, was_newly_created: bool)
    """
    global db_manager
    
    db_manager = DatabaseManager(db_path)
    
    tables_created = False
    data_initialized = False
    
    if create_tables:
        tables_created = db_manager.create_all_tables()
    
    if init_data:
        data_init_result = db_manager.initialize_default_data()
        data_initialized = data_init_result if data_init_result is not None else False
    
    # Return whether database was newly created
    was_newly_created = tables_created or data_initialized
    
    return db_manager, was_newly_created


def get_db_session():
    """Get database session from global manager"""
    if db_manager is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    return db_manager.get_session()


def close_db_session():
    """Close database session"""
    if db_manager:
        db_manager.close_session()


if __name__ == "__main__":
    # Test database creation
    print("Creating test database...")
    db = init_database(db_path='test_quality_system.db')
    print("Database created and initialized successfully!")
    
    # Test query
    session = db.get_session()
    from models import Role, User
    
    roles = session.query(Role).all()
    print(f"\nCreated {len(roles)} roles:")
    for role in roles:
        print(f"  - {role.name}: {role.description}")
    
    users = session.query(User).all()
    print(f"\nCreated {len(users)} users:")
    for user in users:
        print(f"  - {user.username} ({user.full_name}) - Role: {user.role.name if user.role else 'None'}")
    
    session.close()
