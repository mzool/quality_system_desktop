# Excel Import Templates

This document describes the Excel file formats for importing data into the Quality Management System.

## 1. Standards Import

### File Format: `standards_import.xlsx`

**Required Columns:**
- `Code` (Text) - Unique standard code (e.g., "ISO-9001")
- `Name` (Text) - Standard name
- `Version` (Text) - Version number (e.g., "2015")

**Optional Columns:**
- `Industry` (Text) - Industry category (e.g., "manufacturing", "healthcare")
- `Description` (Text) - Detailed description
- `Effective Date` (Date) - When standard becomes effective (format: YYYY-MM-DD)

**Example:**
```
Code        | Name                      | Version | Industry      | Description                    | Effective Date
-----------|---------------------------|---------|---------------|--------------------------------|---------------
ISO-9001   | Quality Management System | 2015    | General       | Requirements for QMS           | 2015-09-15
ISO-14001  | Environmental Management  | 2015    | General       | Environmental management req.  | 2015-09-15
IATF-16949 | Automotive QMS           | 2016    | Automotive    | Automotive industry standard   | 2016-10-01
```

**How to Use:**
1. Create Excel file with columns above
2. Fill in your standards data
3. In application: Standards tab → Import from Excel
4. Select your file
5. Standards are imported and ready to use

---

## 2. Criteria Import

### File Format: `criteria_import.xlsx`

**Required Columns:**
- `Code` (Text) - Criteria code (e.g., "4.1", "DIM-001")
- `Title` (Text) - Short title
- `Type` (Text) - Data type: numeric, boolean, text, select, multiselect, date, file

**Optional Columns:**
- `Description` (Text) - Detailed description
- `Requirement Type` (Text) - mandatory, conditional, optional (default: mandatory)
- `Min` (Number) - Minimum acceptable value
- `Max` (Number) - Maximum acceptable value
- `Unit` (Text) - Measurement unit (mm, °C, ppm, etc.)
- `Severity` (Text) - critical, major, minor (default: minor)
- `Section` (Text) - Section code for organization
- `Options` (Text) - For select/multiselect types, separate with semicolons

**Example:**
```
Code    | Title                  | Type    | Description              | Min  | Max  | Unit | Severity | Options
--------|------------------------|---------|--------------------------|------|------|------|----------|------------------
DIM-001 | Overall Length         | numeric | Product overall length   | 99.5 | 100.5| mm   | major    |
VIS-001 | Surface Finish         | select  | Visual surface check     |      |      |      | minor    | Good;Fair;Poor
FUNC-01 | Operation Test         | boolean | Functional test          |      |      |      | critical |
TEMP-01 | Operating Temperature  | numeric | Max operating temp       | 20   | 80   | °C   | major    |
```

**How to Use:**
1. Create standard first (if not exists)
2. Create Excel file with criteria
3. In application code or custom import dialog:
```python
from excel_handler import ExcelHandler

handler = ExcelHandler(session)
criteria_list = handler.import_criteria_from_excel(
    filepath='criteria_import.xlsx',
    standard_id=1  # ID of the standard
)
```

---

## 3. Filled Template Import

### File Format: Template exported from application

**Workflow:**
1. **Export Template**: In application, select a template and export to Excel
2. **Fill Template**: Inspector fills in the "Value" column
3. **Import Filled Template**: Import back to create a record

**Template Structure (Auto-generated):**
```
Section     | Code    | Title              | Type    | Required | Min  | Max  | Unit | Value    | Compliance | Remarks
------------|---------|--------------------|---------| ---------|------|------|------|----------|------------|--------
Dimensional | DIM-001 | Overall Length     | numeric | Yes      | 99.5 | 100.5| mm   | 100.2    | Pass       |
Visual      | VIS-001 | Surface Finish     | select  | Yes      |      |      |      | Good     | Pass       |
Functional  | FUNC-01 | Operation Test     | boolean | Yes      |      |      |      | Yes      | Pass       |
```

**Fill Guidelines:**
- **Value Column**: Enter your measurement or observation
- **Compliance Column**: Auto-calculated for numeric types, or enter "Pass"/"Fail"
- **Remarks Column**: Optional notes

**Import Code:**
```python
from excel_handler import ExcelHandler

handler = ExcelHandler(session)
record = handler.import_record_from_filled_template(
    filepath='filled_inspection_form.xlsx',
    template_id=1,
    created_by_id=user.id,
    title='Daily Inspection - Batch 450',
    batch_number='BATCH-450'
)
```

---

## 4. Bulk Records Export Format

When you export records to Excel, the format is:

```
Record Number | Title              | Template         | Status   | Priority | Scheduled Date      | Completed Date     | Batch Number | Product ID | Location | Department | Created By  | Assigned To | Compliance Score | Failed Items | Overall Compliance | Notes
--------------|--------------------| -----------------|----------|----------|---------------------|--------------------|--------------| -----------|----------|------------|-------------|-------------|------------------|--------------|--------------------|---------
REC-2026-001  | Daily Inspection   | Final Inspection | approved | medium   | 2026-02-09 08:00:00 | 2026-02-09 09:30:00| BATCH-450    | PROD-123   | Line 3   | Production | John Smith  | Jane Doe    | 95.5             | 1            | Pass               |
REC-2026-002  | Incoming VQA       | VQA Template     | rejected | high     | 2026-02-09 10:00:00 | 2026-02-09 11:00:00| BATCH-451    | PROD-124   | Incoming | QC         | Alice Brown | Bob Jones   | 75.0             | 5            | Fail               | Multiple defects
```

**Color Coding:**
- ✅ Green cells = Passed/Approved
- ❌ Red cells = Failed/Rejected
- 🟡 Orange cells = Under Review
- ⚪ Gray cells = Draft/Pending

---

## 5. Best Practices

### Standards Import
- Use consistent code format (e.g., "ISO-XXXX", "ASTM-YYYY")
- Include version in code for easy identification
- Fill description field for better documentation

### Criteria Import
- Use hierarchical codes (e.g., "4.1", "4.1.1", "4.1.2")
- Always specify unit for numeric types
- Provide realistic min/max values
- Use select type with options for standardized responses

### Filled Templates
- Complete all required fields
- For numeric values, include only the number (no units)
- Use consistent format for dates (YYYY-MM-DD)
- Add remarks for borderline cases

### General Tips
- Save files with descriptive names including date
- Keep a master copy of import templates
- Test import with small sample first
- Review imported data before using in production
- Backup database before large imports

---

## 6. Error Handling

### Common Import Errors

**"Missing required column"**
- Ensure Excel file has all required columns
- Check spelling matches exactly (case-sensitive)
- No extra spaces in column headers

**"Duplicate code"**
- Standard code + version must be unique
- Criteria code must be unique within a standard
- Change code or check if already exists

**"Invalid date format"**
- Use YYYY-MM-DD format
- Or Excel date cells formatted as Date
- Avoid text dates like "Feb 9, 2026"

**"Foreign key constraint failed"**
- Referenced entity doesn't exist
- Create parent entity first (e.g., standard before criteria)
- Check IDs are correct

---

## 7. Advanced: Custom Import Scripts

For complex imports, you can write Python scripts:

```python
from database import get_db_session
from excel_handler import ExcelHandler
from models import Standard, StandardCriteria
import pandas as pd

session = get_db_session()
handler = ExcelHandler(session)

# Import from custom format
df = pd.read_excel('custom_format.xlsx')

for _, row in df.iterrows():
    # Custom processing
    standard = Standard(
        code=row['MyCode'],
        name=row['MyName'],
        # ... custom mapping
    )
    session.add(standard)

session.commit()
```

---

## 8. Sample Files

Sample Excel files are available in `samples/` directory:
- `sample_standards.xlsx` - Example standards import
- `sample_criteria.xlsx` - Example criteria import
- `sample_template_filled.xlsx` - Example filled inspection form

You can use these as templates for your own data.
