"""
SQLAlchemy ORM Models for Quality Management System
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, Numeric, DateTime, Date,
    ForeignKey, Index, JSON, LargeBinary
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import func

Base = declarative_base()


# ============================================================================
# 1. USERS AND ROLES
# ============================================================================

class Role(Base):
    __tablename__ = 'roles'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    permissions = Column(JSON)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    users = relationship('User', back_populates='role')
    
    def __repr__(self):
        return f"<Role(id={self.id}, name='{self.name}')>"


class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(255), unique=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    role_id = Column(Integer, ForeignKey('roles.id'))
    department = Column(String(100))
    phone = Column(String(50))
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    created_by_id = Column(Integer, ForeignKey('users.id'))
    meta = Column(JSON)
    
    # Relationships
    role = relationship('Role', back_populates='users')
    created_by = relationship('User', remote_side=[id], backref='created_users')
    
    # Records created by this user
    created_records = relationship('Record', foreign_keys='Record.created_by_id', back_populates='creator')
    assigned_records = relationship('Record', foreign_keys='Record.assigned_to_id', back_populates='assignee')
    
    __table_args__ = (
        Index('idx_users_role', 'role_id'),
        Index('idx_users_active', 'is_active'),
    )
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"


# ============================================================================
# 2. STANDARDS AND CRITERIA
# ============================================================================

class Standard(Base):
    __tablename__ = 'standards'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    code = Column(String(100), unique=True, nullable=False)
    version = Column(String(50), nullable=False)
    description = Column(Text)
    industry = Column(String(100))
    scope = Column(Text)
    effective_date = Column(Date)
    expiry_date = Column(Date)
    is_active = Column(Boolean, default=True)
    document_url = Column(Text)
    meta = Column(JSON)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    created_by_id = Column(Integer, ForeignKey('users.id'))
    
    # Relationships
    created_by = relationship('User')
    sections = relationship('StandardSection', back_populates='standard', cascade='all, delete-orphan')
    criteria = relationship('StandardCriteria', back_populates='standard', cascade='all, delete-orphan')
    templates = relationship('TestTemplate', back_populates='standard')
    records = relationship('Record', back_populates='standard')
    
    __table_args__ = (
        Index('idx_standards_active', 'is_active'),
        Index('idx_standards_industry', 'industry'),
    )
    
    def __repr__(self):
        return f"<Standard(id={self.id}, code='{self.code}', version='{self.version}')>"


class StandardSection(Base):
    __tablename__ = 'standard_sections'
    
    id = Column(Integer, primary_key=True)
    standard_id = Column(Integer, ForeignKey('standards.id', ondelete='CASCADE'), nullable=False)
    parent_section_id = Column(Integer, ForeignKey('standard_sections.id'))
    code = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    sort_order = Column(Integer)
    meta = Column(JSON)
    
    # Relationships
    standard = relationship('Standard', back_populates='sections')
    parent = relationship('StandardSection', remote_side=[id], backref='subsections')
    criteria = relationship('StandardCriteria', back_populates='section')
    
    __table_args__ = (
        Index('idx_standard_sections_standard', 'standard_id'),
        Index('idx_standard_sections_parent', 'parent_section_id'),
    )
    
    def __repr__(self):
        return f"<StandardSection(id={self.id}, code='{self.code}', title='{self.title}')>"


class StandardCriteria(Base):
    __tablename__ = 'standard_criteria'
    
    id = Column(Integer, primary_key=True)
    standard_id = Column(Integer, ForeignKey('standards.id', ondelete='CASCADE'), nullable=False)
    section_id = Column(Integer, ForeignKey('standard_sections.id'))
    code = Column(String(100), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    requirement_type = Column(String(50), nullable=False)  # mandatory, conditional, optional
    data_type = Column(String(50), nullable=False)  # numeric, boolean, text, select, multiselect, date, file
    validation_rules = Column(JSON)
    limit_min = Column(Numeric)
    limit_max = Column(Numeric)
    tolerance = Column(Numeric)
    unit = Column(String(50))
    severity = Column(String(50))  # critical, major, minor
    options = Column(JSON)  # For select/multiselect
    help_text = Column(Text)
    sort_order = Column(Integer)
    is_active = Column(Boolean, default=True)
    meta = Column(JSON)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    standard = relationship('Standard', back_populates='criteria')
    section = relationship('StandardSection', back_populates='criteria')
    template_fields = relationship('TemplateField', back_populates='criteria')
    record_items = relationship('RecordItem', back_populates='criteria')
    
    __table_args__ = (
        Index('idx_criteria_standard', 'standard_id'),
        Index('idx_criteria_section', 'section_id'),
        Index('idx_criteria_active', 'is_active'),
    )
    
    def __repr__(self):
        return f"<StandardCriteria(id={self.id}, code='{self.code}', title='{self.title}')>"


# ============================================================================
# 3. TEST TEMPLATES / SHEETS
# ============================================================================

class TestTemplate(Base):
    __tablename__ = 'test_templates'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    code = Column(String(100), unique=True, nullable=False)
    standard_id = Column(Integer, ForeignKey('standards.id'))
    description = Column(Text)
    category = Column(String(100))  # inspection, audit, vqa, ncr, calibration
    version = Column(String(50), default='1.0')
    
    # Visual layout and structure
    layout = Column(JSON)
    sections = Column(JSON)
    
    # Form configuration
    form_config = Column(JSON)
    
    # Approval workflow
    requires_approval = Column(Boolean, default=False)
    approval_levels = Column(Integer, default=0)
    
    # Status and lifecycle
    is_active = Column(Boolean, default=True)
    effective_date = Column(Date)
    obsolete_date = Column(Date)
    
    # Metadata
    frequency = Column(String(50))
    estimated_duration_minutes = Column(Integer)
    required_equipment = Column(JSON)
    required_certifications = Column(JSON)
    
    # Audit fields
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    created_by_id = Column(Integer, ForeignKey('users.id'))
    updated_by_id = Column(Integer, ForeignKey('users.id'))
    
    meta = Column(JSON)
    
    # Relationships
    standard = relationship('Standard', back_populates='templates')
    created_by = relationship('User', foreign_keys=[created_by_id])
    updated_by = relationship('User', foreign_keys=[updated_by_id])
    fields = relationship('TemplateField', back_populates='template', cascade='all, delete-orphan')
    records = relationship('Record', back_populates='template')
    
    __table_args__ = (
        Index('idx_templates_standard', 'standard_id'),
        Index('idx_templates_category', 'category'),
        Index('idx_templates_active', 'is_active'),
    )
    
    def __repr__(self):
        return f"<TestTemplate(id={self.id}, code='{self.code}', name='{self.name}')>"


class TemplateField(Base):
    __tablename__ = 'template_fields'
    
    id = Column(Integer, primary_key=True)
    template_id = Column(Integer, ForeignKey('test_templates.id', ondelete='CASCADE'), nullable=False)
    criteria_id = Column(Integer, ForeignKey('standard_criteria.id'), nullable=False)
    section_key = Column(String(100))
    is_required = Column(Boolean, default=True)
    is_visible = Column(Boolean, default=True)
    sort_order = Column(Integer)
    default_value = Column(Text)
    display_config = Column(JSON)
    conditional_logic = Column(JSON)
    created_at = Column(DateTime, default=datetime.now)
    
    # Relationships
    template = relationship('TestTemplate', back_populates='fields')
    criteria = relationship('StandardCriteria', back_populates='template_fields')
    record_items = relationship('RecordItem', back_populates='template_field')
    
    __table_args__ = (
        Index('idx_template_fields_template', 'template_id'),
        Index('idx_template_fields_criteria', 'criteria_id'),
    )
    
    def __repr__(self):
        return f"<TemplateField(id={self.id}, template_id={self.template_id}, criteria_id={self.criteria_id})>"


# ============================================================================
# 4. RECORDS (ACTUAL TEST INSTANCES)
# ============================================================================

class Record(Base):
    __tablename__ = 'records'
    
    id = Column(Integer, primary_key=True)
    record_number = Column(String(100), unique=True, nullable=False)
    template_id = Column(Integer, ForeignKey('test_templates.id'))
    standard_id = Column(Integer, ForeignKey('standards.id'))
    
    # Record metadata
    title = Column(String(255))
    category = Column(String(100))
    
    # Lifecycle and status
    status = Column(String(50), nullable=False, default='draft')
    priority = Column(String(50))
    
    # Scheduling
    scheduled_date = Column(DateTime)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    due_date = Column(DateTime)
    
    # Relationships
    parent_record_id = Column(Integer, ForeignKey('records.id'))
    batch_number = Column(String(100))
    product_id = Column(String(100))
    process_id = Column(String(100))
    
    # Location and context
    location = Column(String(255))
    department = Column(String(100))
    shift = Column(String(50))
    
    # Personnel
    created_by_id = Column(Integer, ForeignKey('users.id'))
    assigned_to_id = Column(Integer, ForeignKey('users.id'))
    approved_by_id = Column(Integer, ForeignKey('users.id'))
    reviewed_by_id = Column(Integer, ForeignKey('users.id'))
    
    # Results summary
    overall_compliance = Column(Boolean)
    compliance_score = Column(Numeric(5, 2))
    failed_items_count = Column(Integer, default=0)
    
    # Comments and notes
    notes = Column(Text)
    internal_notes = Column(Text)
    
    # Attachments
    attachments = Column(JSON)
    
    # Audit trail
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Flexible metadata
    meta = Column(JSON)
    
    # Relationships
    template = relationship('TestTemplate', back_populates='records')
    standard = relationship('Standard', back_populates='records')
    parent_record = relationship('Record', remote_side=[id], backref='follow_up_records')
    creator = relationship('User', foreign_keys=[created_by_id], back_populates='created_records')
    assignee = relationship('User', foreign_keys=[assigned_to_id], back_populates='assigned_records')
    approver = relationship('User', foreign_keys=[approved_by_id])
    reviewer = relationship('User', foreign_keys=[reviewed_by_id])
    items = relationship('RecordItem', back_populates='record', cascade='all, delete-orphan')
    non_conformances = relationship('NonConformance', back_populates='record')
    
    __table_args__ = (
        Index('idx_records_template', 'template_id'),
        Index('idx_records_standard', 'standard_id'),
        Index('idx_records_status', 'status'),
        Index('idx_records_created_by', 'created_by_id'),
        Index('idx_records_assigned_to', 'assigned_to_id'),
        Index('idx_records_batch', 'batch_number'),
    )
    
    def __repr__(self):
        return f"<Record(id={self.id}, record_number='{self.record_number}', status='{self.status}')>"


class RecordItem(Base):
    __tablename__ = 'record_items'
    
    id = Column(Integer, primary_key=True)
    record_id = Column(Integer, ForeignKey('records.id', ondelete='CASCADE'), nullable=False)
    criteria_id = Column(Integer, ForeignKey('standard_criteria.id'), nullable=False)
    template_field_id = Column(Integer, ForeignKey('template_fields.id'))
    
    # Value storage
    value = Column(Text)
    numeric_value = Column(Numeric)
    
    # Compliance
    compliance = Column(Boolean)
    deviation = Column(Numeric)
    
    # Additional context
    remarks = Column(Text)
    attachments = Column(JSON)
    
    # Measurement details
    measured_at = Column(DateTime)
    measured_by_id = Column(Integer, ForeignKey('users.id'))
    equipment_used = Column(String(255))
    
    # Audit
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    meta = Column(JSON)
    
    # Relationships
    record = relationship('Record', back_populates='items')
    criteria = relationship('StandardCriteria', back_populates='record_items')
    template_field = relationship('TemplateField', back_populates='record_items')
    measured_by = relationship('User')
    
    __table_args__ = (
        Index('idx_record_items_record', 'record_id'),
        Index('idx_record_items_criteria', 'criteria_id'),
        Index('idx_record_items_compliance', 'compliance'),
    )
    
    def __repr__(self):
        return f"<RecordItem(id={self.id}, record_id={self.record_id}, value='{self.value}')>"


# ============================================================================
# 5. NON-CONFORMANCE TRACKING
# ============================================================================

class NonConformance(Base):
    __tablename__ = 'non_conformances'
    
    id = Column(Integer, primary_key=True)
    nc_number = Column(String(100), unique=True, nullable=False)
    record_id = Column(Integer, ForeignKey('records.id'))
    record_item_id = Column(Integer, ForeignKey('record_items.id'))
    
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(String(50), nullable=False)
    category = Column(String(100))
    
    # Root cause analysis
    root_cause = Column(Text)
    root_cause_category = Column(String(100))
    
    # Corrective actions
    immediate_action = Column(Text)
    corrective_action = Column(Text)
    preventive_action = Column(Text)
    
    # Timeline
    detected_date = Column(DateTime, nullable=False)
    target_closure_date = Column(DateTime)
    closed_date = Column(DateTime)
    
    # Status
    status = Column(String(50), default='open')
    
    # Responsibility
    reported_by_id = Column(Integer, ForeignKey('users.id'))
    assigned_to_id = Column(Integer, ForeignKey('users.id'))
    verified_by_id = Column(Integer, ForeignKey('users.id'))
    
    # Impact
    cost_impact = Column(Numeric(12, 2))
    customer_impact = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    meta = Column(JSON)
    
    # Relationships
    record = relationship('Record', back_populates='non_conformances')
    record_item = relationship('RecordItem')
    reported_by = relationship('User', foreign_keys=[reported_by_id])
    assigned_to = relationship('User', foreign_keys=[assigned_to_id])
    verified_by = relationship('User', foreign_keys=[verified_by_id])
    
    __table_args__ = (
        Index('idx_nc_record', 'record_id'),
        Index('idx_nc_status', 'status'),
        Index('idx_nc_severity', 'severity'),
    )
    
    def __repr__(self):
        return f"<NonConformance(id={self.id}, nc_number='{self.nc_number}', severity='{self.severity}')>"


# ============================================================================
# 6. WORKFLOWS
# ============================================================================

class Workflow(Base):
    __tablename__ = 'workflows'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    code = Column(String(100), unique=True, nullable=False)
    standard_id = Column(Integer, ForeignKey('standards.id'))
    template_id = Column(Integer, ForeignKey('test_templates.id'))
    
    description = Column(Text)
    trigger_event = Column(String(100))
    
    # Workflow definition
    steps = Column(JSON)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    created_by_id = Column(Integer, ForeignKey('users.id'))
    
    # Relationships
    standard = relationship('Standard')
    template = relationship('TestTemplate')
    created_by = relationship('User')
    instances = relationship('WorkflowInstance', back_populates='workflow')
    
    __table_args__ = (
        Index('idx_workflows_template', 'template_id'),
    )
    
    def __repr__(self):
        return f"<Workflow(id={self.id}, code='{self.code}', name='{self.name}')>"


class WorkflowInstance(Base):
    __tablename__ = 'workflow_instances'
    
    id = Column(Integer, primary_key=True)
    workflow_id = Column(Integer, ForeignKey('workflows.id'), nullable=False)
    record_id = Column(Integer, ForeignKey('records.id'))
    nc_id = Column(Integer, ForeignKey('non_conformances.id'))
    
    current_step = Column(Integer, default=1)
    status = Column(String(50), default='in_progress')
    
    started_at = Column(DateTime, default=datetime.now)
    completed_at = Column(DateTime)
    
    meta = Column(JSON)
    
    # Relationships
    workflow = relationship('Workflow', back_populates='instances')
    record = relationship('Record')
    nc = relationship('NonConformance')
    step_executions = relationship('WorkflowStepExecution', back_populates='instance', cascade='all, delete-orphan')
    
    __table_args__ = (
        Index('idx_workflow_instances_record', 'record_id'),
    )
    
    def __repr__(self):
        return f"<WorkflowInstance(id={self.id}, workflow_id={self.workflow_id}, status='{self.status}')>"


class WorkflowStepExecution(Base):
    __tablename__ = 'workflow_step_executions'
    
    id = Column(Integer, primary_key=True)
    workflow_instance_id = Column(Integer, ForeignKey('workflow_instances.id', ondelete='CASCADE'), nullable=False)
    step_number = Column(Integer, nullable=False)
    step_name = Column(String(100))
    
    assigned_to_id = Column(Integer, ForeignKey('users.id'))
    status = Column(String(50), default='pending')
    
    action = Column(String(100))
    comments = Column(Text)
    
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    due_at = Column(DateTime)
    
    performed_by_id = Column(Integer, ForeignKey('users.id'))
    created_at = Column(DateTime, default=datetime.now)
    
    # Relationships
    instance = relationship('WorkflowInstance', back_populates='step_executions')
    assigned_to = relationship('User', foreign_keys=[assigned_to_id])
    performed_by = relationship('User', foreign_keys=[performed_by_id])
    
    __table_args__ = (
        Index('idx_step_exec_instance', 'workflow_instance_id'),
        Index('idx_step_exec_assigned', 'assigned_to_id'),
    )
    
    def __repr__(self):
        return f"<WorkflowStepExecution(id={self.id}, step={self.step_number}, status='{self.status}')>"


# ============================================================================
# 7. AUDIT TRAIL
# ============================================================================

class AuditLog(Base):
    __tablename__ = 'audit_log'
    
    id = Column(Integer, primary_key=True)
    table_name = Column(String(100), nullable=False)
    record_id = Column(Integer, nullable=False)
    action = Column(String(50), nullable=False)  # insert, update, delete
    
    user_id = Column(Integer, ForeignKey('users.id'))
    username = Column(String(255))
    
    old_values = Column(JSON)
    new_values = Column(JSON)
    changed_fields = Column(JSON)
    
    ip_address = Column(String(45))
    user_agent = Column(Text)
    
    timestamp = Column(DateTime, default=datetime.now)
    
    meta = Column(JSON)
    
    # Relationships
    user = relationship('User')
    
    __table_args__ = (
        Index('idx_audit_table_record', 'table_name', 'record_id'),
        Index('idx_audit_user', 'user_id'),
        Index('idx_audit_timestamp', 'timestamp'),
    )
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, table='{self.table_name}', action='{self.action}')>"


# ============================================================================
# 8. NOTIFICATIONS
# ============================================================================

class Notification(Base):
    __tablename__ = 'notifications'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String(50))  # info, warning, alert, reminder
    priority = Column(String(50), default='normal')
    
    related_record_id = Column(Integer)
    related_nc_id = Column(Integer)
    
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime)
    
    action_url = Column(Text)
    
    created_at = Column(DateTime, default=datetime.now)
    expires_at = Column(DateTime)
    
    # Relationships
    user = relationship('User')
    
    __table_args__ = (
        Index('idx_notifications_user', 'user_id'),
        Index('idx_notifications_read', 'is_read'),
    )
    
    def __repr__(self):
        return f"<Notification(id={self.id}, title='{self.title}', user_id={self.user_id})>"


# ============================================================================
# 9. REPORTS
# ============================================================================

class SavedReport(Base):
    __tablename__ = 'saved_reports'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    report_type = Column(String(100))
    
    filters = Column(JSON)
    columns = Column(JSON)
    chart_config = Column(JSON)
    
    is_public = Column(Boolean, default=False)
    
    created_by_id = Column(Integer, ForeignKey('users.id'))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    created_by = relationship('User')
    
    def __repr__(self):
        return f"<SavedReport(id={self.id}, name='{self.name}', type='{self.report_type}')>"


# ============================================================================
# 10. DOCUMENTS
# ============================================================================

class Document(Base):
    __tablename__ = 'documents'
    
    id = Column(Integer, primary_key=True)
    document_number = Column(String(100), unique=True, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    category = Column(String(100))
    
    file_name = Column(String(255))
    file_path = Column(Text)
    file_type = Column(String(50))
    file_size = Column(Integer)
    
    version = Column(String(50), default='1.0')
    status = Column(String(50), default='draft')
    
    standard_id = Column(Integer, ForeignKey('standards.id'))
    template_id = Column(Integer, ForeignKey('test_templates.id'))
    
    effective_date = Column(Date)
    review_date = Column(Date)
    obsolete_date = Column(Date)
    
    created_by_id = Column(Integer, ForeignKey('users.id'))
    approved_by_id = Column(Integer, ForeignKey('users.id'))
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    meta = Column(JSON)
    
    # Relationships
    standard = relationship('Standard')
    template = relationship('TestTemplate')
    created_by = relationship('User', foreign_keys=[created_by_id])
    approved_by = relationship('User', foreign_keys=[approved_by_id])
    
    __table_args__ = (
        Index('idx_documents_standard', 'standard_id'),
        Index('idx_documents_status', 'status'),
    )
    
    def __repr__(self):
        return f"<Document(id={self.id}, document_number='{self.document_number}', title='{self.title}')>"


# ============================================================================
# 11. IMAGE STORAGE
# ============================================================================

class ImageAttachment(Base):
    """Store images related to records, items, or non-conformances"""
    __tablename__ = 'image_attachments'
    
    id = Column(Integer, primary_key=True)
    
    # Polymorphic relationship - can belong to different entities
    entity_type = Column(String(50), nullable=False)  # record, record_item, non_conformance
    entity_id = Column(Integer, nullable=False)
    
    # Image data
    filename = Column(String(255), nullable=False)
    file_path = Column(Text)  # Path to file on disk
    file_data = Column(LargeBinary)  # Optional: store small images in DB
    file_size = Column(Integer)
    mime_type = Column(String(100))
    
    # Image metadata
    width = Column(Integer)
    height = Column(Integer)
    thumbnail_path = Column(Text)
    
    # Description
    description = Column(Text)
    tags = Column(JSON)
    
    # Audit
    uploaded_by_id = Column(Integer, ForeignKey('users.id'))
    uploaded_at = Column(DateTime, default=datetime.now)
    
    # Relationships
    uploaded_by = relationship('User')
    
    __table_args__ = (
        Index('idx_image_entity', 'entity_type', 'entity_id'),
    )
    
    def __repr__(self):
        return f"<ImageAttachment(id={self.id}, filename='{self.filename}', entity_type='{self.entity_type}')>"


# ============================================================================
# 10. COMPANY SETTINGS
# ============================================================================

class CompanySettings(Base):
    __tablename__ = 'company_settings'
    
    id = Column(Integer, primary_key=True)
    company_name = Column(String(255), nullable=False)
    company_logo = Column(LargeBinary)  # Store logo as binary data
    logo_filename = Column(String(255))
    
    # Contact Information
    address = Column(Text)
    city = Column(String(100))
    state = Column(String(100))
    postal_code = Column(String(20))
    country = Column(String(100))
    
    phone = Column(String(50))
    fax = Column(String(50))
    email = Column(String(255))
    website = Column(String(255))
    
    # Additional Information
    registration_number = Column(String(100))
    tax_id = Column(String(100))
    certification_info = Column(Text)
    
    # Settings
    date_format = Column(String(50), default='%Y-%m-%d')
    timezone = Column(String(100), default='UTC')
    
    # Audit
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    updated_by_id = Column(Integer, ForeignKey('users.id'))
    
    # Relationship
    updated_by = relationship('User')
    
    def __repr__(self):
        return f"<CompanySettings(id={self.id}, company_name='{self.company_name}')>"
