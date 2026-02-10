# Template Configuration Guide

## What Template Configurations Do

When you create or edit a template, you can configure three main areas that affect how users fill out records:

1. **Layout Configuration** - How fields are arranged on screen
2. **Section Configuration** - How fields are grouped together
3. **Form Configuration** - How users interact with the form

---

## 1. Layout Configuration

### **Columns** (1-6)
Controls how many columns of fields appear side-by-side.

**Visual Examples:**

```
1 Column:                2 Columns:               3 Columns:
[Name        ]           [Name    ] [Date  ]     [Name] [Date] [Time]
[Date        ]           [Product ] [Batch ]     [Prod] [Batch] [Qty]
[Description ]           [Desc              ]     [Description       ]
```

**When to use:**
- **1-2 columns**: Simple forms, mobile-friendly
- **3-4 columns**: Complex forms with many fields
- **5-6 columns**: Very compact layouts (dense data entry)

### **Style**
Controls the visual appearance of the form.

- **grid**: Table-like layout with borders and cells
- **linear**: Simple vertical list (easiest to read)
- **compact**: Minimal spacing (fits more on screen)
- **spacious**: Extra breathing room (easier on eyes)
- **wizard**: Step-by-step multi-page form

### **Orientation**
Controls label placement relative to fields.

```
vertical:               horizontal:
Name:                   Name: [          ]
[          ]            Date: [          ]

Date:
[          ]
```

**When to use:**
- **vertical**: Better for mobile, narrow screens
- **horizontal**: Better for desktop, faster data entry
- **auto**: System chooses based on screen size

### **Spacing** (0-50 pixels)
Distance between form fields.

```
Spacing = 0:            Spacing = 20:

[Name]                  [Name]
[Date]                  
[Product]               [Date]
                        
                        [Product]
```

---

## 2. Section Configuration

**What it does**: Divides the form into logical groups with headers.

**Example Input:**
```
General Information
Measurements and Tests
Quality Results
Sign-off and Approval
```

**What users see:**
```
╔═══════════════════════════════════╗
║ General Information               ║
╠═══════════════════════════════════╣
  Name:        [          ]
  Date:        [          ]
  Operator:    [          ]

╔═══════════════════════════════════╗
║ Measurements and Tests            ║
╠═══════════════════════════════════╣
  Length:      [    ] mm
  Weight:      [    ] kg
  Temperature: [    ] °C

╔═══════════════════════════════════╗
║ Quality Results                   ║
╠═══════════════════════════════════╣
  Pass/Fail:   [    ]
  Score:       [    ] %

╔═══════════════════════════════════╗
║ Sign-off and Approval             ║
╠═══════════════════════════════════╣
  Inspector:   [          ]
  Date:        [          ]
```

**Benefits:**
- Makes long forms easier to navigate
- Groups related fields together
- Creates a clear structure
- Users can focus on one section at a time

---

## 3. Form Configuration

### **Validation Level**

- **strict**: All required fields must be filled correctly before saving
  - ✅ Use for: Critical quality checks, regulatory compliance
  - ❌ Users CANNOT save until everything is correct

- **normal**: Basic checks, required fields must be filled
  - ✅ Use for: Most standard forms
  - ⚠️ Shows warnings but allows some flexibility

- **permissive**: Shows warnings but allows saving anyway
  - ✅ Use for: Informal checklists, draft-heavy processes
  - ⚠️ Data quality may suffer

- **none**: No validation (not recommended)
  - ❌ Avoid unless absolutely necessary

### **Submit Button Text**

Customize what the button says:
- "Save Record" (default)
- "Complete Inspection"
- "Submit Report"
- "Finalize Audit"
- "Sign Off"

Makes the action clearer to users!

### **Enable Auto-save**

☑️ **Checked**: Form saves automatically as users type
- ✅ Great for: Long forms, unreliable networks
- ✅ Users won't lose work if browser crashes
- ⚠️ May slow down on very large forms

☐ **Unchecked**: Users must click Save button
- ✅ More control over when data is saved
- ⚠️ Risk of losing work

### **Show Progress Indicator**

☑️ **Checked**: Displays "45% Complete" or progress bar
```
[████████░░░░░░░░]  45% Complete

✓ General Information
✓ Measurements  
○ Quality Results     ← Currently here
○ Sign-off
```

✅ Use for: Multi-section forms, long inspections
✅ Motivates users to complete the form

### **Allow Saving as Draft**

☑️ **Checked**: Users can save incomplete records
```
[Save as Draft] [Complete & Submit]
```
- ✅ Great for: Complex inspections that take multiple sessions
- ✅ Users can pause and resume later

☐ **Unchecked**: Must complete everything before saving
- ✅ Ensures data completeness
- ⚠️ Users might lose work if interrupted

---

## How to See Configuration in Action

When creating or editing a record:

1. **Select a template** from the dropdown
2. A popup will appear showing:
   - Layout settings (columns, style, etc.)
   - Section names
   - Form settings (validation, auto-save, etc.)
   - Number of fields in the template

**Example popup:**
```
Template Configuration Applied

Layout:
  • Columns: 2
  • Style: grid  
  • Orientation: horizontal
  • Spacing: 10px

Sections:
  • General Information
  • Measurements
  • Results

Form Settings:
  • Validation: strict
  • Auto-save enabled
  • Progress indicator enabled
  • Draft mode allowed

This template has 15 fields configured.
```

---

## Best Practices

### For Simple Forms (5-10 fields)
```yaml
Columns: 1-2
Style: linear
Sections: None or 1-2 max
Validation: normal
```

### For Standard Inspections (10-30 fields)
```yaml
Columns: 2
Style: grid
Sections: 3-4 logical groups
Validation: strict
Auto-save: enabled
Progress: enabled
Draft: enabled
```

### For Complex Audits (30+ fields)
```yaml
Columns: 2-3
Style: wizard (step-by-step)
Sections: 5-8 clear sections
Validation: strict
Auto-save: enabled
Progress: enabled
Draft: enabled
```

### For Mobile/Field Use
```yaml
Columns: 1
Style: linear or spacious
Orientation: vertical
Spacing: 15-20px
Draft: enabled
```

---

## Tips

1. **Start Simple**: Don't over-configure. Test with 1-2 sections first.

2. **Match Your Process**: If your paper form has sections, use them in the template too.

3. **Test the Template**: Create a test record to see how it looks before rolling out.

4. **Get User Feedback**: Ask operators if the form is easy to use.

5. **Iterate**: You can always edit the template later to improve it.

---

## Quick Reference

| Setting | Effect | Best For |
|---------|--------|----------|
| 1-2 columns | Simple, easy to read | Mobile, new users |
| 3+ columns | Compact, fits more | Desktop, power users |
| Sections | Groups related fields | Long forms (10+ fields) |
| Strict validation | Ensures data quality | Critical processes |
| Auto-save | Protects against data loss | Unstable environments |
| Progress indicator | Shows completion | Multi-step processes |
| Draft mode | Allows pausing work | Complex inspections |

---

## Need Help?

If you're not sure what to configure, use these defaults:
```yaml
Columns: 2
Style: grid
Orientation: horizontal
Spacing: 10px
Validation: normal
Auto-save: enabled
Draft: enabled
```

These work well for 80% of use cases!
