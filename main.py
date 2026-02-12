"""
Main Application - Quality Management System
Multiplatform Desktop Application using PyQt6
"""
import sys
import os

# Set environment variables for better Linux stability
if sys.platform == 'linux':
    # Force gstreamer if available, but if FFmpeg is already loaded, these might not help
    os.environ["QT_MULTIMEDIA_BACKEND"] = "gstreamer"
    os.environ["GST_DEBUG"] = "1"  # Error only
    # Ensure local directory is in path
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QTabWidget,
    QMessageBox, QFileDialog, QToolBar, QStatusBar, QGroupBox,
    QDialog, QFormLayout, QLineEdit, QTextEdit, QComboBox, QDateEdit,
    QCheckBox, QSpinBox, QDoubleSpinBox, QDialogButtonBox, QScrollArea,
    QInputDialog, QHeaderView
)
from PyQt6.QtCore import Qt, QDate, QTimer
from PyQt6.QtGui import QAction, QFont, QImage, QPixmap, QPalette, QColor
from datetime import datetime, timedelta
from pathlib import Path
import json

# Import our modules
from database import init_database, get_db_session, close_db_session
from models import *
from excel_handler import ExcelHandler
from pdf_generator import PDFGenerator
from image_handler import ImageHandler
from reports import ReportsGenerator
from version import __version__, __app_name__
try:
    from updater import Updater
    UPDATER_AVAILABLE = True
except ImportError:
    UPDATER_AVAILABLE = False
    print("Updater module not available")


# ============================================================================
# DIALOG CLASSES
# ============================================================================

class RecordDialog(QDialog):
    """Dialog for creating/editing records"""
    
    def __init__(self, session, current_user, record=None, parent=None):
        super().__init__(parent)
        self.session = session
        self.current_user = current_user
        self.record = record  # None for new record
        
        self.setWindowTitle("Edit Record" if record else "New Record")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        
        self.setup_ui()
        
        if record:
            self.load_record_data()
    
    def setup_ui(self):
        """Setup dialog UI"""
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        
        # Create tabs for record info and items
        tabs = QTabWidget()
        
        # Tab 1: Record Info
        info_widget = QWidget()
        info_scroll = QScrollArea()
        info_scroll.setWidgetResizable(True)
        info_scroll.setWidget(info_widget)
        
        form_layout = QFormLayout()
        info_widget.setLayout(form_layout)
        
        # Record Number (auto-generated or display only)
        self.record_number = QLineEdit()
        if self.record:
            self.record_number.setText(self.record.record_number)
            self.record_number.setReadOnly(True)
        else:
            self.record_number.setPlaceholderText("Auto-generated")
            self.record_number.setReadOnly(True)
        form_layout.addRow("Record Number:", self.record_number)
        
        # Template selection
        self.template_combo = QComboBox()
        self.template_combo.currentIndexChanged.connect(self.on_template_changed)
        self.load_templates()
        form_layout.addRow("Template:*", self.template_combo)
        
        # Title
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Enter record title")
        form_layout.addRow("Title:*", self.title_input)
        
        # Parent Record (for follow-ups, re-inspections, etc.)
        self.parent_record_combo = QComboBox()
        self.parent_record_combo.addItem("-- No Parent Record --", None)
        self.load_parent_records()
        self.parent_record_combo.setToolTip("Link to a parent record for follow-up or related records")
        form_layout.addRow("Parent Record:", self.parent_record_combo)
        
        # Category
        self.category_combo = QComboBox()
        self.category_combo.addItems(['inspection', 'audit', 'vqa', 'ncr', 'calibration', 'testing', 'other'])
        self.category_combo.setEditable(True)
        form_layout.addRow("Category:", self.category_combo)
        
        # Status
        self.status_combo = QComboBox()
        self.status_combo.addItems(['draft', 'in_progress', 'pending_review', 'approved', 'rejected', 'completed'])
        form_layout.addRow("Status:", self.status_combo)
        
        # Priority
        self.priority_combo = QComboBox()
        self.priority_combo.addItems(['low', 'normal', 'high', 'urgent'])
        self.priority_combo.setCurrentText('normal')
        form_layout.addRow("Priority:", self.priority_combo)
        
        # Dates
        self.scheduled_date = QDateEdit()
        self.scheduled_date.setCalendarPopup(True)
        self.scheduled_date.setDate(datetime.now().date())
        form_layout.addRow("Scheduled Date:", self.scheduled_date)
        
        self.due_date = QDateEdit()
        self.due_date.setCalendarPopup(True)
        self.due_date.setDate(datetime.now().date())
        form_layout.addRow("Due Date:", self.due_date)
        
        # Workflow Dates
        self.started_at_input = QDateEdit()
        self.started_at_input.setCalendarPopup(True)
        self.started_at_input.setDate(datetime.now().date())
        self.started_at_input.setSpecialValueText("Not Started")
        self.started_at_input.setToolTip("Date when work started on this record")
        form_layout.addRow("Started At:", self.started_at_input)
        
        self.completed_at_input = QDateEdit()
        self.completed_at_input.setCalendarPopup(True)
        self.completed_at_input.setDate(datetime.now().date())
        self.completed_at_input.setSpecialValueText("Not Completed")
        self.completed_at_input.setToolTip("Date when all work was completed")
        form_layout.addRow("Completed At:", self.completed_at_input)
        
        # Personnel
        self.assigned_combo = QComboBox()
        form_layout.addRow("Assigned To:", self.assigned_combo)
        
        self.reviewed_by_combo = QComboBox()
        self.reviewed_by_combo.addItem("-- Not Reviewed --", None)
        form_layout.addRow("Reviewed By:", self.reviewed_by_combo)
        
        self.approved_by_combo = QComboBox()
        self.approved_by_combo.addItem("-- Not Approved --", None)
        form_layout.addRow("Approved By:", self.approved_by_combo)
        
        # Load users after all combo boxes are created
        self.load_users()
        
        # Location and Context
        self.batch_number_input = QLineEdit()
        self.batch_number_input.setPlaceholderText("Enter batch number")
        form_layout.addRow("Batch Number:", self.batch_number_input)
        
        self.product_id_input = QLineEdit()
        self.product_id_input.setPlaceholderText("Enter product ID")
        form_layout.addRow("Product ID:", self.product_id_input)
        
        self.process_id_input = QLineEdit()
        self.process_id_input.setPlaceholderText("Enter process ID")
        form_layout.addRow("Process ID:", self.process_id_input)
        
        self.location_input = QLineEdit()
        self.location_input.setPlaceholderText("Enter location")
        form_layout.addRow("Location:", self.location_input)
        
        self.department_input = QLineEdit()
        self.department_input.setPlaceholderText("Enter department")
        form_layout.addRow("Department:", self.department_input)
        
        self.shift_combo = QComboBox()
        self.shift_combo.addItem("-- Not Set --", None)
        self.shift_combo.addItems(['Day Shift', 'Night Shift', 'Morning', 'Afternoon', 'Evening'])
        self.shift_combo.setEditable(True)
        form_layout.addRow("Shift:", self.shift_combo)
        
        # Notes
        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(80)
        self.notes_input.setPlaceholderText("Enter any notes or comments")
        form_layout.addRow("Notes:", self.notes_input)
        
        self.internal_notes_input = QTextEdit()
        self.internal_notes_input.setMaximumHeight(60)
        self.internal_notes_input.setPlaceholderText("Internal notes (not shown in reports)")
        form_layout.addRow("Internal Notes:", self.internal_notes_input)
        
        tabs.addTab(info_scroll, "Record Info")
        
        # Tab 2: Record Items
        items_widget = QWidget()
        items_layout = QVBoxLayout()
        items_widget.setLayout(items_layout)
        
        # Info label
        info_label = QLabel("Select a template to automatically load all criteria fields. Fill in values directly in the table.\n"
                           "✓ Pass/Fail is automatically calculated based on min/max/tolerance limits | You can override manually if needed")
        info_label.setStyleSheet("color: #2f3542; padding: 10px; background-color: #e3f2fd; border-radius: 4px; border-left: 5px solid #1e90ff;")
        info_label.setWordWrap(True)
        items_layout.addWidget(info_label)
        
        # Toolbar for items
        items_toolbar = QHBoxLayout()
        btn_load_template = QPushButton("Add Template Fields")
        btn_load_template.clicked.connect(self.load_template_fields_to_table)
        btn_load_template.setToolTip("Add all fields from selected template to the table")
        
        btn_clear_items = QPushButton("Clear All")
        btn_clear_items.clicked.connect(self.clear_all_items)
        btn_clear_items.setToolTip("Clear all items from the table")
        
        btn_add_item = QPushButton("Add Single Item")
        btn_add_item.clicked.connect(self.add_record_item)
        btn_add_item.setToolTip("Add one item manually")
        
        btn_remove_item = QPushButton("Remove Selected")
        btn_remove_item.clicked.connect(self.remove_record_item)
        
        items_toolbar.addWidget(btn_load_template)
        items_toolbar.addWidget(btn_clear_items)
        items_toolbar.addWidget(btn_add_item)
        items_toolbar.addWidget(btn_remove_item)
        items_toolbar.addStretch()
        
        items_layout.addLayout(items_toolbar)
        
        # Items table - now editable
        self.items_table = QTableWidget()
        self.items_table.setColumnCount(8)
        self.items_table.setHorizontalHeaderLabels([
            'Item ID', 'Field ID', 'Criteria Code', 'Title', 'Value', 'Compliance', 'Deviation', 'Remarks'
        ])
        self.items_table.setColumnHidden(0, True)  # Hide Item ID
        self.items_table.setColumnHidden(1, True)  # Hide Field ID
        self.items_table.horizontalHeader().setStretchLastSection(True)
        self.items_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.items_table.setAlternatingRowColors(True)
        
        # Set column widths
        self.items_table.setColumnWidth(2, 120)  # Criteria Code
        self.items_table.setColumnWidth(3, 250)  # Title
        self.items_table.setColumnWidth(4, 150)  # Value
        self.items_table.setColumnWidth(5, 100)  # Compliance
        self.items_table.setColumnWidth(6, 100)  # Deviation
        
        # Connect cell changed signal for auto-validation
        self.items_table.cellChanged.connect(self.on_item_cell_changed)
        
        items_layout.addWidget(self.items_table)
        
        tabs.addTab(items_widget, "Record Items")
        
        # Tab 3: Attachments
        attachments_widget = QWidget()
        attachments_layout = QVBoxLayout()
        attachments_widget.setLayout(attachments_layout)
        
        # Toolbar for attachments
        attachments_toolbar = QHBoxLayout()
        btn_upload = QPushButton("Upload File")
        btn_upload.clicked.connect(self.upload_attachment)
        btn_download = QPushButton("Download")
        btn_download.clicked.connect(self.download_attachment)
        btn_remove_attachment = QPushButton("Remove")
        btn_remove_attachment.clicked.connect(self.remove_attachment)
        
        btn_attach_image = QPushButton("📷 Attach Image")
        btn_attach_image.clicked.connect(self.attach_image_to_record)
        btn_view_images = QPushButton("🖼️ View Images")
        btn_view_images.clicked.connect(self.view_attached_images)
        
        attachments_toolbar.addWidget(btn_upload)
        attachments_toolbar.addWidget(btn_download)
        attachments_toolbar.addWidget(btn_remove_attachment)
        attachments_toolbar.addWidget(btn_attach_image)
        attachments_toolbar.addWidget(btn_view_images)
        attachments_toolbar.addStretch()
        
        attachments_layout.addLayout(attachments_toolbar)
        
        # Attachments table
        self.attachments_table = QTableWidget()
        self.attachments_table.setColumnCount(4)
        self.attachments_table.setHorizontalHeaderLabels([
            'Filename', 'Type', 'Size', 'Date'
        ])
        self.attachments_table.horizontalHeader().setStretchLastSection(True)
        self.attachments_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        attachments_layout.addWidget(self.attachments_table)
        
        tabs.addTab(attachments_widget, "Attachments")
        
        main_layout.addWidget(tabs)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.save_record)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)
    
    def load_templates(self):
        """Load templates into combo box"""
        templates = self.session.query(TestTemplate).filter_by(is_active=True).all()
        self.template_combo.addItem("-- Select Template --", None)
        for template in templates:
            self.template_combo.addItem(f"{template.code} - {template.name}", template.id)
    
    def load_parent_records(self):
        """Load potential parent records (excluding current record if editing)"""
        query = self.session.query(Record).order_by(Record.created_at.desc())
        
        # Exclude current record if editing
        if self.record:
            query = query.filter(Record.id != self.record.id)
        
        records = query.limit(50).all()
        for record in records:
            self.parent_record_combo.addItem(
                f"{record.record_number} - {record.title or 'Untitled'}", 
                record.id
            )
    
    def load_users(self):
        """Load users into combo box"""
        users = self.session.query(User).filter_by(is_active=True).all()
        self.assigned_combo.addItem("-- Not Assigned --", None)
        for user in users:
            self.assigned_combo.addItem(user.full_name, user.id)
            # Also populate reviewed_by and approved_by combos
            self.reviewed_by_combo.addItem(user.full_name, user.id)
            self.approved_by_combo.addItem(user.full_name, user.id)
    
    def load_record_data(self):
        """Load existing record data"""
        if not self.record:
            return
        
        self.title_input.setText(self.record.title or "")
        self.status_combo.setCurrentText(self.record.status)
        
        if self.record.category:
            self.category_combo.setCurrentText(self.record.category)
        
        if self.record.priority:
            self.priority_combo.setCurrentText(self.record.priority)
        
        if self.record.template_id:
            index = self.template_combo.findData(self.record.template_id)
            if index >= 0:
                self.template_combo.setCurrentIndex(index)
        
        # Load parent record
        if self.record.parent_record_id:
            index = self.parent_record_combo.findData(self.record.parent_record_id)
            if index >= 0:
                self.parent_record_combo.setCurrentIndex(index)
        
        if self.record.assigned_to_id:
            index = self.assigned_combo.findData(self.record.assigned_to_id)
            if index >= 0:
                self.assigned_combo.setCurrentIndex(index)
        
        if self.record.scheduled_date:
            self.scheduled_date.setDate(self.record.scheduled_date.date())
        
        if self.record.due_date:
            self.due_date.setDate(self.record.due_date.date())
        
        # Load workflow dates
        if self.record.started_at:
            self.started_at_input.setDate(self.record.started_at.date() if hasattr(self.record.started_at, 'date') else self.record.started_at)
        else:
            self.started_at_input.setDate(self.started_at_input.minimumDate())  # Set to minimum to show special value
        
        if self.record.completed_at:
            self.completed_at_input.setDate(self.record.completed_at.date() if hasattr(self.record.completed_at, 'date') else self.record.completed_at)
        else:
            self.completed_at_input.setDate(self.completed_at_input.minimumDate())  # Set to minimum to show special value
        
        # Load reviewed_by and approved_by
        if self.record.reviewed_by_id:
            index = self.reviewed_by_combo.findData(self.record.reviewed_by_id)
            if index >= 0:
                self.reviewed_by_combo.setCurrentIndex(index)
        
        if self.record.approved_by_id:
            index = self.approved_by_combo.findData(self.record.approved_by_id)
            if index >= 0:
                self.approved_by_combo.setCurrentIndex(index)
        
        if self.record.batch_number:
            self.batch_number_input.setText(self.record.batch_number)
        
        if self.record.product_id:
            self.product_id_input.setText(self.record.product_id)
        
        if self.record.process_id:
            self.process_id_input.setText(self.record.process_id)
        
        if self.record.location:
            self.location_input.setText(self.record.location)
        
        if self.record.department:
            self.department_input.setText(self.record.department)
        
        if self.record.shift:
            self.shift_combo.setCurrentText(self.record.shift)
        
        if self.record.notes:
            self.notes_input.setText(self.record.notes)
        
        if self.record.internal_notes:
            self.internal_notes_input.setText(self.record.internal_notes)
        
        # Load record items and attachments
        self.load_record_items()
        self.load_attachments()
    
    def on_template_changed(self):
        """Handle template selection change - Apply template configuration"""
        template_id = self.template_combo.currentData()
        if not template_id:
            return
        
        try:
            template = self.session.get(TestTemplate, template_id)
            if not template:
                return
            
            # Show preview of template configuration
            config_info = []
            
            # Layout Configuration
            if template.layout:
                layout = template.layout if isinstance(template.layout, dict) else {}
                config_info.append("<b>Layout:</b>")
                config_info.append(f"  • Columns: {layout.get('columns', 2)}")
                config_info.append(f"  • Style: {layout.get('style', 'grid')}")
                config_info.append(f"  • Orientation: {layout.get('orientation', 'vertical')}")
                config_info.append(f"  • Spacing: {layout.get('spacing', 10)}px")
            
            # Section Configuration
            if template.sections:
                sections = template.sections if isinstance(template.sections, list) else []
                if sections:
                    config_info.append("<b>Sections:</b>")
                    for section in sections:
                        if isinstance(section, dict):
                            config_info.append(f"  • {section.get('title', 'Untitled')}")
            
            # Form Configuration
            if template.form_config:
                form_config = template.form_config if isinstance(template.form_config, dict) else {}
                config_info.append("<b>Form Settings:</b>")
                config_info.append(f"  • Validation: {form_config.get('validation', 'normal')}")
                if form_config.get('auto_save'):
                    config_info.append("  • Auto-save enabled")
                if form_config.get('show_progress'):
                    config_info.append("  • Progress indicator enabled")
                if form_config.get('allow_draft'):
                    config_info.append("  • Draft mode allowed")
            
        except Exception as e:
            print(f"Error loading template configuration: {e}")
    
    def load_record_items(self):
        """Load record items for the record"""
        if not self.record:
            return
        
        # Disconnect signal to prevent validation during loading
        self.items_table.cellChanged.disconnect(self.on_item_cell_changed)
        
        items = self.session.query(RecordItem).filter_by(
            record_id=self.record.id
        ).all()
        
        self.items_table.setRowCount(len(items))
        for row_idx, item in enumerate(items):
            # Item ID (hidden)
            self.items_table.setItem(row_idx, 0, QTableWidgetItem(str(item.id)))
            
            # Field ID (hidden)
            field_id = str(item.template_field_id) if item.template_field_id else ''
            self.items_table.setItem(row_idx, 1, QTableWidgetItem(field_id))
            
            # Criteria Code (read-only)
            code_item = QTableWidgetItem(item.criteria.code if item.criteria else '')
            code_item.setFlags(code_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            code_item.setBackground(Qt.GlobalColor.lightGray)
            self.items_table.setItem(row_idx, 2, code_item)
            
            # Title (read-only)
            title_item = QTableWidgetItem(item.criteria.title if item.criteria else '')
            title_item.setFlags(title_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            title_item.setBackground(Qt.GlobalColor.lightGray)
            self.items_table.setItem(row_idx, 3, title_item)
            
            # Value (editable) - format numbers nicely
            value_text = ''
            if item.value:
                value_text = item.value
            elif item.numeric_value is not None:
                # Format number: remove trailing zeros, max 2 decimals for non-integers
                if item.numeric_value == int(item.numeric_value):
                    value_text = str(int(item.numeric_value))
                else:
                    value_text = f'{item.numeric_value:.10g}'  # Use g format to remove trailing zeros
            
            self.items_table.setItem(row_idx, 4, QTableWidgetItem(value_text))
            
            # Compliance (editable combo box)
            compliance_text = 'Pass' if item.compliance else 'Fail' if item.compliance is not None else ''
            compliance_item = QTableWidgetItem(compliance_text)
            
            # Color code compliance
            if item.compliance is True:
                compliance_item.setBackground(Qt.GlobalColor.green)
            elif item.compliance is False:
                compliance_item.setBackground(Qt.GlobalColor.red)
            
            self.items_table.setItem(row_idx, 5, compliance_item)
            
            # Deviation (editable) - format numbers nicely
            deviation_text = ''
            if item.deviation is not None:
                if item.deviation == int(item.deviation):
                    deviation_text = str(int(item.deviation))
                else:
                    deviation_text = f'{item.deviation:.10g}'
            
            self.items_table.setItem(row_idx, 6, QTableWidgetItem(deviation_text))
            
            # Remarks (editable)
            self.items_table.setItem(row_idx, 7, QTableWidgetItem(item.remarks or ''))
        
        # Reconnect signal
        self.items_table.cellChanged.connect(self.on_item_cell_changed)
    
    def load_template_fields_to_table(self):
        """Add all template fields to items table for easy data entry"""
        template_id = self.template_combo.currentData()
        if not template_id:
            QMessageBox.warning(self, "No Template", "Please select a template first.")
            return
        
        # Get template fields/criteria
        template_fields = self.session.query(TemplateField).filter_by(
            template_id=template_id
        ).order_by(TemplateField.sort_order).all()
        
        if not template_fields:
            QMessageBox.warning(self, "No Fields", "The selected template has no fields defined.")
            return
        
        # Disconnect signal to prevent validation during loading
        self.items_table.cellChanged.disconnect(self.on_item_cell_changed)
        
        # Add new rows for all template fields (allow duplicates)
        current_row_count = self.items_table.rowCount()
        self.items_table.setRowCount(current_row_count + len(template_fields))
        
        for idx, field in enumerate(template_fields):
            row_idx = current_row_count + idx
            criteria = field.criteria
            
            # Item ID (hidden) - empty for new items
            self.items_table.setItem(row_idx, 0, QTableWidgetItem(''))
            
            # Field ID (hidden)
            self.items_table.setItem(row_idx, 1, QTableWidgetItem(str(field.id)))
            
            # Criteria Code (read-only)
            code_item = QTableWidgetItem(criteria.code if criteria else '')
            code_item.setFlags(code_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            code_item.setBackground(Qt.GlobalColor.lightGray)
            self.items_table.setItem(row_idx, 2, code_item)
            
            # Title (read-only)
            title_item = QTableWidgetItem(criteria.title if criteria else "Untitled")
            title_item.setFlags(title_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            title_item.setBackground(Qt.GlobalColor.lightGray)
            self.items_table.setItem(row_idx, 3, title_item)
            
            # Value (editable) - set default or expected value as placeholder
            value_item = QTableWidgetItem('')
            if field.default_value:
                value_item.setText(str(field.default_value))
            
            # Add tooltip showing limits and tolerance
            if criteria:
                tooltip = self.get_limits_tooltip(criteria)
                if tooltip:
                    value_item.setToolTip(tooltip)
                    title_item.setToolTip(tooltip)  # Also add to title for visibility
            
            self.items_table.setItem(row_idx, 4, value_item)
            
            # Compliance (editable)
            self.items_table.setItem(row_idx, 5, QTableWidgetItem(''))
            
            # Deviation (editable)
            self.items_table.setItem(row_idx, 6, QTableWidgetItem(''))
            
            # Remarks (editable)
            self.items_table.setItem(row_idx, 7, QTableWidgetItem(''))
        
        # Reconnect signal
        self.items_table.cellChanged.connect(self.on_item_cell_changed)
        
        self.parent().statusbar.showMessage(f"Added {len(template_fields)} field(s) from template", 3000)
    
    def clear_all_items(self):
        """Clear all items from the table"""
        if self.items_table.rowCount() == 0:
            return
        
        reply = QMessageBox.question(
            self, "Confirm Clear",
            "Are you sure you want to clear all items from the table?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.items_table.setRowCount(0)
    
    def on_item_cell_changed(self, row, column):
        """Handle cell changes in items table - auto-validate values"""
        # Only process changes to the Value column (column 4)
        if column != 4:
            return
        
        value_item = self.items_table.item(row, 4)
        if not value_item:
            return
        
        value_text = value_item.text().strip()
        if not value_text:
            return
        
        # Get the field ID for this row
        field_id_item = self.items_table.item(row, 1)
        if not field_id_item or not field_id_item.text():
            return
        
        try:
            field_id = int(field_id_item.text())
            field = self.session.get(TemplateField, field_id)
            if not field or not field.criteria:
                return
            
            criteria = field.criteria
            
            # Validate the value using limit_min, limit_max, tolerance
            is_valid = self.validate_value_with_limits(value_text, criteria)
            
            # Auto-set compliance
            compliance_item = self.items_table.item(row, 5)
            if not compliance_item:
                compliance_item = QTableWidgetItem()
                self.items_table.setItem(row, 5, compliance_item)
            
            # Temporarily disconnect signal to prevent infinite loop
            self.items_table.cellChanged.disconnect(self.on_item_cell_changed)
            
            # Only auto-set if user hasn't manually edited compliance
            current_compliance = compliance_item.text().strip()
            if not current_compliance or current_compliance.lower() in ['pass', 'fail']:
                compliance_item.setText('Pass' if is_valid else 'Fail')
                
                # Color code for visual feedback
                if is_valid:
                    compliance_item.setBackground(Qt.GlobalColor.green)
                else:
                    compliance_item.setBackground(Qt.GlobalColor.red)
            
            # Calculate deviation for numeric values (from midpoint of min/max)
            if criteria.data_type == 'numeric' and criteria.limit_min is not None and criteria.limit_max is not None:
                try:
                    numeric_value = float(value_text)
                    midpoint = (float(criteria.limit_min) + float(criteria.limit_max)) / 2
                    deviation = numeric_value - midpoint
                    
                    deviation_item = self.items_table.item(row, 6)
                    if not deviation_item:
                        deviation_item = QTableWidgetItem()
                        self.items_table.setItem(row, 6, deviation_item)
                    deviation_item.setText(str(round(deviation, 2)))
                except:
                    pass
            
            # Reconnect signal
            self.items_table.cellChanged.connect(self.on_item_cell_changed)
            
        except Exception as e:
            print(f"Error in auto-validation: {e}")
            # Reconnect signal even if error occurs
            try:
                self.items_table.cellChanged.connect(self.on_item_cell_changed)
            except:
                pass
    
    def validate_value_with_limits(self, value_text, criteria):
        """Validate a value using limit_min, limit_max, and tolerance"""
        try:
            # Numeric validation
            if criteria.data_type == 'numeric':
                try:
                    numeric_value = float(value_text)
                except ValueError:
                    return False  # Can't parse as number
                
                # Check if within limits
                if criteria.limit_min is not None:
                    min_val = float(criteria.limit_min)
                    # Apply tolerance if specified
                    if criteria.tolerance is not None:
                        min_val -= float(criteria.tolerance)
                    
                    if numeric_value < min_val:
                        return False
                
                if criteria.limit_max is not None:
                    max_val = float(criteria.limit_max)
                    # Apply tolerance if specified
                    if criteria.tolerance is not None:
                        max_val += float(criteria.tolerance)
                    
                    if numeric_value > max_val:
                        return False
                
                return True
            
            # For non-numeric, just check if not empty
            else:
                return bool(value_text.strip())
                
        except Exception as e:
            print(f"Validation error: {e}")
            return True  # Default to pass if validation fails
    
    def get_limits_tooltip(self, criteria):
        """Generate tooltip text showing limits and tolerance"""
        try:
            if criteria.data_type != 'numeric':
                return ""
            
            tooltip_parts = ["Acceptable Range:"]
            
            if criteria.limit_min is not None or criteria.limit_max is not None:
                min_val = float(criteria.limit_min) if criteria.limit_min is not None else "N/A"
                max_val = float(criteria.limit_max) if criteria.limit_max is not None else "N/A"
                
                if criteria.tolerance is not None:
                    tol = float(criteria.tolerance)
                    if min_val != "N/A":
                        tooltip_parts.append(f"• Minimum: {min_val} (with tolerance: {min_val - tol})")
                    if max_val != "N/A":
                        tooltip_parts.append(f"• Maximum: {max_val} (with tolerance: {max_val + tol})")
                    tooltip_parts.append(f"• Tolerance: ±{tol}")
                else:
                    if min_val != "N/A":
                        tooltip_parts.append(f"• Minimum: {min_val}")
                    if max_val != "N/A":
                        tooltip_parts.append(f"• Maximum: {max_val}")
                
                if criteria.unit:
                    tooltip_parts.append(f"• Unit: {criteria.unit}")
            else:
                return ""
            
            return "\n".join(tooltip_parts) if len(tooltip_parts) > 1 else ""
            
        except Exception as e:
            print(f"Error generating tooltip: {e}")
            return ""
    
    def save_items_from_table(self, record):
        """Save all items from the items table to the database"""
        # First, get existing items for this record
        existing_items = {}
        if record.id:
            for item in self.session.query(RecordItem).filter_by(record_id=record.id).all():
                existing_items[item.id] = item
        
        # Track which items we've seen from the table
        seen_item_ids = set()
        
        # Process each row in the table
        for row_idx in range(self.items_table.rowCount()):
            item_id_text = self.items_table.item(row_idx, 0).text() if self.items_table.item(row_idx, 0) else ''
            field_id_text = self.items_table.item(row_idx, 1).text() if self.items_table.item(row_idx, 1) else ''
            value_text = self.items_table.item(row_idx, 4).text() if self.items_table.item(row_idx, 4) else ''
            compliance_text = self.items_table.item(row_idx, 5).text() if self.items_table.item(row_idx, 5) else ''
            deviation_text = self.items_table.item(row_idx, 6).text() if self.items_table.item(row_idx, 6) else ''
            remarks_text = self.items_table.item(row_idx, 7).text() if self.items_table.item(row_idx, 7) else ''
            
            # Skip rows with no value and no compliance data
            if not value_text and not compliance_text and not deviation_text and not remarks_text:
                continue
            
            # Get field ID
            if not field_id_text:
                continue  # Skip rows without field ID
            
            field_id = int(field_id_text)
            field = self.session.get(TemplateField, field_id)
            if not field:
                continue
            
            # Determine if updating existing or creating new
            if item_id_text and item_id_text.isdigit():
                item_id = int(item_id_text)
                item = existing_items.get(item_id)
                seen_item_ids.add(item_id)
            else:
                item = None
            
            # Create new item if needed
            if not item:
                item = RecordItem()
                item.record_id = record.id
                item.created_by_id = self.current_user.id
                self.session.add(item)
            
            # Update item fields
            item.template_field_id = field_id
            item.criteria_id = field.criteria_id
            
            # Handle value - could be text or numeric
            if value_text:
                # Try to parse as number
                try:
                    item.numeric_value = float(value_text)
                    item.value = None
                except ValueError:
                    item.value = value_text
                    item.numeric_value = None
            else:
                item.value = None
                item.numeric_value = None
            
            # Handle compliance
            if compliance_text:
                compliance_lower = compliance_text.lower()
                if 'pass' in compliance_lower or compliance_lower == 'y' or compliance_lower == 'yes' or compliance_lower == 'true' or compliance_lower == '1':
                    item.compliance = True
                elif 'fail' in compliance_lower or compliance_lower == 'n' or compliance_lower == 'no' or compliance_lower == 'false' or compliance_lower == '0':
                    item.compliance = False
                else:
                    item.compliance = None
            else:
                item.compliance = None
            
            # Handle deviation
            if deviation_text:
                try:
                    item.deviation = float(deviation_text)
                except ValueError:
                    item.deviation = None
            else:
                item.deviation = None
            
            # Handle remarks
            item.remarks = remarks_text if remarks_text else None
            item.updated_by_id = self.current_user.id
        
        # Delete items that were not in the table (removed by user)
        for item_id, item in existing_items.items():
            if item_id not in seen_item_ids:
                self.session.delete(item)
        
        # Flush to save items before compliance calculation
        self.session.flush()
    
    def load_attachments(self):
        """Load attachments for the record"""
        if not self.record or not self.record.attachments:
            self.attachments_table.setRowCount(0)
            return
        
        try:
            attachments = json.loads(self.record.attachments) if isinstance(self.record.attachments, str) else self.record.attachments
            if not isinstance(attachments, list):
                attachments = []
        except (json.JSONDecodeError, TypeError):
            attachments = []
        
        self.attachments_table.setRowCount(len(attachments))
        for row_idx, att in enumerate(attachments):
            self.attachments_table.setItem(row_idx, 0, QTableWidgetItem(att.get('filename', '')))
            self.attachments_table.setItem(row_idx, 1, QTableWidgetItem(att.get('type', '')))
            self.attachments_table.setItem(row_idx, 2, QTableWidgetItem(att.get('size', '')))
            self.attachments_table.setItem(row_idx, 3, QTableWidgetItem(att.get('date', '')))
    
    def upload_attachment(self):
        """Upload and attach a file"""
        if not self.record:
            QMessageBox.warning(self, "Save Required", "Please save the record first before adding attachments.")
            return
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select File to Attach", "",
            "All Files (*);;Documents (*.pdf *.doc *.docx);;Images (*.png *.jpg *.jpeg);;Excel (*.xlsx *.xls)"
        )
        
        if file_path:
            try:
                import os
                import shutil
                from pathlib import Path
                
                # Create attachments directory if not exists
                attachments_dir = Path.home() / '.quality_system' / 'attachments' / 'records'
                attachments_dir.mkdir(parents=True, exist_ok=True)
                
                # Copy file to attachments directory with unique name
                filename = os.path.basename(file_path)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                unique_filename = f"{timestamp}_{filename}"
                dest_path = attachments_dir / unique_filename
                
                shutil.copy2(file_path, dest_path)
                
                # Get file info
                file_size = os.path.getsize(dest_path)
                size_str = self.format_file_size(file_size)
                file_type = os.path.splitext(filename)[1] or 'file'
                
                # Add to attachments JSON
                attachments = []
                if self.record.attachments:
                    try:
                        attachments = json.loads(self.record.attachments) if isinstance(self.record.attachments, str) else self.record.attachments
                        if not isinstance(attachments, list):
                            attachments = []
                    except (json.JSONDecodeError, TypeError):
                        attachments = []
                
                attachment_info = {
                    'filename': filename,
                    'stored_name': unique_filename,
                    'path': str(dest_path),
                    'type': file_type,
                    'size': size_str,
                    'date': datetime.now().strftime('%Y-%m-%d %H:%M')
                }
                
                attachments.append(attachment_info)
                self.record.attachments = json.dumps(attachments)
                self.session.commit()
                
                self.load_attachments()
                QMessageBox.information(self, "Success", f"File '{filename}' attached successfully.")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to attach file:\n{str(e)}")
    
    def download_attachment(self):
        """Download selected attachment"""
        if self.attachments_table.currentRow() < 0:
            QMessageBox.warning(self, "No Selection", "Please select an attachment to download")
            return
        
        try:
            attachments = json.loads(self.record.attachments) if isinstance(self.record.attachments, str) else self.record.attachments
            att = attachments[self.attachments_table.currentRow()]
            
            # Ask user where to save
            save_path, _ = QFileDialog.getSaveFileName(
                self, "Save Attachment", att['filename'], "All Files (*)"
            )
            
            if save_path:
                import shutil
                shutil.copy2(att['path'], save_path)
                QMessageBox.information(self, "Success", "File downloaded successfully.")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to download file:\n{str(e)}")
    
    def remove_attachment(self):
        """Remove selected attachment"""
        if self.attachments_table.currentRow() < 0:
            QMessageBox.warning(self, "No Selection", "Please select an attachment to remove")
            return
        
        reply = QMessageBox.question(
            self, "Confirm Delete",
            "Are you sure you want to remove this attachment?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                import os
                attachments = json.loads(self.record.attachments) if isinstance(self.record.attachments, str) else self.record.attachments
                att = attachments[self.attachments_table.currentRow()]
                
                # Remove file from disk
                if os.path.exists(att['path']):
                    os.remove(att['path'])
                
                # Remove from JSON
                attachments.pop(self.attachments_table.currentRow())
                self.record.attachments = json.dumps(attachments) if attachments else None
                self.session.commit()
                
                self.load_attachments()
                QMessageBox.information(self, "Success", "Attachment removed.")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to remove attachment:\n{str(e)}")
    
    def format_file_size(self, size_bytes):
        """Format file size in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    def add_record_item(self):
        """Add an item to the record"""
        if not self.record:
            QMessageBox.warning(self, "Save Required", 
                               "Please save the record first before adding items.")
            return
        
        template_id = self.template_combo.currentData()
        if not template_id:
            QMessageBox.warning(self, "No Template", "Please select a template first.")
            return
        
        # Get template fields/criteria
        template_fields = self.session.query(TemplateField).filter_by(
            template_id=template_id
        ).order_by(TemplateField.sort_order).all()
        
        if not template_fields:
            QMessageBox.warning(self, "No Fields", "The selected template has no fields defined.")
            return
        
        dialog = RecordItemDialog(self.session, self.current_user, self.record, 
                                  template_fields=template_fields, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_record_items()
    
    def edit_record_item(self):
        """Edit selected record item"""
        if self.items_table.currentRow() < 0:
            QMessageBox.warning(self, "No Selection", "Please select an item to edit")
            return
        
        item_id = int(self.items_table.item(self.items_table.currentRow(), 0).text())
        item = self.session.get(RecordItem, item_id)
        
        if item:
            dialog = RecordItemDialog(self.session, self.current_user, self.record, 
                                      item=item, parent=self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.load_record_items()
    
    def remove_record_item(self):
        """Remove selected record item"""
        if self.items_table.currentRow() < 0:
            QMessageBox.warning(self, "No Selection", "Please select an item to remove")
            return
        
        item_id = int(self.items_table.item(self.items_table.currentRow(), 0).text())
        item = self.session.get(RecordItem, item_id)
        
        if item:
            reply = QMessageBox.question(
                self, "Confirm Delete", 
                "Are you sure you want to delete this item?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.session.delete(item)
                self.session.commit()
                
                # Recalculate compliance after item deletion
                if self.record:
                    self.recalculate_record_compliance()
                
                self.load_record_items()
    
    def recalculate_record_compliance(self):
        """Recalculate compliance fields for the current record"""
        try:
            # Query all items for this record
            items = self.session.query(RecordItem).filter_by(record_id=self.record.id).all()
            
            if items:
                # Count items with compliance status
                items_with_compliance = [item for item in items if item.compliance is not None]
                passed_items = [item for item in items_with_compliance if item.compliance]
                failed_items = [item for item in items_with_compliance if not item.compliance]
                
                # Calculate overall_compliance (True only if ALL items pass)
                if items_with_compliance:
                    self.record.overall_compliance = len(passed_items) == len(items_with_compliance)
                else:
                    self.record.overall_compliance = None
                
                # Calculate compliance_score (percentage of passing items)
                if items_with_compliance:
                    self.record.compliance_score = (len(passed_items) / len(items_with_compliance)) * 100
                else:
                    self.record.compliance_score = None
                
                # Calculate failed_items_count
                self.record.failed_items_count = len(failed_items)
            else:
                # No items - set to None/0
                self.record.overall_compliance = None
                self.record.compliance_score = None
                self.record.failed_items_count = 0
            
            self.session.commit()
            
        except Exception as e:
            # Don't show error to user, just log it
            print(f"Warning: Failed to recalculate compliance: {e}")
    
    def attach_image_to_record(self):
        """Open image upload dialog for this record"""
        if not self.record:
            QMessageBox.warning(self, "Save Required", "Please save the record first before attaching images.")
            return
        
        dialog = ImageUploadDialog(self.session, self.current_user, self, self.record.id, 'record')
        dialog.exec()
    
    def view_attached_images(self):
        """View images attached to this record"""
        if not self.record:
            QMessageBox.warning(self, "Save Required", "Please save the record first.")
            return
        
        # Query images for this record
        images = self.session.query(ImageAttachment).filter(
            ImageAttachment.entity_type == 'record',
            ImageAttachment.entity_id == self.record.id
        ).all()
        
        if not images:
            QMessageBox.information(self, "No Images", "No images attached to this record.")
            return
        
        # Show list of images
        msg = f"Attached Images ({len(images)}):\n\n"
        for idx, img in enumerate(images, 1):
            msg += f"{idx}. {img.description or img.filename}\n"
        
        QMessageBox.information(self, "Attached Images", msg)
    
    def save_record(self):
        """Save the record"""
        # Validation
        if not self.title_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Please enter a title")
            return
        
        template_id = self.template_combo.currentData()
        if not template_id:
            QMessageBox.warning(self, "Validation Error", "Please select a template")
            return
        
        try:
            if self.record:
                # Update existing record
                record = self.record
            else:
                # Create new record
                record = Record()
                # Generate record number
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                count = self.session.query(Record).count() + 1
                record.record_number = f"REC-{timestamp}-{count:04d}"
                record.created_by_id = self.current_user.id
            
            # Update fields
            record.title = self.title_input.text().strip()
            record.template_id = template_id
            record.parent_record_id = self.parent_record_combo.currentData()
            record.category = self.category_combo.currentText() or None
            record.status = self.status_combo.currentText()
            record.priority = self.priority_combo.currentText()
            record.assigned_to_id = self.assigned_combo.currentData()
            record.scheduled_date = datetime.combine(
                self.scheduled_date.date().toPyDate(),
                datetime.min.time()
            )
            record.due_date = datetime.combine(
                self.due_date.date().toPyDate(),
                datetime.min.time()
            )
            
            # Save workflow dates
            # Only set started_at/completed_at if not at minimum date (special value)
            if self.started_at_input.date() != self.started_at_input.minimumDate():
                record.started_at = datetime.combine(
                    self.started_at_input.date().toPyDate(),
                    datetime.min.time()
                )
            else:
                record.started_at = None
            
            if self.completed_at_input.date() != self.completed_at_input.minimumDate():
                record.completed_at = datetime.combine(
                    self.completed_at_input.date().toPyDate(),
                    datetime.min.time()
                )
            else:
                record.completed_at = None
            
            # Save reviewed_by and approved_by
            record.reviewed_by_id = self.reviewed_by_combo.currentData()
            record.approved_by_id = self.approved_by_combo.currentData()
            
            record.batch_number = self.batch_number_input.text().strip() or None
            record.product_id = self.product_id_input.text().strip() or None
            record.process_id = self.process_id_input.text().strip() or None
            record.location = self.location_input.text().strip() or None
            record.department = self.department_input.text().strip() or None
            shift_text = self.shift_combo.currentText()
            record.shift = shift_text if shift_text != "-- Not Set --" else None
            record.notes = self.notes_input.toPlainText() or None
            record.internal_notes = self.internal_notes_input.toPlainText() or None
            record.updated_by_id = self.current_user.id
            
            # Get standard from template
            template = self.session.get(TestTemplate, template_id)
            if template:
                record.standard_id = template.standard_id
            
            if not self.record:
                self.session.add(record)
            
            # Flush to get record ID for compliance calculation
            self.session.flush()
            
            # Save record items from table
            self.save_items_from_table(record)
            
            # Auto-calculate compliance fields from RecordItems
            items = self.session.query(RecordItem).filter_by(record_id=record.id).all()
            if items:
                # Count items with compliance status
                total_items = len(items)
                items_with_compliance = [item for item in items if item.compliance is not None]
                passed_items = [item for item in items_with_compliance if item.compliance]
                failed_items = [item for item in items_with_compliance if not item.compliance]
                
                # Calculate overall_compliance (True only if ALL items pass)
                if items_with_compliance:
                    record.overall_compliance = len(passed_items) == len(items_with_compliance)
                else:
                    record.overall_compliance = None
                
                # Calculate compliance_score (percentage of passing items)
                if items_with_compliance:
                    record.compliance_score = (len(passed_items) / len(items_with_compliance)) * 100
                else:
                    record.compliance_score = None
                
                # Calculate failed_items_count
                record.failed_items_count = len(failed_items)
            else:
                # No items yet - set to None/0
                record.overall_compliance = None
                record.compliance_score = None
                record.failed_items_count = 0
            
            self.session.commit()
            
            # Audit logging
            action = 'update' if self.record else 'insert'
            try:
                log_entry = AuditLog(
                    table_name='records',
                    record_id=record.id,
                    action=action,
                    user_id=self.current_user.id,
                    username=self.current_user.full_name,
                    timestamp=datetime.now()
                )
                self.session.add(log_entry)
                self.session.commit()
            except:
                pass  # Don't fail the operation if logging fails
            
            # Notification for assignment changes
            if record.assigned_to_id and record.assigned_to_id != self.current_user.id:
                try:
                    notif = Notification(
                        user_id=record.assigned_to_id,
                        title=f"Record Assigned: {record.record_number}",
                        message=f"You have been assigned to record '{record.title}' by {self.current_user.full_name}",
                        type='info',
                        priority='normal',
                        related_record_id=record.id,
                        created_at=datetime.now()
                    )
                    self.session.add(notif)
                    self.session.commit()
                except:
                    pass  # Don't fail the operation if notification fails
            
            self.accept()
            
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to save record:\n{str(e)}")


class RecordItemDialog(QDialog):
    """Dialog for creating/editing record items"""
    
    def __init__(self, session, current_user, record, item=None, template_fields=None, parent=None):
        super().__init__(parent)
        self.session = session
        self.current_user = current_user
        self.record = record
        self.item = item
        self.template_fields = template_fields or []
        
        self.setWindowTitle("Edit Item" if item else "New Item")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        
        self.setup_ui()
        
        if item:
            self.load_item_data()
    
    def setup_ui(self):
        """Setup dialog UI"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        form_layout = QFormLayout()
        
        # Criteria Selection
        if not self.item:
            self.criteria_combo = QComboBox()
            
            for field in self.template_fields:
                if field.criteria:
                    self.criteria_combo.addItem(
                        f"{field.criteria.code} - {field.criteria.title}", 
                        {'criteria_id': field.criteria.id, 'field_id': field.id}
                    )
            
            form_layout.addRow("Criteria:*", self.criteria_combo)
        else:
            # Display only for editing
            criteria_label = QLabel(f"{self.item.criteria.code} - {self.item.criteria.title}")
            form_layout.addRow("Criteria:", criteria_label)
        
        # Value input (will be shown/hidden based on criteria type)
        self.value_input = QLineEdit()
        self.value_input.setPlaceholderText("Enter value")
        form_layout.addRow("Value:*", self.value_input)
        
        self.numeric_input = QDoubleSpinBox()
        self.numeric_input.setRange(-999999, 999999)
        self.numeric_input.setDecimals(4)
        self.numeric_input.setVisible(False)
        form_layout.addRow("Numeric Value:", self.numeric_input)
        
        # Compliance
        self.compliance_combo = QComboBox()
        self.compliance_combo.addItem("-- Not Set --", None)
        self.compliance_combo.addItem("Pass", True)
        self.compliance_combo.addItem("Fail", False)
        form_layout.addRow("Compliance:", self.compliance_combo)
        
        # Deviation
        self.deviation_input = QDoubleSpinBox()
        self.deviation_input.setRange(-999999, 999999)
        self.deviation_input.setDecimals(4)
        form_layout.addRow("Deviation:", self.deviation_input)
        
        # Remarks
        self.remarks_input = QTextEdit()
        self.remarks_input.setMaximumHeight(80)
        self.remarks_input.setPlaceholderText("Enter any remarks")
        form_layout.addRow("Remarks:", self.remarks_input)
        
        # Measured At
        self.measured_at = QDateEdit()
        self.measured_at.setCalendarPopup(True)
        self.measured_at.setDate(datetime.now().date())
        form_layout.addRow("Measured At:", self.measured_at)
        
        # Equipment Used
        self.equipment_input = QLineEdit()
        self.equipment_input.setPlaceholderText("Equipment used for measurement")
        form_layout.addRow("Equipment:", self.equipment_input)
        
        layout.addLayout(form_layout)
        
        # Attachments Section
        attachments_group = QGroupBox("Attachments")
        attachments_layout = QVBoxLayout()
        
        # Toolbar for attachments
        attachments_toolbar = QHBoxLayout()
        btn_upload = QPushButton("Upload File")
        btn_upload.clicked.connect(self.upload_attachment)
        btn_download = QPushButton("Download")
        btn_download.clicked.connect(self.download_attachment)
        btn_remove_attachment = QPushButton("Remove")
        btn_remove_attachment.clicked.connect(self.remove_attachment)
        
        attachments_toolbar.addWidget(btn_upload)
        attachments_toolbar.addWidget(btn_download)
        attachments_toolbar.addWidget(btn_remove_attachment)
        attachments_toolbar.addStretch()
        
        attachments_layout.addLayout(attachments_toolbar)
        
        # Attachments table
        self.attachments_table = QTableWidget()
        self.attachments_table.setColumnCount(4)
        self.attachments_table.setHorizontalHeaderLabels([
            'Filename', 'Type', 'Size', 'Date'
        ])
        self.attachments_table.horizontalHeader().setStretchLastSection(True)
        self.attachments_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.attachments_table.setMaximumHeight(150)
        attachments_layout.addWidget(self.attachments_table)
        
        attachments_group.setLayout(attachments_layout)
        layout.addWidget(attachments_group)
        
        # Load attachments if editing
        if self.item:
            self.load_attachments()
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.save_item)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # Connect criteria change signal AFTER all widgets are created
        if not self.item and hasattr(self, 'criteria_combo'):
            self.criteria_combo.currentIndexChanged.connect(self.on_criteria_changed)
            # Trigger initial update
            if self.criteria_combo.count() > 0:
                self.on_criteria_changed()
    
    def on_criteria_changed(self):
        """Handle criteria selection change"""
        if not hasattr(self, 'criteria_combo') or not hasattr(self, 'value_input') or not hasattr(self, 'numeric_input'):
            return
        
        field_data = self.criteria_combo.currentData()
        if field_data:
            criteria_id = field_data.get('criteria_id') if isinstance(field_data, dict) else field_data
            criteria = self.session.get(StandardCriteria, criteria_id)
            if criteria and criteria.data_type == 'numeric':
                self.value_input.setVisible(False)
                self.numeric_input.setVisible(True)
            else:
                self.value_input.setVisible(True)
                self.numeric_input.setVisible(False)
    
    def load_item_data(self):
        """Load existing item data"""
        if not self.item:
            return
        
        if self.item.criteria and self.item.criteria.data_type == 'numeric':
            self.value_input.setVisible(False)
            self.numeric_input.setVisible(True)
            if self.item.numeric_value is not None:
                self.numeric_input.setValue(float(self.item.numeric_value))
        else:
            if self.item.value:
                self.value_input.setText(self.item.value)
        
        if self.item.compliance is not None:
            if self.item.compliance:
                self.compliance_combo.setCurrentIndex(1)  # Pass
            else:
                self.compliance_combo.setCurrentIndex(2)  # Fail
        
        if self.item.deviation is not None:
            self.deviation_input.setValue(float(self.item.deviation))
        
        if self.item.remarks:
            self.remarks_input.setText(self.item.remarks)
        
        if self.item.measured_at:
            self.measured_at.setDate(self.item.measured_at.date())
        
        if self.item.equipment_used:
            self.equipment_input.setText(self.item.equipment_used)
    
    def save_item(self):
        """Save the record item"""
        try:
            if self.item:
                item = self.item
            else:
                # Validate criteria selection
                if not hasattr(self, 'criteria_combo'):
                    QMessageBox.warning(self, "Error", "No criteria selected")
                    return
                
                field_data = self.criteria_combo.currentData()
                if not field_data:
                    QMessageBox.warning(self, "Validation Error", "Please select a criteria")
                    return
                
                item = RecordItem()
                item.record_id = self.record.id
                item.criteria_id = field_data.get('criteria_id') if isinstance(field_data, dict) else field_data
                item.template_field_id = field_data.get('field_id') if isinstance(field_data, dict) else None
                item.measured_by_id = self.current_user.id
            
            # Determine criteria type and save appropriate value
            if self.item:
                criteria = item.criteria
            else:
                field_data = self.criteria_combo.currentData()
                criteria_id = field_data.get('criteria_id') if isinstance(field_data, dict) else field_data
                criteria = self.session.get(StandardCriteria, criteria_id)
            
            if criteria and criteria.data_type == 'numeric':
                item.numeric_value = self.numeric_input.value()
                item.value = str(self.numeric_input.value())
            else:
                item.value = self.value_input.text().strip()
                item.numeric_value = None
            
            # Compliance
            compliance_value = self.compliance_combo.currentData()
            item.compliance = compliance_value
            
            # Deviation
            if self.deviation_input.value() != 0:
                item.deviation = self.deviation_input.value()
            else:
                item.deviation = None
            
            item.remarks = self.remarks_input.toPlainText() or None
            item.measured_at = datetime.combine(
                self.measured_at.date().toPyDate(),
                datetime.now().time()
            )
            item.equipment_used = self.equipment_input.text().strip() or None
            
            if not self.item:
                self.session.add(item)
            
            self.session.commit()
            
            # Recalculate record compliance after item change
            self.recalculate_record_compliance()
            
            self.accept()
            
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to save item:\n{str(e)}")
    
    def recalculate_record_compliance(self):
        """Recalculate compliance fields for the parent record"""
        try:
            # Query all items for this record
            items = self.session.query(RecordItem).filter_by(record_id=self.record.id).all()
            
            if items:
                # Count items with compliance status
                items_with_compliance = [item for item in items if item.compliance is not None]
                passed_items = [item for item in items_with_compliance if item.compliance]
                failed_items = [item for item in items_with_compliance if not item.compliance]
                
                # Calculate overall_compliance (True only if ALL items pass)
                if items_with_compliance:
                    self.record.overall_compliance = len(passed_items) == len(items_with_compliance)
                else:
                    self.record.overall_compliance = None
                
                # Calculate compliance_score (percentage of passing items)
                if items_with_compliance:
                    self.record.compliance_score = (len(passed_items) / len(items_with_compliance)) * 100
                else:
                    self.record.compliance_score = None
                
                # Calculate failed_items_count
                self.record.failed_items_count = len(failed_items)
            else:
                # No items - set to None/0
                self.record.overall_compliance = None
                self.record.compliance_score = None
                self.record.failed_items_count = 0
            
            self.session.commit()
            
        except Exception as e:
            # Don't show error to user, just log it
            print(f"Warning: Failed to recalculate compliance: {e}")
    
    def load_attachments(self):
        """Load attachments for the record item"""
        if not self.item or not self.item.attachments:
            self.attachments_table.setRowCount(0)
            return
        
        try:
            attachments = json.loads(self.item.attachments) if isinstance(self.item.attachments, str) else self.item.attachments
            if not isinstance(attachments, list):
                attachments = []
        except (json.JSONDecodeError, TypeError):
            attachments = []
        
        self.attachments_table.setRowCount(len(attachments))
        for row_idx, att in enumerate(attachments):
            self.attachments_table.setItem(row_idx, 0, QTableWidgetItem(att.get('filename', '')))
            self.attachments_table.setItem(row_idx, 1, QTableWidgetItem(att.get('type', '')))
            self.attachments_table.setItem(row_idx, 2, QTableWidgetItem(att.get('size', '')))
            self.attachments_table.setItem(row_idx, 3, QTableWidgetItem(att.get('date', '')))
    
    def upload_attachment(self):
        """Upload and attach a file"""
        if not self.item:
            QMessageBox.warning(self, "Save Required", "Please save the item first before adding attachments.")
            return
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select File to Attach", "",
            "All Files (*);;Documents (*.pdf *.doc *.docx);;Images (*.png *.jpg *.jpeg);;Excel (*.xlsx *.xls)"
        )
        
        if file_path:
            try:
                import os
                import shutil
                from pathlib import Path
                
                # Create attachments directory if not exists
                attachments_dir = Path.home() / '.quality_system' / 'attachments' / 'items'
                attachments_dir.mkdir(parents=True, exist_ok=True)
                
                # Copy file to attachments directory with unique name
                filename = os.path.basename(file_path)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                unique_filename = f"{timestamp}_{filename}"
                dest_path = attachments_dir / unique_filename
                
                shutil.copy2(file_path, dest_path)
                
                # Get file info
                file_size = os.path.getsize(dest_path)
                size_str = self.format_file_size(file_size)
                file_type = os.path.splitext(filename)[1] or 'file'
                
                # Add to attachments JSON
                attachments = []
                if self.item.attachments:
                    try:
                        attachments = json.loads(self.item.attachments) if isinstance(self.item.attachments, str) else self.item.attachments
                        if not isinstance(attachments, list):
                            attachments = []
                    except (json.JSONDecodeError, TypeError):
                        attachments = []
                
                attachment_info = {
                    'filename': filename,
                    'stored_name': unique_filename,
                    'path': str(dest_path),
                    'type': file_type,
                    'size': size_str,
                    'date': datetime.now().strftime('%Y-%m-%d %H:%M')
                }
                
                attachments.append(attachment_info)
                self.item.attachments = json.dumps(attachments)
                self.session.commit()
                
                self.load_attachments()
                QMessageBox.information(self, "Success", f"File '{filename}' attached successfully.")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to attach file:\\n{str(e)}")
    
    def download_attachment(self):
        """Download selected attachment"""
        if self.attachments_table.currentRow() < 0:
            QMessageBox.warning(self, "No Selection", "Please select an attachment to download")
            return
        
        try:
            attachments = json.loads(self.item.attachments) if isinstance(self.item.attachments, str) else self.item.attachments
            att = attachments[self.attachments_table.currentRow()]
            
            # Ask user where to save
            save_path, _ = QFileDialog.getSaveFileName(
                self, "Save Attachment", att['filename'], "All Files (*)"
            )
            
            if save_path:
                import shutil
                shutil.copy2(att['path'], save_path)
                QMessageBox.information(self, "Success", "File downloaded successfully.")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to download file:\\n{str(e)}")
    
    def remove_attachment(self):
        """Remove selected attachment"""
        if self.attachments_table.currentRow() < 0:
            QMessageBox.warning(self, "No Selection", "Please select an attachment to remove")
            return
        
        reply = QMessageBox.question(
            self, "Confirm Delete",
            "Are you sure you want to remove this attachment?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                import os
                attachments = json.loads(self.item.attachments) if isinstance(self.item.attachments, str) else self.item.attachments
                att = attachments[self.attachments_table.currentRow()]
                
                # Remove file from disk
                if os.path.exists(att['path']):
                    os.remove(att['path'])
                
                # Remove from JSON
                attachments.pop(self.attachments_table.currentRow())
                self.item.attachments = json.dumps(attachments) if attachments else None
                self.session.commit()
                
                self.load_attachments()
                QMessageBox.information(self, "Success", "Attachment removed.")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to remove attachment:\\n{str(e)}")
    
    def format_file_size(self, size_bytes):
        """Format file size in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"


class TemplateDialog(QDialog):
    """Dialog for creating/editing templates"""
    
    def __init__(self, session, current_user, template=None, parent=None):
        super().__init__(parent)
        self.session = session
        self.current_user = current_user
        self.template = template
        
        self.setWindowTitle("Edit Template" if template else "New Template")
        self.setMinimumWidth(900)
        self.setMinimumHeight(600)
        
        self.setup_ui()
        
        if template:
            self.load_template_data()
    
    def setup_ui(self):
        """Setup dialog UI"""
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        
        # Create tabs for template info and fields
        tabs = QTabWidget()
        
        # Tab 1: Template Info
        info_widget = QWidget()
        info_scroll = QScrollArea()
        info_scroll.setWidgetResizable(True)
        info_scroll.setWidget(info_widget)
        
        info_layout = QFormLayout()
        info_widget.setLayout(info_layout)
        
        # Code
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("e.g., TPL-001")
        if self.template:
            self.code_input.setReadOnly(True)
        info_layout.addRow("Code:*", self.code_input)
        
        # Name
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter template name")
        info_layout.addRow("Name:*", self.name_input)
        
        # Standard
        self.standard_combo = QComboBox()
        self.standard_combo.currentIndexChanged.connect(self.on_standard_changed)
        self.load_standards()
        info_layout.addRow("Standard:", self.standard_combo)
        
        # Category
        self.category_combo = QComboBox()
        self.category_combo.addItems(['inspection', 'audit', 'vqa', 'ncr', 'calibration', 'other'])
        info_layout.addRow("Category:", self.category_combo)
        
        # Version
        self.version_input = QLineEdit()
        self.version_input.setText('1.0')
        info_layout.addRow("Version:", self.version_input)
        
        # Description
        self.description_input = QTextEdit()
        self.description_input.setMaximumHeight(100)
        self.description_input.setPlaceholderText("Enter template description")
        info_layout.addRow("Description:", self.description_input)
        
        # Requires Approval
        self.requires_approval_check = QCheckBox("Requires Approval")
        info_layout.addRow("", self.requires_approval_check)
        
        # Is Active
        self.is_active_check = QCheckBox("Active")
        self.is_active_check.setChecked(True)
        info_layout.addRow("", self.is_active_check)
        
        # Approval Levels
        self.approval_levels_input = QSpinBox()
        self.approval_levels_input.setMinimum(0)
        self.approval_levels_input.setMaximum(10)
        self.approval_levels_input.setValue(1)
        self.approval_levels_input.setToolTip("Number of approval levels required")
        info_layout.addRow("Approval Levels:", self.approval_levels_input)
        
        # Frequency
        self.frequency_combo = QComboBox()
        self.frequency_combo.addItems(['once', 'daily', 'weekly', 'monthly', 'quarterly', 'yearly', 'ad-hoc'])
        self.frequency_combo.setToolTip("Expected execution frequency")
        info_layout.addRow("Frequency:", self.frequency_combo)
        
        # Estimated Duration
        self.estimated_duration_input = QSpinBox()
        self.estimated_duration_input.setMinimum(0)
        self.estimated_duration_input.setMaximum(9999)
        self.estimated_duration_input.setSuffix(" min")
        self.estimated_duration_input.setToolTip("Estimated duration in minutes")
        info_layout.addRow("Estimated Duration:", self.estimated_duration_input)
        
        # Required Equipment
        self.required_equipment_input = QTextEdit()
        self.required_equipment_input.setMaximumHeight(80)
        self.required_equipment_input.setPlaceholderText("Enter required equipment (one per line)")
        self.required_equipment_input.setToolTip("List required equipment, one per line")
        info_layout.addRow("Required Equipment:", self.required_equipment_input)
        
        # Required Certifications
        self.required_certifications_input = QTextEdit()
        self.required_certifications_input.setMaximumHeight(80)
        self.required_certifications_input.setPlaceholderText("Enter required certifications (one per line)")
        self.required_certifications_input.setToolTip("List required certifications, one per line")
        info_layout.addRow("Required Certifications:", self.required_certifications_input)
        
        # Layout Configuration
        layout_label = QLabel("Layout Configuration - Controls how the form looks")
        layout_label.setStyleSheet("font-weight: bold; margin-top: 10px; color: #2f3542;")
        info_layout.addRow(layout_label)
        
        layout_help = QLabel("<i>These settings control how fields are displayed when users create records.</i>")
        layout_help.setWordWrap(True)
        info_layout.addRow("", layout_help)
        
        layout_group = QGroupBox()
        layout_group_layout = QFormLayout()
        
        self.layout_columns_input = QSpinBox()
        self.layout_columns_input.setRange(1, 6)
        self.layout_columns_input.setValue(2)
        self.layout_columns_input.setToolTip("How many columns to use:\n1 = Single column (fields stacked)\n2 = Two columns (side-by-side)\n3+ = More columns (compact layout)")
        layout_group_layout.addRow("Columns:", self.layout_columns_input)
        
        self.layout_style_combo = QComboBox()
        self.layout_style_combo.addItems(['grid', 'linear', 'compact', 'spacious', 'wizard'])
        self.layout_style_combo.setToolTip("Form appearance:\ngrid = Table-like layout\nlinear = Simple vertical list\ncompact = Minimal spacing\nspacious = Extra space between fields\nwizard = Step-by-step form")
        layout_group_layout.addRow("Style:", self.layout_style_combo)
        
        self.layout_orientation_combo = QComboBox()
        self.layout_orientation_combo.addItems(['vertical', 'horizontal', 'auto'])
        self.layout_orientation_combo.setToolTip("Field arrangement:\nvertical = Labels above fields\nhorizontal = Labels beside fields\nauto = Automatically choose best")
        layout_group_layout.addRow("Orientation:", self.layout_orientation_combo)
        
        self.layout_spacing_input = QSpinBox()
        self.layout_spacing_input.setRange(0, 50)
        self.layout_spacing_input.setValue(10)
        self.layout_spacing_input.setSuffix(" px")
        self.layout_spacing_input.setToolTip("Space between fields in pixels (0=no space, 20=large gaps)")
        layout_group_layout.addRow("Spacing:", self.layout_spacing_input)
        
        layout_group.setLayout(layout_group_layout)
        info_layout.addRow(layout_group)
        
        # Sections Configuration
        sections_label = QLabel("Sections Configuration - Group fields into categories")
        sections_label.setStyleSheet("font-weight: bold; margin-top: 10px; color: #2f3542;")
        info_layout.addRow(sections_label)
        
        sections_help = QLabel("<i>Divide the form into sections (e.g., 'General Info', 'Measurements', 'Results')</i>")
        sections_help.setWordWrap(True)
        info_layout.addRow("", sections_help)
        
        self.sections_input = QTextEdit()
        self.sections_input.setMaximumHeight(80)
        self.sections_input.setPlaceholderText('Example:\nGeneral Information\nMeasurements\nQuality Results\nSign-off')
        self.sections_input.setToolTip("Enter section titles, one per line. Each section will appear as a separate group in the form.\n\nExample:\n- General Information\n- Measurements\n- Quality Results")
        info_layout.addRow("Section Titles:", self.sections_input)
        
        # Form Configuration
        form_config_label = QLabel("Form Configuration - Control user interaction")
        form_config_label.setStyleSheet("font-weight: bold; margin-top: 10px; color: #2f3542;")
        info_layout.addRow(form_config_label)
        
        form_help = QLabel("<i>These settings control how users can fill out and submit the form.</i>")
        form_help.setWordWrap(True)
        info_layout.addRow("", form_help)
        
        form_config_group = QGroupBox()
        form_config_layout = QFormLayout()
        
        self.form_validation_combo = QComboBox()
        self.form_validation_combo.addItems(['strict', 'normal', 'permissive', 'none'])
        self.form_validation_combo.setToolTip("Data checking level:\nstrict = All required fields must be filled, strict format checks\nnormal = Basic validation only\npermissive = Warnings but allows saving\nnone = No validation (not recommended)")
        form_config_layout.addRow("Validation:", self.form_validation_combo)
        
        self.form_submit_button_input = QLineEdit()
        self.form_submit_button_input.setText("Save Record")
        self.form_submit_button_input.setToolTip("Text shown on the save button (e.g., 'Complete Inspection', 'Submit Report')")
        form_config_layout.addRow("Submit Button:", self.form_submit_button_input)
        
        self.form_auto_save_check = QCheckBox("Enable auto-save (saves as you type)")
        self.form_auto_save_check.setToolTip("Automatically saves work in progress - useful for long forms")
        form_config_layout.addRow("", self.form_auto_save_check)
        
        self.form_show_progress_check = QCheckBox("Show progress indicator (% complete)")
        self.form_show_progress_check.setToolTip("Shows a progress bar indicating form completion percentage")
        form_config_layout.addRow("", self.form_show_progress_check)
        
        self.form_allow_draft_check = QCheckBox("Allow saving as draft (incomplete records)")
        self.form_allow_draft_check.setChecked(True)
        self.form_allow_draft_check.setToolTip("Users can save incomplete records and finish them later")
        form_config_layout.addRow("", self.form_allow_draft_check)
        
        form_config_group.setLayout(form_config_layout)
        info_layout.addRow(form_config_group)
        
        tabs.addTab(info_scroll, "Template Info")
        
        # Tab 2: Template Fields
        fields_widget = QWidget()
        fields_layout = QVBoxLayout()
        fields_widget.setLayout(fields_layout)
        
        # Toolbar for fields
        fields_toolbar = QHBoxLayout()
        btn_add_field = QPushButton("Add Field")
        btn_add_field.clicked.connect(self.add_template_field)
        btn_remove_field = QPushButton("Remove Field")
        btn_remove_field.clicked.connect(self.remove_template_field)
        btn_move_up = QPushButton("Move Up")
        btn_move_up.clicked.connect(self.move_field_up)
        btn_move_down = QPushButton("Move Down")
        btn_move_down.clicked.connect(self.move_field_down)
        
        fields_toolbar.addWidget(btn_add_field)
        fields_toolbar.addWidget(btn_remove_field)
        fields_toolbar.addWidget(btn_move_up)
        fields_toolbar.addWidget(btn_move_down)
        fields_toolbar.addStretch()
        
        fields_layout.addLayout(fields_toolbar)
        
        # Fields table
        self.fields_table = QTableWidget()
        self.fields_table.setColumnCount(6)
        self.fields_table.setHorizontalHeaderLabels([
            'Criteria ID', 'Criteria Code', 'Title', 'Data Type', 'Required', 'Visible'
        ])
        self.fields_table.setColumnHidden(0, True)
        self.fields_table.horizontalHeader().setStretchLastSection(True)
        self.fields_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        fields_layout.addWidget(self.fields_table)
        
        tabs.addTab(fields_widget, "Template Fields")
        
        # Tab 3: Custom Fields (Meta)
        meta_widget = QWidget()
        meta_layout = QVBoxLayout()
        meta_widget.setLayout(meta_layout)
        
        meta_label = QLabel("Custom metadata fields (key-value pairs)")
        meta_layout.addWidget(meta_label)
        
        # Toolbar for meta
        meta_toolbar = QHBoxLayout()
        btn_add_meta = QPushButton("Add Field")
        btn_add_meta.clicked.connect(self.add_meta_field)
        btn_remove_meta = QPushButton("Remove Field")
        btn_remove_meta.clicked.connect(self.remove_meta_field)
        
        meta_toolbar.addWidget(btn_add_meta)
        meta_toolbar.addWidget(btn_remove_meta)
        meta_toolbar.addStretch()
        
        meta_layout.addLayout(meta_toolbar)
        
        # Meta table
        self.meta_table = QTableWidget()
        self.meta_table.setColumnCount(2)
        self.meta_table.setHorizontalHeaderLabels(['Key', 'Value'])
        self.meta_table.horizontalHeader().setStretchLastSection(True)
        self.meta_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        meta_layout.addWidget(self.meta_table)
        
        tabs.addTab(meta_widget, "Custom Fields")
        
        main_layout.addWidget(tabs)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.save_template)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)
    
    def load_standards(self):
        """Load standards into combo box"""
        standards = self.session.query(Standard).filter_by(is_active=True).all()
        self.standard_combo.addItem("-- No Standard --", None)
        for standard in standards:
            self.standard_combo.addItem(f"{standard.code} - {standard.name}", standard.id)
    
    def on_standard_changed(self):
        """Handle standard selection change"""
        # This could be used to suggest criteria from the selected standard
        pass
    
    def add_template_field(self):
        """Add a field to the template"""
        standard_id = self.standard_combo.currentData()
        
        # Get available criteria
        if standard_id:
            criteria = self.session.query(StandardCriteria).filter_by(
                standard_id=standard_id, is_active=True
            ).all()
        else:
            criteria = self.session.query(StandardCriteria).filter_by(is_active=True).all()
        
        if not criteria:
            QMessageBox.warning(self, "No Criteria", 
                               "No criteria available. Please select a standard with criteria.")
            return
        
        # Show dialog to select criteria
        dialog = QDialog(self)
        dialog.setWindowTitle("Select Criteria")
        dialog.setMinimumWidth(700)
        dialog.setMinimumHeight(500)
        
        layout = QVBoxLayout()
        dialog.setLayout(layout)
        
        label = QLabel("Select a criteria to add to this template:")
        layout.addWidget(label)
        
        # Criteria list
        criteria_table = QTableWidget()
        criteria_table.setColumnCount(5)
        criteria_table.setHorizontalHeaderLabels(['ID', 'Code', 'Title', 'Data Type', 'Requirement'])
        criteria_table.setColumnHidden(0, True)
        criteria_table.setRowCount(len(criteria))
        criteria_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        criteria_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        
        for row_idx, criterion in enumerate(criteria):
            criteria_table.setItem(row_idx, 0, QTableWidgetItem(str(criterion.id)))
            criteria_table.setItem(row_idx, 1, QTableWidgetItem(criterion.code))
            criteria_table.setItem(row_idx, 2, QTableWidgetItem(criterion.title))
            criteria_table.setItem(row_idx, 3, QTableWidgetItem(criterion.data_type))
            criteria_table.setItem(row_idx, 4, QTableWidgetItem(criterion.requirement_type))
        
        # Resize columns
        criteria_table.horizontalHeader().setStretchLastSection(True)
        criteria_table.resizeColumnsToContents()
        
        # Select first row by default
        if criteria_table.rowCount() > 0:
            criteria_table.selectRow(0)
        
        layout.addWidget(criteria_table)
        
        # Field configuration
        config_group = QGroupBox("Field Configuration")
        config_layout = QFormLayout()
        config_group.setLayout(config_layout)
        
        required_check = QCheckBox("Required")
        required_check.setChecked(True)
        config_layout.addRow("Is Required:", required_check)
        
        visible_check = QCheckBox("Visible")
        visible_check.setChecked(True)
        config_layout.addRow("Is Visible:", visible_check)
        
        layout.addWidget(config_group)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        # Enable double-click to accept
        criteria_table.doubleClicked.connect(dialog.accept)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_row = criteria_table.currentRow()
            if selected_row >= 0:
                criterion_id = int(criteria_table.item(selected_row, 0).text())
                criterion = self.session.get(StandardCriteria, criterion_id)
                
                if criterion:
                    # Check if criteria already added
                    for row in range(self.fields_table.rowCount()):
                        existing_id = self.fields_table.item(row, 0).text()
                        if existing_id == str(criterion.id):
                            QMessageBox.warning(self, "Duplicate Field", 
                                               "This criteria is already added to the template.")
                            return
                    
                    # Add to table
                    row = self.fields_table.rowCount()
                    self.fields_table.insertRow(row)
                    
                    self.fields_table.setItem(row, 0, QTableWidgetItem(str(criterion.id)))
                    self.fields_table.setItem(row, 1, QTableWidgetItem(criterion.code))
                    self.fields_table.setItem(row, 2, QTableWidgetItem(criterion.title))
                    self.fields_table.setItem(row, 3, QTableWidgetItem(criterion.data_type))
                    
                    required_item = QTableWidgetItem("Yes" if required_check.isChecked() else "No")
                    required_item.setData(Qt.ItemDataRole.UserRole, required_check.isChecked())
                    self.fields_table.setItem(row, 4, required_item)
                    
                    visible_item = QTableWidgetItem("Yes" if visible_check.isChecked() else "No")
                    visible_item.setData(Qt.ItemDataRole.UserRole, visible_check.isChecked())
                    self.fields_table.setItem(row, 5, visible_item)
                    
                    # Select the newly added row
                    self.fields_table.selectRow(row)
            else:
                QMessageBox.warning(self, "No Selection", "Please select a criteria to add.")
    
    def remove_template_field(self):
        """Remove selected field"""
        if self.fields_table.currentRow() >= 0:
            self.fields_table.removeRow(self.fields_table.currentRow())
    
    def move_field_up(self):
        """Move field up in order"""
        row = self.fields_table.currentRow()
        if row > 0:
            # Swap rows
            for col in range(self.fields_table.columnCount()):
                item1 = self.fields_table.takeItem(row, col)
                item2 = self.fields_table.takeItem(row - 1, col)
                self.fields_table.setItem(row - 1, col, item1)
                self.fields_table.setItem(row, col, item2)
            self.fields_table.setCurrentCell(row - 1, 0)
    
    def move_field_down(self):
        """Move field down in order"""
        row = self.fields_table.currentRow()
        if row < self.fields_table.rowCount() - 1:
            # Swap rows
            for col in range(self.fields_table.columnCount()):
                item1 = self.fields_table.takeItem(row, col)
                item2 = self.fields_table.takeItem(row + 1, col)
                self.fields_table.setItem(row + 1, col, item1)
                self.fields_table.setItem(row, col, item2)
            self.fields_table.setCurrentCell(row + 1, 0)
    
    def load_template_data(self):
        """Load existing template data"""
        if not self.template:
            return
        
        self.code_input.setText(self.template.code)
        self.name_input.setText(self.template.name)
        
        if self.template.standard_id:
            index = self.standard_combo.findData(self.template.standard_id)
            if index >= 0:
                self.standard_combo.setCurrentIndex(index)
        
        if self.template.category:
            self.category_combo.setCurrentText(self.template.category)
        
        if self.template.version:
            self.version_input.setText(self.template.version)
        
        if self.template.description:
            self.description_input.setText(self.template.description)
        
        self.requires_approval_check.setChecked(self.template.requires_approval)
        self.is_active_check.setChecked(self.template.is_active)
        
        # Load meta data
        self.load_meta_data()
        
        # Load approval levels
        if self.template.approval_levels:
            self.approval_levels_input.setValue(self.template.approval_levels)
        
        # Load frequency
        if self.template.frequency:
            self.frequency_combo.setCurrentText(self.template.frequency)
        
        # Load estimated duration
        if self.template.estimated_duration_minutes:
            self.estimated_duration_input.setValue(self.template.estimated_duration_minutes)
        
        # Load required equipment (JSON list to text)
        if self.template.required_equipment:
            try:
                equipment_list = json.loads(self.template.required_equipment)
                self.required_equipment_input.setText('\n'.join(equipment_list))
            except (json.JSONDecodeError, TypeError):
                # If it's not valid JSON, treat as text
                self.required_equipment_input.setText(self.template.required_equipment)
        
        # Load required certifications (JSON list to text)
        if self.template.required_certifications:
            try:
                cert_list = json.loads(self.template.required_certifications)
                self.required_certifications_input.setText('\n'.join(cert_list))
            except (json.JSONDecodeError, TypeError):
                # If it's not valid JSON, treat as text
                self.required_certifications_input.setText(self.template.required_certifications)
        
        # Load layout configuration
        if self.template.layout:
            try:
                layout_dict = self.template.layout if isinstance(self.template.layout, dict) else json.loads(self.template.layout)
                
                if 'columns' in layout_dict:
                    self.layout_columns_input.setValue(int(layout_dict['columns']))
                if 'style' in layout_dict:
                    self.layout_style_combo.setCurrentText(layout_dict['style'])
                if 'orientation' in layout_dict:
                    self.layout_orientation_combo.setCurrentText(layout_dict['orientation'])
                if 'spacing' in layout_dict:
                    self.layout_spacing_input.setValue(int(layout_dict['spacing']))
            except Exception as e:
                print(f"Error loading layout: {e}")
        
        # Load sections configuration
        if self.template.sections:
            try:
                sections_data = self.template.sections if isinstance(self.template.sections, list) else json.loads(self.template.sections)
                # Extract section titles from list of dicts
                if isinstance(sections_data, list) and sections_data:
                    section_titles = [s.get('title', '') for s in sections_data if isinstance(s, dict)]
                    self.sections_input.setText('\n'.join(section_titles))
                else:
                    self.sections_input.setText('')
            except Exception as e:
                print(f"Error loading sections: {e}")
        
        # Load form configuration
        if self.template.form_config:
            try:
                config_dict = self.template.form_config if isinstance(self.template.form_config, dict) else json.loads(self.template.form_config)
                
                if 'validation' in config_dict:
                    self.form_validation_combo.setCurrentText(config_dict['validation'])
                if 'submit_button' in config_dict:
                    self.form_submit_button_input.setText(config_dict['submit_button'])
                if 'auto_save' in config_dict:
                    self.form_auto_save_check.setChecked(bool(config_dict['auto_save']))
                if 'show_progress' in config_dict:
                    self.form_show_progress_check.setChecked(bool(config_dict['show_progress']))
                if 'allow_draft' in config_dict:
                    self.form_allow_draft_check.setChecked(bool(config_dict['allow_draft']))
            except Exception as e:
                print(f"Error loading form_config: {e}")
        
        # Load template fields
        fields = self.session.query(TemplateField).filter_by(
            template_id=self.template.id
        ).order_by(TemplateField.sort_order).all()
        
        self.fields_table.setRowCount(len(fields))
        for row_idx, field in enumerate(fields):
            if field.criteria:
                self.fields_table.setItem(row_idx, 0, QTableWidgetItem(str(field.criteria_id)))
                self.fields_table.setItem(row_idx, 1, QTableWidgetItem(field.criteria.code))
                self.fields_table.setItem(row_idx, 2, QTableWidgetItem(field.criteria.title))
                self.fields_table.setItem(row_idx, 3, QTableWidgetItem(field.criteria.data_type))
                
                required_item = QTableWidgetItem("Yes" if field.is_required else "No")
                required_item.setData(Qt.ItemDataRole.UserRole, field.is_required)
                self.fields_table.setItem(row_idx, 4, required_item)
                
                visible_item = QTableWidgetItem("Yes" if field.is_visible else "No")
                visible_item.setData(Qt.ItemDataRole.UserRole, field.is_visible)
                self.fields_table.setItem(row_idx, 5, visible_item)
    
    def add_meta_field(self):
        """Add a new meta field row"""
        row = self.meta_table.rowCount()
        self.meta_table.insertRow(row)
        self.meta_table.setItem(row, 0, QTableWidgetItem(""))
        self.meta_table.setItem(row, 1, QTableWidgetItem(""))
    
    def remove_meta_field(self):
        """Remove selected meta field"""
        if self.meta_table.currentRow() < 0:
            QMessageBox.warning(self, "No Selection", "Please select a field to remove")
            return
        self.meta_table.removeRow(self.meta_table.currentRow())
    
    def load_meta_data(self):
        """Load meta JSON data into table"""
        if not self.template or not self.template.meta:
            return
        
        try:
            meta_dict = self.template.meta if isinstance(self.template.meta, dict) else {}
            self.meta_table.setRowCount(len(meta_dict))
            
            for row_idx, (key, value) in enumerate(meta_dict.items()):
                self.meta_table.setItem(row_idx, 0, QTableWidgetItem(str(key)))
                self.meta_table.setItem(row_idx, 1, QTableWidgetItem(str(value)))
        except Exception as e:
            print(f"Error loading meta data: {e}")
    
    def save_meta_data(self, template):
        """Save meta table data as JSON"""
        meta_dict = {}
        for row in range(self.meta_table.rowCount()):
            key_item = self.meta_table.item(row, 0)
            value_item = self.meta_table.item(row, 1)
            
            if key_item and key_item.text().strip():
                key = key_item.text().strip()
                value = value_item.text() if value_item else ""
                meta_dict[key] = value
        
        template.meta = meta_dict if meta_dict else None
    
    def save_template(self):
        """Save the template"""
        # Validation
        if not self.code_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Please enter a code")
            return
        
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Please enter a name")
            return
        
        try:
            if self.template:
                # Update existing template
                template = self.template
            else:
                # Create new template
                # Check if code already exists
                existing = self.session.query(TestTemplate).filter_by(
                    code=self.code_input.text().strip()
                ).first()
                if existing:
                    QMessageBox.warning(self, "Validation Error", 
                                       "A template with this code already exists")
                    return
                
                template = TestTemplate()
                template.code = self.code_input.text().strip()
                template.created_by_id = self.current_user.id
            
            # Update fields
            template.name = self.name_input.text().strip()
            template.standard_id = self.standard_combo.currentData()
            template.category = self.category_combo.currentText()
            template.version = self.version_input.text().strip()
            template.description = self.description_input.toPlainText()
            template.requires_approval = self.requires_approval_check.isChecked()
            template.is_active = self.is_active_check.isChecked()
            template.updated_by_id = self.current_user.id
            
            # Save approval levels
            template.approval_levels = self.approval_levels_input.value() if self.approval_levels_input.value() > 0 else None
            
            # Save frequency
            template.frequency = self.frequency_combo.currentText()
            
            # Save estimated duration
            template.estimated_duration_minutes = self.estimated_duration_input.value() if self.estimated_duration_input.value() > 0 else None
            
            # Save required equipment (text lines to JSON list)
            equipment_text = self.required_equipment_input.toPlainText().strip()
            if equipment_text:
                equipment_list = [line.strip() for line in equipment_text.split('\n') if line.strip()]
                template.required_equipment = json.dumps(equipment_list) if equipment_list else None
            else:
                template.required_equipment = None
            
            # Save required certifications (text lines to JSON list)
            cert_text = self.required_certifications_input.toPlainText().strip()
            if cert_text:
                cert_list = [line.strip() for line in cert_text.split('\n') if line.strip()]
                template.required_certifications = json.dumps(cert_list) if cert_list else None
            else:
                template.required_certifications = None
            
            # Save layout configuration
            layout_dict = {
                'columns': self.layout_columns_input.value(),
                'style': self.layout_style_combo.currentText(),
                'orientation': self.layout_orientation_combo.currentText(),
                'spacing': self.layout_spacing_input.value()
            }
            template.layout = layout_dict
            
            # Save sections configuration
            sections_text = self.sections_input.toPlainText().strip()
            if sections_text:
                # Convert line-separated titles to list of section dicts
                section_titles = [line.strip() for line in sections_text.split('\n') if line.strip()]
                sections_data = [{'title': title, 'fields': []} for title in section_titles]
                template.sections = sections_data
            else:
                template.sections = None
            
            # Save form configuration
            form_config_dict = {
                'validation': self.form_validation_combo.currentText(),
                'submit_button': self.form_submit_button_input.text().strip(),
                'auto_save': self.form_auto_save_check.isChecked(),
                'show_progress': self.form_show_progress_check.isChecked(),
                'allow_draft': self.form_allow_draft_check.isChecked()
            }
            template.form_config = form_config_dict
            
            # Save meta data
            self.save_meta_data(template)
            
            if not self.template:
                self.session.add(template)
            
            self.session.flush()  # Get template ID
            
            # Save template fields
            # Remove existing fields using the relationship (safer than query.delete())
            if self.template:
                # Check if template is in use by records
                records_count = self.session.query(Record).filter_by(template_id=template.id).count()
                
                if records_count > 0:
                    # Template is in use - warn user but allow field updates
                    reply = QMessageBox.question(
                        self,
                        "Template In Use",
                        f"This template is used by {records_count} record(s).\n\n"
                        "Changing template fields may affect existing records.\n\n"
                        "Do you want to continue?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.No
                    )
                    
                    if reply == QMessageBox.StandardButton.No:
                        return
                
                # Before deleting fields, clear template_field_id references in record_items
                # This prevents foreign key constraint errors
                existing_field_ids = [field.id for field in template.fields]
                if existing_field_ids:
                    self.session.query(RecordItem).filter(
                        RecordItem.template_field_id.in_(existing_field_ids)
                    ).update({RecordItem.template_field_id: None}, synchronize_session=False)
                    self.session.flush()
                
                # Clear existing fields - cascade will handle deletion
                template.fields.clear()
                self.session.flush()
            
            # Add fields from table
            for row_idx in range(self.fields_table.rowCount()):
                criteria_id = int(self.fields_table.item(row_idx, 0).text())
                is_required = self.fields_table.item(row_idx, 4).data(Qt.ItemDataRole.UserRole)
                is_visible = self.fields_table.item(row_idx, 5).data(Qt.ItemDataRole.UserRole)
                
                field = TemplateField()
                field.template_id = template.id
                field.criteria_id = criteria_id
                field.is_required = is_required
                field.is_visible = is_visible
                field.sort_order = row_idx
                
                self.session.add(field)
            
            self.session.commit()
            
            # Audit logging
            action = 'update' if self.template else 'insert'
            try:
                log_entry = AuditLog(
                    table_name='templates',
                    record_id=template.id,
                    action=action,
                    user_id=self.current_user.id,
                    username=self.current_user.full_name,
                    new_values={'name': template.name, 'code': template.code, 'version': template.version},
                    timestamp=datetime.now()
                )
                self.session.add(log_entry)
                self.session.commit()
            except:
                pass
            
            self.accept()
            
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to save template:\n{str(e)}")


class StandardDialog(QDialog):
    """Dialog for creating/editing standards"""
    
    def __init__(self, session, current_user, standard=None, parent=None):
        super().__init__(parent)
        self.session = session
        self.current_user = current_user
        self.standard = standard
        
        self.setWindowTitle("Edit Standard" if standard else "New Standard")
        self.setMinimumWidth(900)
        self.setMinimumHeight(600)
        
        self.setup_ui()
        
        if standard:
            self.load_standard_data()
    
    def setup_ui(self):
        """Setup dialog UI"""
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        
        # Create tabs for standard info, sections, and criteria
        tabs = QTabWidget()
        
        # Tab 1: Standard Info
        info_widget = QWidget()
        info_scroll = QScrollArea()
        info_scroll.setWidgetResizable(True)
        info_scroll.setWidget(info_widget)
        
        info_layout = QFormLayout()
        info_widget.setLayout(info_layout)
        
        # Code
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("e.g., ISO-9001")
        if self.standard:
            self.code_input.setReadOnly(True)
        info_layout.addRow("Code:*", self.code_input)
        
        # Name
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter standard name")
        info_layout.addRow("Name:*", self.name_input)
        
        # Version
        self.version_input = QLineEdit()
        self.version_input.setPlaceholderText("e.g., 2015")
        info_layout.addRow("Version:*", self.version_input)
        
        # Industry
        self.industry_combo = QComboBox()
        self.industry_combo.addItems([
            'General', 'Manufacturing', 'Healthcare', 'Automotive',
            'Aerospace', 'Food & Beverage', 'Pharmaceutical', 'Construction'
        ])
        self.industry_combo.setEditable(True)
        info_layout.addRow("Industry:", self.industry_combo)
        
        # Description
        self.description_input = QTextEdit()
        self.description_input.setMaximumHeight(100)
        self.description_input.setPlaceholderText("Enter standard description")
        info_layout.addRow("Description:", self.description_input)
        
        # Scope
        self.scope_input = QTextEdit()
        self.scope_input.setMaximumHeight(80)
        self.scope_input.setPlaceholderText("Enter scope")
        info_layout.addRow("Scope:", self.scope_input)
        
        # Effective Date
        self.effective_date = QDateEdit()
        self.effective_date.setCalendarPopup(True)
        self.effective_date.setDate(datetime.now().date())
        self.effective_date.setSpecialValueText("Not Set")
        info_layout.addRow("Effective Date:", self.effective_date)
        
        # Expiry Date
        self.expiry_date = QDateEdit()
        self.expiry_date.setCalendarPopup(True)
        self.expiry_date.setDate(datetime.now().date())
        self.expiry_date.setSpecialValueText("Not Set")
        info_layout.addRow("Expiry Date:", self.expiry_date)
        
        # Document URL
        self.document_url_input = QLineEdit()
        self.document_url_input.setPlaceholderText("Enter document URL or file path")
        info_layout.addRow("Document URL:", self.document_url_input)
        
        # Is Active
        self.is_active_check = QCheckBox("Active")
        self.is_active_check.setChecked(True)
        info_layout.addRow("", self.is_active_check)
        
        tabs.addTab(info_scroll, "Standard Info")
        
        # Tab 2: Sections
        sections_widget = QWidget()
        sections_layout = QVBoxLayout()
        sections_widget.setLayout(sections_layout)
        
        # Toolbar for sections
        sections_toolbar = QHBoxLayout()
        btn_add_section = QPushButton("Add Section")
        btn_add_section.clicked.connect(self.add_section)
        btn_edit_section = QPushButton("Edit Section")
        btn_edit_section.clicked.connect(self.edit_section)
        btn_remove_section = QPushButton("Remove Section")
        btn_remove_section.clicked.connect(self.remove_section)
        
        sections_toolbar.addWidget(btn_add_section)
        sections_toolbar.addWidget(btn_edit_section)
        sections_toolbar.addWidget(btn_remove_section)
        sections_toolbar.addStretch()
        
        sections_layout.addLayout(sections_toolbar)
        
        # Sections table
        self.sections_table = QTableWidget()
        self.sections_table.setColumnCount(5)
        self.sections_table.setHorizontalHeaderLabels([
            'ID', 'Code', 'Title', 'Description', 'Order'
        ])
        self.sections_table.setColumnHidden(0, True)
        self.sections_table.horizontalHeader().setStretchLastSection(True)
        self.sections_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        sections_layout.addWidget(self.sections_table)
        
        tabs.addTab(sections_widget, "Sections")
        
        # Tab 3: Criteria
        criteria_widget = QWidget()
        criteria_layout = QVBoxLayout()
        criteria_widget.setLayout(criteria_layout)
        
        # Toolbar for criteria
        criteria_toolbar = QHBoxLayout()
        btn_add_criteria = QPushButton("Add Criteria")
        btn_add_criteria.clicked.connect(self.add_criteria)
        btn_edit_criteria = QPushButton("Edit Criteria")
        btn_edit_criteria.clicked.connect(self.edit_criteria)
        btn_remove_criteria = QPushButton("Remove Criteria")
        btn_remove_criteria.clicked.connect(self.remove_criteria)
        
        criteria_toolbar.addWidget(btn_add_criteria)
        criteria_toolbar.addWidget(btn_edit_criteria)
        criteria_toolbar.addWidget(btn_remove_criteria)
        criteria_toolbar.addStretch()
        
        criteria_layout.addLayout(criteria_toolbar)
        
        # Criteria table
        self.criteria_table = QTableWidget()
        self.criteria_table.setColumnCount(7)
        self.criteria_table.setHorizontalHeaderLabels([
            'ID', 'Code', 'Title', 'Data Type', 'Requirement', 'Severity', 'Active'
        ])
        self.criteria_table.setColumnHidden(0, True)
        self.criteria_table.horizontalHeader().setStretchLastSection(True)
        self.criteria_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        criteria_layout.addWidget(self.criteria_table)
        
        tabs.addTab(criteria_widget, "Criteria")
        
        # Tab 4: Custom Fields (Meta)
        meta_widget = QWidget()
        meta_layout = QVBoxLayout()
        meta_widget.setLayout(meta_layout)
        
        meta_label = QLabel("Custom metadata fields (key-value pairs)")
        meta_layout.addWidget(meta_label)
        
        # Toolbar for meta
        meta_toolbar = QHBoxLayout()
        btn_add_meta = QPushButton("Add Field")
        btn_add_meta.clicked.connect(self.add_meta_field)
        btn_remove_meta = QPushButton("Remove Field")
        btn_remove_meta.clicked.connect(self.remove_meta_field)
        
        meta_toolbar.addWidget(btn_add_meta)
        meta_toolbar.addWidget(btn_remove_meta)
        meta_toolbar.addStretch()
        
        meta_layout.addLayout(meta_toolbar)
        
        # Meta table
        self.meta_table = QTableWidget()
        self.meta_table.setColumnCount(2)
        self.meta_table.setHorizontalHeaderLabels(['Key', 'Value'])
        self.meta_table.horizontalHeader().setStretchLastSection(True)
        self.meta_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        meta_layout.addWidget(self.meta_table)
        
        tabs.addTab(meta_widget, "Custom Fields")

        # Tab 5: Attachments
        attachments_widget = QWidget()
        attachments_layout = QVBoxLayout()
        attachments_widget.setLayout(attachments_layout)
        
        # Toolbar for attachments
        attachments_toolbar = QHBoxLayout()
        btn_add_image = QPushButton("Attach Image")
        btn_add_image.clicked.connect(self.attach_image)
        btn_view_image = QPushButton("View Selected")
        btn_view_image.clicked.connect(self.view_image)
        btn_delete_image = QPushButton("Delete Selected")
        btn_delete_image.clicked.connect(self.delete_image)
        
        attachments_toolbar.addWidget(btn_add_image)
        attachments_toolbar.addWidget(btn_view_image)
        attachments_toolbar.addWidget(btn_delete_image)
        attachments_toolbar.addStretch()
        
        attachments_layout.addLayout(attachments_toolbar)
        
        # Images table
        self.images_table = QTableWidget()
        self.images_table.setColumnCount(4)
        self.images_table.setHorizontalHeaderLabels([
            'ID', 'Filename', 'Description', 'Uploaded At'
        ])
        self.images_table.setColumnHidden(0, True)
        self.images_table.horizontalHeader().setStretchLastSection(True)
        self.images_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        attachments_layout.addWidget(self.images_table)
        
        tabs.addTab(attachments_widget, "Attachments")
        
        main_layout.addWidget(tabs)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.save_standard)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)
    
    def add_section(self):
        """Add a section to the standard"""
        if not self.standard:
            QMessageBox.warning(self, "Save Required", 
                               "Please save the standard first before adding sections.")
            return
        
        dialog = SectionDialog(self.session, self.standard, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_sections()
    
    def edit_section(self):
        """Edit selected section"""
        if self.sections_table.currentRow() < 0:
            QMessageBox.warning(self, "No Selection", "Please select a section to edit")
            return
        
        section_id = int(self.sections_table.item(self.sections_table.currentRow(), 0).text())
        section = self.session.get(StandardSection, section_id)
        
        if section:
            dialog = SectionDialog(self.session, self.standard, section=section, parent=self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.load_sections()
    
    def remove_section(self):
        """Remove selected section"""
        if self.sections_table.currentRow() < 0:
            QMessageBox.warning(self, "No Selection", "Please select a section to remove")
            return
        
        section_id = int(self.sections_table.item(self.sections_table.currentRow(), 0).text())
        section = self.session.get(StandardSection, section_id)
        
        if section:
            reply = QMessageBox.question(
                self, "Confirm Delete", 
                f"Are you sure you want to delete section '{section.code}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.session.delete(section)
                self.session.commit()
                self.load_sections()
    
    def add_criteria(self):
        """Add criteria to the standard"""
        if not self.standard:
            QMessageBox.warning(self, "Save Required", 
                               "Please save the standard first before adding criteria.")
            return
        
        dialog = CriteriaDialog(self.session, self.standard, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_criteria()
    
    def edit_criteria(self):
        """Edit selected criteria"""
        if self.criteria_table.currentRow() < 0:
            QMessageBox.warning(self, "No Selection", "Please select criteria to edit")
            return
        
        criteria_id = int(self.criteria_table.item(self.criteria_table.currentRow(), 0).text())
        criteria = self.session.get(StandardCriteria, criteria_id)
        
        if criteria:
            dialog = CriteriaDialog(self.session, self.standard, criteria=criteria, parent=self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.load_criteria()
    
    def remove_criteria(self):
        """Remove selected criteria"""
        if self.criteria_table.currentRow() < 0:
            QMessageBox.warning(self, "No Selection", "Please select criteria to remove")
            return
        
        criteria_id = int(self.criteria_table.item(self.criteria_table.currentRow(), 0).text())
        criteria = self.session.get(StandardCriteria, criteria_id)
        
        if criteria:
            reply = QMessageBox.question(
                self, "Confirm Delete", 
                f"Are you sure you want to delete criteria '{criteria.code}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.session.delete(criteria)
                self.session.commit()
                self.load_criteria()

    def attach_image(self):
        """Attach an image to the standard"""
        if not self.standard:
            QMessageBox.warning(self, "Save Required", "Please save the standard first.")
            return
            
        dialog = ImageUploadDialog(self.session, self.current_user, self, self.standard.id, 'standard')
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_images()

    def load_images(self):
        """Load images attached to this standard"""
        if not self.standard:
            return
            
        self.images_table.setRowCount(0)
        
        images = self.session.query(ImageAttachment).filter(
            ImageAttachment.entity_type == 'standard',
            ImageAttachment.entity_id == self.standard.id
        ).all()
        
        for img in images:
            row = self.images_table.rowCount()
            self.images_table.insertRow(row)
            
            self.images_table.setItem(row, 0, QTableWidgetItem(str(img.id)))
            self.images_table.setItem(row, 1, QTableWidgetItem(img.filename))
            self.images_table.setItem(row, 2, QTableWidgetItem(img.description or ""))
            self.images_table.setItem(row, 3, QTableWidgetItem(img.uploaded_at.strftime('%Y-%m-%d %H:%M')))

    def view_image(self):
        """View the selected image"""
        if self.images_table.currentRow() < 0:
            QMessageBox.warning(self, "No Selection", "Please select an image to view")
            return
            
        image_id = int(self.images_table.item(self.images_table.currentRow(), 0).text())
        image_attachment = self.session.get(ImageAttachment, image_id)
        
        if image_attachment:
            img_path = image_attachment.file_path
            
            if img_path and os.path.exists(img_path):
                from pathlib import Path
                import webbrowser
                webbrowser.open(Path(img_path).as_uri())
            else:
                QMessageBox.warning(self, "Error", "Image file not found")

    def delete_image(self):
        """Delete the selected image"""
        if self.images_table.currentRow() < 0:
            QMessageBox.warning(self, "No Selection", "Please select an image to delete")
            return
            
        image_id = int(self.images_table.item(self.images_table.currentRow(), 0).text())
        image_attachment = self.session.get(ImageAttachment, image_id)
        
        if image_attachment:
            reply = QMessageBox.question(
                self, "Confirm Delete",
                f"Are you sure you want to delete the image '{image_attachment.filename}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Delete physical file
                from image_handler import ImageHandler
                handler = ImageHandler(self.session)
                handler.delete_image(image_attachment.id)
                
                self.load_images()
    
    def load_sections(self):
        """Load sections for the standard"""
        if not self.standard:
            return
        
        sections = self.session.query(StandardSection).filter_by(
            standard_id=self.standard.id
        ).order_by(StandardSection.sort_order).all()
        
        self.sections_table.setRowCount(len(sections))
        for row_idx, section in enumerate(sections):
            self.sections_table.setItem(row_idx, 0, QTableWidgetItem(str(section.id)))
            self.sections_table.setItem(row_idx, 1, QTableWidgetItem(section.code))
            self.sections_table.setItem(row_idx, 2, QTableWidgetItem(section.title))
            self.sections_table.setItem(row_idx, 3, QTableWidgetItem(section.description or ''))
            self.sections_table.setItem(row_idx, 4, QTableWidgetItem(str(section.sort_order or 0)))
    
    def load_criteria(self):
        """Load criteria for the standard"""
        if not self.standard:
            return
        
        criteria = self.session.query(StandardCriteria).filter_by(
            standard_id=self.standard.id
        ).order_by(StandardCriteria.sort_order).all()
        
        self.criteria_table.setRowCount(len(criteria))
        for row_idx, criterion in enumerate(criteria):
            self.criteria_table.setItem(row_idx, 0, QTableWidgetItem(str(criterion.id)))
            self.criteria_table.setItem(row_idx, 1, QTableWidgetItem(criterion.code))
            self.criteria_table.setItem(row_idx, 2, QTableWidgetItem(criterion.title))
            self.criteria_table.setItem(row_idx, 3, QTableWidgetItem(criterion.data_type))
            self.criteria_table.setItem(row_idx, 4, QTableWidgetItem(criterion.requirement_type))
            self.criteria_table.setItem(row_idx, 5, QTableWidgetItem(criterion.severity or ''))
            self.criteria_table.setItem(row_idx, 6, QTableWidgetItem('Yes' if criterion.is_active else 'No'))
    
    def add_meta_field(self):
        """Add a new meta field row"""
        row = self.meta_table.rowCount()
        self.meta_table.insertRow(row)
        self.meta_table.setItem(row, 0, QTableWidgetItem(""))
        self.meta_table.setItem(row, 1, QTableWidgetItem(""))
    
    def remove_meta_field(self):
        """Remove selected meta field"""
        if self.meta_table.currentRow() < 0:
            QMessageBox.warning(self, "No Selection", "Please select a field to remove")
            return
        self.meta_table.removeRow(self.meta_table.currentRow())
    
    def load_meta_data(self):
        """Load meta JSON data into table"""
        if not self.standard or not self.standard.meta:
            return
        
        try:
            meta_dict = self.standard.meta if isinstance(self.standard.meta, dict) else {}
            self.meta_table.setRowCount(len(meta_dict))
            
            for row_idx, (key, value) in enumerate(meta_dict.items()):
                self.meta_table.setItem(row_idx, 0, QTableWidgetItem(str(key)))
                self.meta_table.setItem(row_idx, 1, QTableWidgetItem(str(value)))
        except Exception as e:
            print(f"Error loading meta data: {e}")
    
    def save_meta_data(self, standard):
        """Save meta table data as JSON"""
        meta_dict = {}
        for row in range(self.meta_table.rowCount()):
            key_item = self.meta_table.item(row, 0)
            value_item = self.meta_table.item(row, 1)
            
            if key_item and key_item.text().strip():
                key = key_item.text().strip()
                value = value_item.text() if value_item else ""
                meta_dict[key] = value
        
        standard.meta = meta_dict if meta_dict else None
    
    def load_standard_data(self):
        """Load existing standard data"""
        if not self.standard:
            return
        
        self.code_input.setText(self.standard.code)
        self.name_input.setText(self.standard.name)
        self.version_input.setText(self.standard.version)
        
        if self.standard.industry:
            self.industry_combo.setCurrentText(self.standard.industry)
        
        if self.standard.description:
            self.description_input.setText(self.standard.description)
        
        if self.standard.scope:
            self.scope_input.setText(self.standard.scope)
        
        if self.standard.effective_date:
            self.effective_date.setDate(self.standard.effective_date)
        
        if self.standard.expiry_date:
            self.expiry_date.setDate(self.standard.expiry_date)
        
        if self.standard.document_url:
            self.document_url_input.setText(self.standard.document_url)
        
        self.is_active_check.setChecked(self.standard.is_active)
        
        # Load sections, criteria, meta, and images
        self.load_sections()
        self.load_criteria()
        self.load_meta_data()
        self.load_images()
    
    def save_standard(self):
        """Save the standard"""
        # Validation
        if not self.code_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Please enter a code")
            return
        
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Please enter a name")
            return
        
        if not self.version_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Please enter a version")
            return
        
        try:
            if self.standard:
                # Update existing standard
                standard = self.standard
            else:
                # Create new standard
                # Check if code already exists
                existing = self.session.query(Standard).filter_by(
                    code=self.code_input.text().strip()
                ).first()
                if existing:
                    QMessageBox.warning(self, "Validation Error", 
                                       "A standard with this code already exists")
                    return
                
                standard = Standard()
                standard.code = self.code_input.text().strip()
                standard.created_by_id = self.current_user.id
            
            # Update fields
            standard.name = self.name_input.text().strip()
            standard.version = self.version_input.text().strip()
            standard.industry = self.industry_combo.currentText()
            standard.description = self.description_input.toPlainText()
            standard.scope = self.scope_input.toPlainText()
            standard.effective_date = self.effective_date.date().toPyDate()
            standard.expiry_date = self.expiry_date.date().toPyDate()
            standard.document_url = self.document_url_input.text().strip() or None
            standard.is_active = self.is_active_check.isChecked()
            
            # Save meta data
            self.save_meta_data(standard)
            
            if not self.standard:
                self.session.add(standard)
                self.session.flush()
                self.standard = standard  # Store for sections/criteria
            
            self.session.commit()
            
            # Audit logging
            action = 'update' if self.standard else 'insert'
            try:
                log_entry = AuditLog(
                    table_name='standards',
                    record_id=standard.id,
                    action=action,
                    user_id=self.current_user.id,
                    username=self.current_user.full_name,
                    new_values={'code': standard.code, 'name': standard.name, 'version': standard.version},
                    timestamp=datetime.now()
                )
                self.session.add(log_entry)
                self.session.commit()
            except:
                pass
            
            self.accept()
            
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to save standard:\n{str(e)}")


class SectionDialog(QDialog):
    """Dialog for creating/editing standard sections"""
    
    def __init__(self, session, standard, section=None, parent=None):
        super().__init__(parent)
        self.session = session
        self.standard = standard
        self.section = section
        
        self.setWindowTitle("Edit Section" if section else "New Section")
        self.setMinimumWidth(500)
        
        self.setup_ui()
        
        if section:
            self.load_section_data()
    
    def setup_ui(self):
        """Setup dialog UI"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        form_layout = QFormLayout()
        
        # Code
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("e.g., 4.1")
        form_layout.addRow("Code:*", self.code_input)
        
        # Title
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Enter section title")
        form_layout.addRow("Title:*", self.title_input)
        
        # Parent Section (for hierarchical nesting)
        self.parent_section_combo = QComboBox()
        self.parent_section_combo.addItem("-- No Parent (Top Level) --", None)
        self.load_parent_sections()
        self.parent_section_combo.setToolTip("Select a parent section to create nested hierarchy")
        form_layout.addRow("Parent Section:", self.parent_section_combo)
        
        # Description
        self.description_input = QTextEdit()
        self.description_input.setMaximumHeight(100)
        self.description_input.setPlaceholderText("Enter section description")
        form_layout.addRow("Description:", self.description_input)
        
        # Sort Order
        self.sort_order_input = QLineEdit()
        self.sort_order_input.setPlaceholderText("0")
        self.sort_order_input.setText("0")
        form_layout.addRow("Sort Order:", self.sort_order_input)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.save_section)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def load_parent_sections(self):
        """Load potential parent sections (excluding current section if editing)"""
        sections = self.session.query(StandardSection).filter_by(
            standard_id=self.standard.id
        ).order_by(StandardSection.sort_order).all()
        
        for section in sections:
            # Don't allow section to be its own parent
            if self.section and section.id == self.section.id:
                continue
            self.parent_section_combo.addItem(
                f"{section.code} - {section.title}",
                section.id
            )
    
    def load_section_data(self):
        """Load existing section data"""
        if not self.section:
            return
        
        self.code_input.setText(self.section.code)
        self.title_input.setText(self.section.title)
        
        if self.section.description:
            self.description_input.setText(self.section.description)
        
        # Load parent section
        if self.section.parent_section_id:
            index = self.parent_section_combo.findData(self.section.parent_section_id)
            if index >= 0:
                self.parent_section_combo.setCurrentIndex(index)
        
        if self.section.sort_order is not None:
            self.sort_order_input.setText(str(self.section.sort_order))
    
    def save_section(self):
        """Save the section"""
        # Validation
        if not self.code_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Please enter a code")
            return
        
        if not self.title_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Please enter a title")
            return
        
        try:
            if self.section:
                section = self.section
            else:
                section = StandardSection()
                section.standard_id = self.standard.id
            
            section.code = self.code_input.text().strip()
            section.title = self.title_input.text().strip()
            section.description = self.description_input.toPlainText() or None
            section.parent_section_id = self.parent_section_combo.currentData()
            
            try:
                section.sort_order = int(self.sort_order_input.text())
            except:
                section.sort_order = 0
            
            if not self.section:
                self.session.add(section)
            
            self.session.commit()
            self.accept()
            
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to save section:\n{str(e)}")


class CriteriaDialog(QDialog):
    """Dialog for creating/editing standard criteria"""
    
    def __init__(self, session, standard, criteria=None, parent=None):
        super().__init__(parent)
        self.session = session
        self.standard = standard
        self.criteria = criteria
        
        self.setWindowTitle("Edit Criteria" if criteria else "New Criteria")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        
        self.setup_ui()
        
        if criteria:
            self.load_criteria_data()
    
    def setup_ui(self):
        """Setup dialog UI"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Create scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll.setWidget(scroll_widget)
        
        form_layout = QFormLayout()
        scroll_widget.setLayout(form_layout)
        
        # Section
        self.section_combo = QComboBox()
        self.section_combo.addItem("-- No Section --", None)
        sections = self.session.query(StandardSection).filter_by(
            standard_id=self.standard.id
        ).order_by(StandardSection.sort_order).all()
        for section in sections:
            self.section_combo.addItem(f"{section.code} - {section.title}", section.id)
        form_layout.addRow("Section:", self.section_combo)
        
        # Code
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("e.g., 4.1.1")
        form_layout.addRow("Code:*", self.code_input)
        
        # Title
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Enter criteria title")
        form_layout.addRow("Title:*", self.title_input)
        
        # Description
        self.description_input = QTextEdit()
        self.description_input.setMaximumHeight(80)
        self.description_input.setPlaceholderText("Enter criteria description")
        form_layout.addRow("Description:", self.description_input)
        
        # Requirement Type
        self.requirement_type_combo = QComboBox()
        self.requirement_type_combo.addItems(['mandatory', 'conditional', 'optional'])
        form_layout.addRow("Requirement Type:*", self.requirement_type_combo)
        
        # Data Type
        self.data_type_combo = QComboBox()
        self.data_type_combo.addItems([
            'numeric', 'boolean', 'text', 'select', 'multiselect', 'date', 'file'
        ])
        self.data_type_combo.currentTextChanged.connect(self.on_data_type_changed)
        form_layout.addRow("Data Type:*", self.data_type_combo)
        
        # Numeric fields (shown only for numeric data type)
        self.numeric_group = QWidget()
        numeric_layout = QFormLayout()
        self.numeric_group.setLayout(numeric_layout)
        
        self.limit_min_input = QLineEdit()
        self.limit_min_input.setPlaceholderText("Enter minimum value")
        numeric_layout.addRow("Min Value:", self.limit_min_input)
        
        self.limit_max_input = QLineEdit()
        self.limit_max_input.setPlaceholderText("Enter maximum value")
        numeric_layout.addRow("Max Value:", self.limit_max_input)
        
        self.tolerance_input = QLineEdit()
        self.tolerance_input.setPlaceholderText("Enter tolerance")
        numeric_layout.addRow("Tolerance:", self.tolerance_input)
        
        self.unit_input = QLineEdit()
        self.unit_input.setPlaceholderText("e.g., mm, kg, °C")
        numeric_layout.addRow("Unit:", self.unit_input)
        
        form_layout.addRow("", self.numeric_group)
        self.numeric_group.setVisible(False)
        
        # Options (for select/multiselect)
        self.options_group = QWidget()
        options_layout = QVBoxLayout()
        self.options_group.setLayout(options_layout)
        
        options_label = QLabel("Options (one per line):")
        options_layout.addWidget(options_label)
        
        self.options_input = QTextEdit()
        self.options_input.setMaximumHeight(100)
        self.options_input.setPlaceholderText("Option 1\nOption 2\nOption 3")
        options_layout.addWidget(self.options_input)
        
        form_layout.addRow("", self.options_group)
        self.options_group.setVisible(False)
        
        # Severity
        self.severity_combo = QComboBox()
        self.severity_combo.addItem("-- Not Set --", None)
        self.severity_combo.addItems(['critical', 'major', 'minor'])
        form_layout.addRow("Severity:", self.severity_combo)
        
        # Help Text
        self.help_text_input = QTextEdit()
        self.help_text_input.setMaximumHeight(60)
        self.help_text_input.setPlaceholderText("Enter help text for users")
        form_layout.addRow("Help Text:", self.help_text_input)
        
        # Validation Rules (User-Friendly Interface)
        validation_label = QLabel("Validation Rules")
        validation_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        validation_label.setToolTip("Rules that will be checked when users enter data for this criteria")
        form_layout.addRow(validation_label)
        
        # Text validation group
        self.text_validation_group = QGroupBox("Text Validation")
        text_validation_layout = QFormLayout()
        self.text_validation_group.setLayout(text_validation_layout)
        
        self.min_length_check = QCheckBox("Minimum Length")
        self.min_length_input = QSpinBox()
        self.min_length_input.setRange(0, 10000)
        self.min_length_input.setValue(0)
        self.min_length_input.setEnabled(False)
        self.min_length_check.toggled.connect(self.min_length_input.setEnabled)
        min_length_layout = QHBoxLayout()
        min_length_layout.addWidget(self.min_length_check)
        min_length_layout.addWidget(self.min_length_input)
        min_length_layout.addStretch()
        text_validation_layout.addRow("", min_length_layout)
        
        self.max_length_check = QCheckBox("Maximum Length")
        self.max_length_input = QSpinBox()
        self.max_length_input.setRange(0, 10000)
        self.max_length_input.setValue(100)
        self.max_length_input.setEnabled(False)
        self.max_length_check.toggled.connect(self.max_length_input.setEnabled)
        max_length_layout = QHBoxLayout()
        max_length_layout.addWidget(self.max_length_check)
        max_length_layout.addWidget(self.max_length_input)
        max_length_layout.addStretch()
        text_validation_layout.addRow("", max_length_layout)
        
        self.pattern_check = QCheckBox("Must Match Pattern (Regex)")
        self.pattern_input = QLineEdit()
        self.pattern_input.setPlaceholderText("e.g., ^[A-Z][0-9]{3}$ for format like A123")
        self.pattern_input.setEnabled(False)
        self.pattern_check.toggled.connect(self.pattern_input.setEnabled)
        pattern_layout = QHBoxLayout()
        pattern_layout.addWidget(self.pattern_check)
        pattern_layout.addWidget(self.pattern_input)
        text_validation_layout.addRow("", pattern_layout)
        
        self.required_check = QCheckBox("Required Field (Cannot be empty)")
        text_validation_layout.addRow("", self.required_check)
        
        form_layout.addRow("", self.text_validation_group)
        self.text_validation_group.setVisible(False)
        
        # Numeric validation group
        self.numeric_validation_group = QGroupBox("Numeric Validation")
        numeric_validation_layout = QFormLayout()
        self.numeric_validation_group.setLayout(numeric_validation_layout)
        
        self.min_value_check = QCheckBox("Minimum Value")
        self.min_value_input = QDoubleSpinBox()
        self.min_value_input.setRange(-999999.99, 999999.99)
        self.min_value_input.setDecimals(2)
        self.min_value_input.setValue(0)
        self.min_value_input.setEnabled(False)
        self.min_value_check.toggled.connect(self.min_value_input.setEnabled)
        min_value_layout = QHBoxLayout()
        min_value_layout.addWidget(self.min_value_check)
        min_value_layout.addWidget(self.min_value_input)
        min_value_layout.addStretch()
        numeric_validation_layout.addRow("", min_value_layout)
        
        self.max_value_check = QCheckBox("Maximum Value")
        self.max_value_input = QDoubleSpinBox()
        self.max_value_input.setRange(-999999.99, 999999.99)
        self.max_value_input.setDecimals(2)
        self.max_value_input.setValue(100)
        self.max_value_input.setEnabled(False)
        self.max_value_check.toggled.connect(self.max_value_input.setEnabled)
        max_value_layout = QHBoxLayout()
        max_value_layout.addWidget(self.max_value_check)
        max_value_layout.addWidget(self.max_value_input)
        max_value_layout.addStretch()
        numeric_validation_layout.addRow("", max_value_layout)
        
        self.numeric_required_check = QCheckBox("Required Field (Must have a value)")
        numeric_validation_layout.addRow("", self.numeric_required_check)
        
        form_layout.addRow("", self.numeric_validation_group)
        self.numeric_validation_group.setVisible(False)
        
        # Sort Order
        self.sort_order_input = QLineEdit()
        self.sort_order_input.setText("0")
        form_layout.addRow("Sort Order:", self.sort_order_input)
        
        # Is Active
        self.is_active_check = QCheckBox("Active")
        self.is_active_check.setChecked(True)
        form_layout.addRow("", self.is_active_check)
        
        layout.addWidget(scroll)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.save_criteria)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def on_data_type_changed(self, data_type):
        """Show/hide fields based on data type"""
        self.numeric_group.setVisible(data_type == 'numeric')
        self.options_group.setVisible(data_type in ['select', 'multiselect'])
        
        # Show appropriate validation group
        if data_type == 'numeric':
            self.text_validation_group.setVisible(False)
            self.numeric_validation_group.setVisible(True)
        elif data_type in ['text', 'select', 'multiselect']:
            self.text_validation_group.setVisible(True)
            self.numeric_validation_group.setVisible(False)
        else:
            self.text_validation_group.setVisible(False)
            self.numeric_validation_group.setVisible(False)
    
    def load_criteria_data(self):
        """Load existing criteria data"""
        if not self.criteria:
            return
        
        if self.criteria.section_id:
            index = self.section_combo.findData(self.criteria.section_id)
            if index >= 0:
                self.section_combo.setCurrentIndex(index)
        
        self.code_input.setText(self.criteria.code)
        self.title_input.setText(self.criteria.title)
        
        if self.criteria.description:
            self.description_input.setText(self.criteria.description)
        
        self.requirement_type_combo.setCurrentText(self.criteria.requirement_type)
        self.data_type_combo.setCurrentText(self.criteria.data_type)
        
        if self.criteria.limit_min is not None:
            self.limit_min_input.setText(str(self.criteria.limit_min))
        
        if self.criteria.limit_max is not None:
            self.limit_max_input.setText(str(self.criteria.limit_max))
        
        if self.criteria.tolerance is not None:
            self.tolerance_input.setText(str(self.criteria.tolerance))
        
        if self.criteria.unit:
            self.unit_input.setText(self.criteria.unit)
        
        if self.criteria.options:
            self.options_input.setText('\n'.join(self.criteria.options))
        
        if self.criteria.severity:
            self.severity_combo.setCurrentText(self.criteria.severity)
        
        if self.criteria.help_text:
            self.help_text_input.setText(self.criteria.help_text)
        
        # Load validation rules into user-friendly fields
        if self.criteria.validation_rules:
            try:
                rules = self.criteria.validation_rules if isinstance(self.criteria.validation_rules, dict) else json.loads(self.criteria.validation_rules)  
                
                # Text validation rules
                if 'min_length' in rules:
                    self.min_length_check.setChecked(True)
                    self.min_length_input.setValue(int(rules['min_length']))
                
                if 'max_length' in rules:
                    self.max_length_check.setChecked(True)
                    self.max_length_input.setValue(int(rules['max_length']))
                
                if 'pattern' in rules:
                    self.pattern_check.setChecked(True)
                    self.pattern_input.setText(rules['pattern'])
                
                if 'required' in rules and rules['required']:
                    self.required_check.setChecked(True)
                
                # Numeric validation rules
                if 'min_value' in rules:
                    self.min_value_check.setChecked(True)
                    self.min_value_input.setValue(float(rules['min_value']))
                
                if 'max_value' in rules:
                    self.max_value_check.setChecked(True)
                    self.max_value_input.setValue(float(rules['max_value']))
                
                if 'numeric_required' in rules and rules['numeric_required']:
                    self.numeric_required_check.setChecked(True)
                    
            except Exception as e:
                print(f"Error loading validation rules: {e}")
        
        if self.criteria.sort_order is not None:
            self.sort_order_input.setText(str(self.criteria.sort_order))
        
        self.is_active_check.setChecked(self.criteria.is_active)
    
    def save_criteria(self):
        """Save the criteria"""
        # Validation
        if not self.code_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Please enter a code")
            return
        
        if not self.title_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Please enter a title")
            return
        
        try:
            if self.criteria:
                criteria = self.criteria
            else:
                criteria = StandardCriteria()
                criteria.standard_id = self.standard.id
            
            criteria.section_id = self.section_combo.currentData()
            criteria.code = self.code_input.text().strip()
            criteria.title = self.title_input.text().strip()
            criteria.description = self.description_input.toPlainText() or None
            criteria.requirement_type = self.requirement_type_combo.currentText()
            criteria.data_type = self.data_type_combo.currentText()
            
            # Numeric fields
            if criteria.data_type == 'numeric':
                try:
                    criteria.limit_min = float(self.limit_min_input.text()) if self.limit_min_input.text() else None
                except:
                    criteria.limit_min = None
                
                try:
                    criteria.limit_max = float(self.limit_max_input.text()) if self.limit_max_input.text() else None
                except:
                    criteria.limit_max = None
                
                try:
                    criteria.tolerance = float(self.tolerance_input.text()) if self.tolerance_input.text() else None
                except:
                    criteria.tolerance = None
                
                criteria.unit = self.unit_input.text().strip() or None
            else:
                criteria.limit_min = None
                criteria.limit_max = None
                criteria.tolerance = None
                criteria.unit = None
            
            # Options for select/multiselect
            if criteria.data_type in ['select', 'multiselect']:
                options_text = self.options_input.toPlainText().strip()
                if options_text:
                    criteria.options = [opt.strip() for opt in options_text.split('\n') if opt.strip()]
                else:
                    criteria.options = None
            else:
                criteria.options = None
            
            severity_text = self.severity_combo.currentText()
            criteria.severity = severity_text if severity_text != "-- Not Set --" else None
            
            criteria.help_text = self.help_text_input.toPlainText() or None
            
            # Build validation rules from user-friendly fields
            validation_rules = {}
            
            # Text validation rules
            if criteria.data_type in ['text', 'select', 'multiselect']:
                if self.min_length_check.isChecked():
                    validation_rules['min_length'] = self.min_length_input.value()
                
                if self.max_length_check.isChecked():
                    validation_rules['max_length'] = self.max_length_input.value()
                
                if self.pattern_check.isChecked() and self.pattern_input.text().strip():
                    validation_rules['pattern'] = self.pattern_input.text().strip()
                
                if self.required_check.isChecked():
                    validation_rules['required'] = True
            
            # Numeric validation rules
            elif criteria.data_type == 'numeric':
                if self.min_value_check.isChecked():
                    validation_rules['min_value'] = self.min_value_input.value()
                
                if self.max_value_check.isChecked():
                    validation_rules['max_value'] = self.max_value_input.value()
                
                if self.numeric_required_check.isChecked():
                    validation_rules['numeric_required'] = True
            
            # Save validation rules dict as JSON (or None if empty)
            criteria.validation_rules = validation_rules if validation_rules else None
            
            try:
                criteria.sort_order = int(self.sort_order_input.text())
            except:
                criteria.sort_order = 0
            
            criteria.is_active = self.is_active_check.isChecked()
            
            if not self.criteria:
                self.session.add(criteria)
            
            self.session.commit()
            
            # Audit logging
            action = 'update' if self.criteria else 'insert'
            try:
                log_entry = AuditLog(
                    table_name='criteria',
                    record_id=criteria.id,
                    action=action,
                    user_id=self.current_user.id,
                    username=self.current_user.full_name,
                    new_values={'code': criteria.code, 'title': criteria.title, 'data_type': criteria.data_type},
                    timestamp=datetime.now()
                )
                self.session.add(log_entry)
                self.session.commit()
            except:
                pass
            
            self.accept()
            
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to save criteria:\n{str(e)}")


class NonConformanceDialog(QDialog):
    """Dialog for creating/editing non-conformances"""
    
    def __init__(self, session, current_user, nc=None, parent=None):
        super().__init__(parent)
        self.session = session
        self.current_user = current_user
        self.nc = nc
        
        self.setWindowTitle("Edit Non-Conformance" if nc else "New Non-Conformance")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        
        self.setup_ui()
        
        if nc:
            self.load_nc_data()
    
    def setup_ui(self):
        """Setup dialog UI"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Create scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll.setWidget(scroll_widget)
        
        form_layout = QFormLayout()
        scroll_widget.setLayout(form_layout)
        
        # NC Number (auto-generated or display only)
        self.nc_number = QLineEdit()
        if self.nc:
            self.nc_number.setText(self.nc.nc_number)
            self.nc_number.setReadOnly(True)
        else:
            self.nc_number.setPlaceholderText("Auto-generated")
            self.nc_number.setReadOnly(True)
        form_layout.addRow("NC Number:", self.nc_number)
        
        # Title
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Enter NC title")
        form_layout.addRow("Title:*", self.title_input)
        
        # Severity
        self.severity_combo = QComboBox()
        self.severity_combo.addItems(['minor', 'major', 'critical'])
        form_layout.addRow("Severity:*", self.severity_combo)
        
        # Status
        self.status_combo = QComboBox()
        self.status_combo.addItems(['open', 'investigating', 'action_planned', 'action_taken', 'verified', 'closed'])
        form_layout.addRow("Status:", self.status_combo)
        
        # Related Record
        self.record_combo = QComboBox()
        self.load_records()
        form_layout.addRow("Related Record:", self.record_combo)
        
        # Detected Date
        self.detected_date = QDateEdit()
        self.detected_date.setCalendarPopup(True)
        self.detected_date.setDate(datetime.now().date())
        form_layout.addRow("Detected Date:", self.detected_date)
        
        # Assigned To
        self.assigned_combo = QComboBox()
        form_layout.addRow("Assigned To:", self.assigned_combo)
        
        # Description
        self.description_input = QTextEdit()
        self.description_input.setMaximumHeight(100)
        self.description_input.setPlaceholderText("Describe the non-conformance")
        form_layout.addRow("Description:*", self.description_input)
        
        # Root Cause
        self.root_cause_input = QTextEdit()
        self.root_cause_input.setMaximumHeight(80)
        self.root_cause_input.setPlaceholderText("Root cause analysis")
        form_layout.addRow("Root Cause:", self.root_cause_input)
        
        # Corrective Action
        self.corrective_action_input = QTextEdit()
        self.corrective_action_input.setMaximumHeight(80)
        self.corrective_action_input.setPlaceholderText("Proposed corrective action")
        form_layout.addRow("Corrective Action:", self.corrective_action_input)
        
        # Record Item (specific item causing NC)
        self.record_item_combo = QComboBox()
        self.record_item_combo.addItem("-- No Specific Item --", None)
        self.record_combo.currentIndexChanged.connect(self.on_record_changed)
        form_layout.addRow("Related Item:", self.record_item_combo)
        
        # Cost Impact
        self.cost_impact_input = QDoubleSpinBox()
        self.cost_impact_input.setPrefix("$ ")
        self.cost_impact_input.setMinimum(0)
        self.cost_impact_input.setMaximum(999999999)
        self.cost_impact_input.setDecimals(2)
        self.cost_impact_input.setToolTip("Estimated cost impact of the non-conformance")
        form_layout.addRow("Cost Impact:", self.cost_impact_input)
        
        # Customer Impact
        self.customer_impact_check = QCheckBox("Has Customer Impact")
        self.customer_impact_check.setToolTip("Check if this NC impacts customer")
        form_layout.addRow("", self.customer_impact_check)
        
        # Verified By
        self.verified_by_combo = QComboBox()
        self.verified_by_combo.addItem("-- Not Verified --", None)
        form_layout.addRow("Verified By:", self.verified_by_combo)
        
        # Load users into both combo boxes
        self.load_users()
        
        layout.addWidget(scroll)
        
        # Image attachment buttons (if NC exists)
        if self.nc:
            image_toolbar = QHBoxLayout()
            btn_attach_image = QPushButton("📷 Attach Image")
            btn_attach_image.clicked.connect(self.attach_image_to_nc)
            btn_view_images = QPushButton("🖼️ View Images")
            btn_view_images.clicked.connect(self.view_attached_images)
            
            image_toolbar.addWidget(btn_attach_image)
            image_toolbar.addWidget(btn_view_images)
            image_toolbar.addStretch()
            layout.addLayout(image_toolbar)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.save_nc)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def load_records(self):
        """Load records into combo box"""
        records = self.session.query(Record).order_by(Record.created_at.desc()).limit(100).all()
        self.record_combo.addItem("-- No Related Record --", None)
        for record in records:
            self.record_combo.addItem(f"{record.record_number} - {record.title or 'Untitled'}", record.id)
    
    def load_users(self):
        """Load users into combo box"""
        users = self.session.query(User).filter_by(is_active=True).all()
        self.assigned_combo.addItem("-- Not Assigned --", None)
        for user in users:
            self.assigned_combo.addItem(user.full_name, user.id)
            # Also populate verified_by combo
            self.verified_by_combo.addItem(user.full_name, user.id)
    
    def on_record_changed(self):
        """Load record items when record is selected"""
        self.record_item_combo.clear()
        self.record_item_combo.addItem("-- No Specific Item --", None)
        
        record_id = self.record_combo.currentData()
        if record_id:
            items = self.session.query(RecordItem).filter_by(record_id=record_id).all()
            for item in items:
                criteria_text = f"{item.criteria.code} - {item.criteria.title}" if item.criteria else f"Item {item.id}"
                self.record_item_combo.addItem(criteria_text, item.id)
    
    def load_nc_data(self):
        """Load existing NC data"""
        if not self.nc:
            return
        
        self.title_input.setText(self.nc.title)
        self.severity_combo.setCurrentText(self.nc.severity)
        self.status_combo.setCurrentText(self.nc.status)
        
        if self.nc.record_id:
            index = self.record_combo.findData(self.nc.record_id)
            if index >= 0:
                self.record_combo.setCurrentIndex(index)
        
        if self.nc.assigned_to_id:
            index = self.assigned_combo.findData(self.nc.assigned_to_id)
            if index >= 0:
                self.assigned_combo.setCurrentIndex(index)
        
        if self.nc.detected_date:
            self.detected_date.setDate(self.nc.detected_date)
        
        if self.nc.description:
            self.description_input.setText(self.nc.description)
        
        if self.nc.root_cause:
            self.root_cause_input.setText(self.nc.root_cause)
        
        if self.nc.corrective_action:
            self.corrective_action_input.setText(self.nc.corrective_action)
        
        # Load record item if exists
        if self.nc.record_item_id:
            # Trigger loading of record items first
            self.on_record_changed()
            index = self.record_item_combo.findData(self.nc.record_item_id)
            if index >= 0:
                self.record_item_combo.setCurrentIndex(index)
        
        # Load cost impact
        if self.nc.cost_impact:
            self.cost_impact_input.setValue(float(self.nc.cost_impact))
        
        # Load customer impact
        if self.nc.customer_impact is not None:
            self.customer_impact_check.setChecked(self.nc.customer_impact)
        
        # Load verified by
        if self.nc.verified_by_id:
            index = self.verified_by_combo.findData(self.nc.verified_by_id)
            if index >= 0:
                self.verified_by_combo.setCurrentIndex(index)
    
    def save_nc(self):
        """Save the non-conformance"""
        # Validation
        if not self.title_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Please enter a title")
            return
        
        if not self.description_input.toPlainText().strip():
            QMessageBox.warning(self, "Validation Error", "Please enter a description")
            return
        
        try:
            if self.nc:
                # Update existing NC
                nc = self.nc
            else:
                # Create new NC
                nc = NonConformance()
                # Generate NC number
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                count = self.session.query(NonConformance).count() + 1
                nc.nc_number = f"NC-{timestamp}-{count:04d}"
                nc.detected_by_id = self.current_user.id
            
            # Update fields
            nc.title = self.title_input.text().strip()
            nc.severity = self.severity_combo.currentText()
            nc.status = self.status_combo.currentText()
            nc.record_id = self.record_combo.currentData()
            nc.assigned_to_id = self.assigned_combo.currentData()
            nc.detected_date = self.detected_date.date().toPyDate()
            nc.description = self.description_input.toPlainText()
            nc.root_cause = self.root_cause_input.toPlainText()
            nc.corrective_action = self.corrective_action_input.toPlainText()
            
            # Save new fields
            nc.record_item_id = self.record_item_combo.currentData()
            nc.cost_impact = self.cost_impact_input.value() if self.cost_impact_input.value() > 0 else None
            nc.customer_impact = self.customer_impact_check.isChecked()
            nc.verified_by_id = self.verified_by_combo.currentData()
            
            if not self.nc:
                self.session.add(nc)
            
            self.session.commit()
            
            # Audit logging
            action = 'update' if self.nc else 'insert'
            try:
                log_entry = AuditLog(
                    table_name='non_conformances',
                    record_id=nc.id,
                    action=action,
                    user_id=self.current_user.id,
                    username=self.current_user.full_name,
                    new_values={'nc_number': nc.nc_number, 'title': nc.title, 'status': nc.status, 'severity': nc.severity},
                    timestamp=datetime.now()
                )
                self.session.add(log_entry)
                self.session.commit()
            except:
                pass
            
            self.accept()
            
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to save non-conformance:\n{str(e)}")
    
    def attach_image_to_nc(self):
        """Open image upload dialog for this NC"""
        dialog = ImageUploadDialog(self.session, self.current_user, self, self.nc.id, 'non_conformance')
        dialog.exec()
    
    def view_attached_images(self):
        """View images attached to this NC"""
        # Query images for this NC
        images = self.session.query(ImageAttachment).filter(
            ImageAttachment.entity_type == 'non_conformance',
            ImageAttachment.entity_id == self.nc.id
        ).all()
        
        if not images:
            QMessageBox.information(self, "No Images", "No images attached to this NC.")
            return
        
        # Show list of images
        msg = f"Attached Images ({len(images)}):\n\n"
        for idx, img in enumerate(images, 1):
            msg += f"{idx}. {img.description or img.filename}\n"
        
        QMessageBox.information(self, "Attached Images", msg)


class UserDialog(QDialog):
    """Dialog for creating/editing users (Admin only)"""
    
    def __init__(self, session, current_user, user=None, parent=None):
        super().__init__(parent)
        self.session = session
        self.current_user = current_user
        self.user = user
        
        self.setWindowTitle("Edit User" if user else "New User")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        self.setup_ui()
        
        if user:
            self.load_user_data()
    
    def setup_ui(self):
        """Setup dialog UI"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        form_layout = QFormLayout()
        
        # Username
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter username")
        if self.user:
            self.username_input.setReadOnly(True)
        form_layout.addRow("Username:*", self.username_input)
        
        # Full Name
        self.fullname_input = QLineEdit()
        self.fullname_input.setPlaceholderText("Enter full name")
        form_layout.addRow("Full Name:*", self.fullname_input)
        
        # Email
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Enter email address")
        form_layout.addRow("Email:*", self.email_input)
        
        # Password fields
        if not self.user:
            # New user - password required
            self.password_input = QLineEdit()
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.password_input.setPlaceholderText("Enter password")
            form_layout.addRow("Password:*", self.password_input)
            
            self.confirm_password_input = QLineEdit()
            self.confirm_password_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.confirm_password_input.setPlaceholderText("Confirm password")
            form_layout.addRow("Confirm Password:*", self.confirm_password_input)
        else:
            # Existing user - optional password change
            self.change_password_check = QCheckBox("Change Password")
            self.change_password_check.stateChanged.connect(self.on_change_password_toggled)
            form_layout.addRow("", self.change_password_check)
            
            self.password_group = QWidget()
            password_layout = QFormLayout()
            self.password_group.setLayout(password_layout)
            
            self.password_input = QLineEdit()
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.password_input.setPlaceholderText("Enter new password")
            password_layout.addRow("New Password:", self.password_input)
            
            self.confirm_password_input = QLineEdit()
            self.confirm_password_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.confirm_password_input.setPlaceholderText("Confirm new password")
            password_layout.addRow("Confirm Password:", self.confirm_password_input)
            
            self.password_group.setVisible(False)
            form_layout.addRow("", self.password_group)
        
        # Role
        self.role_combo = QComboBox()
        self.load_roles()
        form_layout.addRow("Role:*", self.role_combo)
        
        # Department
        self.department_input = QLineEdit()
        self.department_input.setPlaceholderText("Enter department")
        form_layout.addRow("Department:", self.department_input)
        
        # Phone
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("Enter phone number")
        form_layout.addRow("Phone:", self.phone_input)
        
        # Is Active
        self.is_active_check = QCheckBox("Active")
        self.is_active_check.setChecked(True)
        form_layout.addRow("", self.is_active_check)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.save_user)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def load_roles(self):
        """Load roles into combo box"""
        roles = self.session.query(Role).all()
        for role in roles:
            self.role_combo.addItem(role.name, role.id)
    
    def on_change_password_toggled(self, state):
        """Toggle password fields visibility"""
        if hasattr(self, 'password_group'):
            self.password_group.setVisible(state == Qt.CheckState.Checked.value)
            if state != Qt.CheckState.Checked.value:
                # Clear password fields when unchecked
                self.password_input.clear()
                self.confirm_password_input.clear()
    
    def load_user_data(self):
        """Load existing user data"""
        if not self.user:
            return
        
        self.username_input.setText(self.user.username)
        self.fullname_input.setText(self.user.full_name)
        self.email_input.setText(self.user.email)
        
        if self.user.role_id:
            index = self.role_combo.findData(self.user.role_id)
            if index >= 0:
                self.role_combo.setCurrentIndex(index)
        
        if self.user.department:
            self.department_input.setText(self.user.department)
        
        if self.user.phone:
            self.phone_input.setText(self.user.phone)
        
        self.is_active_check.setChecked(self.user.is_active)
    
    def save_user(self):
        """Save the user"""
        # Validation
        if not self.username_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Please enter a username")
            return
        
        if not self.fullname_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Please enter a full name")
            return
        
        if not self.email_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Please enter an email address")
            return
        
        # Password validation
        if not self.user:
            # New user - password required
            if not self.password_input.text():
                QMessageBox.warning(self, "Validation Error", "Please enter a password")
                return
            
            if self.password_input.text() != self.confirm_password_input.text():
                QMessageBox.warning(self, "Validation Error", "Passwords do not match")
                return
            
            if len(self.password_input.text()) < 6:
                QMessageBox.warning(self, "Validation Error", "Password must be at least 6 characters")
                return
        else:
            # Existing user - validate only if changing password
            if hasattr(self, 'change_password_check') and self.change_password_check.isChecked():
                if not self.password_input.text():
                    QMessageBox.warning(self, "Validation Error", "Please enter a new password")
                    return
                
                if self.password_input.text() != self.confirm_password_input.text():
                    QMessageBox.warning(self, "Validation Error", "Passwords do not match")
                    return
                
                if len(self.password_input.text()) < 6:
                    QMessageBox.warning(self, "Validation Error", "Password must be at least 6 characters")
                    return
        
        try:
            import hashlib
            
            if self.user:
                # Update existing user
                user = self.user
            else:
                # Create new user
                # Check if username already exists
                existing = self.session.query(User).filter_by(
                    username=self.username_input.text().strip()
                ).first()
                if existing:
                    QMessageBox.warning(self, "Validation Error", 
                                       "A user with this username already exists")
                    return
                
                # Check if email already exists
                existing_email = self.session.query(User).filter_by(
                    email=self.email_input.text().strip()
                ).first()
                if existing_email:
                    QMessageBox.warning(self, "Validation Error", 
                                       "A user with this email already exists")
                    return
                
                user = User()
                user.username = self.username_input.text().strip()
                user.password_hash = hashlib.sha256(
                    self.password_input.text().encode()
                ).hexdigest()
                user.created_by_id = self.current_user.id
            
            # Update fields
            user.full_name = self.fullname_input.text().strip()
            user.email = self.email_input.text().strip()
            user.role_id = self.role_combo.currentData()
            user.department = self.department_input.text().strip() or None
            user.phone = self.phone_input.text().strip() or None
            user.is_active = self.is_active_check.isChecked()
            
            # Update password for existing user if requested
            if self.user and hasattr(self, 'change_password_check') and self.change_password_check.isChecked():
                user.password_hash = hashlib.sha256(
                    self.password_input.text().encode()
                ).hexdigest()
            user.is_active = self.is_active_check.isChecked()
            
            if not self.user:
                self.session.add(user)
            
            self.session.commit()
            
            # Audit logging
            action = 'update' if self.user else 'insert'
            try:
                log_entry = AuditLog(
                    table_name='users',
                    record_id=user.id,
                    action=action,
                    user_id=self.current_user.id,
                    username=self.current_user.full_name,
                    new_values={'username': user.username, 'full_name': user.full_name, 'email': user.email, 'is_active': user.is_active},
                    timestamp=datetime.now()
                )
                self.session.add(log_entry)
                self.session.commit()
            except:
                pass
            
            self.accept()
            
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to save user:\n{str(e)}")


class ProfileDialog(QDialog):
    """Dialog for users to manage their profile"""
    
    def __init__(self, session, user, parent=None):
        super().__init__(parent)
        self.session = session
        self.user = user
        
        self.setWindowTitle("My Profile")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        self.setup_ui()
        self.load_user_data()
    
    def setup_ui(self):
        """Setup dialog UI"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Create tabs
        tabs = QTabWidget()
        
        # Tab 1: Profile Info
        info_widget = QWidget()
        info_layout = QFormLayout()
        info_widget.setLayout(info_layout)
        
        # Username (readonly)
        self.username_label = QLabel()
        info_layout.addRow("Username:", self.username_label)
        
        # Full Name
        self.fullname_input = QLineEdit()
        info_layout.addRow("Full Name:*", self.fullname_input)
        
        # Email
        self.email_input = QLineEdit()
        info_layout.addRow("Email:*", self.email_input)
        
        # Department (readonly)
        self.department_label = QLabel()
        info_layout.addRow("Department:", self.department_label)
        
        # Phone
        self.phone_input = QLineEdit()
        info_layout.addRow("Phone:", self.phone_input)
        
        # Role (readonly)
        self.role_label = QLabel()
        info_layout.addRow("Role:", self.role_label)
        
        tabs.addTab(info_widget, "Profile Info")
        
        # Tab 2: Change Password
        password_widget = QWidget()
        password_layout = QFormLayout()
        password_widget.setLayout(password_layout)
        
        self.current_password_input = QLineEdit()
        self.current_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        password_layout.addRow("Current Password:*", self.current_password_input)
        
        self.new_password_input = QLineEdit()
        self.new_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        password_layout.addRow("New Password:*", self.new_password_input)
        
        self.confirm_new_password_input = QLineEdit()
        self.confirm_new_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        password_layout.addRow("Confirm New Password:*", self.confirm_new_password_input)
        
        btn_change_password = QPushButton("Change Password")
        btn_change_password.clicked.connect(self.change_password)
        password_layout.addRow("", btn_change_password)
        
        tabs.addTab(password_widget, "Change Password")
        
        layout.addWidget(tabs)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.save_profile)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def load_user_data(self):
        """Load user data"""
        self.username_label.setText(self.user.username)
        self.fullname_input.setText(self.user.full_name)
        self.email_input.setText(self.user.email)
        self.department_label.setText(self.user.department or "N/A")
        self.phone_input.setText(self.user.phone or "")
        self.role_label.setText(self.user.role.name if self.user.role else "N/A")
    
    def save_profile(self):
        """Save profile changes"""
        # Validation
        if not self.fullname_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Please enter a full name")
            return
        
        if not self.email_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Please enter an email address")
            return
        
        try:
            # Check if email is already used by another user
            existing_email = self.session.query(User).filter(
                User.email == self.email_input.text().strip(),
                User.id != self.user.id
            ).first()
            if existing_email:
                QMessageBox.warning(self, "Validation Error", 
                                   "This email is already used by another user")
                return
            
            # Update fields
            self.user.full_name = self.fullname_input.text().strip()
            self.user.email = self.email_input.text().strip()
            self.user.phone = self.phone_input.text().strip() or None
            
            self.session.commit()
            QMessageBox.information(self, "Success", "Profile updated successfully")
            self.accept()
            
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to update profile:\n{str(e)}")
    
    def change_password(self):
        """Change user password"""
        import hashlib
        
        # Validation
        if not self.current_password_input.text():
            QMessageBox.warning(self, "Validation Error", "Please enter your current password")
            return
        
        if not self.new_password_input.text():
            QMessageBox.warning(self, "Validation Error", "Please enter a new password")
            return
        
        if len(self.new_password_input.text()) < 6:
            QMessageBox.warning(self, "Validation Error", "Password must be at least 6 characters")
            return
        
        if self.new_password_input.text() != self.confirm_new_password_input.text():
            QMessageBox.warning(self, "Validation Error", "New passwords do not match")
            return
        
        # Verify current password
        current_hash = hashlib.sha256(self.current_password_input.text().encode()).hexdigest()
        if current_hash != self.user.password_hash:
            QMessageBox.warning(self, "Validation Error", "Current password is incorrect")
            return
        
        try:
            # Update password
            self.user.password_hash = hashlib.sha256(
                self.new_password_input.text().encode()
            ).hexdigest()
            
            self.session.commit()
            
            # Clear password fields
            self.current_password_input.clear()
            self.new_password_input.clear()
            self.confirm_new_password_input.clear()
            
            QMessageBox.information(self, "Success", "Password changed successfully")
            
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to change password:\n{str(e)}")


class CompanySettingsDialog(QDialog):
    """Dialog for managing company settings"""
    
    def __init__(self, session, current_user, parent=None):
        super().__init__(parent)
        self.session = session
        self.current_user = current_user
        self.logo_data = None
        self.logo_filename = None
        
        self.setWindowTitle("Company Settings")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        
        self.setup_ui()
        self.load_settings()
    
    def setup_ui(self):
        """Setup dialog UI"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Create scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll.setWidget(scroll_widget)
        
        form_layout = QFormLayout()
        scroll_widget.setLayout(form_layout)
        
        # Logo Section
        logo_label = QLabel("<b>Company Logo</b>")
        logo_label.setStyleSheet("font-size: 12pt; color: #2f3542; margin-top: 10px;")
        form_layout.addRow(logo_label)
        
        logo_layout = QHBoxLayout()
        self.logo_preview = QLabel()
        self.logo_preview.setFixedSize(150, 150)
        self.logo_preview.setStyleSheet("border: 2px solid #ccc; background-color: #f0f0f0;")
        self.logo_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo_preview.setText("No Logo")
        logo_layout.addWidget(self.logo_preview)
        
        logo_buttons_layout = QVBoxLayout()
        btn_upload_logo = QPushButton("Upload Logo")
        btn_upload_logo.clicked.connect(self.upload_logo)
        btn_remove_logo = QPushButton("Remove Logo")
        btn_remove_logo.clicked.connect(self.remove_logo)
        logo_buttons_layout.addWidget(btn_upload_logo)
        logo_buttons_layout.addWidget(btn_remove_logo)
        logo_buttons_layout.addStretch()
        logo_layout.addLayout(logo_buttons_layout)
        logo_layout.addStretch()
        
        form_layout.addRow("", logo_layout)
        
        # Company Information
        company_label = QLabel("<b>Company Information</b>")
        company_label.setStyleSheet("font-size: 12pt; color: #2f3542; margin-top: 15px;")
        form_layout.addRow(company_label)
        
        self.company_name_input = QLineEdit()
        self.company_name_input.setPlaceholderText("Enter company name")
        form_layout.addRow("Company Name:*", self.company_name_input)
        
        self.registration_number_input = QLineEdit()
        self.registration_number_input.setPlaceholderText("Enter registration number")
        form_layout.addRow("Registration Number:", self.registration_number_input)
        
        self.tax_id_input = QLineEdit()
        self.tax_id_input.setPlaceholderText("Enter tax ID")
        form_layout.addRow("Tax ID:", self.tax_id_input)
        
        # Contact Information
        contact_label = QLabel("<b>Contact Information</b>")
        contact_label.setStyleSheet("font-size: 12pt; color: #2f3542; margin-top: 15px;")
        form_layout.addRow(contact_label)
        
        self.address_input = QTextEdit()
        self.address_input.setMaximumHeight(80)
        self.address_input.setPlaceholderText("Enter street address")
        form_layout.addRow("Address:", self.address_input)
        
        self.city_input = QLineEdit()
        self.city_input.setPlaceholderText("Enter city")
        form_layout.addRow("City:", self.city_input)
        
        self.state_input = QLineEdit()
        self.state_input.setPlaceholderText("Enter state/province")
        form_layout.addRow("State/Province:", self.state_input)
        
        self.postal_code_input = QLineEdit()
        self.postal_code_input.setPlaceholderText("Enter postal code")
        form_layout.addRow("Postal Code:", self.postal_code_input)
        
        self.country_input = QLineEdit()
        self.country_input.setPlaceholderText("Enter country")
        form_layout.addRow("Country:", self.country_input)
        
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("Enter phone number")
        form_layout.addRow("Phone:", self.phone_input)
        
        self.fax_input = QLineEdit()
        self.fax_input.setPlaceholderText("Enter fax number")
        form_layout.addRow("Fax:", self.fax_input)
        
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Enter email address")
        form_layout.addRow("Email:", self.email_input)
        
        self.website_input = QLineEdit()
        self.website_input.setPlaceholderText("Enter website URL")
        form_layout.addRow("Website:", self.website_input)
        
        # Additional Information
        additional_label = QLabel("<b>Additional Information</b>")
        additional_label.setStyleSheet("font-size: 12pt; color: #2f3542; margin-top: 15px;")
        form_layout.addRow(additional_label)
        
        self.certification_input = QTextEdit()
        self.certification_input.setMaximumHeight(80)
        self.certification_input.setPlaceholderText("Enter certification information")
        form_layout.addRow("Certifications:", self.certification_input)
        
        layout.addWidget(scroll)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.save_settings)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def upload_logo(self):
        """Upload company logo"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Company Logo", "",
            "Image Files (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        
        if file_path:
            try:
                # Read image file
                with open(file_path, 'rb') as f:
                    self.logo_data = f.read()
                self.logo_filename = Path(file_path).name
                
                # Display preview
                from PyQt6.QtGui import QPixmap
                pixmap = QPixmap(file_path)
                scaled_pixmap = pixmap.scaled(
                    150, 150,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.logo_preview.setPixmap(scaled_pixmap)
                self.logo_preview.setText("")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load logo:\n{str(e)}")
    
    def remove_logo(self):
        """Remove company logo"""
        self.logo_data = None
        self.logo_filename = None
        self.logo_preview.clear()
        self.logo_preview.setText("No Logo")
    
    def load_settings(self):
        """Load existing company settings"""
        settings = self.session.query(CompanySettings).first()
        
        if settings:
            self.company_name_input.setText(settings.company_name or "")
            self.registration_number_input.setText(settings.registration_number or "")
            self.tax_id_input.setText(settings.tax_id or "")
            
            self.address_input.setText(settings.address or "")
            self.city_input.setText(settings.city or "")
            self.state_input.setText(settings.state or "")
            self.postal_code_input.setText(settings.postal_code or "")
            self.country_input.setText(settings.country or "")
            
            self.phone_input.setText(settings.phone or "")
            self.fax_input.setText(settings.fax or "")
            self.email_input.setText(settings.email or "")
            self.website_input.setText(settings.website or "")
            
            self.certification_input.setText(settings.certification_info or "")
            
            # Load logo
            if settings.company_logo:
                try:
                    from PyQt6.QtGui import QPixmap
                    pixmap = QPixmap()
                    pixmap.loadFromData(settings.company_logo)
                    scaled_pixmap = pixmap.scaled(
                        150, 150,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    self.logo_preview.setPixmap(scaled_pixmap)
                    self.logo_preview.setText("")
                    self.logo_data = settings.company_logo
                    self.logo_filename = settings.logo_filename
                except Exception as e:
                    print(f"Error loading logo: {e}")
    
    def save_settings(self):
        """Save company settings"""
        # Validation
        if not self.company_name_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Please enter company name")
            return
        
        try:
            # Get or create settings
            settings = self.session.query(CompanySettings).first()
            
            if not settings:
                settings = CompanySettings()
                self.session.add(settings)
            
            # Update fields
            settings.company_name = self.company_name_input.text().strip()
            settings.registration_number = self.registration_number_input.text().strip() or None
            settings.tax_id = self.tax_id_input.text().strip() or None
            
            settings.address = self.address_input.toPlainText().strip() or None
            settings.city = self.city_input.text().strip() or None
            settings.state = self.state_input.text().strip() or None
            settings.postal_code = self.postal_code_input.text().strip() or None
            settings.country = self.country_input.text().strip() or None
            
            settings.phone = self.phone_input.text().strip() or None
            settings.fax = self.fax_input.text().strip() or None
            settings.email = self.email_input.text().strip() or None
            settings.website = self.website_input.text().strip() or None
            
            settings.certification_info = self.certification_input.toPlainText().strip() or None
            
            # Update logo if changed
            if self.logo_data:
                settings.company_logo = self.logo_data
                settings.logo_filename = self.logo_filename
            elif self.logo_data is None and not self.logo_preview.pixmap():
                settings.company_logo = None
                settings.logo_filename = None
            
            settings.updated_by_id = self.current_user.id
            
            self.session.commit()
            QMessageBox.information(self, "Success", "Company settings saved successfully")
            self.accept()
            
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to save settings:\n{str(e)}")


class QuickAddReadingDialog(QDialog):
    """Dialog for quickly adding multiple readings to a record at once"""
    
    def __init__(self, session, record, parent=None):
        super().__init__(parent)
        self.session = session
        self.record = record
        self.inputs = {}  # Store input widgets by field_id
        
        self.setWindowTitle(f"Quick Add Readings: {record.record_number}")
        self.setMinimumWidth(750)
        self.setMinimumHeight(500)
        
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Info header
        header = QLabel(f"<b>Record:</b> {self.record.record_number} | <b>Title:</b> {self.record.title or 'Untitled'}")
        header.setStyleSheet("padding: 10px; background-color: #f1f2f6; border-radius: 4px;")
        layout.addWidget(header)
        
        instruction = QLabel("Enter values for one or more criteria below. Empty fields will be ignored.")
        instruction.setStyleSheet("color: #57606f; font-style: italic; margin-bottom: 5px;")
        layout.addWidget(instruction)
        
        # Readings Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Criteria", "Limits", "Reading Value", "Status"])
        
        # Horizontal header styling
        header_view = self.table.horizontalHeader()
        header_view.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header_view.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(2, 160)
        header_view.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(3, 100)
        
        self.load_fields()
        layout.addWidget(self.table)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.save)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def load_fields(self):
        """Load fields into the table from the template"""
        if not self.record.template:
            return
            
        fields = self.session.query(TemplateField).filter_by(
            template_id=self.record.template_id
        ).order_by(TemplateField.sort_order).all()
        
        self.table.setRowCount(len(fields))
        
        for row, field in enumerate(fields):
            criteria = field.criteria
            if not criteria: continue
            
            # 1. Criteria Name
            name = f"{criteria.code} - {criteria.title}" if criteria.code else criteria.title
            name_item = QTableWidgetItem(name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 0, name_item)
            
            # 2. Limits
            limits = []
            if criteria.limit_min is not None: limits.append(f"Min: {criteria.limit_min}")
            if criteria.limit_max is not None: limits.append(f"Max: {criteria.limit_max}")
            if criteria.tolerance is not None: limits.append(f"±{criteria.tolerance}")
            limit_text = " | ".join(limits) if limits else "No Limits"
            limit_item = QTableWidgetItem(limit_text)
            limit_item.setFlags(limit_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            limit_item.setForeground(Qt.GlobalColor.darkGray)
            self.table.setItem(row, 1, limit_item)
            
            # 3. Value Input
            input_widget = QLineEdit()
            input_widget.setPlaceholderText("Enter value...")
            input_widget.setFrame(False)
            
            # Connect validator to status label
            status_label = QLabel("Pending")
            status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # Use closure to capture variables for lambda
            input_widget.textChanged.connect(
                lambda text, c=criteria, lbl=status_label: self.update_status(text, c, lbl)
            )
            
            self.table.setCellWidget(row, 2, input_widget)
            self.inputs[field.id] = input_widget
            
            # 4. Status
            self.table.setCellWidget(row, 3, status_label)
            
    def update_status(self, text, criteria, label):
        """Update individual status label based on input value"""
        text = text.strip()
        if not text:
            label.setText("Pending")
            label.setStyleSheet("")
            return
            
        try:
            val = float(text)
            is_pass = True
            if criteria.data_type == 'numeric':
                if criteria.limit_min is not None:
                    min_val = float(criteria.limit_min)
                    if criteria.tolerance is not None: min_val -= float(criteria.tolerance)
                    if val < min_val: is_pass = False
                if is_pass and criteria.limit_max is not None:
                    max_val = float(criteria.limit_max)
                    if criteria.tolerance is not None: max_val += float(criteria.tolerance)
                    if val > max_val: is_pass = False
            
            if is_pass:
                label.setText("PASS")
                label.setStyleSheet("color: green; font-weight: bold;")
            else:
                label.setText("FAIL")
                label.setStyleSheet("color: red; font-weight: bold;")
        except ValueError:
            label.setText("Error")
            label.setStyleSheet("color: orange;")

    def save(self):
        """Save all rows that have a value entered"""
        added_count = 0
        try:
            for field_id, input_widget in self.inputs.items():
                val_text = input_widget.text().strip()
                if not val_text:
                    continue
                
                val = float(val_text)
                field = self.session.get(TemplateField, field_id)
                criteria = field.criteria
                
                # Compliance calculation
                is_pass = True
                if criteria and criteria.data_type == 'numeric':
                    if criteria.limit_min is not None:
                        min_val = float(criteria.limit_min)
                        if criteria.tolerance is not None: min_val -= float(criteria.tolerance)
                        if val < min_val: is_pass = False
                    if is_pass and criteria.limit_max is not None:
                        max_val = float(criteria.limit_max)
                        if criteria.tolerance is not None: max_val += float(criteria.tolerance)
                        if val > max_val: is_pass = False
                
                # Create RecordItem
                item = RecordItem(
                    record_id=self.record.id,
                    criteria_id=field.criteria_id,
                    template_field_id=field.id,
                    numeric_value=val,
                    compliance=is_pass,
                    measured_at=datetime.now()
                )
                self.session.add(item)
                added_count += 1
            
            if added_count > 0:
                self.session.commit()
                self.accept()
            else:
                QMessageBox.warning(self, "No Data", "Please enter at least one reading value.")
                
        except ValueError:
            QMessageBox.warning(self, "Invalid Data", "Please ensure all entered values are valid numbers.")
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to save readings:\n{str(e)}")


class LoginDialog(QDialog):
    """Login dialog for user authentication"""
    
    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.authenticated_user = None
        
        self.setWindowTitle("Quality Management System - Login")
        self.setMinimumWidth(400)
        self.setFixedHeight(250)
        
        # Remove close button (user must login or quit)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint)
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup login UI"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Title
        title = QLabel("Quality Management System")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        subtitle = QLabel("Please login to continue")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)
        
        layout.addSpacing(20)
        
        # Login form
        form_layout = QFormLayout()
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter username")
        form_layout.addRow("Username:", self.username_input)
        
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Enter password")
        self.password_input.returnPressed.connect(self.login)
        form_layout.addRow("Password:", self.password_input)
        
        layout.addLayout(form_layout)
        
        layout.addSpacing(20)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        btn_login = QPushButton("Login")
        btn_login.setDefault(True)
        btn_login.clicked.connect(self.login)
        
        btn_quit = QPushButton("Quit")
        btn_quit.clicked.connect(self.reject_and_quit)
        
        button_layout.addWidget(btn_login)
        button_layout.addWidget(btn_quit)
        
        layout.addLayout(button_layout)
        
        # Set focus to username
        self.username_input.setFocus()
    
    def login(self):
        """Attempt to login"""
        import hashlib
        
        username = self.username_input.text().strip()
        password = self.password_input.text()
        
        if not username or not password:
            QMessageBox.warning(self, "Login Failed", "Please enter both username and password")
            return
        
        try:
            # Hash password
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            # Find user
            user = self.session.query(User).filter_by(
                username=username,
                password_hash=password_hash
            ).first()
            
            if user:
                if not user.is_active:
                    QMessageBox.warning(self, "Login Failed", 
                                       "Your account has been deactivated. Please contact an administrator.")
                    return
                
                # Update last login
                user.last_login = datetime.now()
                self.session.commit()
                
                self.authenticated_user = user
                self.accept()
            else:
                QMessageBox.warning(self, "Login Failed", 
                                   "Invalid username or password")
                self.password_input.clear()
                self.password_input.setFocus()
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Login error:\n{str(e)}")
    
    def reject_and_quit(self):
        """Quit the application"""
        self.reject()


class AuditLogDialog(QDialog):
    """Dialog for viewing audit logs"""
    
    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        
        self.setWindowTitle("Audit Log")
        self.setMinimumWidth(1000)
        self.setMinimumHeight(600)
        
        self.setup_ui()
        self.load_logs()
    
    def setup_ui(self):
        """Setup dialog UI"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Filters
        filter_group = QGroupBox("Filters")
        filter_layout = QHBoxLayout()
        
        filter_layout.addWidget(QLabel("Entity:"))
        self.entity_filter = QComboBox()
        self.entity_filter.addItem("All", None)
        self.entity_filter.addItem("Records", "records")
        self.entity_filter.addItem("Templates", "templates")
        self.entity_filter.addItem("Standards", "standards")
        self.entity_filter.addItem("Criteria", "criteria")
        self.entity_filter.addItem("Non-Conformances", "non_conformances")
        self.entity_filter.addItem("Users", "users")
        self.entity_filter.addItem("Documents", "documents")
        filter_layout.addWidget(self.entity_filter)
        
        filter_layout.addWidget(QLabel("Action:"))
        self.action_filter = QComboBox()
        self.action_filter.addItem("All", None)
        self.action_filter.addItems(['insert', 'update', 'delete'])
        filter_layout.addWidget(self.action_filter)
        
        filter_layout.addWidget(QLabel("User:"))
        self.user_filter = QComboBox()
        self.user_filter.addItem("All", None)
        self.load_users()
        filter_layout.addWidget(self.user_filter)
        
        btn_filter = QPushButton("Apply Filter")
        btn_filter.clicked.connect(self.load_logs)
        filter_layout.addWidget(btn_filter)
        
        filter_layout.addStretch()
        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)
        
        # Logs table
        self.logs_table = QTableWidget()
        self.logs_table.setColumnCount(7)
        self.logs_table.setHorizontalHeaderLabels([
            'ID', 'Entity', 'Entity ID', 'Action', 'User', 'Timestamp', 'Changes'
        ])
        self.logs_table.setColumnHidden(0, True)
        self.logs_table.horizontalHeader().setStretchLastSection(True)
        self.logs_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.logs_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.logs_table)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def load_users(self):
        """Load users for filter"""
        users = self.session.query(User).all()
        for user in users:
            self.user_filter.addItem(user.full_name, user.id)
    
    def load_logs(self):
        """Load audit logs"""
        query = self.session.query(AuditLog).order_by(AuditLog.timestamp.desc())
        
        # Apply filters
        entity_type = self.entity_filter.currentData()
        if entity_type:
            query = query.filter(AuditLog.table_name == entity_type)
        
        action = self.action_filter.currentText()
        if action != "All":
            query = query.filter(AuditLog.action == action)
        
        user_id = self.user_filter.currentData()
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        
        logs = query.limit(500).all()
        
        self.logs_table.setRowCount(len(logs))
        for row_idx, log in enumerate(logs):
            self.logs_table.setItem(row_idx, 0, QTableWidgetItem(str(log.id)))
            self.logs_table.setItem(row_idx, 1, QTableWidgetItem(log.table_name or ''))
            self.logs_table.setItem(row_idx, 2, QTableWidgetItem(str(log.record_id) if log.record_id else ''))
            self.logs_table.setItem(row_idx, 3, QTableWidgetItem(log.action or ''))
            self.logs_table.setItem(row_idx, 4, QTableWidgetItem(log.user.full_name if log.user else log.username or ''))
            self.logs_table.setItem(row_idx, 5, QTableWidgetItem(log.timestamp.strftime('%Y-%m-%d %H:%M:%S') if log.timestamp else ''))
            
            # Format changes as JSON string
            changes_text = ''
            if log.changed_fields:
                try:
                    changes_dict = log.changed_fields if isinstance(log.changed_fields, dict) else json.loads(log.changed_fields)
                    changes_text = ', '.join([f"{k}: {v}" for k, v in changes_dict.items()])
                except:
                    changes_text = str(log.changed_fields)
            self.logs_table.setItem(row_idx, 6, QTableWidgetItem(changes_text[:100] + '...' if len(changes_text) > 100 else changes_text))


class NotificationDialog(QDialog):
    """Dialog for viewing notifications"""
    
    def __init__(self, session, current_user, parent=None):
        super().__init__(parent)
        self.session = session
        self.current_user = current_user
        
        self.setWindowTitle("Notifications")
        self.setMinimumWidth(800)
        self.setMinimumHeight(500)
        
        self.setup_ui()
        self.load_notifications()
    
    def setup_ui(self):
        """Setup dialog UI"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Toolbar
        toolbar = QHBoxLayout()
        
        self.unread_check = QCheckBox("Show Unread Only")
        self.unread_check.stateChanged.connect(self.load_notifications)
        toolbar.addWidget(self.unread_check)
        
        btn_mark_read = QPushButton("Mark as Read")
        btn_mark_read.clicked.connect(self.mark_as_read)
        toolbar.addWidget(btn_mark_read)
        
        btn_mark_all_read = QPushButton("Mark All as Read")
        btn_mark_all_read.clicked.connect(self.mark_all_as_read)
        toolbar.addWidget(btn_mark_all_read)
        
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # Notifications table
        self.notifications_table = QTableWidget()
        self.notifications_table.setColumnCount(6)
        self.notifications_table.setHorizontalHeaderLabels([
            'ID', 'Type', 'Title', 'Message', 'Created', 'Read'
        ])
        self.notifications_table.setColumnHidden(0, True)
        self.notifications_table.horizontalHeader().setStretchLastSection(True)
        self.notifications_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.notifications_table)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def load_notifications(self):
        """Load notifications for current user"""
        query = self.session.query(Notification).filter_by(
            user_id=self.current_user.id
        ).order_by(Notification.created_at.desc())
        
        if self.unread_check.isChecked():
            query = query.filter_by(is_read=False)
        
        notifications = query.limit(100).all()
        
        self.notifications_table.setRowCount(len(notifications))
        for row_idx, notif in enumerate(notifications):
            self.notifications_table.setItem(row_idx, 0, QTableWidgetItem(str(notif.id)))
            self.notifications_table.setItem(row_idx, 1, QTableWidgetItem(notif.type or ''))
            self.notifications_table.setItem(row_idx, 2, QTableWidgetItem(notif.title or ''))
            self.notifications_table.setItem(row_idx, 3, QTableWidgetItem(notif.message or ''))
            self.notifications_table.setItem(row_idx, 4, QTableWidgetItem(notif.created_at.strftime('%Y-%m-%d %H:%M') if notif.created_at else ''))
            self.notifications_table.setItem(row_idx, 5, QTableWidgetItem('Yes' if notif.is_read else 'No'))
            
            # Highlight unread
            if not notif.is_read:
                for col in range(self.notifications_table.columnCount()):
                    item = self.notifications_table.item(row_idx, col)
                    if item:
                        font = item.font()
                        font.setBold(True)
                        item.setFont(font)
    
    def mark_as_read(self):
        """Mark selected notifications as read"""
        if self.notifications_table.currentRow() < 0:
            QMessageBox.warning(self, "No Selection", "Please select a notification")
            return
        
        notif_id = int(self.notifications_table.item(self.notifications_table.currentRow(), 0).text())
        notif = self.session.get(Notification, notif_id)
        if notif:
            notif.is_read = True
            notif.read_at = datetime.now()
            self.session.commit()
            self.load_notifications()
    
    def mark_all_as_read(self):
        """Mark all notifications as read"""
        self.session.query(Notification).filter_by(
            user_id=self.current_user.id,
            is_read=False
        ).update({
            'is_read': True,
            'read_at': datetime.now()
        })
        self.session.commit()
        self.load_notifications()


class DocumentDialog(QDialog):
    """Dialog for managing documents"""
    
    def __init__(self, session, current_user, parent=None):
        super().__init__(parent)
        self.session = session
        self.current_user = current_user
        
        self.setWindowTitle("Document Management")
        self.setMinimumWidth(900)
        self.setMinimumHeight(600)
        
        self.setup_ui()
        self.load_documents()
    
    def log_action(self, action, table_name, record_id, old_values=None, new_values=None):
        """Log an action to audit trail"""
        try:
            # Calculate changed fields
            changed_fields = {}
            if old_values and new_values:
                for key in new_values:
                    if key in old_values and old_values[key] != new_values[key]:
                        changed_fields[key] = {'old': old_values[key], 'new': new_values[key]}
            
            log_entry = AuditLog(
                table_name=table_name,
                record_id=record_id,
                action=action,
                user_id=self.current_user.id if self.current_user else None,
                username=self.current_user.full_name if self.current_user else 'System',
                old_values=old_values,
                new_values=new_values,
                changed_fields=changed_fields,
                timestamp=datetime.now()
            )
            self.session.add(log_entry)
            self.session.commit()
        except Exception as e:
            print(f"Failed to log action: {e}")
    
    def create_notification(self, user_id, title, message, notif_type='info', priority='normal', related_record_id=None, related_nc_id=None):
        """Create a notification for a user"""
        try:
            notification = Notification(
                user_id=user_id,
                title=title,
                message=message,
                type=notif_type,
                priority=priority,
                related_record_id=related_record_id,
                related_nc_id=related_nc_id,
                is_read=False,
                created_at=datetime.now()
            )
            self.session.add(notification)
            self.session.commit()
        except Exception as e:
            print(f"Failed to create notification: {e}")
    
    def setup_ui(self):
        """Setup dialog UI"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Toolbar
        toolbar = QHBoxLayout()
        
        btn_upload = QPushButton("Upload Document")
        btn_upload.clicked.connect(self.upload_document)
        toolbar.addWidget(btn_upload)
        
        btn_view = QPushButton("View/Open")
        btn_view.clicked.connect(self.view_document)
        toolbar.addWidget(btn_view)
        
        btn_download = QPushButton("Download")
        btn_download.clicked.connect(self.download_document)
        toolbar.addWidget(btn_download)
        
        btn_print = QPushButton("Print")
        btn_print.clicked.connect(self.print_document)
        toolbar.addWidget(btn_print)
        
        btn_edit = QPushButton("Edit Info")
        btn_edit.clicked.connect(self.edit_document)
        toolbar.addWidget(btn_edit)
        
        btn_delete = QPushButton("Delete")
        btn_delete.clicked.connect(self.delete_document)
        toolbar.addWidget(btn_delete)
        
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # Documents table
        self.documents_table = QTableWidget()
        self.documents_table.setColumnCount(9)
        self.documents_table.setHorizontalHeaderLabels([
            'ID', 'Document #', 'Title', 'Category', 'Version', 'Status', 'Created By', 'Created At', 'Size'
        ])
        self.documents_table.setColumnHidden(0, True)
        self.documents_table.horizontalHeader().setStretchLastSection(True)
        self.documents_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.documents_table.doubleClicked.connect(self.view_document)
        layout.addWidget(self.documents_table)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def load_documents(self):
        """Load documents"""
        documents = self.session.query(Document).order_by(Document.created_at.desc()).all()
        
        self.documents_table.setRowCount(len(documents))
        for row_idx, doc in enumerate(documents):
            # Format file size
            size_str = ''
            if doc.file_size:
                if doc.file_size < 1024:
                    size_str = f"{doc.file_size} B"
                elif doc.file_size < 1024 * 1024:
                    size_str = f"{doc.file_size / 1024:.1f} KB"
                else:
                    size_str = f"{doc.file_size / (1024 * 1024):.1f} MB"
            
            self.documents_table.setItem(row_idx, 0, QTableWidgetItem(str(doc.id)))
            self.documents_table.setItem(row_idx, 1, QTableWidgetItem(doc.document_number or ''))
            self.documents_table.setItem(row_idx, 2, QTableWidgetItem(doc.title or ''))
            self.documents_table.setItem(row_idx, 3, QTableWidgetItem(doc.category or ''))
            self.documents_table.setItem(row_idx, 4, QTableWidgetItem(doc.version or ''))
            self.documents_table.setItem(row_idx, 5, QTableWidgetItem(doc.status or ''))
            self.documents_table.setItem(row_idx, 6, QTableWidgetItem(doc.created_by.full_name if doc.created_by else ''))
            self.documents_table.setItem(row_idx, 7, QTableWidgetItem(doc.created_at.strftime('%Y-%m-%d %H:%M') if doc.created_at else ''))
            self.documents_table.setItem(row_idx, 8, QTableWidgetItem(size_str))
    
    def upload_document(self):
        """Upload a new document"""
        dialog = DocumentUploadDialog(self.session, self.current_user, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_documents()
    
    def view_document(self):
        """View/Open selected document"""
        if self.documents_table.currentRow() < 0:
            QMessageBox.warning(self, "No Selection", "Please select a document")
            return
        
        doc_id = int(self.documents_table.item(self.documents_table.currentRow(), 0).text())
        doc = self.session.get(Document, doc_id)
        
        if doc and doc.file_path:
            try:
                import os
                import subprocess
                import platform
                
                if os.path.exists(doc.file_path):
                    # Open file with default application
                    if platform.system() == 'Windows':
                        os.startfile(doc.file_path)
                    elif platform.system() == 'Darwin':  # macOS
                        subprocess.call(['open', doc.file_path])
                    else:  # Linux
                        subprocess.call(['xdg-open', doc.file_path])
                else:
                    QMessageBox.warning(self, "File Not Found", "The document file no longer exists")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to open document:\n{str(e)}")
    
    def print_document(self):
        """Print selected document"""
        if self.documents_table.currentRow() < 0:
            QMessageBox.warning(self, "No Selection", "Please select a document")
            return
        
        doc_id = int(self.documents_table.item(self.documents_table.currentRow(), 0).text())
        doc = self.session.get(Document, doc_id)
        
        if doc and doc.file_path:
            try:
                import os
                import subprocess
                import platform
                
                if os.path.exists(doc.file_path):
                    # Open print dialog based on OS
                    if platform.system() == 'Windows':
                        os.startfile(doc.file_path, 'print')
                    elif platform.system() == 'Darwin':  # macOS
                        subprocess.call(['lpr', doc.file_path])
                    else:  # Linux
                        subprocess.call(['lp', doc.file_path])
                    
                    QMessageBox.information(self, "Print", "Document sent to printer")
                else:
                    QMessageBox.warning(self, "File Not Found", "The document file no longer exists")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to print document:\n{str(e)}")
    
    def edit_document(self):
        """Edit document metadata"""
        if self.documents_table.currentRow() < 0:
            QMessageBox.warning(self, "No Selection", "Please select a document")
            return
        
        doc_id = int(self.documents_table.item(self.documents_table.currentRow(), 0).text())
        doc = self.session.get(Document, doc_id)
        
        if doc:
            dialog = DocumentUploadDialog(self.session, self.current_user, self, doc)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.load_documents()
    
    def download_document(self):
        """Download selected document"""
        if self.documents_table.currentRow() < 0:
            QMessageBox.warning(self, "No Selection", "Please select a document")
            return
        
        doc_id = int(self.documents_table.item(self.documents_table.currentRow(), 0).text())
        doc = self.session.get(Document, doc_id)
        
        if doc:
            save_path, _ = QFileDialog.getSaveFileName(
                self, "Save Document", doc.file_name, "All Files (*)"
            )
            
            if save_path:
                try:
                    import shutil
                    shutil.copy2(doc.file_path, save_path)
                    QMessageBox.information(self, "Success", "Document downloaded successfully")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to download:\n{str(e)}")
    
    def delete_document(self):
        """Delete selected document"""
        if self.documents_table.currentRow() < 0:
            QMessageBox.warning(self, "No Selection", "Please select a document")
            return
        
        reply = QMessageBox.question(
            self, "Confirm Delete",
            "Are you sure you want to delete this document?\nThe file will also be removed from disk.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            doc_id = int(self.documents_table.item(self.documents_table.currentRow(), 0).text())
            doc = self.session.get(Document, doc_id)
            
            if doc:
                try:
                    import os
                    # Audit logging before delete
                    try:
                        log_entry = AuditLog(
                            table_name='documents',
                            record_id=doc.id,
                            action='delete',
                            user_id=self.current_user.id,
                            username=self.current_user.full_name,
                            old_values={'document_number': doc.document_number, 'title': doc.title, 'version': doc.version},
                            timestamp=datetime.now()
                        )
                        self.session.add(log_entry)
                    except:
                        pass
                    
                    # Remove file from disk
                    if doc.file_path and os.path.exists(doc.file_path):
                        os.remove(doc.file_path)
                    
                    self.session.delete(doc)
                    self.session.commit()
                    self.load_documents()
                    QMessageBox.information(self, "Success", "Document deleted")
                except Exception as e:
                    self.session.rollback()
                    QMessageBox.critical(self, "Error", f"Failed to delete:\n{str(e)}")


class DocumentUploadDialog(QDialog):
    """Dialog for uploading/editing documents"""
    
    def __init__(self, session, current_user, parent=None, document=None):
        super().__init__(parent)
        self.session = session
        self.current_user = current_user
        self.document = document
        self.selected_file_path = None
        
        self.setWindowTitle("Edit Document" if document else "Upload Document")
        self.setMinimumWidth(500)
        
        self.setup_ui()
        if document:
            self.load_document_data()
    
    def setup_ui(self):
        """Setup dialog UI"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        form_layout = QFormLayout()
        
        # File selection (only for new documents)
        if not self.document:
            file_layout = QHBoxLayout()
            self.file_label = QLabel("No file selected")
            btn_browse = QPushButton("Browse...")
            btn_browse.clicked.connect(self.browse_file)
            file_layout.addWidget(self.file_label, 1)
            file_layout.addWidget(btn_browse)
            form_layout.addRow("File *:", file_layout)
        
        # Document number
        self.doc_number_edit = QLineEdit()
        if not self.document:
            # Auto-generate document number
            count = self.session.query(Document).count()
            self.doc_number_edit.setText(f"DOC-{count + 1:05d}")
        form_layout.addRow("Document # *:", self.doc_number_edit)
        
        # Title
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Enter document title")
        form_layout.addRow("Title *:", self.title_edit)
        
        # Category
        self.category_combo = QComboBox()
        self.category_combo.addItems([
            "Policy", "Procedure", "Work Instruction", "Form", 
            "Record", "Specification", "Drawing", "Manual", "Other"
        ])
        self.category_combo.setEditable(True)
        form_layout.addRow("Category:", self.category_combo)
        
        # Description
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(80)
        self.description_edit.setPlaceholderText("Enter document description")
        form_layout.addRow("Description:", self.description_edit)
        
        # Version
        self.version_edit = QLineEdit()
        self.version_edit.setText("1.0")
        form_layout.addRow("Version:", self.version_edit)
        
        # Status
        self.status_combo = QComboBox()
        self.status_combo.addItems(["draft", "under_review", "approved", "obsolete"])
        form_layout.addRow("Status:", self.status_combo)
        
        layout.addLayout(form_layout)
        
        # Info label
        info_label = QLabel("* Required fields")
        info_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(info_label)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.save_document)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def browse_file(self):
        """Browse for file to upload"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Document", "",
            "All Files (*);;PDF (*.pdf);;Word (*.doc *.docx);;Excel (*.xls *.xlsx)"
        )
        
        if file_path:
            import os
            self.selected_file_path = file_path
            filename = os.path.basename(file_path)
            self.file_label.setText(filename)
            
            # Auto-fill title if empty
            if not self.title_edit.text():
                name_without_ext = os.path.splitext(filename)[0]
                self.title_edit.setText(name_without_ext)
    
    def load_document_data(self):
        """Load existing document data"""
        self.doc_number_edit.setText(self.document.document_number or '')
        self.title_edit.setText(self.document.title or '')
        
        if self.document.category:
            idx = self.category_combo.findText(self.document.category)
            if idx >= 0:
                self.category_combo.setCurrentIndex(idx)
            else:
                self.category_combo.setCurrentText(self.document.category)
        
        self.description_edit.setPlainText(self.document.description or '')
        self.version_edit.setText(self.document.version or '')
        
        if self.document.status:
            idx = self.status_combo.findText(self.document.status)
            if idx >= 0:
                self.status_combo.setCurrentIndex(idx)
    
    def save_document(self):
        """Save document"""
        # Validation
        if not self.doc_number_edit.text().strip():
            QMessageBox.warning(self, "Validation Error", "Document number is required")
            self.doc_number_edit.setFocus()
            return
        
        if not self.title_edit.text().strip():
            QMessageBox.warning(self, "Validation Error", "Title is required")
            self.title_edit.setFocus()
            return
        
        if not self.document and not self.selected_file_path:
            QMessageBox.warning(self, "Validation Error", "Please select a file")
            return
        
        try:
            if self.document:
                # Update existing document
                doc = self.document
            else:
                # Create new document
                doc = Document()
                doc.created_by_id = self.current_user.id
                
                # Save file
                import os
                import shutil
                from pathlib import Path
                
                # Create documents directory
                docs_dir = Path.home() / '.quality_system' / 'documents'
                docs_dir.mkdir(parents=True, exist_ok=True)
                
                # Copy file with unique name
                filename = os.path.basename(self.selected_file_path)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                unique_filename = f"{timestamp}_{filename}"
                dest_path = docs_dir / unique_filename
                
                shutil.copy2(self.selected_file_path, dest_path)
                
                doc.file_name = filename
                doc.file_path = str(dest_path)
                doc.file_size = os.path.getsize(dest_path)
                doc.file_type = os.path.splitext(filename)[1][1:]  # Extension without dot
            
            # Update fields
            doc.document_number = self.doc_number_edit.text().strip()
            doc.title = self.title_edit.text().strip()
            doc.category = self.category_combo.currentText()
            doc.description = self.description_edit.toPlainText().strip() or None
            doc.version = self.version_edit.text().strip()
            doc.status = self.status_combo.currentText()
            doc.updated_at = datetime.now()
            
            if not self.document:
                self.session.add(doc)
            
            self.session.commit()
            
            # Audit logging
            audit_action = 'update' if self.document else 'insert'
            try:
                log_entry = AuditLog(
                    table_name='documents',
                    record_id=doc.id,
                    action=audit_action,
                    user_id=self.current_user.id,
                    username=self.current_user.full_name,
                    new_values={'document_number': doc.document_number, 'title': doc.title, 'version': doc.version, 'status': doc.status},
                    timestamp=datetime.now()
                )
                self.session.add(log_entry)
                self.session.commit()
            except:
                pass
            
            action = "updated" if self.document else "uploaded"
            QMessageBox.information(self, "Success", f"Document {action} successfully")
            self.accept()
            
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to save document:\n{str(e)}")
            import traceback
            traceback.print_exc()


class ImageUploadDialog(QDialog):
    """Dialog for uploading images with entity linking"""
    
    def __init__(self, session, current_user, parent=None, entity_id=None, entity_type=None):
        super().__init__(parent)
        self.session = session
        self.current_user = current_user
        self.selected_file_path = None
        self.preset_entity_id = entity_id
        self.preset_entity_type = entity_type
        
        self.setWindowTitle("Upload Image")
        self.setMinimumWidth(500)
        
        self.setup_ui()
        
        # Pre-select entity if provided
        if entity_type and entity_id:
            self.entity_type_combo.setCurrentText(entity_type)
            # Find and select the entity in the combo
            for i in range(self.entity_id_combo.count()):
                if self.entity_id_combo.itemData(i) == entity_id:
                    self.entity_id_combo.setCurrentIndex(i)
                    break
    
    def setup_ui(self):
        """Setup dialog UI"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        form_layout = QFormLayout()
        
        # File selection
        file_layout = QHBoxLayout()
        self.file_label = QLabel("No file selected")
        btn_browse = QPushButton("Browse...")
        btn_browse.clicked.connect(self.browse_file)
        
        btn_camera = QPushButton("Take Photo")
        btn_camera.clicked.connect(self.take_photo)
        btn_camera.setStyleSheet("background-color: #576574; color: white;")
        
        file_layout.addWidget(self.file_label, 1)
        file_layout.addWidget(btn_browse)
        file_layout.addWidget(btn_camera)
        form_layout.addRow("Image Source *:", file_layout)
        
        # Entity Type
        self.entity_type_combo = QComboBox()
        self.entity_type_combo.addItems(["standalone", "record", "non_conformance", "document", "standard"])
        self.entity_type_combo.currentTextChanged.connect(self.on_entity_type_changed)
        form_layout.addRow("Attach To *:", self.entity_type_combo)
        
        # Entity ID (shown only when not standalone)
        self.entity_id_label = QLabel("Entity ID *:")
        self.entity_id_combo = QComboBox()
        self.entity_id_combo.setEditable(False)
        form_layout.addRow(self.entity_id_label, self.entity_id_combo)
        
        # Description
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(80)
        self.description_edit.setPlaceholderText("Enter image description (optional)")
        form_layout.addRow("Description:", self.description_edit)
        
        layout.addLayout(form_layout)
        
        # Info label
        info_label = QLabel("* Required fields")
        info_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(info_label)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.save_image)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # Initial state
        self.on_entity_type_changed("standalone")
    
    def browse_file(self):
        """Browse for image file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Image", "",
            "Images (*.png *.jpg *.jpeg *.gif *.bmp);;All Files (*)"
        )
        
        if file_path:
            import os
            self.selected_file_path = file_path
            filename = os.path.basename(file_path)
            self.file_label.setText(filename)

    def take_photo(self):
        """Take a photo using the device camera"""
        try:
            # Try OpenCV first (more stable on Linux)
            try:
                from camera_opencv import OpenCVCameraDialog
                dialog = OpenCVCameraDialog(self)
            except (ImportError, Exception):
                # Fall back to Qt Multimedia
                from camera_dialog import CameraCaptureDialog
                dialog = CameraCaptureDialog(self)
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                if dialog.captured_file:
                    import os
                    self.selected_file_path = dialog.captured_file
                    filename = os.path.basename(self.selected_file_path)
                    self.file_label.setText(f"Captured: {filename}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open camera:\n{str(e)}")
    
    def on_entity_type_changed(self, entity_type):
        """Handle entity type change"""
        self.entity_id_combo.clear()
        
        if entity_type == "standalone":
            # Hide entity ID selection for standalone images
            self.entity_id_label.setVisible(False)
            self.entity_id_combo.setVisible(False)
        else:
            # Show entity ID selection
            self.entity_id_label.setVisible(True)
            self.entity_id_combo.setVisible(True)
            
            # Populate entity combo based on type
            if entity_type == "record":
                records = self.session.query(Record).order_by(Record.record_number.desc()).limit(100).all()
                for record in records:
                    template_name = record.template.name if record.template else "No Template"
                    display = f"{record.record_number} - {template_name}"
                    self.entity_id_combo.addItem(display, record.id)
            
            elif entity_type == "non_conformance":
                ncs = self.session.query(NonConformance).order_by(NonConformance.nc_number.desc()).limit(100).all()
                for nc in ncs:
                    display = f"{nc.nc_number} - {nc.title or 'No Title'}"
                    self.entity_id_combo.addItem(display, nc.id)
            
            elif entity_type == "document":
                docs = self.session.query(Document).order_by(Document.created_at.desc()).limit(100).all()
                for doc in docs:
                    display = f"{doc.document_number or 'N/A'} - {doc.title or 'No Title'}"
                    self.entity_id_combo.addItem(display, doc.id)
            
            elif entity_type == "standard":
                stds = self.session.query(Standard).order_by(Standard.code.asc()).all()
                for std in stds:
                    display = f"{std.code} - {std.name}"
                    self.entity_id_combo.addItem(display, std.id)
    
    def save_image(self):
        """Save image attachment"""
        import os
        import shutil
        from pathlib import Path
        from PIL import Image as PILImage
        
        # Validation
        if not self.selected_file_path:
            QMessageBox.warning(self, "Validation Error", "Please select an image file")
            return
        
        if not os.path.exists(self.selected_file_path):
            QMessageBox.critical(self, "Error", f"Source file does not exist:\n{self.selected_file_path}")
            return
            
        entity_type = self.entity_type_combo.currentText()
        
        if entity_type != "standalone" and self.entity_id_combo.currentIndex() < 0:
            QMessageBox.warning(self, "Validation Error", f"Please select a {entity_type}")
            return
        
        try:
            # Create images directory
            images_dir = Path.home() / '.quality_system' / 'images'
            try:
                images_dir.mkdir(parents=True, exist_ok=True)
            except Exception as de:
                raise Exception(f"Failed to create directory {images_dir}: {str(de)}")
            
            # Copy file with unique name
            source_file = self.selected_file_path
            filename = os.path.basename(source_file)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Sanitize filename
            clean_filename = "".join([c for c in filename if c.isalnum() or c in ('.','_','-')]).strip()
            if not clean_filename: clean_filename = "captured_image.jpg"
            
            unique_filename = f"{timestamp}_{clean_filename}"
            dest_path = images_dir / unique_filename
            
            try:
                shutil.copy2(source_file, dest_path)
            except Exception as ce:
                raise Exception(f"Failed to copy file from {source_file} to {dest_path}: {str(ce)}")
            
            # Get image dimensions and MIME type
            file_size = os.path.getsize(dest_path)
            mime_type = None
            width = None
            height = None
            
            try:
                with PILImage.open(dest_path) as pil_img:
                    width, height = pil_img.size
                    fmt = pil_img.format.lower() if pil_img.format else 'jpeg'
                    mime_type = f"image/{fmt}"
            except Exception as pe:
                print(f"Pillow could not read image metadata: {pe}")
                # Fallback to defaults
                mime_type = "image/jpeg"
            
            # Create image attachment record
            img = ImageAttachment()
            img.entity_type = entity_type
            
            if entity_type == "standalone":
                img.entity_id = 0
            else:
                img.entity_id = self.entity_id_combo.currentData()
            
            img.filename = clean_filename
            img.file_path = str(dest_path)
            img.file_size = file_size
            img.mime_type = mime_type
            img.width = width
            img.height = height
            img.description = self.description_edit.toPlainText().strip() or None
            img.uploaded_by_id = self.current_user.id
            img.uploaded_at = datetime.now()
            
            self.session.add(img)
            self.session.commit()
            
            QMessageBox.information(self, "Success", "Image uploaded successfully")
            self.accept()
            
        except Exception as e:
            self.session.rollback()
            import traceback
            error_details = traceback.format_exc()
            print(error_details)
            QMessageBox.critical(self, "Upload Error", f"Failed to upload image:\n{str(e)}\n\nDetails have been printed to terminal.")


class ImageAttachmentDialog(QDialog):
    """Dialog for managing image attachments"""
    
    def __init__(self, session, current_user, parent=None):
        super().__init__(parent)
        self.session = session
        self.current_user = current_user
        
        self.setWindowTitle("Image Attachments")
        self.setMinimumWidth(1000)
        self.setMinimumHeight(700)
        
        self.setup_ui()
        self.load_images()
    
    def setup_ui(self):
        """Setup dialog UI"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Toolbar
        toolbar = QHBoxLayout()
        
        btn_upload = QPushButton("Upload Image")
        btn_upload.clicked.connect(self.upload_image)
        toolbar.addWidget(btn_upload)
        
        btn_view = QPushButton("View Full Size")
        btn_view.clicked.connect(self.view_image)
        toolbar.addWidget(btn_view)
        
        btn_delete = QPushButton("Delete")
        btn_delete.clicked.connect(self.delete_image)
        toolbar.addWidget(btn_delete)
        
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # Images table
        self.images_table = QTableWidget()
        self.images_table.setColumnCount(8)
        self.images_table.setHorizontalHeaderLabels([
            'ID', 'Description', 'Entity Type', 'Entity ID', 'File Name', 'Size', 'Uploaded By', 'Uploaded At'
        ])
        self.images_table.setColumnHidden(0, True)
        self.images_table.horizontalHeader().setStretchLastSection(True)
        self.images_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.images_table.doubleClicked.connect(self.view_image)
        layout.addWidget(self.images_table)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def load_images(self):
        """Load image attachments"""
        images = self.session.query(ImageAttachment).order_by(ImageAttachment.uploaded_at.desc()).all()
        
        self.images_table.setRowCount(len(images))
        for row_idx, img in enumerate(images):
            # Format file size
            size_str = ''
            if img.file_size:
                if img.file_size < 1024:
                    size_str = f"{img.file_size} B"
                elif img.file_size < 1024 * 1024:
                    size_str = f"{img.file_size / 1024:.1f} KB"
                else:
                    size_str = f"{img.file_size / (1024 * 1024):.1f} MB"
            
            self.images_table.setItem(row_idx, 0, QTableWidgetItem(str(img.id)))
            self.images_table.setItem(row_idx, 1, QTableWidgetItem(img.description or ''))
            self.images_table.setItem(row_idx, 2, QTableWidgetItem(img.entity_type or ''))
            self.images_table.setItem(row_idx, 3, QTableWidgetItem(str(img.entity_id) if img.entity_id else ''))
            self.images_table.setItem(row_idx, 4, QTableWidgetItem(img.filename or ''))
            self.images_table.setItem(row_idx, 5, QTableWidgetItem(size_str))
            self.images_table.setItem(row_idx, 6, QTableWidgetItem(img.uploaded_by.full_name if img.uploaded_by else ''))
            self.images_table.setItem(row_idx, 7, QTableWidgetItem(img.uploaded_at.strftime('%Y-%m-%d %H:%M') if img.uploaded_at else ''))
    
    def upload_image(self):
        """Upload a new image"""
        dialog = ImageUploadDialog(self.session, self.current_user, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_images()
    
    def view_image(self):
        """View selected image in full size"""
        if self.images_table.currentRow() < 0:
            QMessageBox.warning(self, "No Selection", "Please select an image")
            return
        
        img_id = int(self.images_table.item(self.images_table.currentRow(), 0).text())
        img = self.session.get(ImageAttachment, img_id)
        
        if img and img.file_path:
            try:
                import os
                if os.path.exists(img.file_path):
                    from pathlib import Path
                    import webbrowser
                    webbrowser.open(Path(img.file_path).as_uri())
                else:
                    QMessageBox.warning(self, "File Not Found", "The image file no longer exists")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to open image:\n{str(e)}")
    
    def delete_image(self):
        """Delete selected image"""
        if self.images_table.currentRow() < 0:
            QMessageBox.warning(self, "No Selection", "Please select an image")
            return
        
        reply = QMessageBox.question(
            self, "Confirm Delete",
            "Are you sure you want to delete this image?\nThe file will also be removed from disk.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            img_id = int(self.images_table.item(self.images_table.currentRow(), 0).text())
            img = self.session.get(ImageAttachment, img_id)
            
            if img:
                try:
                    import os
                    # Remove file from disk
                    if img.file_path and os.path.exists(img.file_path):
                        os.remove(img.file_path)
                    
                    self.session.delete(img)
                    self.session.commit()
                    self.load_images()
                    QMessageBox.information(self, "Success", "Image deleted")
                except Exception as e:
                    self.session.rollback()
                    QMessageBox.critical(self, "Error", f"Failed to delete:\n{str(e)}")


class WorkflowFormDialog(QDialog):
    """Dialog for creating/editing workflow details"""
    
    def __init__(self, session, workflow=None, parent=None):
        super().__init__(parent)
        self.session = session
        self.workflow = workflow
        
        self.setWindowTitle("New Workflow" if workflow is None else "Edit Workflow")
        self.setMinimumWidth(500)
        
        self.setup_ui()
        if workflow:
            self.load_workflow_data()
    
    def setup_ui(self):
        """Setup form UI"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        form_layout = QFormLayout()
        
        # Name (required)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Enter workflow name")
        form_layout.addRow("Name *:", self.name_edit)
        
        # Code (required, unique)
        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText("Enter unique code (e.g., WF001)")
        form_layout.addRow("Code *:", self.code_edit)
        
        # Description
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(80)
        self.description_edit.setPlaceholderText("Enter workflow description")
        form_layout.addRow("Description:", self.description_edit)
        
        # Trigger Event
        self.trigger_combo = QComboBox()
        self.trigger_combo.addItem("", None)
        self.trigger_combo.addItems([
            "record_created",
            "record_completed",
            "record_approved",
            "nc_detected",
            "nc_closed",
            "manual"
        ])
        form_layout.addRow("Trigger Event:", self.trigger_combo)
        
        # Standard
        self.standard_combo = QComboBox()
        self.standard_combo.addItem("None", None)
        standards = self.session.query(Standard).order_by(Standard.name).all()
        for standard in standards:
            self.standard_combo.addItem(f"{standard.code} - {standard.name}", standard.id)
        form_layout.addRow("Associated Standard:", self.standard_combo)
        
        # Template
        self.template_combo = QComboBox()
        self.template_combo.addItem("None", None)
        templates = self.session.query(TestTemplate).order_by(TestTemplate.name).all()
        for template in templates:
            self.template_combo.addItem(template.name, template.id)
        form_layout.addRow("Associated Template:", self.template_combo)
        
        # Active
        self.active_check = QCheckBox()
        self.active_check.setChecked(True)
        form_layout.addRow("Active:", self.active_check)
        
        layout.addLayout(form_layout)
        
        # Info label
        info_label = QLabel("* Required fields")
        info_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(info_label)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.validate_and_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def load_workflow_data(self):
        """Load existing workflow data into form"""
        self.name_edit.setText(self.workflow.name or '')
        self.code_edit.setText(self.workflow.code or '')
        self.code_edit.setEnabled(False)  # Don't allow changing code for existing workflows
        self.description_edit.setPlainText(self.workflow.description or '')
        
        if self.workflow.trigger_event:
            idx = self.trigger_combo.findText(self.workflow.trigger_event)
            if idx >= 0:
                self.trigger_combo.setCurrentIndex(idx)
        
        if self.workflow.standard_id:
            idx = self.standard_combo.findData(self.workflow.standard_id)
            if idx >= 0:
                self.standard_combo.setCurrentIndex(idx)
        
        if self.workflow.template_id:
            idx = self.template_combo.findData(self.workflow.template_id)
            if idx >= 0:
                self.template_combo.setCurrentIndex(idx)
        
        self.active_check.setChecked(self.workflow.is_active)
    
    def validate_and_accept(self):
        """Validate form before accepting"""
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Validation Error", "Name is required")
            self.name_edit.setFocus()
            return
        
        if not self.code_edit.text().strip():
            QMessageBox.warning(self, "Validation Error", "Code is required")
            self.code_edit.setFocus()
            return
        
        # Check code uniqueness for new workflows
        if not self.workflow:
            existing = self.session.query(Workflow).filter_by(
                code=self.code_edit.text().strip()
            ).first()
            if existing:
                QMessageBox.warning(self, "Validation Error", 
                                  f"Code '{self.code_edit.text().strip()}' already exists. Please use a unique code.")
                self.code_edit.setFocus()
                return
        
        self.accept()


class WorkflowDialog(QDialog):
    """Dialog for managing workflows"""
    
    def __init__(self, session, current_user, parent=None):
        super().__init__(parent)
        self.session = session
        self.current_user = current_user
        
        self.setWindowTitle("Workflow Management")
        self.setMinimumWidth(900)
        self.setMinimumHeight(600)
        
        self.setup_ui()
        self.load_workflows()
    
    def setup_ui(self):
        """Setup dialog UI"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Toolbar
        toolbar = QHBoxLayout()
        
        btn_new = QPushButton("New Workflow")
        btn_new.clicked.connect(self.new_workflow)
        toolbar.addWidget(btn_new)
        
        btn_edit = QPushButton("Edit")
        btn_edit.clicked.connect(self.edit_workflow)
        toolbar.addWidget(btn_edit)
        
        btn_delete = QPushButton("Delete")
        btn_delete.clicked.connect(self.delete_workflow)
        toolbar.addWidget(btn_delete)
        
        btn_instances = QPushButton("View Instances")
        btn_instances.clicked.connect(self.view_instances)
        toolbar.addWidget(btn_instances)
        
        btn_define_steps = QPushButton("Define Steps")
        btn_define_steps.clicked.connect(self.define_workflow_steps)
        toolbar.addWidget(btn_define_steps)
        
        btn_export_pdf = QPushButton("Export to PDF")
        btn_export_pdf.clicked.connect(self.export_workflow_pdf)
        toolbar.addWidget(btn_export_pdf)
        
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # Workflows table
        self.workflows_table = QTableWidget()
        self.workflows_table.setColumnCount(6)
        self.workflows_table.setHorizontalHeaderLabels([
            'ID', 'Name', 'Description', 'Active Instances', 'Created By', 'Created At'
        ])
        self.workflows_table.setColumnHidden(0, True)
        self.workflows_table.horizontalHeader().setStretchLastSection(True)
        self.workflows_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.workflows_table)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def load_workflows(self):
        """Load workflows"""
        workflows = self.session.query(Workflow).order_by(Workflow.created_at.desc()).all()
        
        self.workflows_table.setRowCount(len(workflows))
        for row_idx, wf in enumerate(workflows):
            # Count active instances
            active_count = self.session.query(WorkflowInstance).filter_by(
                workflow_id=wf.id,
                status='active'
            ).count()
            
            self.workflows_table.setItem(row_idx, 0, QTableWidgetItem(str(wf.id)))
            self.workflows_table.setItem(row_idx, 1, QTableWidgetItem(wf.name or ''))
            self.workflows_table.setItem(row_idx, 2, QTableWidgetItem(wf.description or ''))
            self.workflows_table.setItem(row_idx, 3, QTableWidgetItem(str(active_count)))
            self.workflows_table.setItem(row_idx, 4, QTableWidgetItem(wf.created_by.full_name if wf.created_by else ''))
            self.workflows_table.setItem(row_idx, 5, QTableWidgetItem(wf.created_at.strftime('%Y-%m-%d') if wf.created_at else ''))
    
    def new_workflow(self):
        """Create new workflow"""
        dialog = WorkflowFormDialog(self.session, None, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                wf = Workflow()
                wf.name = dialog.name_edit.text().strip()
                wf.code = dialog.code_edit.text().strip()
                wf.description = dialog.description_edit.toPlainText().strip() or None
                wf.trigger_event = dialog.trigger_combo.currentText() if dialog.trigger_combo.currentText() else None
                wf.standard_id = dialog.standard_combo.currentData() if dialog.standard_combo.currentData() else None
                wf.template_id = dialog.template_combo.currentData() if dialog.template_combo.currentData() else None
                wf.is_active = dialog.active_check.isChecked()
                wf.created_by_id = self.current_user.id
                wf.created_at = datetime.now()
                wf.steps = None  # Initialize steps as None, can be defined later
                
                self.session.add(wf)
                self.session.commit()
                
                self.load_workflows()
                QMessageBox.information(self, "Success", "Workflow created successfully")
            except Exception as e:
                self.session.rollback()
                QMessageBox.critical(self, "Error", f"Failed to create workflow:\n{str(e)}")
    
    def edit_workflow(self):
        """Edit selected workflow"""
        if self.workflows_table.currentRow() < 0:
            QMessageBox.warning(self, "No Selection", "Please select a workflow")
            return
        
        wf_id = int(self.workflows_table.item(self.workflows_table.currentRow(), 0).text())
        wf = self.session.get(Workflow, wf_id)
        
        if wf:
            dialog = WorkflowFormDialog(self.session, wf, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                try:
                    wf.name = dialog.name_edit.text().strip()
                    wf.code = dialog.code_edit.text().strip()
                    wf.description = dialog.description_edit.toPlainText().strip() or None
                    wf.trigger_event = dialog.trigger_combo.currentText() if dialog.trigger_combo.currentText() else None
                    wf.standard_id = dialog.standard_combo.currentData() if dialog.standard_combo.currentData() else None
                    wf.template_id = dialog.template_combo.currentData() if dialog.template_combo.currentData() else None
                    wf.is_active = dialog.active_check.isChecked()
                    wf.updated_at = datetime.now()
                    
                    self.session.commit()
                    self.load_workflows()
                    QMessageBox.information(self, "Success", "Workflow updated")
                except Exception as e:
                    self.session.rollback()
                    QMessageBox.critical(self, "Error", f"Failed to update:\n{str(e)}")
    
    def delete_workflow(self):
        """Delete selected workflow"""
        if self.workflows_table.currentRow() < 0:
            QMessageBox.warning(self, "No Selection", "Please select a workflow")
            return
        
        reply = QMessageBox.question(
            self, "Confirm Delete",
            "Are you sure you want to delete this workflow?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            wf_id = int(self.workflows_table.item(self.workflows_table.currentRow(), 0).text())
            wf = self.session.get(Workflow, wf_id)
            
            if wf:
                try:
                    self.session.delete(wf)
                    self.session.commit()
                    self.load_workflows()
                    QMessageBox.information(self, "Success", "Workflow deleted")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to delete:\\n{str(e)}")
    
    def view_instances(self):
        """View workflow instances"""
        if self.workflows_table.currentRow() < 0:
            QMessageBox.warning(self, "No Selection", "Please select a workflow")
            return
        
        wf_id = int(self.workflows_table.item(self.workflows_table.currentRow(), 0).text())
        wf = self.session.get(Workflow, wf_id)
        
        if wf:
            dialog = WorkflowInstanceDialog(self.session, wf, self.current_user, parent=self)
            dialog.exec()
    
    def define_workflow_steps(self):
        """Define steps for selected workflow"""
        if self.workflows_table.currentRow() < 0:
            QMessageBox.warning(self, "No Selection", "Please select a workflow")
            return
        
        wf_id = int(self.workflows_table.item(self.workflows_table.currentRow(), 0).text())
        wf = self.session.get(Workflow, wf_id)
        
        if wf:
            dialog = WorkflowStepsDialog(self.session, wf, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                try:
                    wf.steps = dialog.get_steps_data()
                    wf.updated_at = datetime.now()
                    self.session.commit()
                    QMessageBox.information(self, "Success", "Workflow steps saved successfully")
                except Exception as e:
                    self.session.rollback()
                    QMessageBox.critical(self, "Error", f"Failed to save steps:\n{str(e)}")
    
    def export_workflow_pdf(self):
        """Export workflow with visual flow diagram to PDF"""
        if self.workflows_table.currentRow() < 0:
            QMessageBox.warning(self, "No Selection", "Please select a workflow")
            return
        
        try:
            wf_id = int(self.workflows_table.item(self.workflows_table.currentRow(), 0).text())
            wf = self.session.get(Workflow, wf_id)
            
            if not wf:
                return
            
            filepath, _ = QFileDialog.getSaveFileName(
                self, "Save Workflow PDF", f"{wf.code}_workflow.pdf", "PDF Files (*.pdf)"
            )
            
            if filepath:
                pdf_gen = PDFGenerator(self.session)
                pdf_gen.generate_workflow_pdf(wf, filepath)
                
                QMessageBox.information(self, "Success", 
                    f"Workflow PDF generated:\n{filepath}\n\nIncludes visual flow diagram and step details.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate PDF:\n{str(e)}")
            import traceback
            traceback.print_exc()


class WorkflowStepsDialog(QDialog):
    """Dialog for defining workflow steps"""
    
    def __init__(self, session, workflow, parent=None):
        super().__init__(parent)
        self.session = session
        self.workflow = workflow
        
        self.setWindowTitle(f"Define Steps - {workflow.name}")
        self.setMinimumWidth(700)
        self.setMinimumHeight(500)
        
        self.setup_ui()
        self.load_steps()
    
    def setup_ui(self):
        """Setup dialog UI"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Info label
        info = QLabel(f"<b>Workflow:</b> {self.workflow.name} ({self.workflow.code})<br/>"
                     "<i>Define the steps of this workflow. Each step can have approvers, actions, and conditions.</i>")
        layout.addWidget(info)
        layout.addWidget(QLabel(""))
        
        # Toolbar
        toolbar = QHBoxLayout()
        
        btn_add = QPushButton("Add Step")
        btn_add.clicked.connect(self.add_step)
        toolbar.addWidget(btn_add)
        
        btn_edit = QPushButton("Edit Step")
        btn_edit.clicked.connect(self.edit_step)
        toolbar.addWidget(btn_edit)
        
        btn_delete = QPushButton("Delete Step")
        btn_delete.clicked.connect(self.delete_step)
        toolbar.addWidget(btn_delete)
        
        btn_move_up = QPushButton("↑ Move Up")
        btn_move_up.clicked.connect(self.move_step_up)
        toolbar.addWidget(btn_move_up)
        
        btn_move_down = QPushButton("↓ Move Down")
        btn_move_down.clicked.connect(self.move_step_down)
        toolbar.addWidget(btn_move_down)
        
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # Steps table
        self.steps_table = QTableWidget()
        self.steps_table.setColumnCount(5)
        self.steps_table.setHorizontalHeaderLabels([
            'Order', 'Step Name', 'Action Type', 'Assigned Role', 'Description'
        ])
        self.steps_table.horizontalHeader().setStretchLastSection(True)
        self.steps_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.steps_table)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.button(QDialogButtonBox.StandardButton.Save).clicked.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def load_steps(self):
        """Load existing steps from workflow"""
        import json
        
        if self.workflow.steps:
            steps = json.loads(self.workflow.steps) if isinstance(self.workflow.steps, str) else self.workflow.steps
            if isinstance(steps, list):
                self.steps_table.setRowCount(len(steps))
                for row_idx, step in enumerate(steps):
                    self.steps_table.setItem(row_idx, 0, QTableWidgetItem(str(row_idx + 1)))
                    self.steps_table.setItem(row_idx, 1, QTableWidgetItem(step.get('name', '')))
                    self.steps_table.setItem(row_idx, 2, QTableWidgetItem(step.get('action_type', '')))
                    self.steps_table.setItem(row_idx, 3, QTableWidgetItem(step.get('assigned_role', '')))
                    
                    # Store complex data in UserRole for later retrieval during edits
                    desc_item = QTableWidgetItem(step.get('description', ''))
                    desc_item.setData(Qt.ItemDataRole.UserRole, step)
                    self.steps_table.setItem(row_idx, 4, desc_item)
    
    def add_step(self):
        """Add new step"""
        all_steps_data = self._get_current_table_data()
        dialog = WorkflowStepFormDialog(self.session, None, self, all_steps_data)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            row = self.steps_table.rowCount()
            self.steps_table.insertRow(row)
            self._update_row_from_dialog(row, dialog)
            self.renumber_steps()
    
    def edit_step(self):
        """Edit selected step"""
        if self.steps_table.currentRow() < 0:
            QMessageBox.warning(self, "No Selection", "Please select a step")
            return
        
        row = self.steps_table.currentRow()
        # Retrieve full step data from UserRole
        step_data = self.steps_table.item(row, 4).data(Qt.ItemDataRole.UserRole) or {}
        
        all_steps_data = self._get_current_table_data()
        dialog = WorkflowStepFormDialog(self.session, step_data, self, all_steps_data)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._update_row_from_dialog(row, dialog)

    def _get_current_table_data(self):
        """Helper to get step names for branching combo"""
        steps = []
        for r in range(self.steps_table.rowCount()):
            steps.append({'name': self.steps_table.item(r, 1).text() if self.steps_table.item(r, 1) else ""})
        return steps

    def _update_row_from_dialog(self, row, dialog):
        """Update table row and hidden data from dialog results"""
        self.steps_table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
        self.steps_table.setItem(row, 1, QTableWidgetItem(dialog.name_edit.text()))
        self.steps_table.setItem(row, 2, QTableWidgetItem(dialog.action_combo.currentText()))
        self.steps_table.setItem(row, 3, QTableWidgetItem(dialog.role_edit.text()))
        
        # Build full step dict
        step_dict = {
            'order': row + 1,
            'name': dialog.name_edit.text(),
            'action_type': dialog.action_combo.currentText(),
            'assigned_role': dialog.role_edit.text(),
            'description': dialog.description_edit.toPlainText(),
            'next_step_success': dialog.success_step.currentData(),
            'success_action': dialog.success_action.text(),
            'next_step_fail': dialog.fail_step.currentData(),
            'fail_action': dialog.fail_action.text()
        }
        
        desc_item = QTableWidgetItem(dialog.description_edit.toPlainText())
        desc_item.setData(Qt.ItemDataRole.UserRole, step_dict)
        self.steps_table.setItem(row, 4, desc_item)
    
    def delete_step(self):
        """Delete selected step"""
        if self.steps_table.currentRow() < 0:
            QMessageBox.warning(self, "No Selection", "Please select a step")
            return
        
        reply = QMessageBox.question(
            self, "Confirm Delete",
            "Are you sure you want to delete this step?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.steps_table.removeRow(self.steps_table.currentRow())
            self.renumber_steps()
    
    def move_step_up(self):
        """Move selected step up"""
        row = self.steps_table.currentRow()
        if row <= 0:
            return
        
        # Swap rows
        for col in range(1, self.steps_table.columnCount()):
            item1 = self.steps_table.takeItem(row, col)
            item2 = self.steps_table.takeItem(row - 1, col)
            self.steps_table.setItem(row, col, item2)
            self.steps_table.setItem(row - 1, col, item1)
        
        self.steps_table.setCurrentCell(row - 1, 0)
        self.renumber_steps()
    
    def move_step_down(self):
        """Move selected step down"""
        row = self.steps_table.currentRow()
        if row < 0 or row >= self.steps_table.rowCount() - 1:
            return
        
        # Swap rows
        for col in range(1, self.steps_table.columnCount()):
            item1 = self.steps_table.takeItem(row, col)
            item2 = self.steps_table.takeItem(row + 1, col)
            self.steps_table.setItem(row, col, item2)
            self.steps_table.setItem(row + 1, col, item1)
        
        self.steps_table.setCurrentCell(row + 1, 0)
        self.renumber_steps()
    
    def renumber_steps(self):
        """Renumber all steps"""
        for row in range(self.steps_table.rowCount()):
            self.steps_table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
    
    def get_steps_data(self):
        """Get steps data as JSON"""
        import json
        steps = []
        
        for row in range(self.steps_table.rowCount()):
            # Pull full step dictionary from UserRole
            step = self.steps_table.item(row, 4).data(Qt.ItemDataRole.UserRole)
            if not step:
                # Fallback for safety
                step = {
                    'order': row + 1,
                    'name': self.steps_table.item(row, 1).text() if self.steps_table.item(row, 1) else '',
                    'action_type': self.steps_table.item(row, 2).text() if self.steps_table.item(row, 2) else '',
                    'assigned_role': self.steps_table.item(row, 3).text() if self.steps_table.item(row, 3) else '',
                    'description': self.steps_table.item(row, 4).text() if self.steps_table.item(row, 4) else ''
                }
            else:
                # Ensure order is correct after moves/deletes
                step['order'] = row + 1
                
            steps.append(step)
        
        return json.dumps(steps)


class WorkflowStepFormDialog(QDialog):
    """Dialog for creating/editing a single workflow step"""
    
    def __init__(self, session, step_data=None, parent=None, all_steps=None):
        super().__init__(parent)
        self.session = session
        self.step_data = step_data
        self.all_steps = all_steps or [] # List of {'name': '...'}
        
        self.setWindowTitle("New Step" if step_data is None else "Edit Step")
        self.setMinimumWidth(550)
        
        self.setup_ui()
        if step_data:
            self.load_step_data()
    
    def setup_ui(self):
        """Setup form UI"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        form_layout = QFormLayout()
        
        # Step Name
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g., 'Review Document', 'Approve Request'")
        form_layout.addRow("Step Name *:", self.name_edit)
        
        # Action Type
        self.action_combo = QComboBox()
        self.action_combo.addItems([
            "Review", "Approve", "Reject", "Submit", "Notify", 
            "Validate", "Execute", "Complete", "Decision", "Custom"
        ])
        form_layout.addRow("Action Type *:", self.action_combo)
        
        # Assigned Role
        self.role_edit = QLineEdit()
        self.role_edit.setPlaceholderText("e.g., 'Quality Manager', 'Engineer', 'Admin'")
        form_layout.addRow("Assigned Role:", self.role_edit)
        
        # Description
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(80)
        self.description_edit.setPlaceholderText("Describe what happens in this step")
        form_layout.addRow("Description:", self.description_edit)
        
        layout.addLayout(form_layout)

        # Branching Logic GroupBox
        branch_group = QGroupBox("Workflow Branching & Actions")
        branch_layout = QVBoxLayout()
        branch_group.setLayout(branch_layout)
        
        # Success Branch
        success_layout = QFormLayout()
        self.success_step = QComboBox()
        self.success_step.addItem("Next Sequential Step", "next")
        self.success_step.addItem("End Workflow (Success)", "end")
        for i, step in enumerate(self.all_steps):
            self.success_step.addItem(f"Step {i+1}: {step.get('name')}", i + 1)
            
        self.success_action = QLineEdit()
        self.success_action.setPlaceholderText("Action to trigger on success (e.g. status='approved')")
        
        success_layout.addRow("If Success -> Go To:", self.success_step)
        success_layout.addRow("Success Action:", self.success_action)
        
        # Failure Branch
        fail_layout = QFormLayout()
        self.fail_step = QComboBox()
        self.fail_step.addItem("End Workflow (Fail)", "end")
        self.fail_step.addItem("Restart Workflow", "restart")
        for i, step in enumerate(self.all_steps):
            self.fail_step.addItem(f"Step {i+1}: {step.get('name')}", i + 1)
            
        self.fail_action = QLineEdit()
        self.fail_action.setPlaceholderText("Action to trigger on failure (e.g. open_nc=true)")
        
        fail_layout.addRow("If Failed -> Go To:", self.fail_step)
        fail_layout.addRow("Failure Action:", self.fail_action)
        
        branch_layout.addWidget(QLabel("<b>On Success (Pass/Green):</b>"))
        branch_layout.addLayout(success_layout)
        branch_layout.addWidget(QLabel(""))
        branch_layout.addWidget(QLabel("<b>On Failure (Fail/Red):</b>"))
        branch_layout.addLayout(fail_layout)
        
        layout.addWidget(branch_group)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.validate_and_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def load_step_data(self):
        """Load existing step data"""
        self.name_edit.setText(self.step_data.get('name', ''))
        
        idx = self.action_combo.findText(self.step_data.get('action_type', ''))
        if idx >= 0:
            self.action_combo.setCurrentIndex(idx)
        
        self.role_edit.setText(self.step_data.get('assigned_role', ''))
        self.description_edit.setPlainText(self.step_data.get('description', ''))

        # Load branching
        s_step = self.step_data.get('next_step_success', 'next')
        idx = self.success_step.findData(s_step)
        if idx >= 0: self.success_step.setCurrentIndex(idx)
        self.success_action.setText(self.step_data.get('success_action', ''))

        f_step = self.step_data.get('next_step_fail', 'end')
        idx = self.fail_step.findData(f_step)
        if idx >= 0: self.fail_step.setCurrentIndex(idx)
        self.fail_action.setText(self.step_data.get('fail_action', ''))
    
    def validate_and_accept(self):
        """Validate form"""
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Validation Error", "Step name is required")
            self.name_edit.setFocus()
            return
        
        self.accept()


class WorkflowInstanceDialog(QDialog):
    """Dialog for managing workflow instances"""
    
    def __init__(self, session, workflow, current_user, parent=None):
        super().__init__(parent)
        self.session = session
        self.workflow = workflow
        self.current_user = current_user
        
        self.setWindowTitle(f"Workflow Instances - {workflow.name}")
        self.setMinimumWidth(800)
        self.setMinimumHeight(500)
        
        self.setup_ui()
        self.load_instances()
    
    def setup_ui(self):
        """Setup dialog UI"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Toolbar
        toolbar = QHBoxLayout()
        
        btn_new = QPushButton("New Instance")
        btn_new.clicked.connect(self.new_instance)
        toolbar.addWidget(btn_new)
        
        btn_transition = QPushButton("Transition State")
        btn_transition.clicked.connect(self.transition_state)
        toolbar.addWidget(btn_transition)
        
        btn_complete = QPushButton("Complete")
        btn_complete.clicked.connect(self.complete_instance)
        toolbar.addWidget(btn_complete)
        
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.cancel_instance)
        toolbar.addWidget(btn_cancel)
        
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # Instances table
        self.instances_table = QTableWidget()
        self.instances_table.setColumnCount(6)
        self.instances_table.setHorizontalHeaderLabels([
            'ID', 'Entity Type', 'Entity ID', 'Current Step', 'Status', 'Started At'
        ])
        self.instances_table.setColumnHidden(0, True)
        self.instances_table.horizontalHeader().setStretchLastSection(True)
        self.instances_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.instances_table)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def load_instances(self):
        """Load workflow instances"""
        instances = self.session.query(WorkflowInstance).filter_by(
            workflow_id=self.workflow.id
        ).order_by(WorkflowInstance.started_at.desc()).all()
        
        self.instances_table.setRowCount(len(instances))
        for row_idx, inst in enumerate(instances):
            # Determine entity type and ID from relationships
            entity_type = ''
            entity_id = ''
            if inst.record_id:
                entity_type = 'Record'
                entity_id = str(inst.record_id)
            elif inst.nc_id:
                entity_type = 'Non-Conformance'
                entity_id = str(inst.nc_id)
            
            self.instances_table.setItem(row_idx, 0, QTableWidgetItem(str(inst.id)))
            self.instances_table.setItem(row_idx, 1, QTableWidgetItem(entity_type))
            self.instances_table.setItem(row_idx, 2, QTableWidgetItem(entity_id))
            self.instances_table.setItem(row_idx, 3, QTableWidgetItem(str(inst.current_step) if inst.current_step else '1'))
            self.instances_table.setItem(row_idx, 4, QTableWidgetItem(inst.status or 'in_progress'))
            self.instances_table.setItem(row_idx, 5, QTableWidgetItem(inst.started_at.strftime('%Y-%m-%d %H:%M') if inst.started_at else ''))
    
    def new_instance(self):
        """Create new workflow instance"""
        try:
            inst = WorkflowInstance()
            inst.workflow_id = self.workflow.id
            inst.current_step = 1
            inst.status = 'in_progress'
            inst.started_at = datetime.now()
            # Note: record_id and nc_id should be set when linking to actual entities
            
            self.session.add(inst)
            self.session.commit()
            
            self.load_instances()
            QMessageBox.information(self, "Success", "Workflow instance created")
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to create instance:\n{str(e)}")
    
    def transition_state(self):
        """Transition workflow instance to next step"""
        if self.instances_table.currentRow() < 0:
            QMessageBox.warning(self, "No Selection", "Please select an instance")
            return
        
        inst_id = int(self.instances_table.item(self.instances_table.currentRow(), 0).text())
        inst = self.session.get(WorkflowInstance, inst_id)
        
        if inst:
            # Get workflow steps
            import json
            steps = []
            if self.workflow.steps:
                try:
                    steps_data = json.loads(self.workflow.steps) if isinstance(self.workflow.steps, str) else self.workflow.steps
                    if isinstance(steps_data, list):
                        steps = steps_data
                except:
                    pass
            
            if not steps:
                QMessageBox.warning(self, "No Steps", "This workflow has no defined steps")
                return
            
            max_step = len(steps)
            current = inst.current_step or 1
            
            if current >= max_step:
                QMessageBox.information(self, "Final Step", "Instance is already at the final step")
                return
            
            try:
                inst.current_step = current + 1
                self.session.commit()
                self.load_instances()
                QMessageBox.information(self, "Success", f"Moved to step {inst.current_step}")
            except Exception as e:
                self.session.rollback()
                QMessageBox.critical(self, "Error", f"Failed to transition:\n{str(e)}")
    
    def complete_instance(self):
        """Mark instance as completed"""
        if self.instances_table.currentRow() < 0:
            QMessageBox.warning(self, "No Selection", "Please select an instance")
            return
        
        inst_id = int(self.instances_table.item(self.instances_table.currentRow(), 0).text())
        inst = self.session.get(WorkflowInstance, inst_id)
        
        if inst:
            try:
                inst.status = 'completed'
                inst.completed_at = datetime.now()
                self.session.commit()
                self.load_instances()
                QMessageBox.information(self, "Success", "Instance completed")
            except Exception as e:
                self.session.rollback()
                QMessageBox.critical(self, "Error", f"Failed to complete:\n{str(e)}")
    
    def cancel_instance(self):
        """Cancel workflow instance"""
        if self.instances_table.currentRow() < 0:
            QMessageBox.warning(self, "No Selection", "Please select an instance")
            return
        
        inst_id = int(self.instances_table.item(self.instances_table.currentRow(), 0).text())
        inst = self.session.get(WorkflowInstance, inst_id)
        
        if inst:
            try:
                inst.status = 'cancelled'
                inst.completed_at = datetime.now()
                self.session.commit()
                self.load_instances()
                QMessageBox.information(self, "Success", "Instance cancelled")
            except Exception as e:
                self.session.rollback()
                QMessageBox.critical(self, "Error", f"Failed to cancel:\n{str(e)}")


class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        
        self.session = None
        self.current_user = None
        
        self.setWindowTitle("Quality Management System")
        self.setGeometry(100, 100, 1400, 900)
        
        # Initialize database
        if not self.init_database():
            sys.exit(1)
        
        # Show login dialog
        if not self.show_login():
            sys.exit(0)
        
        # Setup UI
        self.apply_theme()
        self.setup_ui()
        self.setup_menu()
        self.setup_toolbar()
        self.setup_statusbar()
        
        # Load dashboard
        self.load_dashboard()
        
        # Check for updates (non-blocking)
        if UPDATER_AVAILABLE:
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(2000, self.check_for_updates)  # Check after 2 seconds
    
    def apply_theme(self):
        """Apply a professional light theme to the application"""
        qss = """
        QMainWindow, QDialog {
            background-color: #f5f7fa;
        }
        
        /* General Widget Styling */
        QWidget {
            font-family: 'Segoe UI', Arial, sans-serif;
            font-size: 10pt;
            color: #2d3436;
        }
        
        /* Tab Widget Styling */
        QTabWidget::pane {
            border: 1px solid #dcdde1;
            background: white;
            border-radius: 5px;
        }
        
        QTabBar::tab {
            background: #f1f2f6;
            border: 1px solid #dcdde1;
            padding: 10px 20px;
            border-top-left-radius: 5px;
            border-top-right-radius: 5px;
            margin-right: 2px;
            color: #57606f;
        }
        
        QTabBar::tab:selected {
            background: white;
            border-bottom-color: white;
            font-weight: bold;
            color: #2f3542;
        }
        
        QTabBar::tab:hover {
            background: #dfe4ea;
        }
        
        /* Table Styling */
        QTableWidget, QTreeView, QListView {
            background-color: white;
            alternate-background-color: #f8f9fa;
            border: 1px solid #dcdde1;
            gridline-color: #f1f2f6;
            selection-background-color: #70a1ff;
            selection-color: white;
            border-radius: 4px;
        }
        
        QHeaderView::section {
            background-color: #2f3542;
            color: white;
            padding: 8px;
            border: none;
            font-weight: bold;
            border-right: 1px solid #57606f;
        }
        
        /* Buttons */
        QPushButton {
            background-color: #1e90ff;
            color: white;
            border: none;
            padding: 8px 15px;
            border-radius: 4px;
            font-weight: bold;
        }
        
        QPushButton:hover {
            background-color: #3742fa;
        }
        
        QPushButton:pressed {
            background-color: #2f3542;
        }
        
        QPushButton:disabled {
            background-color: #ced6e0;
            color: #747d8c;
        }
        
        /* Toolbar buttons often need to be smaller or have a different style */
        QToolBar QPushButton {
            padding: 4px 8px;
            font-size: 9pt;
        }
        
        /* Form Controls */
        QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit {
            background-color: white;
            border: 1px solid #ced4da;
            border-radius: 4px;
            padding: 6px;
            color: #2d3436;
        }
        
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus {
            border: 2px solid #70a1ff;
        }
        
        /* Group Box */
        QGroupBox {
            font-weight: bold;
            border: 1px solid #dcdde1;
            border-radius: 8px;
            margin-top: 1.2em;
            padding-top: 10px;
            background-color: #ffffff;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
            color: #2f3542;
        }
        
        /* Dashboard Metric Value */
        #metric_value {
            color: #1e90ff;
            font-size: 24pt;
        }
        
        /* Status Bar */
        QStatusBar {
            background-color: #f1f2f6;
            color: #57606f;
        }
        
        /* Scroll Bar */
        QScrollBar:vertical {
            border: none;
            background: #f1f2f6;
            width: 12px;
            margin: 0px;
        }
        QScrollBar::handle:vertical {
            background: #ced6e0;
            min-height: 25px;
            border-radius: 6px;
        }
        QScrollBar::handle:vertical:hover {
            background: #a4b0be;
        }
        """
        self.setStyleSheet(qss)
    
    def check_for_updates(self):
        """Check for application updates"""
        if not UPDATER_AVAILABLE:
            QMessageBox.information(self, "Updates", "Update checker is not available.\nPlease install 'requests' package.")
            return
        
        try:
            updater = Updater()
            print(f"Checking for updates from: {updater.update_url}")
            print(f"Current version: {updater.current_version}")
            
            update_info = updater.check_for_updates()
            
            if update_info is None:
                QMessageBox.warning(self, "Update Check Failed", 
                                   "Could not check for updates.\n\nPlease check your internet connection.")
                return
            
            if update_info.get('available'):
                # Show update dialog
                from PyQt6.QtCore import Qt
                reply = QMessageBox.question(
                    self,
                    "Update Available",
                    f"A new version {update_info['version']} is available!\n\n"
                    f"Current version: {__version__}\n"
                    f"Latest version: {update_info['version']}\n\n"
                    f"Release Notes:\n{update_info.get('notes', 'No notes available')}\n\n"
                    f"Would you like to download and install the update?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    self.download_and_install_update(updater, update_info)
            else:
                QMessageBox.information(self, "No Updates", 
                                       f"You are running the latest version ({__version__})")
        except Exception as e:
            print(f"Update check failed: {e}")
    
    def download_and_install_update(self, updater, update_info):
        """Download and install update"""
        from PyQt6.QtWidgets import QProgressDialog
        from PyQt6.QtCore import Qt
        
        # Create progress dialog
        progress = QProgressDialog(
            "Downloading update...",
            "Cancel",
            0, 100,
            self
        )
        progress.setWindowTitle("Updating")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.show()
        
        def update_progress(downloaded, total):
            if total > 0:
                percent = int((downloaded / total) * 100)
                progress.setValue(percent)
                QApplication.processEvents()
        
        # Download
        download_url = update_info.get('url')
        installer_path = updater.download_update(download_url, update_progress)
        
        progress.close()
        
        if installer_path:
            reply = QMessageBox.question(
                self,
                "Install Update",
                "Update downloaded successfully!\n\n"
                "The application will close and the installer will start.\n"
                "Do you want to continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Install and exit
                if updater.install_update(installer_path):
                    QApplication.quit()
        else:
            QMessageBox.warning(
                self,
                "Download Failed",
                "Failed to download update. Please try again later or download manually."
            )
    
    def show_login(self):
        """Show login dialog and authenticate user"""
        login_dialog = LoginDialog(self.session, self)
        if login_dialog.exec() == QDialog.DialogCode.Accepted:
            self.current_user = login_dialog.authenticated_user
            return True
        return False
    
    def has_permission(self, permission: str) -> bool:
        """Check if current user has a specific permission"""
        if not self.current_user or not self.current_user.role:
            return False
        
        permissions = self.current_user.role.permissions or {}
        return permissions.get(permission, False)
    
    def is_admin(self) -> bool:
        """Check if current user is admin"""
        return self.current_user and self.current_user.role and self.current_user.role.name == 'Admin'
    
    def log_action(self, action, table_name, record_id, old_values=None, new_values=None):
        """Log an action to audit trail"""
        try:
            # Calculate changed fields
            changed_fields = {}
            if old_values and new_values:
                for key in new_values:
                    if key in old_values and old_values[key] != new_values[key]:
                        changed_fields[key] = {'old': str(old_values[key]), 'new': str(new_values[key])}
            
            log_entry = AuditLog(
                table_name=table_name,
                record_id=record_id,
                action=action,
                user_id=self.current_user.id if self.current_user else None,
                username=self.current_user.full_name if self.current_user else 'System',
                old_values=old_values,
                new_values=new_values,
                changed_fields=changed_fields,
                timestamp=datetime.now()
            )
            self.session.add(log_entry)
            self.session.commit()
        except Exception as e:
            print(f"Failed to log action: {e}")
            import traceback
            traceback.print_exc()
    
    def create_notification(self, user_id, title, message, notif_type='info', priority='normal', related_record_id=None, related_nc_id=None):
        """Create a notification for a user"""
        try:
            notification = Notification(
                user_id=user_id,
                title=title,
                message=message,
                type=notif_type,
                priority=priority,
                related_record_id=related_record_id,
                related_nc_id=related_nc_id,
                is_read=False,
                created_at=datetime.now()
            )
            self.session.add(notification)
            self.session.commit()
        except Exception as e:
            print(f"Failed to create notification: {e}")
            import traceback
            traceback.print_exc()
    
    def logout(self):
        """Logout current user"""
        reply = QMessageBox.question(
            self, "Logout",
            "Are you sure you want to logout?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Close current session
            if self.session:
                self.session.close()
            
            # Close main window
            self.close()
            
            # Restart application (will show login again)
            QApplication.quit()
            QApplication.instance().quit()
    
    def init_database(self):
        """Initialize database connection"""
        try:
            # Initialize database
            db_manager, was_newly_created = init_database(create_tables=True, init_data=True)
            self.session = db_manager.get_session()
            
            # Only show message if database was newly created
            if was_newly_created:
                QMessageBox.information(self, "Database", 
                    "Database initialized successfully!\n\n"
                    "Default admin user created:\n"
                    "Username: admin\n"
                    "Password: admin123\n\n"
                    "**PLEASE CHANGE THIS PASSWORD IMMEDIATELY**")
            return True
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to initialize database:\n{str(e)}")
            return False
    
    def setup_ui(self):
        """Setup main UI"""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Tab widget for different views
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # Create tabs
        self.dashboard_tab = QWidget()
        self.records_tab = QWidget()
        self.templates_tab = QWidget()
        self.standards_tab = QWidget()
        self.nc_tab = QWidget()
        self.reports_tab = QWidget()
        self.users_tab = QWidget()  # For admin users
        
        self.tabs.addTab(self.dashboard_tab, "Dashboard")
        self.tabs.addTab(self.records_tab, "Records")
        self.tabs.addTab(self.templates_tab, "Templates")
        self.tabs.addTab(self.standards_tab, "Standards")
        self.tabs.addTab(self.nc_tab, "Non-Conformances")
        self.tabs.addTab(self.reports_tab, "Reports")
        
        # Add Users tab only for users with manage_users permission
        if self.has_permission('can_manage_users'):
            self.tabs.addTab(self.users_tab, "Users")
        
        # Setup each tab
        self.setup_dashboard_tab()
        self.setup_records_tab()
        self.setup_templates_tab()
        self.setup_standards_tab()
        self.setup_nc_tab()
        self.setup_reports_tab()
        
        # Setup users tab if has permission
        if self.has_permission('can_manage_users'):
            self.setup_users_tab()
    
    def setup_dashboard_tab(self):
        """Setup dashboard tab"""
        layout = QVBoxLayout()
        self.dashboard_tab.setLayout(layout)
        
        # Title
        title = QLabel("Quality Management System Dashboard")
        title.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Metrics row
        metrics_layout = QHBoxLayout()
        
        # Create metric cards
        self.metric_total_records = self.create_metric_card("Total Records (30d)", "0")
        self.metric_pending = self.create_metric_card("Pending Approvals", "0")
        self.metric_open_ncs = self.create_metric_card("Open NCs", "0")
        self.metric_compliance = self.create_metric_card("Avg Compliance", "0%")
        
        metrics_layout.addWidget(self.metric_total_records)
        metrics_layout.addWidget(self.metric_pending)
        metrics_layout.addWidget(self.metric_open_ncs)
        metrics_layout.addWidget(self.metric_compliance)
        
        layout.addLayout(metrics_layout)
        
        # Recent records table
        layout.addWidget(QLabel("Recent Records:"))
        
        self.recent_records_table = QTableWidget()
        self.recent_records_table.setColumnCount(5)
        self.recent_records_table.setHorizontalHeaderLabels([
            'Record Number', 'Title', 'Status', 'Date', 'Compliance'
        ])
        self.recent_records_table.horizontalHeader().setStretchLastSection(True)
        self.recent_records_table.setAlternatingRowColors(True)
        self.recent_records_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.recent_records_table)
    
    def create_metric_card(self, label: str, value: str) -> QGroupBox:
        """Create a metric display card"""
        group = QGroupBox(label)
        layout = QVBoxLayout()
        
        value_label = QLabel(value)
        value_label.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        value_label.setObjectName("metric_value")
        
        layout.addWidget(value_label)
        group.setLayout(layout)
        
        return group
    
    def setup_records_tab(self):
        """Setup records tab"""
        layout = QVBoxLayout()
        self.records_tab.setLayout(layout)
        
        # Toolbar
        toolbar_layout = QHBoxLayout()
        
        btn_new_record = QPushButton("New Record")
        btn_new_record.clicked.connect(self.new_record_dialog)
        btn_new_record.setEnabled(self.has_permission('can_create_records'))
        
        btn_quick_add = QPushButton("Quick Add Reading")
        btn_quick_add.clicked.connect(self.quick_add_reading)
        btn_quick_add.setStyleSheet("background-color: #2ed573; color: white;")
        btn_quick_add.setToolTip("Quickly add a reading to the selected record without opening it")
        
        btn_edit_record = QPushButton("Edit")
        btn_edit_record.clicked.connect(self.edit_record_dialog)
        btn_edit_record.setEnabled(self.has_permission('can_create_records'))
        
        btn_delete_record = QPushButton("Delete")
        btn_delete_record.clicked.connect(self.delete_record)
        btn_delete_record.setEnabled(self.has_permission('can_create_records'))
        
        btn_export_excel = QPushButton("Export to Excel")
        btn_export_excel.clicked.connect(self.export_records_to_excel)
        
        btn_generate_pdf = QPushButton("Generate PDF")
        btn_generate_pdf.clicked.connect(self.generate_record_pdf)
        
        btn_generate_stats_pdf = QPushButton("Statistical Report PDF")
        btn_generate_stats_pdf.clicked.connect(self.generate_statistical_report_pdf)
        btn_generate_stats_pdf.setToolTip("Generate PDF with charts and statistical analysis")
        
        btn_export_data = QPushButton("Export Data (Excel)")
        btn_export_data.clicked.connect(self.export_record_data_to_excel)
        btn_export_data.setToolTip("Export criteria values and statistics to Excel")
        
        btn_date_range_report = QPushButton("Date Range Report")
        btn_date_range_report.clicked.connect(self.generate_date_range_statistical_report)
        btn_date_range_report.setToolTip("Generate statistical report for date range")
        
        btn_refresh = QPushButton("Refresh")
        btn_refresh.clicked.connect(self.load_records)
        
        toolbar_layout.addWidget(btn_new_record)
        toolbar_layout.addWidget(btn_quick_add)
        toolbar_layout.addWidget(btn_edit_record)
        toolbar_layout.addWidget(btn_delete_record)
        toolbar_layout.addWidget(btn_export_excel)
        toolbar_layout.addWidget(btn_export_data)
        toolbar_layout.addWidget(btn_generate_pdf)
        toolbar_layout.addWidget(btn_generate_stats_pdf)
        toolbar_layout.addWidget(btn_date_range_report)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(btn_refresh)
        
        layout.addLayout(toolbar_layout)
        
        # Records table
        self.records_table = QTableWidget()
        self.records_table.setColumnCount(8)
        self.records_table.setHorizontalHeaderLabels([
            'ID', 'Record Number', 'Title', 'Template', 'Status',
            'Date', 'Compliance', 'Score'
        ])
        self.records_table.setColumnHidden(0, True)  # Hide ID column
        self.records_table.horizontalHeader().setStretchLastSection(True)
        self.records_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.records_table.setAlternatingRowColors(True)
        
        layout.addWidget(self.records_table)
    
    def setup_templates_tab(self):
        """Setup templates tab"""
        layout = QVBoxLayout()
        self.templates_tab.setLayout(layout)
        
        # Toolbar
        toolbar_layout = QHBoxLayout()
        
        btn_new_template = QPushButton("New Template")
        btn_new_template.clicked.connect(self.new_template_dialog)
        btn_new_template.setEnabled(self.has_permission('can_edit_templates'))
        btn_edit_template = QPushButton("Edit")
        btn_edit_template.clicked.connect(self.edit_template_dialog)
        btn_edit_template.setEnabled(self.has_permission('can_edit_templates'))
        btn_delete_template = QPushButton("Delete")
        btn_delete_template.clicked.connect(self.delete_template)
        btn_delete_template.setEnabled(self.has_permission('can_edit_templates'))
        btn_export_template = QPushButton("Export Template")
        btn_export_template.clicked.connect(self.export_template)
        btn_refresh_templates = QPushButton("Refresh")
        btn_refresh_templates.clicked.connect(self.load_templates)
        
        toolbar_layout.addWidget(btn_new_template)
        toolbar_layout.addWidget(btn_edit_template)
        toolbar_layout.addWidget(btn_delete_template)
        toolbar_layout.addWidget(btn_export_template)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(btn_refresh_templates)
        
        layout.addLayout(toolbar_layout)
        
        # Templates table
        self.templates_table = QTableWidget()
        self.templates_table.setColumnCount(6)
        self.templates_table.setHorizontalHeaderLabels([
            'ID', 'Code', 'Name', 'Category', 'Standard', 'Active'
        ])
        self.templates_table.setColumnHidden(0, True)
        self.templates_table.horizontalHeader().setStretchLastSection(True)
        self.templates_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.templates_table.setAlternatingRowColors(True)
        
        layout.addWidget(self.templates_table)
    
    def setup_standards_tab(self):
        """Setup standards tab"""
        layout = QVBoxLayout()
        self.standards_tab.setLayout(layout)
        
        # Toolbar
        toolbar_layout = QHBoxLayout()
        
        btn_new_standard = QPushButton("New Standard")
        btn_new_standard.clicked.connect(self.new_standard_dialog)
        btn_new_standard.setEnabled(self.has_permission('can_manage_standards'))
        btn_edit_standard = QPushButton("Edit")
        btn_edit_standard.clicked.connect(self.edit_standard_dialog)
        btn_edit_standard.setEnabled(self.has_permission('can_manage_standards'))
        btn_delete_standard = QPushButton("Delete")
        btn_delete_standard.clicked.connect(self.delete_standard)
        btn_delete_standard.setEnabled(self.has_permission('can_manage_standards'))
        btn_export_standard_pdf = QPushButton("Export to PDF")
        btn_export_standard_pdf.clicked.connect(self.generate_standard_pdf)
        btn_export_standard_pdf.setToolTip("Export standard with all sections and criteria to PDF")
        btn_import_excel = QPushButton("Import from Excel")
        btn_import_excel.clicked.connect(self.import_standards_from_excel)
        btn_import_excel.setEnabled(self.has_permission('can_manage_standards'))
        btn_refresh_standards = QPushButton("Refresh")
        btn_refresh_standards.clicked.connect(self.load_standards)
        
        toolbar_layout.addWidget(btn_new_standard)
        toolbar_layout.addWidget(btn_edit_standard)
        toolbar_layout.addWidget(btn_delete_standard)
        toolbar_layout.addWidget(btn_export_standard_pdf)
        toolbar_layout.addWidget(btn_import_excel)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(btn_refresh_standards)
        
        layout.addLayout(toolbar_layout)
        
        # Standards table
        self.standards_table = QTableWidget()
        self.standards_table.setColumnCount(6)
        self.standards_table.setHorizontalHeaderLabels([
            'ID', 'Code', 'Name', 'Version', 'Industry', 'Active'
        ])
        self.standards_table.setColumnHidden(0, True)
        self.standards_table.horizontalHeader().setStretchLastSection(True)
        self.standards_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.standards_table.setAlternatingRowColors(True)
        
        layout.addWidget(self.standards_table)
    
    def setup_nc_tab(self):
        """Setup non-conformances tab"""
        layout = QVBoxLayout()
        self.nc_tab.setLayout(layout)
        
        # Toolbar
        toolbar_layout = QHBoxLayout()
        
        btn_new_nc = QPushButton("New NC")
        btn_new_nc.clicked.connect(self.new_nc_dialog)
        btn_new_nc.setEnabled(self.has_permission('can_create_records'))
        btn_edit_nc = QPushButton("Edit")
        btn_edit_nc.clicked.connect(self.edit_nc_dialog)
        btn_edit_nc.setEnabled(self.has_permission('can_create_records'))
        btn_delete_nc = QPushButton("Delete")
        btn_delete_nc.clicked.connect(self.delete_nc)
        btn_delete_nc.setEnabled(self.has_permission('can_close_nc'))
        btn_nc_pdf = QPushButton("Generate PDF")
        btn_nc_pdf.clicked.connect(self.generate_nc_pdf)
        btn_refresh_nc = QPushButton("Refresh")
        btn_refresh_nc.clicked.connect(self.load_ncs)
        
        toolbar_layout.addWidget(btn_new_nc)
        toolbar_layout.addWidget(btn_edit_nc)
        toolbar_layout.addWidget(btn_delete_nc)
        toolbar_layout.addWidget(btn_nc_pdf)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(btn_refresh_nc)
        
        layout.addLayout(toolbar_layout)
        
        # NCs table
        self.nc_table = QTableWidget()
        self.nc_table.setColumnCount(7)
        self.nc_table.setHorizontalHeaderLabels([
            'ID', 'NC Number', 'Title', 'Severity', 'Status',
            'Detected', 'Assigned To'
        ])
        self.nc_table.setColumnHidden(0, True)
        self.nc_table.horizontalHeader().setStretchLastSection(True)
        self.nc_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.nc_table.setAlternatingRowColors(True)
        
        layout.addWidget(self.nc_table)
    
    def setup_reports_tab(self):
        """Setup reports tab"""
        layout = QVBoxLayout()
        self.reports_tab.setLayout(layout)
        
        # Report selection
        reports_group = QGroupBox("Generate Report")
        reports_layout = QVBoxLayout()
        
        btn_compliance_report = QPushButton("Compliance Summary Report")
        btn_compliance_report.clicked.connect(self.generate_compliance_report)
        
        btn_trend_report = QPushButton("Trend Analysis Report")
        btn_trend_report.clicked.connect(self.generate_trend_report)
        btn_nc_report = QPushButton("NC Summary Report")
        btn_nc_report.clicked.connect(self.generate_nc_report)
        btn_inspector_report = QPushButton("Inspector Performance Report")
        btn_inspector_report.clicked.connect(self.generate_inspector_report)
        
        reports_layout.addWidget(btn_compliance_report)
        reports_layout.addWidget(btn_trend_report)
        reports_layout.addWidget(btn_nc_report)
        reports_layout.addWidget(btn_inspector_report)
        reports_layout.addStretch()
        
        reports_group.setLayout(reports_layout)
        layout.addWidget(reports_group)
    
    def setup_users_tab(self):
        """Setup users tab (Admin only)"""
        layout = QVBoxLayout()
        self.users_tab.setLayout(layout)
        
        # Toolbar
        toolbar_layout = QHBoxLayout()
        
        btn_new_user = QPushButton("New User")
        btn_new_user.clicked.connect(self.new_user_dialog)
        btn_edit_user = QPushButton("Edit")
        btn_edit_user.clicked.connect(self.edit_user_dialog)
        btn_delete_user = QPushButton("Delete")
        btn_delete_user.clicked.connect(self.delete_user)
        btn_refresh_users = QPushButton("Refresh")
        btn_refresh_users.clicked.connect(self.load_users)
        
        toolbar_layout.addWidget(btn_new_user)
        toolbar_layout.addWidget(btn_edit_user)
        toolbar_layout.addWidget(btn_delete_user)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(btn_refresh_users)
        
        layout.addLayout(toolbar_layout)
        
        # Users table
        self.users_table = QTableWidget()
        self.users_table.setColumnCount(7)
        self.users_table.setHorizontalHeaderLabels([
            'ID', 'Username', 'Full Name', 'Email', 'Role', 'Department', 'Active'
        ])
        self.users_table.setColumnHidden(0, True)
        self.users_table.horizontalHeader().setStretchLastSection(True)
        self.users_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        layout.addWidget(self.users_table)
        
        # Load users
        self.load_users()
    
    def setup_menu(self):
        """Setup menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        new_record_action = QAction("New Record", self)
        new_record_action.triggered.connect(self.new_record_dialog)
        new_record_action.setEnabled(self.has_permission('can_create_records'))
        file_menu.addAction(new_record_action)
        
        file_menu.addSeparator()
        
        import_action = QAction("Import from Excel", self)
        import_action.triggered.connect(self.import_standards_from_excel)
        import_action.setEnabled(self.has_permission('can_manage_standards'))
        file_menu.addAction(import_action)
        
        export_action = QAction("Export to Excel", self)
        export_action.triggered.connect(self.export_records_to_excel)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        logout_action = QAction("Logout", self)
        logout_action.triggered.connect(self.logout)
        file_menu.addAction(logout_action)
        
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Users menu (only for users with can_manage_users permission)
        if self.has_permission('can_manage_users'):
            users_menu = menubar.addMenu("Users")
            
            new_user_action = QAction("New User", self)
            new_user_action.triggered.connect(self.new_user_dialog)
            users_menu.addAction(new_user_action)
            
            users_menu.addSeparator()
            
            view_users_action = QAction("View All Users", self)
            view_users_action.triggered.connect(lambda: self.tabs.setCurrentWidget(self.users_tab))
            users_menu.addAction(view_users_action)
        
        # Profile menu
        profile_menu = menubar.addMenu("Profile")
        
        my_profile_action = QAction("My Profile", self)
        my_profile_action.triggered.connect(self.open_profile_dialog)
        profile_menu.addAction(my_profile_action)
        
        # Tools menu
        tools_menu = menubar.addMenu("Tools")
        
        # Workflows
        workflows_action = QAction("Workflow Management", self)
        workflows_action.triggered.connect(self.open_workflows)
        tools_menu.addAction(workflows_action)
        
        # Audit Log
        audit_log_action = QAction("View Audit Log", self)
        audit_log_action.triggered.connect(self.open_audit_log)
        tools_menu.addAction(audit_log_action)
        
        # Notifications
        notifications_action = QAction("Notifications", self)
        notifications_action.triggered.connect(self.open_notifications)
        tools_menu.addAction(notifications_action)
        
        # Documents
        documents_action = QAction("Document Management", self)
        documents_action.triggered.connect(self.open_documents)
        tools_menu.addAction(documents_action)
        
        # Images
        images_action = QAction("Image Attachments", self)
        images_action.triggered.connect(self.open_images)
        tools_menu.addAction(images_action)
        
        tools_menu.addSeparator()
        
        # Company Settings (Admin only)
        if self.is_admin():
            company_settings_action = QAction("Company Settings", self)
            company_settings_action.triggered.connect(self.open_company_settings)
            tools_menu.addAction(company_settings_action)
        
        # Backup (Admin only)
        if self.is_admin():
            backup_action = QAction("Backup Database", self)
            backup_action.triggered.connect(self.backup_database)
            tools_menu.addAction(backup_action)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
        if UPDATER_AVAILABLE:
            update_action = QAction("Check for Updates", self)
            update_action.triggered.connect(self.check_for_updates)
            help_menu.addAction(update_action)
    
    def setup_toolbar(self):
        """Setup toolbar"""
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        
        # Add toolbar actions
        new_action = QAction("New Record", self)
        new_action.triggered.connect(self.new_record_dialog)
        toolbar.addAction(new_action)
        
        toolbar.addSeparator()
        
        refresh_action = QAction("Refresh", self)
        refresh_action.triggered.connect(self.refresh_current_tab)
        toolbar.addAction(refresh_action)
    
    def setup_statusbar(self):
        """Setup status bar"""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        
        # Show current user
        if self.current_user:
            self.statusbar.showMessage(f"Logged in as: {self.current_user.full_name} ({self.current_user.role.name if self.current_user.role else 'No Role'})")
    
    # ========================================================================
    # DATA LOADING METHODS
    # ========================================================================
    
    def load_dashboard(self):
        """Load dashboard data"""
        try:
            reports_gen = ReportsGenerator(self.session)
            dashboard_data = reports_gen.dashboard_summary()
            
            # Update metrics
            self.metric_total_records.findChild(QLabel, "metric_value").setText(
                str(dashboard_data['total_records_30d'])
            )
            self.metric_pending.findChild(QLabel, "metric_value").setText(
                str(dashboard_data['pending_approvals'])
            )
            self.metric_open_ncs.findChild(QLabel, "metric_value").setText(
                str(dashboard_data['open_ncs'])
            )
            self.metric_compliance.findChild(QLabel, "metric_value").setText(
                f"{dashboard_data['avg_compliance_30d']}%"
            )
            
            # Update recent records table
            recent = dashboard_data['recent_records']
            self.recent_records_table.setRowCount(len(recent))
            
            for row_idx, record in enumerate(recent):
                self.recent_records_table.setItem(row_idx, 0, QTableWidgetItem(record['record_number']))
                self.recent_records_table.setItem(row_idx, 1, QTableWidgetItem(record['title'] or ''))
                self.recent_records_table.setItem(row_idx, 2, QTableWidgetItem(record['status']))
                self.recent_records_table.setItem(row_idx, 3, QTableWidgetItem(record['created_at']))
                self.recent_records_table.setItem(row_idx, 4, QTableWidgetItem(record['compliance']))
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load dashboard: {str(e)}")
    
    def load_records(self):
        """Load records into table"""
        try:
            records = self.session.query(Record).order_by(Record.created_at.desc()).limit(100).all()
            
            self.records_table.setRowCount(len(records))
            
            for row_idx, record in enumerate(records):
                self.records_table.setItem(row_idx, 0, QTableWidgetItem(str(record.id)))
                self.records_table.setItem(row_idx, 1, QTableWidgetItem(record.record_number))
                self.records_table.setItem(row_idx, 2, QTableWidgetItem(record.title or ''))
                self.records_table.setItem(row_idx, 3, QTableWidgetItem(record.template.name if record.template else ''))
                self.records_table.setItem(row_idx, 4, QTableWidgetItem(record.status))
                self.records_table.setItem(row_idx, 5, QTableWidgetItem(
                    record.created_at.strftime('%Y-%m-%d') if record.created_at else ''
                ))
                self.records_table.setItem(row_idx, 6, QTableWidgetItem(
                    'Pass' if record.overall_compliance else 'Fail' if record.overall_compliance is not None else ''
                ))
                self.records_table.setItem(row_idx, 7, QTableWidgetItem(
                    f"{record.compliance_score}%" if record.compliance_score else ''
                ))
            
            self.statusbar.showMessage(f"Loaded {len(records)} records", 3000)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load records: {str(e)}")
    
    def load_templates(self):
        """Load templates into table"""
        try:
            templates = self.session.query(TestTemplate).all()
            
            self.templates_table.setRowCount(len(templates))
            
            for row_idx, template in enumerate(templates):
                self.templates_table.setItem(row_idx, 0, QTableWidgetItem(str(template.id)))
                self.templates_table.setItem(row_idx, 1, QTableWidgetItem(template.code))
                self.templates_table.setItem(row_idx, 2, QTableWidgetItem(template.name))
                self.templates_table.setItem(row_idx, 3, QTableWidgetItem(template.category or ''))
                self.templates_table.setItem(row_idx, 4, QTableWidgetItem(
                    template.standard.name if template.standard else ''
                ))
                self.templates_table.setItem(row_idx, 5, QTableWidgetItem(
                    'Yes' if template.is_active else 'No'
                ))
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load templates: {str(e)}")
    
    def load_standards(self):
        """Load standards into table"""
        try:
            standards = self.session.query(Standard).all()
            
            self.standards_table.setRowCount(len(standards))
            
            for row_idx, standard in enumerate(standards):
                self.standards_table.setItem(row_idx, 0, QTableWidgetItem(str(standard.id)))
                self.standards_table.setItem(row_idx, 1, QTableWidgetItem(standard.code))
                self.standards_table.setItem(row_idx, 2, QTableWidgetItem(standard.name))
                self.standards_table.setItem(row_idx, 3, QTableWidgetItem(standard.version))
                self.standards_table.setItem(row_idx, 4, QTableWidgetItem(standard.industry or ''))
                self.standards_table.setItem(row_idx, 5, QTableWidgetItem(
                    'Yes' if standard.is_active else 'No'
                ))
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load standards: {str(e)}")
    
    def load_ncs(self):
        """Load non-conformances into table"""
        try:
            ncs = self.session.query(NonConformance).order_by(NonConformance.detected_date.desc()).all()
            
            self.nc_table.setRowCount(len(ncs))
            
            for row_idx, nc in enumerate(ncs):
                self.nc_table.setItem(row_idx, 0, QTableWidgetItem(str(nc.id)))
                self.nc_table.setItem(row_idx, 1, QTableWidgetItem(nc.nc_number))
                self.nc_table.setItem(row_idx, 2, QTableWidgetItem(nc.title))
                self.nc_table.setItem(row_idx, 3, QTableWidgetItem(nc.severity))
                self.nc_table.setItem(row_idx, 4, QTableWidgetItem(nc.status))
                self.nc_table.setItem(row_idx, 5, QTableWidgetItem(
                    nc.detected_date.strftime('%Y-%m-%d') if nc.detected_date else ''
                ))
                self.nc_table.setItem(row_idx, 6, QTableWidgetItem(
                    nc.assigned_to.full_name if nc.assigned_to else ''
                ))
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load NCs: {str(e)}")
    
    def load_users(self):
        """Load users into table (Admin only)"""
        try:
            users = self.session.query(User).all()
            
            self.users_table.setRowCount(len(users))
            
            for row_idx, user in enumerate(users):
                self.users_table.setItem(row_idx, 0, QTableWidgetItem(str(user.id)))
                self.users_table.setItem(row_idx, 1, QTableWidgetItem(user.username))
                self.users_table.setItem(row_idx, 2, QTableWidgetItem(user.full_name))
                self.users_table.setItem(row_idx, 3, QTableWidgetItem(user.email))
                self.users_table.setItem(row_idx, 4, QTableWidgetItem(
                    user.role.name if user.role else ''
                ))
                self.users_table.setItem(row_idx, 5, QTableWidgetItem(user.department or ''))
                self.users_table.setItem(row_idx, 6, QTableWidgetItem(
                    'Yes' if user.is_active else 'No'
                ))
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load users: {str(e)}")
    
    def refresh_current_tab(self):
        """Refresh current tab data"""
        current_index = self.tabs.currentIndex()
        
        if current_index == 0:  # Dashboard
            self.load_dashboard()
        elif current_index == 1:  # Records
            self.load_records()
        elif current_index == 2:  # Templates
            self.load_templates()
        elif current_index == 3:  # Standards
            self.load_standards()
        elif current_index == 4:  # NCs
            self.load_ncs()
        elif current_index == 6:  # Users (if admin)
            if self.current_user and self.current_user.role and self.current_user.role.name == 'Admin':
                self.load_users()
    
    # ========================================================================
    # ACTION METHODS
    # ========================================================================
    
    def new_record_dialog(self):
        """Open dialog to create new record"""
        dialog = RecordDialog(self.session, self.current_user, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_records()
            self.statusbar.showMessage("Record created successfully", 3000)
    
    def quick_add_reading(self):
        """Open dialog to quickly add a reading to selected record"""
        selected_rows = self.records_table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select a record to add a reading to")
            return
            
        try:
            record_id = int(self.records_table.item(self.records_table.currentRow(), 0).text())
            record = self.session.get(Record, record_id)
            
            if record:
                if not record.template:
                    QMessageBox.warning(self, "No Template", "This record has no template assigned. Cannot add readings quickly.")
                    return
                    
                dialog = QuickAddReadingDialog(self.session, record, parent=self)
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    self.load_records()
                    self.statusbar.showMessage("Reading added successfully", 3000)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to add reading:\n{str(e)}")
    
    def edit_record_dialog(self):
        """Open dialog to edit selected record"""
        selected_rows = self.records_table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select a record to edit")
            return
        
        try:
            record_id = int(self.records_table.item(self.records_table.currentRow(), 0).text())
            record = self.session.get(Record, record_id)
            
            if record:
                dialog = RecordDialog(self.session, self.current_user, record=record, parent=self)
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    self.load_records()
                    self.statusbar.showMessage("Record updated successfully", 3000)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to edit record:\n{str(e)}")
    
    def delete_record(self):
        """Delete selected record"""
        selected_rows = self.records_table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select a record to delete")
            return
        
        try:
            record_id = int(self.records_table.item(self.records_table.currentRow(), 0).text())
            record = self.session.get(Record, record_id)
            
            if not record:
                QMessageBox.warning(self, "Error", "Record not found")
                return
            
            reply = QMessageBox.question(
                self, "Confirm Delete", 
                f"Are you sure you want to delete record '{record.record_number}'?\n\nThis action cannot be undone.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Audit logging before delete
                try:
                    log_entry = AuditLog(
                        table_name='records',
                        record_id=record.id,
                        action='delete',
                        user_id=self.current_user.id,
                        username=self.current_user.full_name,
                        old_values={'record_number': record.record_number, 'title': record.title, 'status': record.status},
                        timestamp=datetime.now()
                    )
                    self.session.add(log_entry)
                except:
                    pass
                
                self.session.delete(record)
                self.session.commit()
                self.load_records()
                self.statusbar.showMessage("Record deleted successfully", 3000)
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to delete record:\n{str(e)}")
    
    def new_template_dialog(self):
        """Open dialog to create new template"""
        dialog = TemplateDialog(self.session, self.current_user, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_templates()
            self.statusbar.showMessage("Template created successfully", 3000)
    
    def edit_template_dialog(self):
        """Open dialog to edit selected template"""
        selected_rows = self.templates_table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select a template to edit")
            return
        
        try:
            template_id = int(self.templates_table.item(self.templates_table.currentRow(), 0).text())
            template = self.session.get(TestTemplate, template_id)
            
            if template:
                dialog = TemplateDialog(self.session, self.current_user, template=template, parent=self)
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    self.load_templates()
                    self.statusbar.showMessage("Template updated successfully", 3000)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to edit template:\n{str(e)}")
    
    def delete_template(self):
        """Delete selected template"""
        selected_rows = self.templates_table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select a template to delete")
            return
        
        try:
            template_id = int(self.templates_table.item(self.templates_table.currentRow(), 0).text())
            template = self.session.get(TestTemplate, template_id)
            
            if not template:
                QMessageBox.warning(self, "Error", "Template not found")
                return
            
            reply = QMessageBox.question(
                self, "Confirm Delete", 
                f"Are you sure you want to delete template '{template.code}'?\n\nThis action cannot be undone.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Audit logging before delete
                try:
                    log_entry = AuditLog(
                        table_name='templates',
                        record_id=template.id,
                        action='delete',
                        user_id=self.current_user.id,
                        username=self.current_user.full_name,
                        old_values={'code': template.code, 'name': template.name, 'version': template.version},
                        timestamp=datetime.now()
                    )
                    self.session.add(log_entry)
                except:
                    pass
                
                self.session.delete(template)
                self.session.commit()
                self.load_templates()
                self.statusbar.showMessage("Template deleted successfully", 3000)
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to delete template:\n{str(e)}")
    
    def export_template(self):
        """Export selected template to Excel"""
        selected_rows = self.templates_table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select a template to export")
            return
        
        try:
            template_id = int(self.templates_table.item(self.templates_table.currentRow(), 0).text())
            template = self.session.get(TestTemplate, template_id)
            
            if not template:
                QMessageBox.warning(self, "Error", "Template not found")
                return
            
            filepath, _ = QFileDialog.getSaveFileName(
                self, "Save Excel File", f"{template.code}_template.xlsx", "Excel Files (*.xlsx)"
            )
            
            if filepath:
                from excel_handler import export_template_to_excel
                export_template_to_excel(template, self.session, filepath)
                QMessageBox.information(self, "Success", f"Template exported to:\n{filepath}")
                self.statusbar.showMessage("Template exported successfully", 3000)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export template:\n{str(e)}")
    
    def new_standard_dialog(self):
        """Open dialog to create new standard"""
        dialog = StandardDialog(self.session, self.current_user, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_standards()
            self.statusbar.showMessage("Standard created successfully", 3000)
    
    def edit_standard_dialog(self):
        """Open dialog to edit selected standard"""
        selected_rows = self.standards_table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select a standard to edit")
            return
        
        try:
            standard_id = int(self.standards_table.item(self.standards_table.currentRow(), 0).text())
            standard = self.session.get(Standard, standard_id)
            
            if standard:
                dialog = StandardDialog(self.session, self.current_user, standard=standard, parent=self)
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    self.load_standards()
                    self.statusbar.showMessage("Standard updated successfully", 3000)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to edit standard:\n{str(e)}")
    
    def delete_standard(self):
        """Delete selected standard"""
        selected_rows = self.standards_table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select a standard to delete")
            return
        
        try:
            standard_id = int(self.standards_table.item(self.standards_table.currentRow(), 0).text())
            standard = self.session.get(Standard, standard_id)
            
            if not standard:
                QMessageBox.warning(self, "Error", "Standard not found")
                return
            
            reply = QMessageBox.question(
                self, "Confirm Delete", 
                f"Are you sure you want to delete standard '{standard.code}'?\n\nThis action cannot be undone.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Audit logging before delete
                try:
                    log_entry = AuditLog(
                        table_name='standards',
                        record_id=standard.id,
                        action='delete',
                        user_id=self.current_user.id,
                        username=self.current_user.full_name,
                        old_values={'code': standard.code, 'name': standard.name, 'version': standard.version},
                        timestamp=datetime.now()
                    )
                    self.session.add(log_entry)
                except:
                    pass
                
                self.session.delete(standard)
                self.session.commit()
                self.load_standards()
                self.statusbar.showMessage("Standard deleted successfully", 3000)
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to delete standard:\n{str(e)}")
    
    def new_nc_dialog(self):
        """Open dialog to create new non-conformance"""
        dialog = NonConformanceDialog(self.session, self.current_user, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_ncs()
            self.statusbar.showMessage("Non-conformance created successfully", 3000)
    
    def edit_nc_dialog(self):
        """Open dialog to edit selected non-conformance"""
        selected_rows = self.nc_table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select a non-conformance to edit")
            return
        
        try:
            nc_id = int(self.nc_table.item(self.nc_table.currentRow(), 0).text())
            nc = self.session.get(NonConformance, nc_id)
            
            if nc:
                dialog = NonConformanceDialog(self.session, self.current_user, nc=nc, parent=self)
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    self.load_ncs()
                    self.statusbar.showMessage("Non-conformance updated successfully", 3000)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to edit non-conformance:\n{str(e)}")
    
    def delete_nc(self):
        """Delete selected non-conformance"""
        selected_rows = self.nc_table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select a non-conformance to delete")
            return
        
        try:
            nc_id = int(self.nc_table.item(self.nc_table.currentRow(), 0).text())
            nc = self.session.get(NonConformance, nc_id)
            
            if not nc:
                QMessageBox.warning(self, "Error", "Non-conformance not found")
                return
            
            reply = QMessageBox.question(
                self, "Confirm Delete", 
                f"Are you sure you want to delete non-conformance '{nc.nc_number}'?\n\nThis action cannot be undone.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Audit logging before delete
                try:
                    log_entry = AuditLog(
                        table_name='non_conformances',
                        record_id=nc.id,
                        action='delete',
                        user_id=self.current_user.id,
                        username=self.current_user.full_name,
                        old_values={'nc_number': nc.nc_number, 'title': nc.title, 'status': nc.status, 'severity': nc.severity},
                        timestamp=datetime.now()
                    )
                    self.session.add(log_entry)
                except:
                    pass
                
                self.session.delete(nc)
                self.session.commit()
                self.load_ncs()
                self.statusbar.showMessage("Non-conformance deleted successfully", 3000)
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to delete non-conformance:\n{str(e)}")
    
    def new_user_dialog(self):
        """Open dialog to create new user (Admin only)"""
        if not self.has_permission('can_manage_users'):
            QMessageBox.warning(self, "Access Denied", "You do not have permission to create users")
            return
        
        dialog = UserDialog(self.session, self.current_user, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_users()
            self.statusbar.showMessage("User created successfully", 3000)
    
    def edit_user_dialog(self):
        """Open dialog to edit selected user (Admin only)"""
        if not self.has_permission('can_manage_users'):
            QMessageBox.warning(self, "Access Denied", "You do not have permission to edit users")
            return
        
        selected_rows = self.users_table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select a user to edit")
            return
        
        try:
            user_id = int(self.users_table.item(self.users_table.currentRow(), 0).text())
            user = self.session.get(User, user_id)
            
            if user:
                dialog = UserDialog(self.session, self.current_user, user=user, parent=self)
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    self.load_users()
                    self.statusbar.showMessage("User updated successfully", 3000)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to edit user:\n{str(e)}")
    
    def delete_user(self):
        """Delete selected user (Admin only)"""
        if not self.has_permission('can_manage_users'):
            QMessageBox.warning(self, "Access Denied", "You do not have permission to delete users")
            return
        
        selected_rows = self.users_table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select a user to delete")
            return
        
        try:
            user_id = int(self.users_table.item(self.users_table.currentRow(), 0).text())
            user = self.session.get(User, user_id)
            
            if not user:
                QMessageBox.warning(self, "Error", "User not found")
                return
            
            # Prevent deleting self
            if user.id == self.current_user.id:
                QMessageBox.warning(self, "Error", "You cannot delete your own account")
                return
            
            reply = QMessageBox.question(
                self, "Confirm Delete", 
                f"Are you sure you want to delete user '{user.username}'?\n\nThis action cannot be undone.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Audit logging before delete
                try:
                    log_entry = AuditLog(
                        table_name='users',
                        record_id=user.id,
                        action='delete',
                        user_id=self.current_user.id,
                        username=self.current_user.full_name,
                        old_values={'username': user.username, 'full_name': user.full_name, 'email': user.email},
                        timestamp=datetime.now()
                    )
                    self.session.add(log_entry)
                except:
                    pass
                
                self.session.delete(user)
                self.session.commit()
                self.load_users()
                self.statusbar.showMessage("User deleted successfully", 3000)
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to delete user:\n{str(e)}")
    
    def open_profile_dialog(self):
        """Open profile dialog"""
        dialog = ProfileDialog(self.session, self.current_user, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Refresh current user
            self.session.refresh(self.current_user)
            self.setup_statusbar()  # Update status bar with new name
            self.statusbar.showMessage("Profile updated successfully", 3000)
    
    def open_company_settings(self):
        """Open company settings dialog"""
        dialog = CompanySettingsDialog(self.session, self.current_user, parent=self)
        dialog.exec()
    
    def open_workflows(self):
        """Open workflow management dialog"""
        dialog = WorkflowDialog(self.session, self.current_user, parent=self)
        dialog.exec()
    
    def open_audit_log(self):
        """Open audit log viewer"""
        dialog = AuditLogDialog(self.session, parent=self)
        dialog.exec()
    
    def open_notifications(self):
        """Open notifications dialog"""
        dialog = NotificationDialog(self.session, self.current_user, parent=self)
        dialog.exec()
    
    def open_documents(self):
        """Open document management dialog"""
        dialog = DocumentDialog(self.session, self.current_user, parent=self)
        dialog.exec()
    
    def open_images(self):
        """Open image attachments dialog"""
        dialog = ImageAttachmentDialog(self.session, self.current_user, parent=self)
        dialog.exec()
    
    def export_records_to_excel(self):
        """Export records to Excel"""
        try:
            filepath, _ = QFileDialog.getSaveFileName(
                self, "Save Excel File", "", "Excel Files (*.xlsx)"
            )
            
            if filepath:
                records = self.session.query(Record).all()
                excel_handler = ExcelHandler(self.session)
                excel_handler.export_records_to_excel(records, filepath)
                
                QMessageBox.information(self, "Success", f"Records exported to:\n{filepath}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export:\n{str(e)}")
    
    def generate_record_pdf(self):
        """Generate PDF for selected record"""
        selected_rows = self.records_table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select a record")
            return
        
        try:
            record_id = int(self.records_table.item(self.records_table.currentRow(), 0).text())
            record = self.session.get(Record, record_id)
            
            filepath, _ = QFileDialog.getSaveFileName(
                self, "Save PDF File", f"{record.record_number}.pdf", "PDF Files (*.pdf)"
            )
            
            if filepath:
                pdf_gen = PDFGenerator(self.session)
                
                # Check if record has attachments
                if record.attachments:
                    print(f"Record has attachments: {record.attachments}")
                else:
                    print("Record has no attachments")
                
                pdf_gen.generate_record_pdf(record, filepath, include_images=True)
                
                QMessageBox.information(self, "Success", f"PDF generated:\n{filepath}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate PDF:\n{str(e)}")
    
    def generate_statistical_report_pdf(self):
        """Generate statistical analysis PDF with charts for selected record"""
        selected_rows = self.records_table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select a record")
            return
        
        try:
            record_id = int(self.records_table.item(self.records_table.currentRow(), 0).text())
            record = self.session.get(Record, record_id)
            
            if not record.template_id:
                QMessageBox.warning(self, "No Template", "Record must have a template for statistical analysis")
                return
            
            filepath, _ = QFileDialog.getSaveFileName(
                self, "Save Statistical Report PDF", f"{record.record_number}_statistics.pdf", "PDF Files (*.pdf)"
            )
            
            if filepath:
                pdf_gen = PDFGenerator(self.session)
                pdf_gen.generate_statistical_report_pdf(record, filepath, include_images=True)
                
                QMessageBox.information(self, "Success", 
                    f"Statistical report generated:\n{filepath}\n\nIncludes charts, statistics, and analysis for each criteria.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate statistical report:\n{str(e)}")
            import traceback
            traceback.print_exc()
    
    def export_record_data_to_excel(self):
        """Export selected record's data (criteria values and statistics) to Excel"""
        selected_rows = self.records_table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select a record to export")
            return
        
        try:
            record_id = int(self.records_table.item(self.records_table.currentRow(), 0).text())
            record = self.session.get(Record, record_id)
            
            if not record.template_id:
                QMessageBox.warning(self, "No Template", "Record must have a template to export data")
                return
            
            filepath, _ = QFileDialog.getSaveFileName(
                self, "Save Excel File", f"{record.record_number}_data.xlsx", "Excel Files (*.xlsx)"
            )
            
            if filepath:
                excel_handler = ExcelHandler(self.session)
                excel_handler.export_record_data(record, filepath)
                
                QMessageBox.information(self, "Success", 
                    f"Record data exported to:\n{filepath}\n\nIncludes criteria names, values, and statistics.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export data:\n{str(e)}")
            import traceback
            traceback.print_exc()
    
    def generate_date_range_statistical_report(self):
        """Generate statistical report for records in a date range"""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QComboBox, QDateEdit, QDialogButtonBox
        from PyQt6.QtCore import QDate
        
        # Create dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Date Range Statistical Report")
        dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout()
        dialog.setLayout(layout)
        
        # Template selection
        layout.addWidget(QLabel("Select Template:"))
        template_combo = QComboBox()
        templates = self.session.query(TestTemplate).order_by(TestTemplate.name).all()
        for template in templates:
            template_combo.addItem(template.name, template.id)
        layout.addWidget(template_combo)
        
        # Date range
        layout.addWidget(QLabel("\nFrom Date:"))
        from_date = QDateEdit()
        from_date.setCalendarPopup(True)
        from_date.setDate(QDate.currentDate().addMonths(-3))  # Default: 3 months ago
        layout.addWidget(from_date)
        
        layout.addWidget(QLabel("To Date:"))
        to_date = QDateEdit()
        to_date.setCalendarPopup(True)
        to_date.setDate(QDate.currentDate())
        layout.addWidget(to_date)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        # Show dialog
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                template_id = template_combo.currentData()
                start_date = from_date.date().toPyDate()
                end_date = to_date.date().toPyDate()
                
                # Get records in date range
                from datetime import datetime, timedelta
                start_datetime = datetime.combine(start_date, datetime.min.time())
                end_datetime = datetime.combine(end_date, datetime.max.time())
                
                records = self.session.query(Record).filter(
                    Record.template_id == template_id,
                    Record.created_at >= start_datetime,
                    Record.created_at <= end_datetime
                ).order_by(Record.created_at).all()
                
                if not records:
                    QMessageBox.warning(self, "No Data", 
                        f"No records found for the selected template in date range\n"
                        f"{start_date} to {end_date}")
                    return
                
                # Ask for output file
                template = self.session.get(TestTemplate, template_id)
                default_filename = f"{template.name}_stats_{start_date}_to_{end_date}.pdf"
                filepath, _ = QFileDialog.getSaveFileName(
                    self, "Save Statistical Report PDF", default_filename, "PDF Files (*.pdf)"
                )
                
                if filepath:
                    pdf_gen = PDFGenerator(self.session)
                    # Use first record as reference, but data will come from all records
                    pdf_gen.generate_date_range_statistical_report(
                        template_id, start_date, end_date, records, filepath
                    )
                    
                    QMessageBox.information(self, "Success", 
                        f"Date range statistical report generated:\n{filepath}\n\n"
                        f"Analyzed {len(records)} records from {start_date} to {end_date}")
                        
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to generate report:\n{str(e)}")
                import traceback
                traceback.print_exc()
    
    def generate_nc_pdf(self):
        """Generate PDF for selected NC"""
        selected_rows = self.nc_table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select a non-conformance")
            return
        
        try:
            nc_id = int(self.nc_table.item(self.nc_table.currentRow(), 0).text())
            nc = self.session.get(NonConformance, nc_id)
            
            filepath, _ = QFileDialog.getSaveFileName(
                self, "Save PDF File", f"{nc.nc_number}.pdf", "PDF Files (*.pdf)"
            )
            
            if filepath:
                pdf_gen = PDFGenerator(self.session)
                pdf_gen.generate_nc_pdf(nc, filepath)
                
                QMessageBox.information(self, "Success", f"PDF generated:\n{filepath}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate PDF:\n{str(e)}")
    
    def generate_standard_pdf(self):
        """Generate PDF for selected standard with all sections and criteria"""
        selected_rows = self.standards_table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select a standard")
            return
        
        try:
            standard_id = int(self.standards_table.item(self.standards_table.currentRow(), 0).text())
            standard = self.session.get(Standard, standard_id)
            
            filepath, _ = QFileDialog.getSaveFileName(
                self, "Save PDF File", f"{standard.code}_{standard.version}.pdf", "PDF Files (*.pdf)"
            )
            
            if filepath:
                pdf_gen = PDFGenerator(self.session)
                pdf_gen.generate_standard_pdf(standard, filepath)
                
                QMessageBox.information(self, "Success", 
                    f"Standard PDF generated:\n{filepath}\n\n"
                    f"Includes all sections, criteria, and documentation.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate PDF:\n{str(e)}")
            import traceback
            traceback.print_exc()
    
    def import_standards_from_excel(self):
        """Import standards from Excel"""
        try:
            filepath, _ = QFileDialog.getOpenFileName(
                self, "Open Excel File", "", "Excel Files (*.xlsx *.xls)"
            )
            
            if filepath:
                excel_handler = ExcelHandler(self.session)
                standards = excel_handler.import_standards_from_excel(filepath, self.current_user.id)
                
                QMessageBox.information(self, "Success", 
                                       f"Imported {len(standards)} standards")
                self.load_standards()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to import:\n{str(e)}")
    
    def generate_compliance_report(self):
        """Generate compliance report"""
        try:
            reports_gen = ReportsGenerator(self.session)
            report = reports_gen.compliance_summary_report()
            
            # Show report in message box (in production, use a better display)
            report_text = f"""
Compliance Summary Report
========================

Total Records: {report['total_records']}
Passed: {report['passed']}
Failed: {report['failed']}
Pending: {report['pending']}
Pass Rate: {report['pass_rate']}%
Average Score: {report['average_score']}%

Status Breakdown:
{'\n'.join(f'{k}: {v}' for k, v in report['status_breakdown'].items())}
            """
            
            QMessageBox.information(self, "Compliance Report", report_text)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate report:\n{str(e)}")
    
    def generate_trend_report(self):
        """Generate trend analysis report"""
        try:
            reports_gen = ReportsGenerator(self.session)
            report = reports_gen.trend_analysis_report(period='month', limit=12)
            
            # Format report
            trends_text = "\n".join(
                f"{item['period']}: {item['total_records']} records, "
                f"Pass Rate: {item['pass_rate']}%, Avg Score: {item['avg_score']}%"
                for item in report.get('trends', [])
            )
            
            report_text = f"""
Trend Analysis Report
===================

Period: Monthly (Last 12 Months)

Trends:
{trends_text}

Summary:
- Total Records: {report.get('total_records', 0)}
- Average Pass Rate: {report.get('avg_pass_rate', 0)}%
- Trend Direction: {'Improving' if report.get('trend_direction') == 'up' else 'Declining' if report.get('trend_direction') == 'down' else 'Stable'}
            """
            
            QMessageBox.information(self, "Trend Analysis Report", report_text)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate report:\n{str(e)}")
    
    def generate_nc_report(self):
        """Generate NC summary report"""
        try:
            reports_gen = ReportsGenerator(self.session)
            report = reports_gen.nc_summary_report()
            
            # Format report
            severity_text = "\n".join(
                f"  {k}: {v}"
                for k, v in report.get('severity_breakdown', {}).items()
            )
            
            status_text = "\n".join(
                f"  {k}: {v}"
                for k, v in report.get('status_breakdown', {}).items()
            )
            
            report_text = f"""
Non-Conformance Summary Report
============================

Total NCs: {report.get('total_ncs', 0)}
Open: {report.get('open', 0)}
Closed: {report.get('closed', 0)}
Overdue: {report.get('overdue', 0)}

Severity Breakdown:
{severity_text}

Status Breakdown:
{status_text}

Avg Resolution Time: {report.get('avg_resolution_days', 0)} days
Closure Rate: {report.get('closure_rate', 0)}%
            """
            
            QMessageBox.information(self, "NC Summary Report", report_text)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate report:\n{str(e)}")
    
    def generate_inspector_report(self):
        """Generate inspector performance report"""
        try:
            reports_gen = ReportsGenerator(self.session)
            report = reports_gen.inspector_performance_report()
            
            # Format report
            inspectors_text = "\n".join(
                f"  {item['inspector']}: {item['total_records']} records, "
                f"Pass Rate: {item['pass_rate']}%, Avg Score: {item['avg_score']}%"
                for item in report.get('inspectors', [])[:10]  # Top 10
            )
            
            report_text = f"""
Inspector Performance Report
=========================

Total Inspectors: {len(report.get('inspectors', []))}

Top Performers:
{inspectors_text}

Overall Statistics:
- Total Records: {sum(i['total_records'] for i in report.get('inspectors', []))}
- Average Pass Rate: {report.get('overall_pass_rate', 0)}%
- Average Score: {report.get('overall_avg_score', 0)}%
            """
            
            QMessageBox.information(self, "Inspector Performance Report", report_text)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate report:\n{str(e)}")
    
    def backup_database(self):
        """Backup database (Admin only)"""
        if not self.is_admin():
            QMessageBox.warning(self, "Access Denied", "Only administrators can backup the database")
            return
        
        try:
            from database import db_manager
            
            backup_path = db_manager.backup_database()
            QMessageBox.information(self, "Success", 
                                   f"Database backed up to:\n{backup_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to backup:\n{str(e)}")
    
    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(self, "About Quality Management System",
                         f"""
Quality Management System v{__version__}

A comprehensive multiplatform desktop application for managing:
- Quality inspections and records
- Standards and compliance criteria
- Test templates and forms
- Non-conformance tracking
- Reporting and analytics

Features:
✓ Excel import/export
✓ PDF report generation
✓ Image attachments
✓ Comprehensive reporting

© 2026 Quality Management System
                         """)
    
    def closeEvent(self, event):
        """Handle application close"""
        reply = QMessageBox.question(self, "Exit",
                                     "Are you sure you want to exit?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            # Close database session
            if self.session:
                self.session.close()
            event.accept()
        else:
            event.ignore()


def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    # Set light palette for consistent appearance across platforms
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(240, 240, 240))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(0, 0, 0))
    palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(245, 245, 245))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 220))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(0, 0, 0))
    palette.setColor(QPalette.ColorRole.Text, QColor(0, 0, 0))
    palette.setColor(QPalette.ColorRole.Button, QColor(240, 240, 240))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(0, 0, 0))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
    palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    app.setPalette(palette)
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
