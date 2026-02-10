-- ============================================================================
-- QUALITY MANAGEMENT SYSTEM DATABASE SCHEMA
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. USERS AND ROLES
-- ----------------------------------------------------------------------------

CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    permissions JSONB, -- e.g., {"can_create_records": true, "can_approve": true}
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role_id INT REFERENCES roles(id),
    department VARCHAR(100),
    phone VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by INT REFERENCES users(id),
    meta JSONB -- e.g., {"certifications": [], "specializations": []}
);

CREATE INDEX idx_users_role ON users(role_id);
CREATE INDEX idx_users_active ON users(is_active);

-- ----------------------------------------------------------------------------
-- 2. STANDARDS AND CRITERIA
-- ----------------------------------------------------------------------------

CREATE TABLE standards (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    code VARCHAR(100) UNIQUE NOT NULL, -- e.g., "ISO-9001", "ISO-14001"
    version VARCHAR(50) NOT NULL,
    description TEXT,
    industry VARCHAR(100), -- e.g., "manufacturing", "healthcare"
    scope TEXT,
    effective_date DATE,
    expiry_date DATE,
    is_active BOOLEAN DEFAULT TRUE,
    document_url TEXT,
    meta JSONB, -- e.g., {"region": "international", "certification_body": "ISO"}
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by INT REFERENCES users(id),
    CONSTRAINT unique_standard_version UNIQUE (code, version)
);

CREATE INDEX idx_standards_active ON standards(is_active);
CREATE INDEX idx_standards_industry ON standards(industry);

-- Standard sections for organization
CREATE TABLE standard_sections (
    id SERIAL PRIMARY KEY,
    standard_id INT REFERENCES standards(id) ON DELETE CASCADE,
    parent_section_id INT REFERENCES standard_sections(id),
    code VARCHAR(50) NOT NULL, -- e.g., "4", "4.1", "4.1.1"
    title VARCHAR(255) NOT NULL,
    description TEXT,
    sort_order INT,
    meta JSONB
);

CREATE INDEX idx_standard_sections_standard ON standard_sections(standard_id);
CREATE INDEX idx_standard_sections_parent ON standard_sections(parent_section_id);

-- Generic checklist items or rules
CREATE TABLE standard_criteria (
    id SERIAL PRIMARY KEY,
    standard_id INT REFERENCES standards(id) ON DELETE CASCADE,
    section_id INT REFERENCES standard_sections(id),
    code VARCHAR(100) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    requirement_type VARCHAR(50) NOT NULL, -- e.g., "mandatory", "conditional", "optional"
    data_type VARCHAR(50) NOT NULL, -- e.g., "numeric", "boolean", "text", "select", "multiselect", "date", "file"
    validation_rules JSONB, -- e.g., {"min": 0, "max": 100, "regex": "pattern"}
    limit_min NUMERIC,
    limit_max NUMERIC,
    tolerance NUMERIC,
    unit VARCHAR(50), -- e.g., "ppm", "mm", "%", "°C"
    severity VARCHAR(50), -- e.g., "critical", "major", "minor"
    options JSONB, -- For select/multiselect types: ["option1", "option2"]
    help_text TEXT,
    sort_order INT,
    is_active BOOLEAN DEFAULT TRUE,
    meta JSONB, -- e.g., {"calculation_formula": "x * 1.5", "dependencies": []}
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT unique_criteria_code UNIQUE (standard_id, code)
);

CREATE INDEX idx_criteria_standard ON standard_criteria(standard_id);
CREATE INDEX idx_criteria_section ON standard_criteria(section_id);
CREATE INDEX idx_criteria_active ON standard_criteria(is_active);

-- ----------------------------------------------------------------------------
-- 3. TEST TEMPLATES / SHEETS
-- ----------------------------------------------------------------------------

-- Templates define the structure/layout for different types of tests
CREATE TABLE test_templates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    code VARCHAR(100) UNIQUE NOT NULL, -- e.g., "VQA-001", "INSP-FIN-001"
    standard_id INT REFERENCES standards(id),
    description TEXT,
    category VARCHAR(100), -- e.g., "inspection", "audit", "vqa", "ncr", "calibration"
    version VARCHAR(50) DEFAULT '1.0',
    
    -- Visual layout and structure
    layout JSONB, -- e.g., {"type": "grid", "columns": 3, "sections": [...]}
    sections JSONB, -- Define sections: [{"id": "sec1", "title": "Visual Check", "order": 1}]
    
    -- Form configuration
    form_config JSONB, -- e.g., {"allow_attachments": true, "require_signature": true}
    
    -- Approval workflow
    requires_approval BOOLEAN DEFAULT FALSE,
    approval_levels INT DEFAULT 0,
    
    -- Status and lifecycle
    is_active BOOLEAN DEFAULT TRUE,
    effective_date DATE,
    obsolete_date DATE,
    
    -- Metadata
    frequency VARCHAR(50), -- e.g., "daily", "weekly", "monthly", "per_batch"
    estimated_duration_minutes INT,
    required_equipment JSONB, -- e.g., ["caliper", "microscope"]
    required_certifications JSONB, -- e.g., ["Quality Inspector Level 2"]
    
    -- Audit fields
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by INT REFERENCES users(id),
    updated_by INT REFERENCES users(id),
    
    meta JSONB -- Additional flexible metadata
);

CREATE INDEX idx_templates_standard ON test_templates(standard_id);
CREATE INDEX idx_templates_category ON test_templates(category);
CREATE INDEX idx_templates_active ON test_templates(is_active);

-- Template fields - defines which criteria appear in this template
CREATE TABLE template_fields (
    id SERIAL PRIMARY KEY,
    template_id INT REFERENCES test_templates(id) ON DELETE CASCADE,
    criteria_id INT REFERENCES standard_criteria(id),
    section_key VARCHAR(100), -- Links to sections in template
    is_required BOOLEAN DEFAULT TRUE,
    is_visible BOOLEAN DEFAULT TRUE,
    sort_order INT,
    default_value TEXT,
    display_config JSONB, -- e.g., {"width": "full", "show_help": true}
    conditional_logic JSONB, -- e.g., {"show_if": {"field_id": 5, "value": "yes"}}
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_template_fields_template ON template_fields(template_id);
CREATE INDEX idx_template_fields_criteria ON template_fields(criteria_id);

-- ----------------------------------------------------------------------------
-- 4. RECORDS (ACTUAL TEST INSTANCES)
-- ----------------------------------------------------------------------------

CREATE TABLE records (
    id SERIAL PRIMARY KEY,
    record_number VARCHAR(100) UNIQUE NOT NULL, -- e.g., "REC-2024-001234"
    template_id INT REFERENCES test_templates(id),
    standard_id INT REFERENCES standards(id),
    
    -- Record metadata
    title VARCHAR(255),
    category VARCHAR(100), -- Duplicated from template for faster queries
    
    -- Lifecycle and status
    status VARCHAR(50) NOT NULL DEFAULT 'draft', -- e.g., draft, submitted, under_review, approved, rejected, closed
    priority VARCHAR(50), -- e.g., low, medium, high, critical
    
    -- Scheduling
    scheduled_date TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    due_date TIMESTAMP,
    
    -- Relationships
    parent_record_id INT REFERENCES records(id), -- For follow-up records
    batch_number VARCHAR(100),
    product_id VARCHAR(100),
    process_id VARCHAR(100),
    
    -- Location and context
    location VARCHAR(255),
    department VARCHAR(100),
    shift VARCHAR(50),
    
    -- Personnel
    created_by INT REFERENCES users(id),
    assigned_to INT REFERENCES users(id),
    approved_by INT REFERENCES users(id),
    reviewed_by INT REFERENCES users(id),
    
    -- Results summary
    overall_compliance BOOLEAN,
    compliance_score NUMERIC(5,2), -- Percentage
    failed_items_count INT DEFAULT 0,
    
    -- Comments and notes
    notes TEXT,
    internal_notes TEXT, -- Not visible to all users
    
    -- Attachments
    attachments JSONB, -- e.g., [{"name": "photo1.jpg", "url": "...", "type": "image"}]
    
    -- Audit trail
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Flexible metadata
    meta JSONB, -- e.g., {"equipment_used": ["machine_01"], "environmental_conditions": {}}
    
    -- Full-text search
    search_vector tsvector
);

CREATE INDEX idx_records_template ON records(template_id);
CREATE INDEX idx_records_standard ON records(standard_id);
CREATE INDEX idx_records_status ON records(status);
CREATE INDEX idx_records_created_by ON records(created_by);
CREATE INDEX idx_records_assigned_to ON records(assigned_to);
CREATE INDEX idx_records_dates ON records(scheduled_date, due_date);
CREATE INDEX idx_records_batch ON records(batch_number);
CREATE INDEX idx_records_search ON records USING gin(search_vector);

-- Record details / compliance results
CREATE TABLE record_items (
    id SERIAL PRIMARY KEY,
    record_id INT REFERENCES records(id) ON DELETE CASCADE,
    criteria_id INT REFERENCES standard_criteria(id),
    template_field_id INT REFERENCES template_fields(id),
    
    -- Value storage
    value TEXT,
    numeric_value NUMERIC, -- For calculations
    
    -- Compliance
    compliance BOOLEAN,
    deviation NUMERIC, -- Difference from target/limit
    
    -- Additional context
    remarks TEXT,
    attachments JSONB,
    
    -- Measurement details
    measured_at TIMESTAMP,
    measured_by INT REFERENCES users(id),
    equipment_used VARCHAR(255),
    
    -- Audit
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    meta JSONB
);

CREATE INDEX idx_record_items_record ON record_items(record_id);
CREATE INDEX idx_record_items_criteria ON record_items(criteria_id);
CREATE INDEX idx_record_items_compliance ON record_items(compliance);

-- ----------------------------------------------------------------------------
-- 5. NON-CONFORMANCE TRACKING
-- ----------------------------------------------------------------------------

CREATE TABLE non_conformances (
    id SERIAL PRIMARY KEY,
    nc_number VARCHAR(100) UNIQUE NOT NULL,
    record_id INT REFERENCES records(id),
    record_item_id INT REFERENCES record_items(id),
    
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    severity VARCHAR(50) NOT NULL, -- e.g., critical, major, minor
    category VARCHAR(100), -- e.g., product, process, documentation
    
    -- Root cause analysis
    root_cause TEXT,
    root_cause_category VARCHAR(100),
    
    -- Corrective actions
    immediate_action TEXT,
    corrective_action TEXT,
    preventive_action TEXT,
    
    -- Timeline
    detected_date TIMESTAMP NOT NULL,
    target_closure_date TIMESTAMP,
    closed_date TIMESTAMP,
    
    -- Status
    status VARCHAR(50) DEFAULT 'open', -- open, investigating, action_planned, implementing, verifying, closed
    
    -- Responsibility
    reported_by INT REFERENCES users(id),
    assigned_to INT REFERENCES users(id),
    verified_by INT REFERENCES users(id),
    
    -- Impact
    cost_impact NUMERIC(12,2),
    customer_impact BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    meta JSONB
);

CREATE INDEX idx_nc_record ON non_conformances(record_id);
CREATE INDEX idx_nc_status ON non_conformances(status);
CREATE INDEX idx_nc_severity ON non_conformances(severity);

-- ----------------------------------------------------------------------------
-- 6. WORKFLOWS AND APPROVALS
-- ----------------------------------------------------------------------------

CREATE TABLE workflows (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    code VARCHAR(100) UNIQUE NOT NULL,
    standard_id INT REFERENCES standards(id),
    template_id INT REFERENCES test_templates(id),
    
    description TEXT,
    trigger_event VARCHAR(100), -- e.g., "record_submitted", "nc_detected"
    
    -- Workflow definition
    steps JSONB, -- e.g., [{"step": "review", "role_id": 2, "order": 1, "sla_hours": 24}]
    
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by INT REFERENCES users(id)
);

CREATE INDEX idx_workflows_template ON workflows(template_id);

-- Workflow instances (tracks actual workflow executions)
CREATE TABLE workflow_instances (
    id SERIAL PRIMARY KEY,
    workflow_id INT REFERENCES workflows(id),
    record_id INT REFERENCES records(id),
    nc_id INT REFERENCES non_conformances(id),
    
    current_step INT DEFAULT 1,
    status VARCHAR(50) DEFAULT 'in_progress', -- in_progress, completed, cancelled
    
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    
    meta JSONB
);

CREATE INDEX idx_workflow_instances_record ON workflow_instances(record_id);

-- Individual step executions
CREATE TABLE workflow_step_executions (
    id SERIAL PRIMARY KEY,
    workflow_instance_id INT REFERENCES workflow_instances(id) ON DELETE CASCADE,
    step_number INT NOT NULL,
    step_name VARCHAR(100),
    
    assigned_to INT REFERENCES users(id),
    status VARCHAR(50) DEFAULT 'pending', -- pending, in_progress, approved, rejected, completed
    
    action VARCHAR(100), -- e.g., "approve", "reject", "request_changes"
    comments TEXT,
    
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    due_at TIMESTAMP,
    
    performed_by INT REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_step_exec_instance ON workflow_step_executions(workflow_instance_id);
CREATE INDEX idx_step_exec_assigned ON workflow_step_executions(assigned_to);

-- ----------------------------------------------------------------------------
-- 7. AUDIT TRAIL
-- ----------------------------------------------------------------------------

CREATE TABLE audit_log (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL,
    record_id INT NOT NULL,
    action VARCHAR(50) NOT NULL, -- insert, update, delete
    
    user_id INT REFERENCES users(id),
    username VARCHAR(255),
    
    old_values JSONB,
    new_values JSONB,
    changed_fields JSONB, -- Array of field names that changed
    
    ip_address INET,
    user_agent TEXT,
    
    timestamp TIMESTAMP DEFAULT NOW(),
    
    meta JSONB
);

CREATE INDEX idx_audit_table_record ON audit_log(table_name, record_id);
CREATE INDEX idx_audit_user ON audit_log(user_id);
CREATE INDEX idx_audit_timestamp ON audit_log(timestamp);

-- ----------------------------------------------------------------------------
-- 8. NOTIFICATIONS AND ALERTS
-- ----------------------------------------------------------------------------

CREATE TABLE notifications (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id),
    
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    type VARCHAR(50), -- e.g., info, warning, alert, reminder
    priority VARCHAR(50) DEFAULT 'normal',
    
    related_record_id INT,
    related_nc_id INT,
    
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMP,
    
    action_url TEXT,
    
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP
);

CREATE INDEX idx_notifications_user ON notifications(user_id);
CREATE INDEX idx_notifications_read ON notifications(is_read);

-- ----------------------------------------------------------------------------
-- 9. REPORTS AND ANALYTICS
-- ----------------------------------------------------------------------------

CREATE TABLE saved_reports (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    report_type VARCHAR(100), -- e.g., compliance_summary, trend_analysis, nc_report
    
    filters JSONB, -- Saved filter criteria
    columns JSONB, -- Column configuration
    chart_config JSONB, -- Chart settings if applicable
    
    is_public BOOLEAN DEFAULT FALSE,
    
    created_by INT REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ----------------------------------------------------------------------------
-- 10. DOCUMENT MANAGEMENT
-- ----------------------------------------------------------------------------

CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    document_number VARCHAR(100) UNIQUE NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100), -- e.g., procedure, work_instruction, form, certificate
    
    file_name VARCHAR(255),
    file_path TEXT,
    file_type VARCHAR(50),
    file_size BIGINT, -- bytes
    
    version VARCHAR(50) DEFAULT '1.0',
    status VARCHAR(50) DEFAULT 'draft', -- draft, review, approved, obsolete
    
    standard_id INT REFERENCES standards(id),
    template_id INT REFERENCES test_templates(id),
    
    effective_date DATE,
    review_date DATE,
    obsolete_date DATE,
    
    created_by INT REFERENCES users(id),
    approved_by INT REFERENCES users(id),
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    meta JSONB
);

CREATE INDEX idx_documents_standard ON documents(standard_id);
CREATE INDEX idx_documents_status ON documents(status);

-- ----------------------------------------------------------------------------
-- 11. TRIGGERS FOR AUTOMATED UPDATES
-- ----------------------------------------------------------------------------

-- Update timestamps automatically
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply to relevant tables
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_standards_updated_at BEFORE UPDATE ON standards
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_criteria_updated_at BEFORE UPDATE ON standard_criteria
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_templates_updated_at BEFORE UPDATE ON test_templates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_records_updated_at BEFORE UPDATE ON records
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_record_items_updated_at BEFORE UPDATE ON record_items
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_nc_updated_at BEFORE UPDATE ON non_conformances
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Update search vector for records
CREATE OR REPLACE FUNCTION update_record_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector := 
        setweight(to_tsvector('english', coalesce(NEW.record_number, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(NEW.title, '')), 'B') ||
        setweight(to_tsvector('english', coalesce(NEW.notes, '')), 'C');
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_records_search BEFORE INSERT OR UPDATE ON records
    FOR EACH ROW EXECUTE FUNCTION update_record_search_vector();

-- ----------------------------------------------------------------------------
-- END OF SCHEMA
-- ----------------------------------------------------------------------------
