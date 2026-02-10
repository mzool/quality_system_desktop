# Validation Rules Guide

## What are Validation Rules?

Validation rules are automatic checks that ensure users enter correct data when filling out quality records. They help prevent errors and maintain data quality by enforcing specific requirements.

## How Validation Rules Work

When you create a criteria (inspection point), you can set validation rules to control what kind of data users can enter. The system will automatically check the entered data and show errors if it doesn't meet the requirements.

## Types of Validation Rules

### For Text Fields

#### **Minimum Length**
- ☑️ Check "Minimum Length" and set a number (e.g., 5)
- **What it does**: Users must enter at least this many characters
- **Example**: If you set minimum 5, users cannot enter "T1" (only 2 characters)

#### **Maximum Length**
- ☑️ Check "Maximum Length" and set a number (e.g., 100)
- **What it does**: Users cannot enter more than this many characters
- **Example**: If you set maximum 100, users get an error if they type more than 100 characters

#### **Must Match Pattern (Regex)**
- ☑️ Check "Must Match Pattern" and enter a pattern
- **What it does**: Users must enter data in a specific format
- **Common Examples**:
  - `^[A-Z][0-9]{3}$` = Must start with a capital letter followed by exactly 3 numbers (like "A123")
  - `^\d{4}-\d{2}-\d{2}$` = Date format YYYY-MM-DD (like "2026-02-10")
  - `^[A-Z]{2,5}$` = 2 to 5 capital letters only (like "ABC" or "QWERT")
  - `^[0-9]+$` = Only numbers allowed
  - `^[a-zA-Z\s]+$` = Only letters and spaces

#### **Required Field**
- ☑️ Check "Required Field"
- **What it does**: Users must enter something (cannot leave empty)

### For Numeric Fields

#### **Minimum Value**
- ☑️ Check "Minimum Value" and set a number (e.g., 0)
- **What it does**: Users cannot enter a number smaller than this
- **Example**: If you set minimum 0, users get an error if they enter -5

#### **Maximum Value**
- ☑️ Check "Maximum Value" and set a number (e.g., 100)
- **What it does**: Users cannot enter a number larger than this
- **Example**: If you set maximum 100, users get an error if they enter 150

#### **Required Field**
- ☑️ Check "Required Field"
- **What it does**: Users must enter a number (cannot leave empty)

## Real-World Examples

### Example 1: Serial Number Field
**Scenario**: You want serial numbers to follow the format "SN-" + 6 digits
- Data Type: `text`
- Pattern: `^SN-\d{6}$`
- Required: ☑️ Yes

**Result**: Users can only enter values like "SN-123456" or "SN-999999"

### Example 2: Temperature Reading
**Scenario**: Temperature must be between -20°C and 80°C
- Data Type: `numeric`
- Minimum Value: ☑️ -20
- Maximum Value: ☑️ 80
- Required: ☑️ Yes

**Result**: Users get an error if they enter -25 or 90

### Example 3: Operator Name
**Scenario**: Operator name must be 3-50 characters long
- Data Type: `text`
- Minimum Length: ☑️ 3
- Maximum Length: ☑️ 50
- Required: ☑️ Yes

**Result**: Users must enter a name between 3 and 50 characters

### Example 4: Part Code
**Scenario**: Part code must be exactly 2 capital letters + 4 numbers (like "AB1234")
- Data Type: `text`
- Pattern: `^[A-Z]{2}\d{4}$`
- Required: ☑️ Yes

**Result**: Only values like "AB1234", "XY9876" are accepted

## Tips for Using Validation Rules

1. **Start Simple**: Don't add too many rules at once. Start with "Required Field" for important data.

2. **Test Your Patterns**: When using regex patterns, test them first to make sure they work as expected.

3. **Provide Help Text**: Always fill in the "Help Text" field to explain to users what format they should enter (e.g., "Enter serial number in format SN-XXXXXX").

4. **Be Reasonable**: Don't make rules too strict. If a field might vary, don't force a specific pattern.

5. **Use Numeric Limits Wisely**: Set realistic min/max values based on real-world measurements.

## No More JSON Required!

**OLD WAY** (difficult for normal users):
```json
{"pattern": "^[A-Z][0-9]{3}$", "min_length": 4, "max_length": 4, "required": true}
```

**NEW WAY** (easy checkboxes and inputs):
- ☑️ Must Match Pattern: `^[A-Z][0-9]{3}$`
- ☑️ Minimum Length: 4
- ☑️ Maximum Length: 4
- ☑️ Required Field

Much easier! Just check boxes and enter numbers - no JSON knowledge needed!
