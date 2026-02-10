# Quality Management System - Desktop Application

A comprehensive multiplatform desktop application for managing quality inspections, standards compliance, non-conformances, and generating detailed reports.

## Features

### ✅ Core Functionality
- **Records Management**: Create, edit, and track quality inspection records
- **Templates/Sheets**: Define reusable test templates with visual layouts
- **Standards & Criteria**: Manage quality standards (ISO 9001, ISO 14001, etc.)
- **Non-Conformance Tracking**: Full 8D problem-solving workflow
- **User Management**: Role-based access control
- **Workflow Engine**: Automated approval workflows

### 📊 Reporting & Analytics
- Compliance summary reports
- Trend analysis
- Inspector performance metrics
- Department performance tracking
- NC (Non-Conformance) statistics
- Custom report builder

### 📁 Import/Export
- **Excel Import**: Import standards, criteria, and filled templates
- **Excel Export**: Export records, detailed results, and templates as fillable forms
- **PDF Generation**: Professional PDF reports for records and NCs
- **Batch Operations**: Import/export multiple records at once

### 🖼️ Image Support
- Upload images for records, items, and non-conformances
- Automatic thumbnail generation
- Image compression and optimization
- Annotation tools (rectangles, circles, text)
- Before/after comparison images
- Watermarking support

### 🔐 Database
- SQLite database (portable, no server required)
- Full audit trail
- Automatic backups
- Transaction safety

## Installation

### Prerequisites
- Python 3.10 or higher
- pip (Python package installer)

### Step 1: Clone or Download
Download this project to your computer.

### Step 2: Create Virtual Environment (Recommended)
```bash
# Navigate to project directory
cd quality_system

# Create virtual environment
python -m venv env

# Activate virtual environment
# On Windows:
env\Scripts\activate

# On Linux/Mac:
source env/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Run the Application
```bash
python main.py
```

## First Time Setup

When you run the application for the first time:

1. **Database Creation**: The database will be automatically created in `~/.quality_system/quality_system.db`
2. **Default User**: A default admin user is created:
   - **Username**: `admin`
   - **Password**: `admin123`
   - ⚠️ **IMPORTANT**: Change this password immediately!

3. **Default Roles**: Five roles are created:
   - Admin (full access)
   - QA Manager
   - Quality Inspector
   - Auditor
   - Viewer (read-only)

## Usage Guide

### Creating a Standard

1. Go to **Standards** tab
2. Click **New Standard** (or import from Excel)
3. Fill in:
   - Code (e.g., "ISO-9001")
   - Name
   - Version
   - Industry
   - Description

### Importing Standards from Excel

**Excel file format**:
| Code | Name | Version | Industry | Description | Effective Date |
|------|------|---------|----------|-------------|----------------|
| ISO-9001 | Quality Management | 2015 | General | ... | 2015-09-15 |

1. Prepare Excel file with required columns
2. Go to **Standards** tab
3. Click **Import from Excel**
4. Select your file
5. Standards and criteria are imported

### Creating a Template/Sheet

Templates define the structure of inspection forms.

**Example Use Cases**:
- Daily final product inspection
- Incoming material inspection (VQA)
- Process audit checklist
- Equipment calibration form

**Template Structure**:
```json
{
  "layout": {
    "type": "grid",
    "columns": 2,
    "sections": [
      {"id": "visual", "title": "Visual Checks"},
      {"id": "dimensional", "title": "Measurements"}
    ]
  }
}
```

### Creating a Record (Inspection)

1. Go to **Records** tab
2. Click **New Record**
3. Select template
4. Fill in record details:
   - Title
   - Batch number
   - Product ID
   - Location
5. Fill in measurements/values for each criterion
6. Upload images if needed
7. Submit for approval

### Generating PDFs

**For Records**:
1. Select a record in the Records tab
2. Click **Generate PDF**
3. Choose save location
4. Professional PDF report is created with:
   - Record summary
   - Compliance results
   - Detailed measurements
   - Signature section

**For Non-Conformances**:
1. Select an NC in the Non-Conformances tab
2. Click **Generate PDF**
3. 8D report format with root cause analysis

### Excel Export

**Export All Records**:
1. Go to Records tab
2. Click **Export to Excel**
3. Formatted Excel file with color coding:
   - Green = Passed
   - Red = Failed
   - Orange = Under Review

**Export Template as Fillable Form**:
1. Export template to Excel
2. Inspectors can fill it offline
3. Import filled template to create record

### Image Management

**Uploading Images**:
```python
from image_handler import save_image_for_record

# In your code
image_attachment = save_image_for_record(
    session=session,
    image_path="/path/to/defect_photo.jpg",
    record_id=123,
    description="Surface scratch on left side",
    uploaded_by_id=current_user.id
)
```

**Image Features**:
- Automatic resizing (max 1920x1920)
- JPEG compression (85% quality)
- Thumbnail generation (200x200)
- Storage in organized folders
- Metadata tracking (size, dimensions, upload date)

### Reports

**Dashboard Metrics**:
- Total records (last 30 days)
- Pending approvals
- Open non-conformances
- Average compliance score
- Recent activity

**Compliance Summary**:
```python
from reports import ReportsGenerator

reports_gen = ReportsGenerator(session)
report = reports_gen.compliance_summary_report(
    start_date=datetime(2026, 1, 1),
    end_date=datetime(2026, 12, 31),
    department="Production"
)

print(f"Pass Rate: {report['pass_rate']}%")
print(f"Average Score: {report['average_score']}%")
```

**Trend Analysis**:
- Daily, weekly, monthly, or yearly trends
- Pass/fail rates over time
- Compliance score trends

**Failure Analysis**:
- Top 20 most frequently failing criteria
- Severity breakdown
- Department-specific failures

## Database Schema

The application uses a comprehensive database schema with 16+ tables:

### Main Tables
- **users** - User accounts and roles
- **standards** - Quality standards (ISO, customer specs)
- **standard_criteria** - Individual check items
- **test_templates** - Reusable inspection forms
- **records** - Actual inspection instances
- **record_items** - Individual measurements/results
- **non_conformances** - NC tracking and 8D
- **workflows** - Approval workflows
- **image_attachments** - Image storage

### Supporting Tables
- roles
- standard_sections
- template_fields
- workflow_instances
- workflow_step_executions
- audit_log
- notifications
- saved_reports
- documents

## Database Location

**Default Location**: `~/.quality_system/`
- Database: `quality_system.db`
- Images: `images/`
- Backups: `backups/`

**Custom Location**:
```python
from database import init_database

db = init_database(db_path='/custom/path/mydb.db')
```

## Backup & Restore

### Manual Backup
1. Go to **Tools** → **Backup Database**
2. Backup saved to `~/.quality_system/backups/`
3. Filename: `quality_system_backup_YYYYMMDD_HHMMSS.db`

### Programmatic Backup
```python
from database import db_manager

backup_path = db_manager.backup_database()
print(f"Backed up to: {backup_path}")
```

### Restore from Backup
1. Close the application
2. Replace `quality_system.db` with backup file
3. Restart application

## Advanced Usage

### Custom Report Example
```python
from reports import ReportsGenerator
import pandas as pd

# Generate compliance report
reports = ReportsGenerator(session)
data = reports.compliance_summary_report(
    start_date=datetime(2026, 1, 1),
    end_date=datetime(2026, 3, 31)
)

# Convert to DataFrame
df = reports.export_report_to_dataframe(data['status_breakdown'])

# Export to Excel with custom formatting
df.to_excel('custom_report.xlsx', index=False)
```

### Batch Image Processing
```python
from image_handler import ImageHandler
from pathlib import Path

handler = ImageHandler(session)

# Process all images in a folder
image_folder = Path('/path/to/inspection_photos')
for image_path in image_folder.glob('*.jpg'):
    handler.save_image(
        str(image_path),
        entity_type='record',
        entity_id=123,
        description=image_path.stem,
        uploaded_by_id=1
    )
```

### Programmatic Record Creation
```python
from models import Record, RecordItem
from datetime import datetime

# Create record
record = Record(
    record_number='REC-2026-001',
    template_id=1,
    standard_id=1,
    title='Daily Final Inspection - Batch 450',
    batch_number='BATCH-450',
    product_id='PROD-12345',
    location='Line 3',
    department='Production',
    created_by_id=1,
    assigned_to_id=1,
    status='draft'
)

session.add(record)
session.flush()

# Add items
item = RecordItem(
    record_id=record.id,
    criteria_id=1,
    value='50.2',
    numeric_value=50.2,
    compliance=True,
    measured_by_id=1
)

session.add(item)
session.commit()
```

## Keyboard Shortcuts

- **Ctrl+N**: New Record
- **Ctrl+R**: Refresh
- **Ctrl+Q**: Quit
- **F5**: Refresh current tab

## Troubleshooting

### Database Locked Error
**Problem**: SQLite database is locked
**Solution**: 
- Close all instances of the application
- Check no other programs are accessing the database
- Restart the application

### Import Fails
**Problem**: Excel import fails
**Solution**:
- Check Excel file has required columns
- Ensure data types are correct
- Check for duplicate codes/names

### PDF Generation Fails
**Problem**: PDF generation error
**Solution**:
- Check you have write permissions
- Ensure reportlab is installed correctly
- Try a different output path

## Development

### Project Structure
```
quality_system/
├── main.py                 # Main application
├── models.py              # SQLAlchemy models
├── database.py            # Database configuration
├── excel_handler.py       # Excel import/export
├── pdf_generator.py       # PDF generation
├── image_handler.py       # Image handling
├── reports.py             # Reports & analytics
├── requirements.txt       # Dependencies
├── migrations/
│   └── 001.sql           # Database schema
└── env/                   # Virtual environment
```

### Adding Custom Features

**Add Custom Report**:
1. Edit `reports.py`
2. Add method to `ReportsGenerator` class
3. Add button in `main.py` reports tab
4. Connect to your method

**Add Custom Template Field**:
1. Update `test_templates.form_config` JSON
2. Add rendering logic in GUI
3. Update PDF generator if needed

## License

This project is provided as-is for quality management purposes.

## Support

For issues or questions:
1. Check this README
2. Review the code comments
3. Check database schema documentation in `migrations/001.sql`

## Version History

**v1.0.0** (2026-02-09)
- Initial release
- Full CRUD operations for all entities
- Excel import/export
- PDF generation
- Image support
- Comprehensive reporting
- Dashboard analytics

## Future Enhancements

Potential additions:
- [ ] Web interface (Flask/FastAPI backend)
- [ ] Mobile app companion
- [ ] Email notifications
- [ ] Digital signatures
- [ ] Barcode/QR code scanning
- [ ] Real-time collaboration
- [ ] Cloud synchronization
- [ ] AI-powered defect detection
- [ ] Statistical Process Control (SPC) charts
- [ ] Integration with ERP systems

---

**Built with Python, SQLAlchemy, PyQt6, and ❤️**
