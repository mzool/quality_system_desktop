"""
Example Script - Populate Quality System with Sample Data
This script demonstrates how to programmatically create sample data
"""
from datetime import datetime, timedelta
from database import init_database
from models import *
import random


def create_sample_data():
    """Create comprehensive sample data for demonstration"""
    
    # Initialize database
    print("Initializing database...")
    db_manager = init_database(create_tables=True, init_data=True)
    session = db_manager.get_session()
    
    try:
        # Get admin user
        admin = session.query(User).filter_by(username='admin').first()
        
        # Get roles
        inspector_role = session.query(Role).filter_by(name='Quality Inspector').first()
        manager_role = session.query(Role).filter_by(name='QA Manager').first()
        
        print("\n1. Creating additional users...")
        users_data = [
            {'username': 'john.smith', 'full_name': 'John Smith', 'email': 'john@company.com', 'role_id': inspector_role.id, 'department': 'Production'},
            {'username': 'jane.doe', 'full_name': 'Jane Doe', 'email': 'jane@company.com', 'role_id': inspector_role.id, 'department': 'QC Lab'},
            {'username': 'bob.manager', 'full_name': 'Bob Manager', 'email': 'bob@company.com', 'role_id': manager_role.id, 'department': 'Quality Assurance'},
        ]
        
        import hashlib
        users = {}
        for user_data in users_data:
            user = User(
                **user_data,
                password_hash=hashlib.sha256('password123'.encode()).hexdigest(),
                is_active=True,
                created_by_id=admin.id
            )
            session.add(user)
            users[user_data['username']] = user
        
        session.flush()
        print(f"   Created {len(users_data)} users")
        
        # Create Standards
        print("\n2. Creating standards...")
        standards_data = [
            {
                'code': 'ISO-9001',
                'name': 'Quality Management Systems - Requirements',
                'version': '2015',
                'industry': 'General',
                'description': 'ISO 9001:2015 specifies requirements for a quality management system',
                'is_active': True,
                'created_by_id': admin.id
            },
            {
                'code': 'INTERNAL-FPI',
                'name': 'Final Product Inspection Standard',
                'version': '1.0',
                'industry': 'Manufacturing',
                'description': 'Internal standard for final product inspection',
                'is_active': True,
                'created_by_id': admin.id
            }
        ]
        
        standards = {}
        for std_data in standards_data:
            standard = Standard(**std_data)
            session.add(standard)
            standards[std_data['code']] = standard
        
        session.flush()
        print(f"   Created {len(standards_data)} standards")
        
        # Create Criteria for INTERNAL-FPI
        print("\n3. Creating criteria...")
        criteria_data = [
            {
                'standard': standards['INTERNAL-FPI'],
                'code': 'DIM-001',
                'title': 'Overall Length',
                'description': 'Measure overall product length',
                'data_type': 'numeric',
                'requirement_type': 'mandatory',
                'limit_min': 99.5,
                'limit_max': 100.5,
                'unit': 'mm',
                'severity': 'major'
            },
            {
                'standard': standards['INTERNAL-FPI'],
                'code': 'DIM-002',
                'title': 'Width',
                'description': 'Measure product width',
                'data_type': 'numeric',
                'requirement_type': 'mandatory',
                'limit_min': 49.5,
                'limit_max': 50.5,
                'unit': 'mm',
                'severity': 'major'
            },
            {
                'standard': standards['INTERNAL-FPI'],
                'code': 'VIS-001',
                'title': 'Surface Finish',
                'description': 'Visual inspection of surface quality',
                'data_type': 'select',
                'requirement_type': 'mandatory',
                'options': ['Excellent', 'Good', 'Fair', 'Poor'],
                'severity': 'minor'
            },
            {
                'standard': standards['INTERNAL-FPI'],
                'code': 'FUNC-001',
                'title': 'Functional Test',
                'description': 'Product operates correctly',
                'data_type': 'boolean',
                'requirement_type': 'mandatory',
                'severity': 'critical'
            }
        ]
        
        criteria_list = []
        for crit_data in criteria_data:
            criteria = StandardCriteria(**crit_data)
            session.add(criteria)
            criteria_list.append(criteria)
        
        session.flush()
        print(f"   Created {len(criteria_data)} criteria")
        
        # Create Template
        print("\n4. Creating template...")
        template = TestTemplate(
            code='FPI-DAILY',
            name='Daily Final Product Inspection',
            standard_id=standards['INTERNAL-FPI'].id,
            description='Daily inspection form for final products',
            category='inspection',
            version='1.0',
            layout={
                'type': 'grid',
                'columns': 2,
                'sections': [
                    {'id': 'dimensional', 'title': 'Dimensional Checks'},
                    {'id': 'visual', 'title': 'Visual Inspection'},
                    {'id': 'functional', 'title': 'Functional Tests'}
                ]
            },
            form_config={
                'allow_attachments': True,
                'require_signature': True
            },
            is_active=True,
            frequency='daily',
            estimated_duration_minutes=30,
            created_by_id=admin.id
        )
        session.add(template)
        session.flush()
        print(f"   Created template: {template.name}")
        
        # Create Template Fields
        print("\n5. Linking criteria to template...")
        for idx, criteria in enumerate(criteria_list):
            # Determine section
            if criteria.code.startswith('DIM'):
                section = 'dimensional'
            elif criteria.code.startswith('VIS'):
                section = 'visual'
            else:
                section = 'functional'
            
            field = TemplateField(
                template_id=template.id,
                criteria_id=criteria.id,
                section_key=section,
                is_required=True,
                sort_order=idx + 1
            )
            session.add(field)
        
        session.flush()
        print(f"   Created {len(criteria_list)} template fields")
        
        # Create Sample Records
        print("\n6. Creating sample records...")
        records_created = 0
        
        for day_offset in range(30):  # Last 30 days
            # Create 1-3 records per day
            num_records = random.randint(1, 3)
            
            for record_num in range(num_records):
                date = datetime.now() - timedelta(days=29-day_offset)
                
                record = Record(
                    record_number=f"REC-{date.strftime('%Y%m%d')}-{record_num+1:03d}",
                    template_id=template.id,
                    standard_id=standards['INTERNAL-FPI'].id,
                    title=f"Daily Inspection - Batch {1000 + day_offset}",
                    category='inspection',
                    status=random.choice(['approved', 'approved', 'approved', 'rejected']),
                    priority='medium',
                    scheduled_date=date,
                    started_at=date + timedelta(hours=8),
                    completed_at=date + timedelta(hours=9),
                    batch_number=f"BATCH-{1000 + day_offset}",
                    product_id=f"PROD-{random.randint(100, 999)}",
                    location='Line 3',
                    department='Production',
                    created_by_id=users['john.smith'].id,
                    assigned_to_id=users['john.smith'].id,
                    approved_by_id=users['bob.manager'].id
                )
                
                session.add(record)
                session.flush()
                
                # Add record items
                passed = 0
                failed = 0
                
                for criteria in criteria_list:
                    # Generate random but mostly passing values
                    if criteria.data_type == 'numeric':
                        # 90% within limits
                        if random.random() < 0.9:
                            value = random.uniform(criteria.limit_min, criteria.limit_max)
                            compliance = True
                            passed += 1
                        else:
                            value = random.uniform(criteria.limit_min - 1, criteria.limit_max + 1)
                            compliance = criteria.limit_min <= value <= criteria.limit_max
                            if compliance:
                                passed += 1
                            else:
                                failed += 1
                        
                        item = RecordItem(
                            record_id=record.id,
                            criteria_id=criteria.id,
                            value=f"{value:.2f}",
                            numeric_value=value,
                            compliance=compliance,
                            measured_by_id=users['john.smith'].id
                        )
                    
                    elif criteria.data_type == 'select':
                        # 95% good or excellent
                        if random.random() < 0.95:
                            value = random.choice(['Excellent', 'Good'])
                            compliance = True
                            passed += 1
                        else:
                            value = random.choice(['Fair', 'Poor'])
                            compliance = value in ['Excellent', 'Good']
                            if compliance:
                                passed += 1
                            else:
                                failed += 1
                        
                        item = RecordItem(
                            record_id=record.id,
                            criteria_id=criteria.id,
                            value=value,
                            compliance=compliance,
                            measured_by_id=users['john.smith'].id
                        )
                    
                    elif criteria.data_type == 'boolean':
                        # 95% pass
                        compliance = random.random() < 0.95
                        if compliance:
                            passed += 1
                        else:
                            failed += 1
                        
                        item = RecordItem(
                            record_id=record.id,
                            criteria_id=criteria.id,
                            value='Yes' if compliance else 'No',
                            compliance=compliance,
                            measured_by_id=users['john.smith'].id
                        )
                    
                    session.add(item)
                
                # Update record summary
                total = passed + failed
                record.compliance_score = (passed / total * 100) if total > 0 else 0
                record.overall_compliance = failed == 0
                record.failed_items_count = failed
                
                records_created += 1
        
        session.flush()
        print(f"   Created {records_created} sample records")
        
        # Create Sample Non-Conformances
        print("\n7. Creating sample non-conformances...")
        ncs_data = [
            {
                'nc_number': 'NC-2026-001',
                'title': 'Dimensional out of tolerance',
                'description': 'Product length exceeded maximum specification',
                'severity': 'major',
                'category': 'product',
                'status': 'closed',
                'detected_date': datetime.now() - timedelta(days=15),
                'closed_date': datetime.now() - timedelta(days=5),
                'root_cause': 'Machine calibration drift',
                'corrective_action': 'Recalibrated machine, adjusted tolerance monitoring',
                'reported_by_id': users['john.smith'].id,
                'assigned_to_id': users['bob.manager'].id
            },
            {
                'nc_number': 'NC-2026-002',
                'title': 'Surface defect detected',
                'description': 'Multiple surface scratches found on batch',
                'severity': 'minor',
                'category': 'product',
                'status': 'implementing',
                'detected_date': datetime.now() - timedelta(days=5),
                'target_closure_date': datetime.now() + timedelta(days=10),
                'root_cause': 'Improper handling during transport',
                'immediate_action': 'Quarantined affected batch',
                'corrective_action': 'Updated handling procedures, retrained staff',
                'reported_by_id': users['jane.doe'].id,
                'assigned_to_id': users['bob.manager'].id
            }
        ]
        
        for nc_data in ncs_data:
            nc = NonConformance(**nc_data)
            session.add(nc)
        
        session.flush()
        print(f"   Created {len(ncs_data)} non-conformances")
        
        # Commit all changes
        session.commit()
        
        print("\n" + "="*60)
        print("Sample data created successfully!")
        print("="*60)
        print(f"\n📊 Summary:")
        print(f"   Users: {session.query(User).count()}")
        print(f"   Roles: {session.query(Role).count()}")
        print(f"   Standards: {session.query(Standard).count()}")
        print(f"   Criteria: {session.query(StandardCriteria).count()}")
        print(f"   Templates: {session.query(TestTemplate).count()}")
        print(f"   Records: {session.query(Record).count()}")
        print(f"   Non-Conformances: {session.query(NonConformance).count()}")
        
        print(f"\n👤 User Accounts:")
        print(f"   admin / admin123 (Admin)")
        print(f"   john.smith / password123 (Inspector)")
        print(f"   jane.doe / password123 (Inspector)")
        print(f"   bob.manager / password123 (QA Manager)")
        
        print(f"\n🚀 Ready to use! Run: python main.py")
        
    except Exception as e:
        session.rollback()
        print(f"\n❌ Error creating sample data: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()


if __name__ == "__main__":
    print("""
╔════════════════════════════════════════════════════════════╗
║  Quality Management System - Sample Data Generator         ║
║  This will populate the database with sample data          ║
╚════════════════════════════════════════════════════════════╝
    """)
    
    response = input("Do you want to create sample data? (yes/no): ")
    
    if response.lower() in ['yes', 'y']:
        create_sample_data()
    else:
        print("Cancelled.")

