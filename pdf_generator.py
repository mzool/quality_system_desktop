"""
PDF Generation Handler for Quality System
Generate professional PDF reports for records, non-conformances, and custom reports
"""
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    PageBreak, Image as RLImage, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfgen import canvas
from datetime import datetime
from pathlib import Path
from typing import List
from models import *
import os
import tempfile
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
from matplotlib.figure import Figure


class PDFGenerator:
    """Generate PDF reports for quality system"""
    
    def __init__(self, session=None):
        """Initialize PDF generator
        
        Args:
            session: SQLAlchemy session for database access
        """
        self.session = session
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        self.company_settings = None
        self.logo_temp_path = None
        
        # Load company settings if session provided
        if self.session:
            try:
                from models import CompanySettings
                self.company_settings = self.session.query(CompanySettings).first()
                
                # Save logo to temporary file if it exists
                if self.company_settings and self.company_settings.company_logo:
                    import tempfile
                    temp_dir = tempfile.gettempdir()
                    self.logo_temp_path = os.path.join(temp_dir, f"company_logo_{os.getpid()}.png")
                    with open(self.logo_temp_path, 'wb') as f:
                        f.write(self.company_settings.company_logo)
            except Exception as e:
                print(f"Warning: Could not load company settings: {e}")
    
    def __del__(self):
        """Cleanup temporary logo file"""
        if self.logo_temp_path and os.path.exists(self.logo_temp_path):
            try:
                os.remove(self.logo_temp_path)
            except:
                pass
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles"""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1f4788'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Subtitle style
        self.styles.add(ParagraphStyle(
            name='CustomSubtitle',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#2f3542'),
            spaceAfter=12,
            fontName='Helvetica-Bold'
        ))
        
        # Section header
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading3'],
            fontSize=12,
            textColor=colors.HexColor('#2f3542'),
            spaceAfter=6,
            spaceBefore=12,
            fontName='Helvetica-Bold',
            backColor=colors.HexColor('#E7E6E6')
        ))
    
    @staticmethod
    def format_number(num):
        """Format number to remove trailing zeros
        
        Examples:
            44.0 -> '44'
            44.03 -> '44.03'
            44.000000 -> '44'
            44.123456 -> '44.123456'
        """
        if num is None:
            return 'N/A'
        try:
            num_float = float(num)
            if num_float == int(num_float):
                return str(int(num_float))
            else:
                return f'{num_float:.10g}'  # Remove trailing zeros
        except (ValueError, TypeError):
            return str(num)
        
        # Info label
        self.styles.add(ParagraphStyle(
            name='InfoLabel',
            parent=self.styles['Normal'],
            fontSize=10,
            fontName='Helvetica-Bold'
        ))
        
        # Info value
        self.styles.add(ParagraphStyle(
            name='InfoValue',
            parent=self.styles['Normal'],
            fontSize=10,
            fontName='Helvetica'
        ))
    
    def _create_header_footer(self, canvas_obj, doc):
        """Create header and footer for each page"""
        canvas_obj.saveState()
        
        # Header
        y_position = doc.height + doc.topMargin + 0.3*inch
        x_position = inch
        
        # Draw company logo if available
        if self.logo_temp_path and os.path.exists(self.logo_temp_path):
            try:
                # Scale logo to fit header (max 0.5 inch height)
                from reportlab.lib.utils import ImageReader
                img = ImageReader(self.logo_temp_path)
                img_width, img_height = img.getSize()
                
                # Scale to max 0.5 inch height while maintaining aspect ratio
                max_height = 0.5 * inch
                scale_factor = max_height / img_height
                logo_width = img_width * scale_factor
                logo_height = max_height
                
                # Draw logo on left side
                canvas_obj.drawImage(
                    self.logo_temp_path,
                    x_position,
                    y_position - logo_height,
                    width=logo_width,
                    height=logo_height,
                    preserveAspectRatio=True,
                    mask='auto'
                )
                
                # Adjust x position for text to appear next to logo
                x_position += logo_width + 0.2*inch
                
            except Exception as e:
                print(f"Warning: Could not load logo in PDF: {e}")
        
        # Draw company name if available
        if self.company_settings and self.company_settings.company_name:
            canvas_obj.setFont('Helvetica-Bold', 12)
            canvas_obj.setFillColor(colors.HexColor('#1f4788'))
            canvas_obj.drawString(x_position, y_position, 
                                 self.company_settings.company_name)
            
            # Draw "Quality Management System" below company name
            canvas_obj.setFont('Helvetica-Bold', 10)
            canvas_obj.setFillColor(colors.HexColor('#2f3542'))
            canvas_obj.drawString(x_position, y_position - 0.15*inch, 
                                 "Quality Management System")
        else:
            # No company settings - use default header
            canvas_obj.setFont('Helvetica-Bold', 10)
            canvas_obj.setFillColor(colors.HexColor('#2f3542'))
            canvas_obj.drawString(x_position, y_position, 
                                 "Quality Management System")
        
        # Footer
        canvas_obj.setFont('Helvetica', 8)
        canvas_obj.setFillColor(colors.gray)
        
        # Left side: Generated date
        footer_text = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # Add company info to footer if available
        if self.company_settings:
            footer_parts = []
            if self.company_settings.phone:
                footer_parts.append(f"Phone: {self.company_settings.phone}")
            if self.company_settings.email:
                footer_parts.append(f"Email: {self.company_settings.email}")
            if self.company_settings.website:
                footer_parts.append(self.company_settings.website)
            
            if footer_parts:
                footer_text += "  |  " + " | ".join(footer_parts)
        
        canvas_obj.drawString(inch, 0.5*inch, footer_text)
        
        # Right side: Page number
        canvas_obj.drawRightString(doc.width + inch, 0.5*inch, 
                                   f"Page {doc.page}")
        
        canvas_obj.restoreState()
    
    def generate_record_pdf(self, record: Record, filepath: str, include_images: bool = True) -> str:
        """
        Generate comprehensive PDF report for a record
        
        Args:
            record: Record object
            filepath: Output PDF file path
            include_images: Whether to include images in the report
            
        Returns:
            Path to generated PDF file
        """
        # Create PDF document
        doc = SimpleDocTemplate(
            filepath,
            pagesize=A4,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=1*inch,
            bottomMargin=0.75*inch
        )
        
        # Container for PDF elements
        elements = []
        
        # ====================================================================
        # TITLE PAGE
        # ====================================================================
        
        # Title
        title = Paragraph(f"Inspection Report<br/>{record.record_number}", 
                         self.styles['CustomTitle'])
        elements.append(title)
        elements.append(Spacer(1, 0.2*inch))
        
        # Status badge
        status_color = {
            'approved': colors.green,
            'rejected': colors.red,
            'under_review': colors.orange,
            'draft': colors.gray
        }.get(record.status, colors.black)
        
        status_text = f"<font color='{status_color}' size='14'><b>Status: {record.status.upper()}</b></font>"
        elements.append(Paragraph(status_text, self.styles['Normal']))
        elements.append(Spacer(1, 0.3*inch))
        
        # ====================================================================
        # RECORD SUMMARY
        # ====================================================================
        
        elements.append(Paragraph("Record Summary", self.styles['CustomSubtitle']))
        
        summary_data = [
            ['Record Number:', record.record_number],
            ['Title:', record.title or 'N/A'],
            ['Template:', record.template.name if record.template else 'N/A'],
            ['Standard:', record.standard.name if record.standard else 'N/A'],
            ['Category:', record.category or 'N/A'],
            ['Priority:', record.priority or 'N/A'],
            ['', ''],  # Spacer
            ['Batch Number:', record.batch_number or 'N/A'],
            ['Product ID:', record.product_id or 'N/A'],
            ['Location:', record.location or 'N/A'],
            ['Department:', record.department or 'N/A'],
            ['Shift:', record.shift or 'N/A'],
            ['', ''],  # Spacer
            ['Created By:', record.creator.full_name if record.creator else 'N/A'],
            ['Assigned To:', record.assignee.full_name if record.assignee else 'N/A'],
            ['Approved By:', record.approver.full_name if record.approver else 'Pending'],
            ['', ''],  # Spacer
            ['Scheduled Date:', record.scheduled_date.strftime('%Y-%m-%d %H:%M') if record.scheduled_date else 'N/A'],
            ['Started At:', record.started_at.strftime('%Y-%m-%d %H:%M') if record.started_at else 'N/A'],
            ['Completed At:', record.completed_at.strftime('%Y-%m-%d %H:%M') if record.completed_at else 'N/A'],
            ['Due Date:', record.due_date.strftime('%Y-%m-%d %H:%M') if record.due_date else 'N/A'],
        ]
        
        summary_table = Table(summary_data, colWidths=[2*inch, 4*inch])
        summary_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F0F0F0')),
        ]))
        
        elements.append(summary_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # ====================================================================
        # COMPLIANCE SUMMARY
        # ====================================================================
        
        elements.append(Paragraph("Compliance Summary", self.styles['CustomSubtitle']))
        
        compliance_color = colors.green if record.overall_compliance else colors.red if record.overall_compliance is not None else colors.gray
        compliance_text = 'PASS' if record.overall_compliance else 'FAIL' if record.overall_compliance is not None else 'N/A'
        
        compliance_data = [
            ['Overall Compliance:', compliance_text],
            ['Compliance Score:', f"{record.compliance_score}%" if record.compliance_score else 'N/A'],
            ['Failed Items:', str(record.failed_items_count or 0)],
            ['Total Items:', str(len(record.items))],
        ]
        
        compliance_table = Table(compliance_data, colWidths=[2*inch, 4*inch])
        compliance_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E7E6E6')),
            ('BACKGROUND', (1, 0), (1, 0), compliance_color),
            ('TEXTCOLOR', (1, 0), (1, 0), colors.white),
        ]))
        
        elements.append(compliance_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # ====================================================================
        # DETAILED RESULTS
        # ====================================================================
        
        if record.items:
            elements.append(PageBreak())
            elements.append(Paragraph("Detailed Inspection Results", self.styles['CustomSubtitle']))
            elements.append(Spacer(1, 0.2*inch))
            
            # Table headers
            results_data = [[
                Paragraph('<b>Code</b>', self.styles['Normal']),
                Paragraph('<b>Criteria</b>', self.styles['Normal']),
                Paragraph('<b>Value</b>', self.styles['Normal']),
                Paragraph('<b>Limits</b>', self.styles['Normal']),
                Paragraph('<b>Compliance</b>', self.styles['Normal']),
                Paragraph('<b>Remarks</b>', self.styles['Normal'])
            ]]
            
            for item in record.items:
                criteria = item.criteria
                
                # Format limits
                limits = 'N/A'
                if criteria and criteria.limit_min and criteria.limit_max:
                    limits = f"{self.format_number(criteria.limit_min)} - {self.format_number(criteria.limit_max)}"
                    if criteria.unit:
                        limits += f" {criteria.unit}"
                elif criteria and criteria.limit_min:
                    limits = f"≥ {self.format_number(criteria.limit_min)}"
                    if criteria.unit:
                        limits += f" {criteria.unit}"
                elif criteria and criteria.limit_max:
                    limits = f"≤ {self.format_number(criteria.limit_max)}"
                    if criteria.unit:
                        limits += f" {criteria.unit}"
                
                # Compliance status
                compliance_status = '✓ PASS' if item.compliance else '✗ FAIL' if item.compliance is not None else '-'
                
                # Value with unit
                value_display = item.value or 'N/A'
                if item.numeric_value is not None:
                    value_display = self.format_number(item.numeric_value)
                    if criteria and criteria.unit:
                        value_display += f" {criteria.unit}"
                
                # Use Paragraph for text wrapping
                row = [
                    Paragraph(criteria.code if criteria else '', self.styles['Normal']),
                    Paragraph(criteria.title if criteria else '', self.styles['Normal']),
                    Paragraph(str(value_display), self.styles['Normal']),
                    Paragraph(str(limits), self.styles['Normal']),
                    Paragraph(compliance_status, self.styles['Normal']),
                    Paragraph(item.remarks or '', self.styles['Normal'])
                ]
                results_data.append(row)
            
            # Create table with dynamic row colors
            results_table = Table(results_data, colWidths=[0.8*inch, 2*inch, 1.2*inch, 1.2*inch, 0.9*inch, 1.4*inch])
            
            # Build table style
            table_style = [
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2f3542')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (4, 0), (4, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ]
            
            # Color code compliance column
            for i, item in enumerate(record.items, 1):
                if item.compliance is True:
                    table_style.append(('BACKGROUND', (4, i), (4, i), colors.HexColor('#C6EFCE')))
                    table_style.append(('TEXTCOLOR', (4, i), (4, i), colors.HexColor('#006100')))
                elif item.compliance is False:
                    table_style.append(('BACKGROUND', (4, i), (4, i), colors.HexColor('#FFC7CE')))
                    table_style.append(('TEXTCOLOR', (4, i), (4, i), colors.HexColor('#9C0006')))
            
            results_table.setStyle(TableStyle(table_style))
            elements.append(results_table)
        
        # ====================================================================
        # NOTES AND COMMENTS
        # ====================================================================
        
        if record.notes:
            elements.append(Spacer(1, 0.3*inch))
            elements.append(Paragraph("Notes", self.styles['SectionHeader']))
            notes_para = Paragraph(record.notes.replace('\n', '<br/>'), self.styles['Normal'])
            elements.append(notes_para)
        
        # ====================================================================
        # SIGNATURES
        # ====================================================================
        
        elements.append(Spacer(1, 0.5*inch))
        elements.append(Paragraph("Signatures", self.styles['CustomSubtitle']))
        
        sig_data = [
            ['Inspector:', '', 'Date:', ''],
            [record.creator.full_name if record.creator else '_____________', '', 
             record.completed_at.strftime('%Y-%m-%d') if record.completed_at else '_____________', ''],
            ['', '', '', ''],
            ['Approved By:', '', 'Date:', ''],
            [record.approver.full_name if record.approver else '_____________', '',
             record.updated_at.strftime('%Y-%m-%d') if record.approver else '_____________', '']
        ]
        
        sig_table = Table(sig_data, colWidths=[1.5*inch, 2*inch, 0.8*inch, 1.2*inch])
        sig_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 3), (0, 3), 'Helvetica-Bold'),
            ('FONTNAME', (2, 3), (2, 3), 'Helvetica-Bold'),
            ('LINEABOVE', (0, 1), (1, 1), 1, colors.black),
            ('LINEABOVE', (2, 1), (3, 1), 1, colors.black),
            ('LINEABOVE', (0, 4), (1, 4), 1, colors.black),
            ('LINEABOVE', (2, 4), (3, 4), 1, colors.black),
        ]))
        
        elements.append(sig_table)
        
        # ====================================================================
        # ATTACHMENTS (IMAGES)
        # ====================================================================
        
        if include_images and self.session:
            try:
                # Query ImageAttachment table for images linked to this record
                from models import ImageAttachment
                image_attachments = self.session.query(ImageAttachment).filter(
                    ImageAttachment.entity_type == 'record',
                    ImageAttachment.entity_id == record.id
                ).all()
                
                if image_attachments:
                    print(f"Found {len(image_attachments)} images for record {record.id}")
                    elements.append(PageBreak())
                    elements.append(Paragraph("Attached Images", self.styles['CustomSubtitle']))
                    elements.append(Spacer(1, 0.2*inch))
                    
                    for idx, img_attachment in enumerate(image_attachments, 1):
                        att_path = img_attachment.file_path
                        att_name = img_attachment.description or img_attachment.filename or f'Image {idx}'
                        
                        # Verify file exists
                        if not att_path or not os.path.exists(att_path):
                            print(f"Image file not found: {att_path}")
                            elements.append(Paragraph(
                                f"<i>Figure {idx}: {att_name} (File not found)</i>",
                                self.styles['Normal']
                            ))
                            elements.append(Spacer(1, 0.2*inch))
                            continue
                        
                        # Add image caption
                        caption = Paragraph(f"<b>Figure {idx}: {att_name}</b>", self.styles['Normal'])
                        elements.append(caption)
                        elements.append(Spacer(1, 0.1*inch))
                        
                        # Add the image with proper dimensions
                        try:
                            from PIL import Image as PILImage
                            
                            # Read image dimensions
                            with PILImage.open(att_path) as pil_img:
                                img_width, img_height = pil_img.size
                            
                            # Calculate scaled dimensions to fit in page
                            max_width = 5.5 * inch
                            max_height = 4 * inch
                            
                            # Calculate aspect ratio
                            aspect = img_width / img_height
                            
                            if img_width > max_width:
                                img_width = max_width
                                img_height = img_width / aspect
                            
                            if img_height > max_height:
                                img_height = max_height
                                img_width = img_height * aspect
                            
                            # Create and add image
                            print(f"Adding image to PDF: {att_path} ({img_width:.1f}x{img_height:.1f})")
                            img = RLImage(att_path, width=float(img_width), height=float(img_height))
                            elements.append(img)
                            print(f"Image added successfully")
                            
                        except Exception as e:
                            print(f"Error rendering image {att_path}: {str(e)}")
                            import traceback
                            traceback.print_exc()
                            error_text = Paragraph(
                                f"<i>Could not render image: {str(e)}</i>",
                                self.styles['Normal']
                            )
                            elements.append(error_text)
                        
                        elements.append(Spacer(1, 0.3*inch))
                else:
                    print(f"No images found for record {record.id}")
                        
            except Exception as e:
                print(f"Error querying/adding images to PDF: {e}")
                import traceback
                traceback.print_exc()

        # ====================================================================
        # STANDARD ATTACHMENTS (if applicable)
        # ====================================================================
        if record.standard and self.session:
            try:
                std_images = self.session.query(ImageAttachment).filter(
                    ImageAttachment.entity_type == 'standard',
                    ImageAttachment.entity_id == record.standard.id
                ).all()
                
                if std_images:
                    elements.append(PageBreak())
                    elements.append(Paragraph(f"Standard References: {record.standard.name}", self.styles['CustomSubtitle']))
                    elements.append(Spacer(1, 0.2*inch))
                    
                    for s_img in std_images:
                        s_img_path = s_img.file_path
                        if s_img_path and os.path.exists(s_img_path):
                            elements.append(Paragraph(f"<b>Standard Reference:</b> {s_img.description or s_img.filename}", self.styles['Normal']))
                            elements.append(Spacer(1, 0.1*inch))
                            
                            try:
                                from reportlab.lib.utils import ImageReader
                                r_img = ImageReader(s_img_path)
                                w, h = r_img.getSize()
                                aspect = h / float(w)
                                
                                img_w = 5.5 * inch
                                img_h = img_w * aspect
                                
                                if img_h > 4 * inch:
                                    img_h = 4 * inch
                                    img_w = img_h / aspect
                                    
                                elements.append(RLImage(s_img_path, width=img_w, height=img_h))
                                elements.append(Spacer(1, 0.4*inch))
                            except Exception as e:
                                print(f"Error rendering standard image: {e}")
            except Exception as e:
                print(f"Error adding standard images to record PDF: {e}")
        
        # ====================================================================
        # BUILD PDF
        # ====================================================================
        
        doc.build(elements, onFirstPage=self._create_header_footer, 
                 onLaterPages=self._create_header_footer)
        
        return filepath
    
    def generate_statistical_report_pdf(self, record: Record, filepath: str, include_images: bool = True) -> str:
        """
        Generate statistical analysis PDF report with charts for record data
        
        Args:
            record: Record object (used to get template and standard)
            filepath: Output PDF file path
            include_images: Whether to include images at the end
            
        Returns:
            Path to generated PDF file
        """
        doc = SimpleDocTemplate(
            filepath,
            pagesize=A4,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=1*inch,
            bottomMargin=0.75*inch
        )
        
        elements = []
        
        # ====================================================================
        # INTRODUCTION PAGE
        # ====================================================================
        
        title = Paragraph(f"Statistical Quality Report", self.styles['CustomTitle'])
        elements.append(title)
        elements.append(Spacer(1, 0.2*inch))
        
        if record.template:
            template = record.template
            
            # Template info
            intro_data = [
                ['Template Name:', Paragraph(template.name or 'N/A', self.styles['Normal'])],
                ['Template Code:', template.code or 'N/A'],
                ['Category:', template.category or 'N/A'],
                ['Version:', template.version or 'N/A'],
                ['Standard:', record.standard.name if record.standard else 'N/A'],
            ]
            
            if template.description:
                intro_data.append(['', ''])
                intro_data.append(['Description:', Paragraph(template.description, self.styles['Normal'])])
            
            intro_table = Table(intro_data, colWidths=[2*inch, 4.5*inch])
            intro_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F0F0F0')),
            ]))
            
            elements.append(intro_table)
            elements.append(Spacer(1, 0.3*inch))
            
            # Summary of analysis
            elements.append(Paragraph("Statistical Analysis Overview", self.styles['CustomSubtitle']))
            elements.append(Spacer(1, 0.1*inch))
            
            overview_text = """
            This report provides comprehensive statistical analysis for each inspection criteria. 
            For each criterion, data is collected from multiple records using the same template, 
            and the following analyses are performed:
            <br/><br/>
            <b>Statistical Measures:</b>
            <br/>• Range: Difference between maximum and minimum values
            <br/>• Average (X̄): Mean of all measurements
            <br/>• Standard Deviation (σ): Measure of variation or dispersion
            <br/><br/>
            <b>Control Charts:</b>
            <br/>• Line Chart: Trend of values over time
            <br/>• X-bar Chart: Average values with control limits
            <br/>• R Chart: Range control chart for process variation
            """
            
            elements.append(Paragraph(overview_text, self.styles['Normal']))
        
        elements.append(PageBreak())
        
        # ====================================================================
        # STATISTICAL ANALYSIS FOR EACH CRITERIA
        # ====================================================================
        
        if record.template_id and self.session:
            # Get all template fields for this template
            template_fields = self.session.query(TemplateField).filter_by(
                template_id=record.template_id
            ).order_by(TemplateField.sort_order).all()
            
            # Get all records for this template (for statistical analysis)
            # Include all statuses, not just completed
            all_records = self.session.query(Record).filter_by(
                template_id=record.template_id
            ).order_by(Record.created_at.desc()).limit(100).all()  # Limit to last 100 records
            
            # Reverse to get chronological order for charts
            all_records.reverse()
            
            print(f"Found {len(all_records)} records for template {record.template_id}")
            print(f"Template has {len(template_fields)} fields")
            
            total_charts_generated = 0
            if all_records and template_fields:
                for field in template_fields:
                    if not field.criteria:
                        continue
                    
                    criteria = field.criteria
                    print(f"Processing criteria: {criteria.code} (type: {criteria.data_type})")
                    
                    # Skip non-numeric criteria
                    if criteria.data_type != 'numeric':
                        print(f"  Skipping - not numeric")
                        continue
                    
                    # Collect values for this criteria across all records
                    values = []
                    dates = []
                    record_numbers = []
                    
                    for rec in all_records:
                        for item in rec.items:
                            if item.criteria_id == criteria.id and item.numeric_value is not None:
                                values.append(float(item.numeric_value))
                                dates.append(rec.completed_at or rec.created_at)
                                record_numbers.append(rec.record_number)
                    
                    print(f"  Found {len(values)} values for {criteria.code}")
                    
                    if len(values) < 2:
                        print(f"  Skipping - need at least 2 values, only have {len(values)}")
                        continue  # Need at least 2 values for statistics
                    
                    # ====================================================================
                    # PAGE FOR THIS CRITERIA
                    # ====================================================================
                    
                    elements.append(Paragraph(f"Criterion: {criteria.code} - {criteria.title}", 
                                             self.styles['CustomSubtitle']))
                    elements.append(Spacer(1, 0.1*inch))
                    
                    # Calculate statistics
                    values_array = np.array(values)
                    mean_val = np.mean(values_array)
                    std_val = np.std(values_array, ddof=1) if len(values) > 1 else 0
                    range_val = np.max(values_array) - np.min(values_array)
                    min_val = np.min(values_array)
                    max_val = np.max(values_array)
                    
                    # Statistics table
                    stats_data = [
                        ['Statistic', 'Value'],
                        ['Number of Samples', str(len(values))],
                        ['Average (X̄)', self.format_number(mean_val)],
                        ['Std Deviation (σ)', self.format_number(std_val)],
                        ['Range (R)', self.format_number(range_val)],
                        ['Minimum', self.format_number(min_val)],
                        ['Maximum', self.format_number(max_val)],
                    ]
                    
                    if criteria.unit:
                        stats_data[0].append('Unit')
                        for i in range(1, len(stats_data)):
                            if i == 1:
                                stats_data[i].append('-')
                            else:
                                stats_data[i].append(criteria.unit)
                    
                    if criteria.limit_min is not None:
                        stats_data.append(['Lower Limit', f'{criteria.limit_min}', criteria.unit or '-'])
                    if criteria.limit_max is not None:
                        stats_data.append(['Upper Limit', f'{criteria.limit_max}', criteria.unit or '-'])
                    
                    stats_table = Table(stats_data, colWidths=[2*inch, 1.5*inch, 1*inch] if criteria.unit else [2.5*inch, 2*inch])
                    stats_table.setStyle(TableStyle([
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, -1), 9),
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2f3542')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#E7E6E6')]),
                    ]))
                    
                    elements.append(stats_table)
                    elements.append(Spacer(1, 0.2*inch))
                    
                    # Generate charts
                    print(f"Generating charts for criteria {criteria.code}...")
                    chart_paths = self._generate_statistical_charts(
                        values, dates, record_numbers, criteria, mean_val, std_val
                    )
                    print(f"Generated {len(chart_paths)} charts")
                    
                    # Add charts to PDF
                    charts_added = 0
                    for chart_path in chart_paths:
                        print(f"Checking chart: {chart_path}")
                        if os.path.exists(chart_path):
                            try:
                                print(f"Adding chart to PDF: {chart_path}")
                                img = RLImage(chart_path, width=6*inch, height=3.5*inch)
                                elements.append(img)
                                elements.append(Spacer(1, 0.15*inch))
                                charts_added += 1
                            except Exception as e:
                                print(f"Error adding chart to PDF: {e}")
                                error_text = Paragraph(f"<i>Error loading chart: {str(e)}</i>", 
                                                     self.styles['Normal'])
                                elements.append(error_text)
                        else:
                            print(f"Chart file does not exist: {chart_path}")
                            error_text = Paragraph(f"<i>Chart file not found: {os.path.basename(chart_path)}</i>", 
                                                 self.styles['Normal'])
                            elements.append(error_text)
                    
                    print(f"Successfully added {charts_added} charts for {criteria.code}")
                    total_charts_generated += charts_added
                    
                    elements.append(PageBreak())
                
                # After the loop
                if total_charts_generated == 0:
                    print("WARNING: No charts were generated!")
                    elements.append(Paragraph("<i>No statistical charts could be generated. "
                                            "This may be because there are fewer than 2 numeric values "
                                            "for each criterion, or no numeric criteria are defined.</i>",
                                            self.styles['Normal']))
            else:
                elements.append(Paragraph("<i>No data found for statistical analysis.</i>",
                                        self.styles['Normal']))
        else:
            elements.append(Paragraph("<i>Record has no template ID or session is missing.</i>",
                                    self.styles['Normal']))
        
        # ====================================================================
        # IMAGES SECTION (Record & Standard Attachments)
        # ====================================================================
        if include_images and self.session:
            try:
                # 1. Check ImageAttachment table for record-linked images
                image_attachments = self.session.query(ImageAttachment).filter(
                    ImageAttachment.entity_type == 'record',
                    ImageAttachment.entity_id == record.id
                ).all()
                
                # 2. Check ImageAttachment table for standard-linked images
                if record.standard_id:
                    std_images = self.session.query(ImageAttachment).filter(
                        ImageAttachment.entity_type == 'standard',
                        ImageAttachment.entity_id == record.standard_id
                    ).all()
                    image_attachments.extend(std_images)
                
                if image_attachments:
                    elements.append(PageBreak())
                    elements.append(Paragraph("Attached Images & Standard References", self.styles['CustomSubtitle']))
                    elements.append(Spacer(1, 0.2*inch))
                    
                    for idx, img_att in enumerate(image_attachments, 1):
                        att_path = img_att.file_path
                        att_name = img_att.description or img_att.filename or f"Image {idx}"
                        
                        if att_path and os.path.exists(att_path):
                            # Header for the image
                            label = "Standard Attachment" if img_att.entity_type == 'standard' else "Record Attachment"
                            elements.append(Paragraph(f"<b>{label}:</b> {att_name}", self.styles['Normal']))
                            elements.append(Spacer(1, 0.1*inch))
                            
                            try:
                                # Scale image
                                from reportlab.lib.utils import ImageReader
                                r_img = ImageReader(att_path)
                                w, h = r_img.getSize()
                                aspect = h / float(w)
                                img_w = 5.5 * inch
                                img_h = img_w * aspect
                                if img_h > 4 * inch:
                                    img_h = 4 * inch
                                    img_w = img_h / aspect
                                    
                                elements.append(RLImage(att_path, width=img_w, height=img_h))
                                elements.append(Spacer(1, 0.3*inch))
                            except Exception as e:
                                print(f"Error rendering image in statistical report: {e}")
                                elements.append(Paragraph(f"<i>Could not render image: {att_name}</i>", self.styles['Normal']))
                                
                # 3. Legacy record.attachments (JSON)
                if record.attachments:
                    import json
                    legacy_atts = json.loads(record.attachments) if isinstance(record.attachments, str) else record.attachments
                    if legacy_atts and isinstance(legacy_atts, list):
                        # Filter for actual files and add them if not already added
                        pass # (Keep it simple for now, ImageAttachment is the way forward)

            except Exception as e:
                print(f"Error adding images to statistical report: {e}")
        
        # Build PDF
        doc.build(elements, onFirstPage=self._create_header_footer, 
                 onLaterPages=self._create_header_footer)
        
        return filepath
    
    def _generate_statistical_charts(self, values, dates, record_numbers, criteria, mean_val, std_val):
        """Generate statistical charts and return paths to saved images"""
        chart_paths = []
        temp_dir = tempfile.gettempdir()
        
        print(f"Starting chart generation for criteria {criteria.id} in {temp_dir}")
        
        try:
            # Close any existing figures
            plt.close('all')
            
            # Organize data into record-based subgroups
            # This is important since a record can have multiple measurements
            subgroups = []
            current_rn = None
            current_subgroup = []
            
            for i, val in enumerate(values):
                rn = record_numbers[i]
                if rn != current_rn:
                    if current_subgroup:
                        subgroups.append({'rn': current_rn, 'vals': current_subgroup})
                    current_rn = rn
                    current_subgroup = []
                current_subgroup.append(val)
            if current_subgroup:
                subgroups.append({'rn': current_rn, 'vals': current_subgroup})
            
            # Derived data for charts
            rec_means = [np.mean(s['vals']) for s in subgroups]
            rec_ranges = [np.max(s['vals']) - np.min(s['vals']) for s in subgroups]
            rec_labels = [s['rn'] for s in subgroups]
            has_subgroups = any(len(s['vals']) > 1 for s in subgroups)
            
            # Helper for x-axis labels on large datasets
            def set_smart_xticks(ax, labels, count):
                ax.set_xticks(range(count))
                if count > 20:
                    # Show only every Nth label to avoid overlap
                    step = max(1, count // 10)
                    display_labels = [labels[i] if i % step == 0 else "" for i in range(count)]
                    ax.set_xticklabels(display_labels, rotation=45, ha='right', fontsize=8)
                else:
                    ax.set_xticklabels(labels, rotation=45, ha='right', fontsize=8)

            # 1. LINE CHART (Individual measurements)
            print("Generating line chart...")
            fig1 = plt.figure(figsize=(10, 5))
            ax1 = fig1.add_subplot(111)
            
            # Plot all individual values
            ax1.plot(range(len(values)), values, marker='o', linestyle='-', color='#1f77b4', 
                    linewidth=1.5, markersize=4, alpha=0.7, label='Measurements')
            
            # Overlay record averages to show trend clearly
            # Calculate positions for averages (middle of each subgroup)
            pos = 0
            avg_x = []
            for s in subgroups:
                avg_x.append(pos + (len(s['vals']) - 1) / 2)
                pos += len(s['vals'])
            
            if has_subgroups:
                ax1.plot(avg_x, rec_means, marker='s', linestyle='--', color='darkblue', 
                        linewidth=2, markersize=6, label='Record Average')

            ax1.axhline(y=mean_val, color='r', linestyle='--', alpha=0.6, label=f'Grand Average: {mean_val:.2f}')
            
            if criteria.limit_min is not None:
                ax1.axhline(y=float(criteria.limit_min), color='orange', linestyle='-', linewidth=1,
                          label=f'Lower Limit: {criteria.limit_min}')
            if criteria.limit_max is not None:
                ax1.axhline(y=float(criteria.limit_max), color='orange', linestyle='-', linewidth=1,
                          label=f'Upper Limit: {criteria.limit_max}')
            
            ax1.set_xlabel('Record Sequence', fontsize=10)
            ax1.set_ylabel(f'Value {f"({criteria.unit})" if criteria.unit else ""}', fontsize=10)
            ax1.set_title(f'Trend Analysis: {criteria.code} - {criteria.title}', fontsize=12, fontweight='bold')
            
            # Smart labels for individual points might be too crowded, so we label by record index
            sample_labels = []
            for s in subgroups:
                for _ in range(len(s['vals'])):
                    sample_labels.append(s['rn'])
            set_smart_xticks(ax1, sample_labels, len(values))
            
            ax1.legend(fontsize=8, loc='upper left', bbox_to_anchor=(1, 1))
            ax1.grid(True, alpha=0.3)
            
            line_chart_path = os.path.join(temp_dir, f'line_chart_{criteria.id}_{os.getpid()}.png')
            plt.tight_layout()
            fig1.savefig(line_chart_path, dpi=150, bbox_inches='tight', format='png')
            plt.close(fig1)
            
            if os.path.exists(line_chart_path):
                chart_paths.append(line_chart_path)
            
            # 2. X-BAR CHART (Control Chart for Averages)
            print("Generating X-bar chart...")
            fig2 = plt.figure(figsize=(10, 5))
            ax2 = fig2.add_subplot(111)
            
            # Use rec_means for X-bar chart instead of all points
            data_to_plot = rec_means
            labels_to_plot = rec_labels
            
            # Calculate control limits for the records
            grand_avg = np.mean(data_to_plot)
            # Use standard deviation of the record means for control limits
            std_of_means = np.std(data_to_plot, ddof=1) if len(data_to_plot) > 1 else 0
            ucl = grand_avg + 3 * std_of_means
            lcl = grand_avg - 3 * std_of_means
            
            ax2.plot(range(len(data_to_plot)), data_to_plot, marker='o', linestyle='-', 
                    linewidth=2, markersize=7, color='#2ca02c')
            ax2.axhline(y=grand_avg, color='green', linestyle='-', linewidth=2, label=f'X̄: {grand_avg:.2f}')
            ax2.axhline(y=ucl, color='red', linestyle='--', linewidth=1.5, label=f'UCL: {ucl:.2f}')
            ax2.axhline(y=lcl, color='red', linestyle='--', linewidth=1.5, label=f'LCL: {lcl:.2f}')
            
            # Highlight out-of-control points
            for i, val in enumerate(data_to_plot):
                if val > ucl or val < lcl:
                    ax2.plot(i, val, 'rx', markersize=12, markeredgewidth=2)
            
            ax2.set_xlabel('Record Number', fontsize=10)
            ax2.set_ylabel(f'Average Value {f"({criteria.unit})" if criteria.unit else ""}', fontsize=10)
            ax2.set_title(f'X-bar Control Chart: {criteria.code}', fontsize=12, fontweight='bold')
            set_smart_xticks(ax2, labels_to_plot, len(data_to_plot))
            ax2.legend(fontsize=8, loc='upper left', bbox_to_anchor=(1, 1))
            ax2.grid(True, alpha=0.3)
            
            xbar_chart_path = os.path.join(temp_dir, f'xbar_chart_{criteria.id}_{os.getpid()}.png')
            plt.tight_layout()
            fig2.savefig(xbar_chart_path, dpi=150, bbox_inches='tight', format='png')
            plt.close(fig2)
            
            if os.path.exists(xbar_chart_path):
                chart_paths.append(xbar_chart_path)
            
            # 3. R CHART (Range Chart)
            # If we have subgroups, plot ranges. Otherwise, plot Moving Ranges
            print("Generating R chart...")
            fig3 = plt.figure(figsize=(10, 5))
            ax3 = fig3.add_subplot(111)
            
            char_type = "Range"
            if has_subgroups:
                # Subgroup Range Chart
                r_values = rec_ranges
                r_labels = rec_labels
                char_type = "Range (R)"
                avg_r = np.mean(r_values)
                # Simple 3-sigma limits for range
                ucl_r = avg_r + 3 * np.std(r_values, ddof=1) if len(r_values) > 1 else avg_r * 2.5
            else:
                # Moving Range Chart
                char_type = "Moving Range (mR)"
                # Calculate moving ranges BUT ONLY within records if they had multiple points
                # (though has_subgroups=False means they all have 1 point)
                # So it's a standard mR chart across individual records
                r_values = [abs(values[i] - values[i-1]) for i in range(1, len(values))]
                r_labels = record_numbers[1:] # Skip first label
                avg_r = np.mean(r_values)
                ucl_r = avg_r * 3.267 # D4 for n=2
            
            ax3.plot(range(len(r_values)), r_values, marker='o', 
                   linestyle='-', linewidth=2, markersize=6, color='#9467bd')
            ax3.axhline(y=avg_r, color='green', linestyle='-', linewidth=2, 
                      label=f'Average {char_type}: {avg_r:.2f}')
            ax3.axhline(y=ucl_r, color='red', linestyle='--', linewidth=1.5, 
                      label=f'UCL: {ucl_r:.2f}')
            ax3.axhline(y=0, color='red', linestyle='--', linewidth=1.5, label='LCL: 0.00')
            
            # Highlight out-of-control
            for i, r in enumerate(r_values):
                if r > ucl_r:
                    ax3.plot(i, r, 'rx', markersize=12, markeredgewidth=2)
            
            ax3.set_xlabel('Record Number', fontsize=10)
            ax3.set_ylabel(f'{char_type} {f"({criteria.unit})" if criteria.unit else ""}', fontsize=10)
            ax3.set_title(f'{char_type} Control Chart: {criteria.code}', fontsize=12, fontweight='bold')
            set_smart_xticks(ax3, r_labels, len(r_values))
            ax3.legend(fontsize=8, loc='upper left', bbox_to_anchor=(1, 1))
            ax3.grid(True, alpha=0.3)
            
            r_chart_path = os.path.join(temp_dir, f'r_chart_{criteria.id}_{os.getpid()}.png')
            plt.tight_layout()
            fig3.savefig(r_chart_path, dpi=150, bbox_inches='tight', format='png')
            plt.close(fig3)
            
            if os.path.exists(r_chart_path):
                chart_paths.append(r_chart_path)
            
            print(f"Chart generation complete. Generated {len(chart_paths)} charts.")
            
        except Exception as e:
            print(f"Error generating charts: {e}")
            import traceback
            traceback.print_exc()
        
        return chart_paths
    
    def generate_nc_pdf(self, nc: NonConformance, filepath: str) -> str:
        """
        Generate PDF report for Non-Conformance
        
        Args:
            nc: NonConformance object
            filepath: Output PDF file path
            
        Returns:
            Path to generated PDF file
        """
        doc = SimpleDocTemplate(filepath, pagesize=A4)
        elements = []
        
        # Title
        title = Paragraph(f"Non-Conformance Report<br/>{nc.nc_number}", 
                         self.styles['CustomTitle'])
        elements.append(title)
        elements.append(Spacer(1, 0.3*inch))
        
        # Severity badge
        severity_colors = {
            'critical': colors.red,
            'major': colors.orange,
            'minor': colors.yellow
        }
        severity_color = severity_colors.get(nc.severity, colors.gray)
        
        severity_text = f"<font color='{severity_color}' size='16'><b>SEVERITY: {nc.severity.upper()}</b></font>"
        elements.append(Paragraph(severity_text, self.styles['Normal']))
        elements.append(Spacer(1, 0.3*inch))
        
        # NC Details
        elements.append(Paragraph("Non-Conformance Details", self.styles['CustomSubtitle']))
        
        nc_data = [
            ['NC Number:', nc.nc_number],
            ['Title:', nc.title],
            ['Category:', nc.category or 'N/A'],
            ['Severity:', nc.severity],
            ['Status:', nc.status],
            ['', ''],
            ['Detected Date:', nc.detected_date.strftime('%Y-%m-%d') if nc.detected_date else 'N/A'],
            ['Target Closure:', nc.target_closure_date.strftime('%Y-%m-%d') if nc.target_closure_date else 'N/A'],
            ['Closed Date:', nc.closed_date.strftime('%Y-%m-%d') if nc.closed_date else 'Open'],
            ['', ''],
            ['Reported By:', nc.reported_by.full_name if nc.reported_by else 'N/A'],
            ['Assigned To:', nc.assigned_to.full_name if nc.assigned_to else 'N/A'],
            ['Verified By:', nc.verified_by.full_name if nc.verified_by else 'Pending'],
            ['', ''],
            ['Customer Impact:', 'YES' if nc.customer_impact else 'NO'],
            ['Cost Impact:', f"${nc.cost_impact}" if nc.cost_impact else 'N/A'],
        ]
        
        nc_table = Table(nc_data, colWidths=[2*inch, 4*inch])
        nc_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F0F0F0')),
        ]))
        
        elements.append(nc_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Description
        elements.append(Paragraph("Description", self.styles['SectionHeader']))
        elements.append(Paragraph(nc.description or 'N/A', self.styles['Normal']))
        elements.append(Spacer(1, 0.2*inch))
        
        # 8D Sections
        sections = [
            ('Root Cause Analysis', nc.root_cause),
            ('Immediate Action', nc.immediate_action),
            ('Corrective Action', nc.corrective_action),
            ('Preventive Action', nc.preventive_action),
        ]
        
        for section_title, content in sections:
            if content:
                elements.append(Paragraph(section_title, self.styles['SectionHeader']))
                elements.append(Paragraph(content.replace('\n', '<br/>'), self.styles['Normal']))
                elements.append(Spacer(1, 0.2*inch))
        
        # ====================================================================
        # ATTACHMENTS (IMAGES)
        # ====================================================================
        
        if self.session:
            try:
                # Query ImageAttachment table for images linked to this NC
                from models import ImageAttachment
                image_attachments = self.session.query(ImageAttachment).filter(
                    ImageAttachment.entity_type == 'non_conformance',
                    ImageAttachment.entity_id == nc.id
                ).all()
                
                if image_attachments:
                    print(f"Found {len(image_attachments)} images for NC {nc.id}")
                    elements.append(PageBreak())
                    elements.append(Paragraph("Attached Images", self.styles['CustomSubtitle']))
                    elements.append(Spacer(1, 0.2*inch))
                    
                    for idx, img_attachment in enumerate(image_attachments, 1):
                        att_path = img_attachment.file_path
                        att_name = img_attachment.description or img_attachment.filename or f'Image {idx}'
                        
                        # Verify file exists
                        if not att_path or not os.path.exists(att_path):
                            print(f"Image file not found: {att_path}")
                            elements.append(Paragraph(
                                f"<i>Figure {idx}: {att_name} (File not found)</i>",
                                self.styles['Normal']
                            ))
                            elements.append(Spacer(1, 0.2*inch))
                            continue
                        
                        # Add image caption
                        caption = Paragraph(f"<b>Figure {idx}: {att_name}</b>", self.styles['Normal'])
                        elements.append(caption)
                        elements.append(Spacer(1, 0.1*inch))
                        
                        # Add the image with proper dimensions
                        try:
                            from PIL import Image as PILImage
                            
                            # Read image dimensions
                            with PILImage.open(att_path) as pil_img:
                                img_width, img_height = pil_img.size
                            
                            # Calculate scaled dimensions to fit in page
                            max_width = 5.5 * inch
                            max_height = 4 * inch
                            
                            # Calculate aspect ratio
                            aspect = img_width / img_height
                            
                            if img_width > max_width:
                                img_width = max_width
                                img_height = img_width / aspect
                            
                            if img_height > max_height:
                                img_height = max_height
                                img_width = img_height * aspect
                            
                            # Create and add image
                            print(f"Adding image to PDF: {att_path} ({img_width:.1f}x{img_height:.1f})")
                            img = RLImage(att_path, width=float(img_width), height=float(img_height))
                            elements.append(img)
                            print(f"Image added successfully")
                            
                        except Exception as e:
                            print(f"Error rendering image {att_path}: {str(e)}")
                            import traceback
                            traceback.print_exc()
                            error_text = Paragraph(
                                f"<i>Could not render image: {str(e)}</i>",
                                self.styles['Normal']
                            )
                            elements.append(error_text)
                        
                        elements.append(Spacer(1, 0.3*inch))
                else:
                    print(f"No images found for NC {nc.id}")
                        
            except Exception as e:
                print(f"Error querying/adding images to PDF: {e}")
                import traceback
                traceback.print_exc()
        
        doc.build(elements, onFirstPage=self._create_header_footer,
                 onLaterPages=self._create_header_footer)
        
        return filepath
    
    def generate_standard_pdf(self, standard: Standard, filepath: str) -> str:
        """
        Generate comprehensive PDF for a Standard with all sections and criteria
        
        Args:
            standard: Standard object
            filepath: Output PDF file path
            
        Returns:
            Path to generated PDF file
        """
        doc = SimpleDocTemplate(filepath, pagesize=A4)
        elements = []
        
        # Helper function to format numbers
        def format_number(num):
            if num is None:
                return 'N/A'
            if num == int(num):
                return str(int(num))
            else:
                return f'{num:.10g}'
        
        # ====================================================================
        # COVER PAGE
        # ====================================================================
        
        # Title
        title = Paragraph(f"<b>{standard.name}</b><br/>Standard Documentation", 
                         self.styles['CustomTitle'])
        elements.append(title)
        elements.append(Spacer(1, 0.5*inch))
        
        # Standard Information Box
        info_data = [
            ['Standard Code:', Paragraph(f"<b>{standard.code}</b>", self.styles['Normal'])],
            ['Version:', Paragraph(standard.version, self.styles['Normal'])],
            ['Industry:', Paragraph(standard.industry or 'N/A', self.styles['Normal'])],
            ['Status:', Paragraph('<font color="green"><b>ACTIVE</b></font>' if standard.is_active 
                                else '<font color="red"><b>INACTIVE</b></font>', self.styles['Normal'])],
        ]
        
        if standard.effective_date:
            info_data.append(['Effective Date:', 
                            Paragraph(standard.effective_date.strftime('%Y-%m-%d'), self.styles['Normal'])])
        if standard.expiry_date:
            info_data.append(['Expiry Date:', 
                            Paragraph(standard.expiry_date.strftime('%Y-%m-%d'), self.styles['Normal'])])
        
        info_table = Table(info_data, colWidths=[2*inch, 4*inch])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#2f3542')),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E8F0F8')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 8),
        ]))
        
        elements.append(info_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Description
        if standard.description:
            elements.append(Paragraph("<b>Description:</b>", self.styles['SectionHeader']))
            # Wrap description text properly
            desc_para = Paragraph(standard.description.replace('\n', '<br/>'), self.styles['Normal'])
            elements.append(desc_para)
            elements.append(Spacer(1, 0.2*inch))
        
        # Scope
        if standard.scope:
            elements.append(Paragraph("<b>Scope:</b>", self.styles['SectionHeader']))
            scope_para = Paragraph(standard.scope.replace('\n', '<br/>'), self.styles['Normal'])
            elements.append(scope_para)
            elements.append(Spacer(1, 0.2*inch))
        
        # Document URL
        if standard.document_url:
            elements.append(Paragraph("<b>Reference Documentation:</b>", self.styles['SectionHeader']))
            url_para = Paragraph(f'<link href="{standard.document_url}">{standard.document_url}</link>', 
                               self.styles['Normal'])
            elements.append(url_para)
            elements.append(Spacer(1, 0.2*inch))
        
        elements.append(PageBreak())
        
        # ====================================================================
        # TABLE OF CONTENTS
        # ====================================================================
        
        elements.append(Paragraph("<b>Table of Contents</b>", self.styles['CustomSubtitle']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Get sections
        sections = self.session.query(StandardSection).filter_by(
            standard_id=standard.id
        ).order_by(StandardSection.sort_order).all()
        
        if sections:
            toc_data = [['Section Code', 'Section Title']]
            for section in sections:
                toc_data.append([
                    Paragraph(f"<b>{section.code}</b>", self.styles['Normal']),
                    Paragraph(section.title, self.styles['Normal'])
                ])
            
            toc_table = Table(toc_data, colWidths=[1.5*inch, 4.5*inch])
            toc_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2f3542')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('PADDING', (0, 0), (-1, -1), 6),
            ]))
            
            elements.append(toc_table)
        else:
            elements.append(Paragraph("<i>No sections defined</i>", self.styles['Normal']))
        
        elements.append(PageBreak())
        
        # ====================================================================
        # SECTIONS AND CRITERIA
        # ====================================================================
        
        if sections:
            for section in sections:
                # Section Header
                elements.append(Paragraph(f"<b>{section.code}: {section.title}</b>", 
                                        self.styles['CustomSubtitle']))
                elements.append(Spacer(1, 0.1*inch))
                
                # Section Description
                if section.description:
                    desc_para = Paragraph(section.description.replace('\n', '<br/>'), 
                                        self.styles['Normal'])
                    elements.append(desc_para)
                    elements.append(Spacer(1, 0.2*inch))
                
                # Criteria for this section
                criteria_list = self.session.query(StandardCriteria).filter_by(
                    section_id=section.id
                ).order_by(StandardCriteria.sort_order).all()
                
                if criteria_list:
                    elements.append(Paragraph("<b>Criteria:</b>", self.styles['SectionHeader']))
                    elements.append(Spacer(1, 0.1*inch))
                    
                    # Criteria table
                    criteria_data = [[
                        Paragraph('<b>Code</b>', self.styles['Normal']),
                        Paragraph('<b>Title</b>', self.styles['Normal']),
                        Paragraph('<b>Type</b>', self.styles['Normal']),
                        Paragraph('<b>Data Type</b>', self.styles['Normal']),
                        Paragraph('<b>Limits/Values</b>', self.styles['Normal']),
                    ]]
                    
                    for crit in criteria_list:
                        # Build limits/values column
                        limits_text = ''
                        if crit.data_type == 'numeric':
                            if crit.limit_min is not None or crit.limit_max is not None:
                                min_str = format_number(crit.limit_min) if crit.limit_min is not None else '-∞'
                                max_str = format_number(crit.limit_max) if crit.limit_max is not None else '+∞'
                                limits_text = f"{min_str} to {max_str}"
                                if crit.tolerance is not None:
                                    limits_text += f" (±{format_number(crit.tolerance)})"
                                if crit.unit:
                                    limits_text += f" {crit.unit}"
                        elif crit.data_type in ['select', 'multiselect']:
                            if crit.options:
                                import json
                                opts = json.loads(crit.options) if isinstance(crit.options, str) else crit.options
                                if isinstance(opts, list):
                                    limits_text = ', '.join(opts[:3])
                                    if len(opts) > 3:
                                        limits_text += f' (+{len(opts)-3} more)'
                        
                        # Color code requirement type
                        req_type_color = {
                            'mandatory': 'red',
                            'conditional': 'orange',
                            'optional': 'blue'
                        }.get(crit.requirement_type, 'black')
                        
                        criteria_data.append([
                            Paragraph(f"<b>{crit.code}</b>", self.styles['Normal']),
                            Paragraph(crit.title, self.styles['Normal']),
                            Paragraph(f'<font color="{req_type_color}"><b>{crit.requirement_type}</b></font>', 
                                    self.styles['Normal']),
                            Paragraph(crit.data_type, self.styles['Normal']),
                            Paragraph(limits_text or 'N/A', self.styles['Normal']),
                        ])
                    
                    criteria_table = Table(criteria_data, 
                                         colWidths=[0.9*inch, 2*inch, 0.9*inch, 0.9*inch, 1.5*inch])
                    criteria_table.setStyle(TableStyle([
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2f3542')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('FONTSIZE', (0, 0), (-1, -1), 8),
                        ('PADDING', (0, 0), (-1, -1), 4),
                    ]))
                    
                    elements.append(criteria_table)
                    elements.append(Spacer(1, 0.2*inch))
                    
                    # Detailed criteria descriptions
                    for crit in criteria_list:
                        if crit.description or crit.help_text:
                            elements.append(Paragraph(f"<b>{crit.code}:</b> {crit.title}", 
                                                    self.styles['SectionHeader']))
                            if crit.description:
                                desc_para = Paragraph(crit.description.replace('\n', '<br/>'), 
                                                    self.styles['Normal'])
                                elements.append(desc_para)
                            if crit.help_text:
                                help_para = Paragraph(f"<i>Note: {crit.help_text}</i>", 
                                                    self.styles['Normal'])
                                elements.append(help_para)
                            elements.append(Spacer(1, 0.1*inch))
                
                elements.append(Spacer(1, 0.3*inch))
                elements.append(PageBreak())
        
        # ====================================================================
        # SUMMARY STATISTICS
        # ====================================================================
        
        elements.append(Paragraph("<b>Standard Summary</b>", self.styles['CustomSubtitle']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Get all criteria for summary
        all_criteria = self.session.query(StandardCriteria).filter_by(
            standard_id=standard.id
        ).all()
        
        # Count by requirement type
        mandatory_count = sum(1 for c in all_criteria if c.requirement_type == 'mandatory')
        conditional_count = sum(1 for c in all_criteria if c.requirement_type == 'conditional')
        optional_count = sum(1 for c in all_criteria if c.requirement_type == 'optional')
        
        # Count by data type
        numeric_count = sum(1 for c in all_criteria if c.data_type == 'numeric')
        boolean_count = sum(1 for c in all_criteria if c.data_type == 'boolean')
        text_count = sum(1 for c in all_criteria if c.data_type == 'text')
        other_count = len(all_criteria) - numeric_count - boolean_count - text_count
        
        summary_data = [
            ['Total Sections:', str(len(sections))],
            ['Total Criteria:', str(len(all_criteria))],
            ['', ''],
            ['Mandatory Criteria:', str(mandatory_count)],
            ['Conditional Criteria:', str(conditional_count)],
            ['Optional Criteria:', str(optional_count)],
            ['', ''],
            ['Numeric Criteria:', str(numeric_count)],
            ['Boolean Criteria:', str(boolean_count)],
            ['Text Criteria:', str(text_count)],
            ['Other Types:', str(other_count)],
        ]
        
        for i in range(len(summary_data)):
            for j in range(len(summary_data[i])):
                summary_data[i][j] = Paragraph(summary_data[i][j], self.styles['Normal'])
        
        summary_table = Table(summary_data, colWidths=[2.5*inch, 1.5*inch])
        summary_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F0F0F0')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        
        elements.append(summary_table)
        
        # ====================================================================
        # ATTACHMENTS (Images)
        # ====================================================================
        try:
            from image_handler import ImageHandler
            handler = ImageHandler(self.session)
            images = self.session.query(ImageAttachment).filter(
                ImageAttachment.entity_type == 'standard',
                ImageAttachment.entity_id == standard.id
            ).all()
            
            if images:
                elements.append(PageBreak())
                elements.append(Paragraph("Standard Attachments / Reference Images", self.styles['CustomSubtitle']))
                elements.append(Spacer(1, 0.2*inch))
                
                for img in images:
                    img_path = handler.get_image_path(img.id)
                    if img_path and os.path.exists(img_path):
                        try:
                            # Add image label/description
                            elements.append(Paragraph(f"<b>Image:</b> {img.description or img.filename}", self.styles['Normal']))
                            elements.append(Spacer(1, 0.1*inch))
                            
                            # Add image
                            from reportlab.lib.utils import ImageReader
                            r_img = ImageReader(img_path)
                            w, h = r_img.getSize()
                            aspect = h / float(w)
                            
                            # Max width 6 inches
                            img_w = 6 * inch
                            img_h = img_w * aspect
                            
                            # If too tall, scale down
                            if img_h > 4 * inch:
                                img_h = 4 * inch
                                img_w = img_h / aspect
                                
                            elements.append(RLImage(img_path, width=img_w, height=img_h))
                            elements.append(Spacer(1, 0.4*inch))
                        except Exception as e:
                            print(f"Error adding image to PDF: {e}")
        except Exception as e:
            print(f"Error loading images for standard PDF: {e}")
            
        # Build PDF
        doc.build(elements, onFirstPage=self._create_header_footer,
                 onLaterPages=self._create_header_footer)
        
        return filepath
    
    def generate_summary_report_pdf(self, records: List[Record], filepath: str, 
                                   title: str = "Quality Summary Report") -> str:
        """
        Generate summary PDF report for multiple records
        
        Args:
            records: List of Record objects
            filepath: Output PDF file path
            title: Report title
            
        Returns:
            Path to generated PDF file
        """
        doc = SimpleDocTemplate(filepath, pagesize=A4, landscape=True)
        elements = []
        
        # Title
        title_para = Paragraph(title, self.styles['CustomTitle'])
        elements.append(title_para)
        elements.append(Spacer(1, 0.2*inch))
        
        # Summary statistics
        total_records = len(records)
        approved = sum(1 for r in records if r.status == 'approved')
        rejected = sum(1 for r in records if r.status == 'rejected')
        pending = sum(1 for r in records if r.status in ['draft', 'submitted', 'under_review'])
        
        avg_compliance = sum(float(r.compliance_score or 0) for r in records) / total_records if total_records > 0 else 0
        
        stats_data = [
            ['Total Records', str(total_records)],
            ['Approved', str(approved)],
            ['Rejected', str(rejected)],
            ['Pending', str(pending)],
            ['Average Compliance', f"{avg_compliance:.1f}%"]
        ]
        
        stats_table = Table(stats_data, colWidths=[2*inch, 1.5*inch])
        stats_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#2f3542')),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.white),
        ]))
        
        elements.append(stats_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Records table
        elements.append(Paragraph("Records Summary", self.styles['CustomSubtitle']))
        
        records_data = [['Record #', 'Title', 'Status', 'Date', 'Compliance', 'Score']]
        
        for record in records:
            records_data.append([
                record.record_number,
                record.title or 'N/A',
                record.status,
                record.completed_at.strftime('%Y-%m-%d') if record.completed_at else 'N/A',
                'Pass' if record.overall_compliance else 'Fail' if record.overall_compliance is not None else 'N/A',
                f"{record.compliance_score}%" if record.compliance_score else 'N/A'
            ])
        
        records_table = Table(records_data, colWidths=[1.5*inch, 3*inch, 1*inch, 1*inch, 1*inch, 1*inch])
        records_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2f3542')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
        ]))
        
        elements.append(records_table)
        
        doc.build(elements, onFirstPage=self._create_header_footer,
                 onLaterPages=self._create_header_footer)
        
        return filepath
    
    def generate_date_range_statistical_report(self, template_id: int, start_date, end_date, 
                                               records: List[Record], filepath: str) -> str:
        """
        Generate statistical analysis PDF for records in a date range
        
        Args:
            template_id: Template ID
            start_date: Start date
            end_date: End date
            records: List of Record objects in date range
            filepath: Output PDF file path
            
        Returns:
            Path to generated PDF file
        """
        doc = SimpleDocTemplate(filepath, pagesize=A4)
        elements = []
        
        # Get template
        template = self.session.get(TestTemplate, template_id)
        
        # Title
        title = Paragraph(f"Statistical Analysis Report<br/>{start_date} to {end_date}", 
                         self.styles['CustomTitle'])
        elements.append(title)
        elements.append(Spacer(1, 0.2*inch))
        
        # Introduction
        intro_text = (
            f"<b>Template:</b> {template.name}<br/>"
            f"<b>Description:</b> {template.description or 'N/A'}<br/>"
            f"<b>Analysis Period:</b> {start_date} to {end_date}<br/>"
            f"<b>Total Records:</b> {len(records)}<br/>"
        )
        intro_para = Paragraph(intro_text, self.styles['Normal'])
        elements.append(intro_para)
        elements.append(Spacer(1, 0.3*inch))
        
        # Get template fields
        template_fields = self.session.query(TemplateField).filter_by(
            template_id=template_id
        ).order_by(TemplateField.sort_order).all()
        
        print(f"Date Range Report: Found {len(records)} records")
        print(f"Template has {len(template_fields)} fields")
        
        if records and template_fields:
            total_charts_generated = 0
            for field in template_fields:
                if not field.criteria:
                    continue
                
                criteria = field.criteria
                print(f"Processing criteria: {criteria.code} (type: {criteria.data_type})")
                
                # Skip non-numeric criteria
                if criteria.data_type != 'numeric':
                    print(f"  Skipping - not numeric")
                    continue
                
                # Collect values for this criteria across all records
                values = []
                dates = []
                record_numbers = []
                
                for rec in records:
                    for item in rec.items:
                        if item.criteria_id == criteria.id and item.numeric_value is not None:
                            values.append(float(item.numeric_value))
                            dates.append(rec.completed_at or rec.created_at)
                            record_numbers.append(rec.record_number)
                
                print(f"  Found {len(values)} values for {criteria.code}")
                
                if len(values) < 2:
                    print(f"  Skipping - need at least 2 values, only have {len(values)}")
                    continue  # Need at least 2 values for statistics
                
                # Page for this criteria
                elements.append(Paragraph(f"Criterion: {criteria.code} - {criteria.title}", 
                                         self.styles['CustomSubtitle']))
                elements.append(Spacer(1, 0.1*inch))
                
                # Calculate statistics
                values_array = np.array(values)
                mean_val = np.mean(values_array)
                std_val = np.std(values_array, ddof=1) if len(values) > 1 else 0
                range_val = np.max(values_array) - np.min(values_array)
                min_val = np.min(values_array)
                max_val = np.max(values_array)
                
                # Helper function to format numbers nicely
                def format_number(num):
                    if num == int(num):
                        return str(int(num))
                    else:
                        return f'{num:.10g}'  # Remove trailing zeros
                
                # Statistics table
                stats_data = [
                    ['Statistic', 'Value'],
                    ['Number of Samples', str(len(values))],
                    ['Average (X̄)', format_number(mean_val)],
                    ['Std Deviation (σ)', format_number(std_val)],
                    ['Range (R)', format_number(range_val)],
                    ['Minimum', format_number(min_val)],
                    ['Maximum', format_number(max_val)],
                ]
                
                # Add limits if defined
                if criteria.limit_min is not None:
                    stats_data.append(['Lower Limit', format_number(float(criteria.limit_min))])
                if criteria.limit_max is not None:
                    stats_data.append(['Upper Limit', format_number(float(criteria.limit_max))])
                if criteria.tolerance is not None:
                    stats_data.append(['Tolerance', format_number(float(criteria.tolerance))])
                
                # Wrap cells in Paragraph for proper text handling
                for i in range(len(stats_data)):
                    for j in range(len(stats_data[i])):
                        stats_data[i][j] = Paragraph(str(stats_data[i][j]), self.styles['Normal'])
                
                stats_table = Table(stats_data, colWidths=[2.5*inch, 2*inch])
                stats_table.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2f3542')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                ]))
                
                elements.append(stats_table)
                elements.append(Spacer(1, 0.2*inch))
                
                # Generate charts
                print(f"Generating charts for criteria {criteria.code}...")
                chart_paths = self._generate_statistical_charts(
                    values, dates, record_numbers, criteria, mean_val, std_val
                )
                print(f"Generated {len(chart_paths)} charts")
                
                # Add charts to PDF
                charts_added = 0
                for chart_path in chart_paths:
                    print(f"Checking chart: {chart_path}")
                    if os.path.exists(chart_path):
                        try:
                            print(f"Adding chart to PDF: {chart_path}")
                            img = RLImage(chart_path, width=6*inch, height=3.5*inch)
                            elements.append(img)
                            elements.append(Spacer(1, 0.15*inch))
                            charts_added += 1
                        except Exception as e:
                            print(f"Error adding chart to PDF: {e}")
                            error_text = Paragraph(f"<i>Error loading chart: {str(e)}</i>", 
                                                 self.styles['Normal'])
                            elements.append(error_text)
                    else:
                        print(f"Chart file does not exist: {chart_path}")
                        error_text = Paragraph(f"<i>Chart file not found: {os.path.basename(chart_path)}</i>", 
                                             self.styles['Normal'])
                        elements.append(error_text)
                
                print(f"Successfully added {charts_added} charts for {criteria.code}")
                total_charts_generated += charts_added
                
                elements.append(PageBreak())
            
            if total_charts_generated == 0:
                print("WARNING: No charts were generated!")
                elements.append(Paragraph("<i>No statistical charts could be generated. "
                                        "This may be because there are fewer than 2 numeric values "
                                        "for each criterion, or no numeric criteria are defined.</i>",
                                        self.styles['Normal']))
            else:
                print(f"Total charts generated: {total_charts_generated}")
        else:
            elements.append(Paragraph("<i>No data found for statistical analysis in this date range.</i>",
                                    self.styles['Normal']))
        
        doc.build(elements, onFirstPage=self._create_header_footer,
                 onLaterPages=self._create_header_footer)
        
        return filepath
    
    def generate_workflow_pdf(self, workflow: Workflow, filepath: str) -> str:
        """
        Generate PDF for workflow with visual flow diagram
        
        Args:
            workflow: Workflow object
            filepath: Output PDF file path
            
        Returns:
            Path to generated PDF file
        """
        doc = SimpleDocTemplate(filepath, pagesize=A4)
        elements = []
        
        # Title
        title = Paragraph(f"<b>Workflow: {workflow.name}</b><br/>({workflow.code})", 
                         self.styles['CustomTitle'])
        elements.append(title)
        elements.append(Spacer(1, 0.3*inch))
        
        # Workflow Information
        info_data = [
            [Paragraph('<b>Code:</b>', self.styles['Normal']), 
             Paragraph(workflow.code, self.styles['Normal'])],
            [Paragraph('<b>Name:</b>', self.styles['Normal']), 
             Paragraph(workflow.name, self.styles['Normal'])],
            [Paragraph('<b>Status:</b>', self.styles['Normal']), 
             Paragraph('<font color="green"><b>ACTIVE</b></font>' if workflow.is_active 
                      else '<font color="red"><b>INACTIVE</b></font>', self.styles['Normal'])],
        ]
        
        if workflow.description:
            info_data.append([Paragraph('<b>Description:</b>', self.styles['Normal']), 
                            Paragraph(workflow.description.replace('\n', '<br/>'), self.styles['Normal'])])
        
        if workflow.trigger_event:
            info_data.append([Paragraph('<b>Trigger Event:</b>', self.styles['Normal']), 
                            Paragraph(workflow.trigger_event, self.styles['Normal'])])
        
        if workflow.standard:
            info_data.append([Paragraph('<b>Standard:</b>', self.styles['Normal']), 
                            Paragraph(f"{workflow.standard.code} - {workflow.standard.name}", self.styles['Normal'])])
        
        if workflow.template:
            info_data.append([Paragraph('<b>Template:</b>', self.styles['Normal']), 
                            Paragraph(workflow.template.name, self.styles['Normal'])])
        
        info_table = Table(info_data, colWidths=[2*inch, 4*inch])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F0F0F0')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 8),
        ]))
        
        elements.append(info_table)
        elements.append(Spacer(1, 0.4*inch))
        
        # Parse steps
        import json
        steps = []
        if workflow.steps:
            try:
                steps_data = json.loads(workflow.steps) if isinstance(workflow.steps, str) else workflow.steps
                if isinstance(steps_data, list):
                    steps = steps_data
            except:
                pass
        
        if steps:
            # Visual Flow Diagram
            elements.append(Paragraph("<b>Workflow Flow Diagram</b>", self.styles['CustomSubtitle']))
            elements.append(Spacer(1, 0.2*inch))
            
            # Generate flow diagram as image
            try:
                flow_image_path = self._generate_workflow_flow_diagram(workflow, steps)
                if flow_image_path and os.path.exists(flow_image_path):
                    # Get image dimensions to calculate proportional height
                    from PIL import Image as PILImage
                    with PILImage.open(flow_image_path) as pil_img:
                        img_width, img_height = pil_img.size
                    
                    # Calculate height maintaining aspect ratio
                    target_width = 6 * inch
                    aspect_ratio = img_height / img_width
                    target_height = target_width * aspect_ratio
                    
                    img = RLImage(flow_image_path, width=target_width, height=target_height)
                    elements.append(img)
                    elements.append(Spacer(1, 0.3*inch))
                else:
                    print("Flow diagram not generated")
                    elements.append(Paragraph("<i>Flow diagram could not be generated</i>", 
                                            self.styles['Normal']))
            except Exception as e:
                print(f"Error generating flow diagram: {e}")
                import traceback
                traceback.print_exc()
                elements.append(Paragraph(f"<i>Error generating flow diagram: {str(e)}</i>", 
                                        self.styles['Normal']))
            
            elements.append(PageBreak())
            
            # Detailed Steps Table
            elements.append(Paragraph("<b>Workflow Steps Details</b>", self.styles['CustomSubtitle']))
            elements.append(Spacer(1, 0.2*inch))
            
            steps_data = [[
                Paragraph('<b>Order</b>', self.styles['Normal']),
                Paragraph('<b>Step Name</b>', self.styles['Normal']),
                Paragraph('<b>Role / Action</b>', self.styles['Normal']),
                Paragraph('<b>Logic (Success / Fail)</b>', self.styles['Normal']),
                Paragraph('<b>Description</b>', self.styles['Normal']),
            ]]
            
            for idx, step in enumerate(steps):
                if not isinstance(step, dict):
                    continue
                    
                order = str(idx + 1)
                name = str(step.get('name', 'Unnamed'))
                role_action = f"<b>Role:</b> {step.get('assigned_role', 'N/A')}<br/><b>Type:</b> {step.get('action_type', 'N/A')}"
                
                # Logic text
                s_target = step.get('next_step_success', 'next')
                s_target_text = f"Step {s_target}" if str(s_target).isdigit() else s_target.title()
                f_target = step.get('next_step_fail', 'end')
                f_target_text = f"Step {f_target}" if str(f_target).isdigit() else f_target.title()
                
                logic_text = (
                    f"<font color='green'><b>Success:</b> -> {s_target_text}</font><br/>"
                    f"<i>{step.get('success_action', '')}</i><br/>"
                    f"<font color='red'><b>Fail:</b> -> {f_target_text}</font><br/>"
                    f"<i>{step.get('fail_action', '')}</i>"
                )
                
                description = str(step.get('description', 'No description'))[:300]
                
                steps_data.append([
                    Paragraph(order, self.styles['Normal']),
                    Paragraph(f"<b>{name}</b>", self.styles['Normal']),
                    Paragraph(role_action, self.styles['Normal']),
                    Paragraph(logic_text, self.styles['Normal']),
                    Paragraph(description, self.styles['Normal']),
                ])
            
            steps_table = Table(steps_data, colWidths=[0.5*inch, 1.2*inch, 1.2*inch, 1.5*inch, 1.8*inch])
            steps_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2f3542')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('PADDING', (0, 0), (-1, -1), 6),
            ]))
            
            elements.append(steps_table)
        else:
            elements.append(Paragraph("<b>No Steps Defined</b>", self.styles['CustomSubtitle']))
            elements.append(Paragraph("<i>This workflow has no steps defined yet. "
                                    "Use the 'Define Steps' button to add workflow steps.</i>", 
                                    self.styles['Normal']))
        
        # Build PDF
        doc.build(elements, onFirstPage=self._create_header_footer,
                 onLaterPages=self._create_header_footer)
        
        return filepath
    
    def _generate_workflow_flow_diagram(self, workflow, steps):
        """Generate visual flow diagram using matplotlib with branching (Success/Fail)"""
        import tempfile
        import matplotlib.patches as patches
        
        # Validate inputs
        if not steps or not isinstance(steps, list) or len(steps) == 0:
            print("No steps to generate diagram")
            return None
        
        temp_dir = tempfile.gettempdir()
        diagram_path = os.path.join(temp_dir, f'workflow_{workflow.id}_{os.getpid()}.png')
        
        try:
            # Calculate coordinates
            box_width = 4.0
            box_height = 0.8
            vertical_spacing = 1.0
            
            # Add virtual START and END nodes
            total_nodes = len(steps) + 2
            fig_height = max(total_nodes * 1.5, 5)
            fig = plt.figure(figsize=(10, fig_height))
            ax = fig.add_subplot(111)
            ax.set_xlim(0, 10)
            ax.set_ylim(-0.5, total_nodes * (box_height + vertical_spacing))
            ax.axis('off')
            
            # Map step order to Y coordinate
            node_coords = {}
            
            # START Node
            start_y = (total_nodes - 1) * (box_height + vertical_spacing)
            node_coords['start'] = (5, start_y)
            
            # Step Nodes
            for i, step in enumerate(steps):
                y = (len(steps) - i) * (box_height + vertical_spacing)
                node_coords[i + 1] = (5, y)
                
            # END Node
            node_coords['end'] = (5, 0)
            
            # Draw Nodes
            # Draw START
            ax.add_patch(patches.FancyBboxPatch((3, start_y), 4, box_height, 
                         boxstyle="round,pad=0.1", fc='#4CAF50', ec='black', lw=2))
            ax.text(5, start_y + box_height/2, "START", ha='center', va='center', 
                    fontsize=12, fontweight='bold', color='white')
            
            # Draw Steps
            action_colors = {
                'Review': '#FFE4B5', 'Approve': '#90EE90', 'Reject': '#FFB6C1',
                'Submit': '#87CEEB', 'Notify': '#DDA0DD', 'Decision': '#F0E68C',
                'Validate': '#F0E68C', 'Execute': '#FFA07A', 'Complete': '#98FB98'
            }
            
            for i, step in enumerate(steps):
                x, y = node_coords[i + 1]
                color = action_colors.get(step.get('action_type'), '#D3D3D3')
                
                ax.add_patch(patches.FancyBboxPatch((x-2, y), 4, box_height, 
                             boxstyle="round,pad=0.1", fc=color, ec='black', lw=1.5))
                
                # Title
                ax.text(x, y + box_height*0.65, f"Step {i+1}: {step.get('name')}", 
                        ha='center', va='center', fontsize=10, fontweight='bold')
                
                # Role & Action
                role_text = f"[{step.get('assigned_role', 'Unassigned')}] - {step.get('action_type')}"
                ax.text(x, y + box_height*0.3, role_text, 
                        ha='center', va='center', fontsize=8, style='italic')

            # Draw END
            ax.add_patch(patches.FancyBboxPatch((3, 0), 4, box_height, 
                         boxstyle="round,pad=0.1", fc='#f44336', ec='black', lw=2))
            ax.text(5, box_height/2, "END", ha='center', va='center', 
                    fontsize=12, fontweight='bold', color='white')

            # Draw Connections
            # Start to Step 1
            ax.annotate("", xy=(5, node_coords[1][1] + box_height), xytext=(5, start_y),
                        arrowprops=dict(arrowstyle="->", lw=1.5, color='black'))

            for i, step in enumerate(steps):
                curr_idx = i + 1
                curr_pos = node_coords[curr_idx]
                
                # Success Link (Green)
                s_target = step.get('next_step_success', 'next')
                if s_target == 'next':
                    target_idx = curr_idx + 1 if curr_idx < len(steps) else 'end'
                elif s_target == 'end':
                    target_idx = 'end'
                else:
                    try:
                        target_idx = int(s_target)
                    except:
                        target_idx = curr_idx + 1 if curr_idx < len(steps) else 'end'
                
                if target_idx in node_coords:
                    t_pos = node_coords[target_idx]
                    s_action = step.get('success_action', '')
                    
                    if target_idx == curr_idx + 1 or (curr_idx == len(steps) and target_idx == 'end'):
                        # Direct vertical line - slightly offset to avoid overlap with fail lines
                        ax.annotate("", xy=(4.5, t_pos[1] + box_height), xytext=(4.5, curr_pos[1]),
                                   arrowprops=dict(arrowstyle="->", lw=2, color='green'))
                        if s_action:
                            ax.text(4.0, (curr_pos[1] + t_pos[1] + box_height)/2, s_action, 
                                    ha='right', va='center', fontsize=7, color='green', rotation=90)
                    else:
                        # Route around left side with proper clearance
                        step_distance = abs(target_idx if isinstance(target_idx, int) else 0 - curr_idx)
                        x_offset = -3 - (step_distance * 0.5)  # Further left for longer jumps
                        
                        # Path: go left, then vertical, then right
                        path = patches.FancyArrowPatch(
                            (3, curr_pos[1] + box_height/2),  # Start from left edge
                            (3, t_pos[1] + box_height/2),  # End at left edge of target
                            connectionstyle=f"arc3,rad=0",
                            arrowstyle="->",
                            mutation_scale=20,
                            lw=1.5,
                            color='green',
                            alpha=0.7,
                            linestyle='--'
                        )
                        
                        # Create multi-segment path
                        from matplotlib.path import Path as MplPath
                        vertices = [
                            (3, curr_pos[1] + box_height/2),  # Start
                            (x_offset, curr_pos[1] + box_height/2),  # Left
                            (x_offset, t_pos[1] + box_height/2),  # Down/Up
                            (3, t_pos[1] + box_height/2)  # Right to target
                        ]
                        codes = [MplPath.MOVETO, MplPath.LINETO, MplPath.LINETO, MplPath.LINETO]
                        path_obj = MplPath(vertices, codes)
                        patch = patches.PathPatch(path_obj, facecolor='none', edgecolor='green', 
                                                 lw=1.5, alpha=0.7, linestyle='--')
                        ax.add_patch(patch)
                        
                        # Add arrow at end
                        ax.annotate("", xy=(3, t_pos[1] + box_height/2), 
                                   xytext=(x_offset + 0.3, t_pos[1] + box_height/2),
                                   arrowprops=dict(arrowstyle="->", lw=1.5, color='green', alpha=0.7))
                        
                        # Label
                        if s_action:
                            label_y = (curr_pos[1] + t_pos[1]) / 2
                            ax.text(x_offset - 0.3, label_y, s_action, 
                                    ha='center', va='center', fontsize=6, color='green',
                                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))

                # Fail Link (Red)
                f_target = step.get('next_step_fail', 'end')
                if f_target == 'end':
                    target_idx = 'end'
                elif f_target == 'restart':
                    target_idx = 1
                else:
                    try:
                        target_idx = int(f_target)
                    except:
                        target_idx = 'end'
                
                if target_idx in node_coords and target_idx != curr_idx + 1:  # Skip if same as success path
                    t_pos = node_coords[target_idx]
                    f_action = step.get('fail_action', '')
                    
                    # Route around right side with proper clearance
                    step_distance = abs(target_idx if isinstance(target_idx, int) else 0 - curr_idx)
                    x_offset = 7 + (step_distance * 0.5)  # Further right for longer jumps
                    
                    # Create multi-segment path
                    from matplotlib.path import Path as MplPath
                    vertices = [
                        (7, curr_pos[1] + box_height/2),  # Start from right edge
                        (x_offset, curr_pos[1] + box_height/2),  # Right
                        (x_offset, t_pos[1] + box_height/2),  # Down/Up
                        (7, t_pos[1] + box_height/2)  # Left to target
                    ]
                    codes = [MplPath.MOVETO, MplPath.LINETO, MplPath.LINETO, MplPath.LINETO]
                    path_obj = MplPath(vertices, codes)
                    patch = patches.PathPatch(path_obj, facecolor='none', edgecolor='red', 
                                             lw=1.5, alpha=0.7, linestyle='--')
                    ax.add_patch(patch)
                    
                    # Add arrow at end
                    ax.annotate("", xy=(7, t_pos[1] + box_height/2), 
                               xytext=(x_offset - 0.3, t_pos[1] + box_height/2),
                               arrowprops=dict(arrowstyle="->", lw=1.5, color='red', alpha=0.7))
                    
                    # Label
                    if f_action:
                        label_y = (curr_pos[1] + t_pos[1]) / 2
                        ax.text(x_offset + 0.3, label_y, f_action, 
                                ha='center', va='center', fontsize=6, color='red',
                                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))

            plt.tight_layout()
            fig.savefig(diagram_path, dpi=150, bbox_inches='tight', format='png', facecolor='white')
            plt.close(fig)
            return diagram_path
            
        except Exception as e:
            print(f"Error in diagram generation: {e}")
            import traceback
            traceback.print_exc()
            return None
            
        except Exception as e:
            print(f"Error in diagram generation: {e}")
            import traceback
            traceback.print_exc()
            return None


# Convenience functions
def generate_record_pdf(record, output_path):
    """Quick record PDF generation"""
    generator = PDFGenerator()
    return generator.generate_record_pdf(record, output_path)


def generate_nc_pdf(nc, output_path):
    """Quick NC PDF generation"""
    generator = PDFGenerator()
    return generator.generate_nc_pdf(nc, output_path)
