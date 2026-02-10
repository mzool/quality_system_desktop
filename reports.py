"""
Reports Module for Quality System
Generate various analytical reports and statistics
"""
from sqlalchemy import func, and_, or_, extract, case
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from collections import defaultdict
import pandas as pd
from models import *


class ReportsGenerator:
    """Generate various reports and analytics"""
    
    def __init__(self, session):
        """
        Initialize reports generator
        
        Args:
            session: SQLAlchemy session
        """
        self.session = session
    
    # ========================================================================
    # COMPLIANCE REPORTS
    # ========================================================================
    
    def compliance_summary_report(self, start_date: datetime = None, 
                                 end_date: datetime = None,
                                 department: str = None) -> dict:
        """
        Generate compliance summary report
        
        Args:
            start_date: Start date for filtering
            end_date: End date for filtering
            department: Filter by department
            
        Returns:
            Dictionary with compliance statistics
        """
        query = self.session.query(Record)
        
        # Apply filters
        if start_date:
            query = query.filter(Record.created_at >= start_date)
        if end_date:
            query = query.filter(Record.created_at <= end_date)
        if department:
            query = query.filter(Record.department == department)
        
        records = query.all()
        
        if not records:
            return {
                'total_records': 0,
                'message': 'No records found for the specified criteria'
            }
        
        # Calculate statistics
        total = len(records)
        passed = sum(1 for r in records if r.overall_compliance is True)
        failed = sum(1 for r in records if r.overall_compliance is False)
        pending = sum(1 for r in records if r.overall_compliance is None)
        
        avg_score = sum(float(r.compliance_score or 0) for r in records) / total
        
        # Status breakdown
        status_counts = defaultdict(int)
        for record in records:
            status_counts[record.status] += 1
        
        # Category breakdown
        category_counts = defaultdict(int)
        for record in records:
            category_counts[record.category or 'Unknown'] += 1
        
        # Calculate pass rate
        pass_rate = (passed / (passed + failed) * 100) if (passed + failed) > 0 else 0
        
        return {
            'total_records': total,
            'passed': passed,
            'failed': failed,
            'pending': pending,
            'pass_rate': round(pass_rate, 2),
            'average_score': round(avg_score, 2),
            'status_breakdown': dict(status_counts),
            'category_breakdown': dict(category_counts),
            'date_range': {
                'start': start_date.strftime('%Y-%m-%d') if start_date else 'All time',
                'end': end_date.strftime('%Y-%m-%d') if end_date else 'Present'
            }
        }
    
    def trend_analysis_report(self, period: str = 'month', limit: int = 12) -> dict:
        """
        Generate trend analysis report
        
        Args:
            period: Grouping period ('day', 'week', 'month', 'year')
            limit: Number of periods to include
            
        Returns:
            Dictionary with trend data
        """
        # Define date grouping based on period
        if period == 'day':
            date_group = func.date(Record.created_at)
        elif period == 'week':
            date_group = func.strftime('%Y-W%W', Record.created_at)
        elif period == 'month':
            date_group = func.strftime('%Y-%m', Record.created_at)
        else:  # year
            date_group = extract('year', Record.created_at)
        
        # Query for compliance trend
        trend_data = self.session.query(
            date_group.label('period'),
            func.count(Record.id).label('total'),
            func.sum(case((Record.overall_compliance == True, 1), else_=0)).label('passed'),
            func.sum(case((Record.overall_compliance == False, 1), else_=0)).label('failed'),
            func.avg(Record.compliance_score).label('avg_score')
        ).group_by('period').order_by('period').limit(limit).all()
        
        results = []
        for row in trend_data:
            period_val = str(row.period)
            total = row.total
            passed = row.passed or 0
            failed = row.failed or 0
            
            results.append({
                'period': period_val,
                'total': total,
                'passed': int(passed),
                'failed': int(failed),
                'pass_rate': round((passed / total * 100) if total > 0 else 0, 2),
                'avg_score': round(float(row.avg_score or 0), 2)
            })
        
        return {
            'period_type': period,
            'data': results
        }
    
    def criteria_failure_report(self, top_n: int = 20) -> list:
        """
        Report on most frequently failing criteria
        
        Args:
            top_n: Number of top failing criteria to return
            
        Returns:
            List of criteria with failure counts
        """
        failure_data = self.session.query(
            StandardCriteria.id,
            StandardCriteria.code,
            StandardCriteria.title,
            StandardCriteria.severity,
            func.count(RecordItem.id).label('failure_count')
        ).join(
            RecordItem, RecordItem.criteria_id == StandardCriteria.id
        ).filter(
            RecordItem.compliance == False
        ).group_by(
            StandardCriteria.id
        ).order_by(
            func.count(RecordItem.id).desc()
        ).limit(top_n).all()
        
        results = []
        for row in failure_data:
            results.append({
                'criteria_id': row.id,
                'code': row.code,
                'title': row.title,
                'severity': row.severity,
                'failure_count': row.failure_count
            })
        
        return results
    
    # ========================================================================
    # NON-CONFORMANCE REPORTS
    # ========================================================================
    
    def nc_summary_report(self, start_date: datetime = None, 
                         end_date: datetime = None) -> dict:
        """
        Generate non-conformance summary report
        
        Args:
            start_date: Start date for filtering
            end_date: End date for filtering
            
        Returns:
            Dictionary with NC statistics
        """
        query = self.session.query(NonConformance)
        
        if start_date:
            query = query.filter(NonConformance.detected_date >= start_date)
        if end_date:
            query = query.filter(NonConformance.detected_date <= end_date)
        
        ncs = query.all()
        
        if not ncs:
            return {
                'total_ncs': 0,
                'message': 'No non-conformances found'
            }
        
        total = len(ncs)
        
        # Status breakdown
        status_counts = defaultdict(int)
        for nc in ncs:
            status_counts[nc.status] += 1
        
        # Severity breakdown
        severity_counts = defaultdict(int)
        for nc in ncs:
            severity_counts[nc.severity] += 1
        
        # Category breakdown
        category_counts = defaultdict(int)
        for nc in ncs:
            category_counts[nc.category or 'Unknown'] += 1
        
        # Calculate closure metrics
        closed = sum(1 for nc in ncs if nc.status == 'closed')
        open_ncs = total - closed
        
        # Average time to close (for closed NCs)
        closed_ncs = [nc for nc in ncs if nc.closed_date and nc.detected_date]
        if closed_ncs:
            avg_closure_days = sum(
                (nc.closed_date - nc.detected_date).days 
                for nc in closed_ncs
            ) / len(closed_ncs)
        else:
            avg_closure_days = 0
        
        # Customer impact
        customer_impact_count = sum(1 for nc in ncs if nc.customer_impact)
        
        # Cost impact
        total_cost = sum(float(nc.cost_impact or 0) for nc in ncs)
        
        return {
            'total_ncs': total,
            'open': open_ncs,
            'closed': closed,
            'closure_rate': round((closed / total * 100) if total > 0 else 0, 2),
            'avg_closure_days': round(avg_closure_days, 1),
            'status_breakdown': dict(status_counts),
            'severity_breakdown': dict(severity_counts),
            'category_breakdown': dict(category_counts),
            'customer_impact_count': customer_impact_count,
            'total_cost_impact': round(total_cost, 2)
        }
    
    def overdue_ncs_report(self) -> list:
        """
        Report on overdue non-conformances
        
        Returns:
            List of overdue NC dictionaries
        """
        today = datetime.now()
        
        overdue_ncs = self.session.query(NonConformance).filter(
            and_(
                NonConformance.status != 'closed',
                NonConformance.target_closure_date < today
            )
        ).order_by(NonConformance.target_closure_date).all()
        
        results = []
        for nc in overdue_ncs:
            days_overdue = (today - nc.target_closure_date).days
            
            results.append({
                'nc_number': nc.nc_number,
                'title': nc.title,
                'severity': nc.severity,
                'status': nc.status,
                'target_closure_date': nc.target_closure_date.strftime('%Y-%m-%d'),
                'days_overdue': days_overdue,
                'assigned_to': nc.assigned_to.full_name if nc.assigned_to else 'Unassigned'
            })
        
        return results
    
    # ========================================================================
    # PERFORMANCE REPORTS
    # ========================================================================
    
    def inspector_performance_report(self, start_date: datetime = None,
                                    end_date: datetime = None) -> list:
        """
        Report on inspector performance
        
        Args:
            start_date: Start date for filtering
            end_date: End date for filtering
            
        Returns:
            List of inspector performance data
        """
        query = self.session.query(
            User.id,
            User.full_name,
            User.department,
            func.count(Record.id).label('total_inspections'),
            func.avg(Record.compliance_score).label('avg_score'),
            func.sum(case((Record.overall_compliance == True, 1), else_=0)).label('passed'),
            func.sum(case((Record.overall_compliance == False, 1), else_=0)).label('failed')
        ).join(
            Record, Record.created_by_id == User.id
        )
        
        if start_date:
            query = query.filter(Record.created_at >= start_date)
        if end_date:
            query = query.filter(Record.created_at <= end_date)
        
        query = query.group_by(User.id).order_by(
            func.count(Record.id).desc()
        )
        
        results = []
        for row in query.all():
            total = row.total_inspections
            passed = row.passed or 0
            failed = row.failed or 0
            
            results.append({
                'inspector_id': row.id,
                'name': row.full_name,
                'department': row.department,
                'total_inspections': total,
                'passed': int(passed),
                'failed': int(failed),
                'pass_rate': round((passed / total * 100) if total > 0 else 0, 2),
                'avg_score': round(float(row.avg_score or 0), 2)
            })
        
        return results
    
    def department_performance_report(self) -> list:
        """
        Report on department performance
        
        Returns:
            List of department performance data
        """
        dept_data = self.session.query(
            Record.department,
            func.count(Record.id).label('total'),
            func.avg(Record.compliance_score).label('avg_score'),
            func.sum(case((Record.overall_compliance == True, 1), else_=0)).label('passed'),
            func.sum(case((Record.overall_compliance == False, 1), else_=0)).label('failed')
        ).filter(
            Record.department.isnot(None)
        ).group_by(
            Record.department
        ).order_by(
            func.avg(Record.compliance_score).desc()
        ).all()
        
        results = []
        for row in dept_data:
            total = row.total
            passed = row.passed or 0
            failed = row.failed or 0
            
            results.append({
                'department': row.department,
                'total_records': total,
                'passed': int(passed),
                'failed': int(failed),
                'pass_rate': round((passed / total * 100) if total > 0 else 0, 2),
                'avg_score': round(float(row.avg_score or 0), 2)
            })
        
        return results
    
    # ========================================================================
    # CUSTOM REPORTS
    # ========================================================================
    
    def export_report_to_dataframe(self, report_data: dict or list) -> pd.DataFrame:
        """
        Convert report data to pandas DataFrame for easy export
        
        Args:
            report_data: Report data (dict or list of dicts)
            
        Returns:
            pandas DataFrame
        """
        if isinstance(report_data, dict):
            # If it's a single dict with nested data, try to extract the list
            for key, value in report_data.items():
                if isinstance(value, list):
                    return pd.DataFrame(value)
            # Otherwise, convert the dict itself
            return pd.DataFrame([report_data])
        else:
            return pd.DataFrame(report_data)
    
    def dashboard_summary(self) -> dict:
        """
        Get summary data for dashboard display
        
        Returns:
            Dictionary with key metrics
        """
        # Get last 30 days data
        thirty_days_ago = datetime.now() - timedelta(days=30)
        
        # Total records (last 30 days)
        total_records = self.session.query(Record).filter(
            Record.created_at >= thirty_days_ago
        ).count()
        
        # Pending approvals
        pending_approvals = self.session.query(Record).filter(
            Record.status.in_(['submitted', 'under_review'])
        ).count()
        
        # Open NCs
        open_ncs = self.session.query(NonConformance).filter(
            NonConformance.status != 'closed'
        ).count()
        
        # Critical NCs
        critical_ncs = self.session.query(NonConformance).filter(
            and_(
                NonConformance.status != 'closed',
                NonConformance.severity == 'critical'
            )
        ).count()
        
        # Average compliance score (last 30 days)
        avg_compliance = self.session.query(
            func.avg(Record.compliance_score)
        ).filter(
            Record.created_at >= thirty_days_ago
        ).scalar() or 0
        
        # Recent records
        recent_records = self.session.query(Record).order_by(
            Record.created_at.desc()
        ).limit(5).all()
        
        recent_records_data = [{
            'id': r.id,
            'record_number': r.record_number,
            'title': r.title,
            'status': r.status,
            'created_at': r.created_at.strftime('%Y-%m-%d %H:%M'),
            'compliance': 'Pass' if r.overall_compliance else 'Fail' if r.overall_compliance is not None else 'Pending'
        } for r in recent_records]
        
        return {
            'total_records_30d': total_records,
            'pending_approvals': pending_approvals,
            'open_ncs': open_ncs,
            'critical_ncs': critical_ncs,
            'avg_compliance_30d': round(float(avg_compliance), 2),
            'recent_records': recent_records_data
        }
    
    def template_usage_report(self) -> list:
        """
        Report on template usage statistics
        
        Returns:
            List of template usage data
        """
        usage_data = self.session.query(
            TestTemplate.id,
            TestTemplate.code,
            TestTemplate.name,
            TestTemplate.category,
            func.count(Record.id).label('usage_count'),
            func.avg(Record.compliance_score).label('avg_score')
        ).outerjoin(
            Record, Record.template_id == TestTemplate.id
        ).group_by(
            TestTemplate.id
        ).order_by(
            func.count(Record.id).desc()
        ).all()
        
        results = []
        for row in usage_data:
            results.append({
                'template_id': row.id,
                'code': row.code,
                'name': row.name,
                'category': row.category,
                'usage_count': row.usage_count,
                'avg_score': round(float(row.avg_score or 0), 2)
            })
        
        return results


# Convenience functions
def get_compliance_summary(session, start_date=None, end_date=None):
    """Quick compliance summary"""
    generator = ReportsGenerator(session)
    return generator.compliance_summary_report(start_date, end_date)


def get_dashboard_data(session):
    """Quick dashboard summary"""
    generator = ReportsGenerator(session)
    return generator.dashboard_summary()
