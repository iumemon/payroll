"""
Unit tests for the payroll service.

Tests payroll calculations, tax computations, deduction processing, and business logic.
"""

import pytest
from decimal import Decimal
from datetime import datetime, date
from unittest.mock import Mock, patch

from app.services.payroll_service import PayrollService
from app.models.employee import Employee
from app.models.payroll import PayrollRecord, PayPeriod
from app.models.enums import (
    EmploymentType, PayrollFrequency, PayrollStatus, 
    EmployeeStatus, BenefitType, DeductionType
)
from app.core.config import get_settings

settings = get_settings()


@pytest.mark.unit
class TestPayrollCalculations:
    """Test core payroll calculation logic."""
    
    @pytest.fixture
    def sample_employee(self):
        """Create a sample employee for testing."""
        return Employee(
            id=1,
            employee_id="EMP001",
            first_name="John",
            last_name="Doe",
            email="john.doe@company.com",
            department="Engineering",
            position="Software Developer",
            employment_type=EmploymentType.FULL_TIME,
            status=EmployeeStatus.ACTIVE,
            salary=75000.00,
            hourly_rate=36.06,
            federal_tax_allowances=2,
            state_tax_allowances=1,
            additional_federal_withholding=0.0,
            additional_state_withholding=0.0,
            health_insurance_premium=150.00,
            dental_insurance_premium=25.00,
            vision_insurance_premium=10.00,
            retirement_401k_percent=0.05,
            other_deductions=0.0
        )
    
    @pytest.fixture
    def sample_pay_period(self):
        """Create a sample pay period for testing."""
        return PayPeriod(
            id=1,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 15),
            pay_date=date(2024, 1, 20),
            frequency=PayrollFrequency.BI_WEEKLY,
            is_processed=False
        )
    
    @pytest.fixture
    def payroll_service(self):
        """Create a PayrollService instance."""
        mock_db = Mock()
        return PayrollService(db=mock_db)
    
    def test_calculate_gross_pay_salary(self, payroll_service, sample_employee, sample_pay_period):
        """Test gross pay calculation for salaried employee."""
        sample_employee.employment_type = EmploymentType.FULL_TIME
        
        gross_pay = payroll_service.calculate_gross_pay(
            employee=sample_employee,
            pay_period=sample_pay_period,
            regular_hours=80,  # 2 weeks * 40 hours
            overtime_hours=0
        )
        
        # Bi-weekly salary: $75,000 / 26 pay periods = $2,884.62
        expected_gross = Decimal("2884.62")
        assert abs(gross_pay - expected_gross) < Decimal("0.01")
    
    def test_calculate_gross_pay_hourly(self, payroll_service, sample_employee, sample_pay_period):
        """Test gross pay calculation for hourly employee."""
        sample_employee.employment_type = EmploymentType.PART_TIME
        sample_employee.salary = None
        
        gross_pay = payroll_service.calculate_gross_pay(
            employee=sample_employee,
            pay_period=sample_pay_period,
            regular_hours=60,
            overtime_hours=0
        )
        
        # 60 hours * $36.06/hour = $2,163.60
        expected_gross = Decimal("2163.60")
        assert abs(gross_pay - expected_gross) < Decimal("0.01")
    
    def test_calculate_gross_pay_with_overtime(self, payroll_service, sample_employee, sample_pay_period):
        """Test gross pay calculation with overtime."""
        sample_employee.employment_type = EmploymentType.PART_TIME
        sample_employee.salary = None
        
        gross_pay = payroll_service.calculate_gross_pay(
            employee=sample_employee,
            pay_period=sample_pay_period,
            regular_hours=40,
            overtime_hours=10
        )
        
        # Regular: 40 * $36.06 = $1,442.40
        # Overtime: 10 * $36.06 * 1.5 = $540.90
        # Total: $1,983.30
        expected_gross = Decimal("1983.30")
        assert abs(gross_pay - expected_gross) < Decimal("0.01")
    
    def test_calculate_federal_tax(self, payroll_service, sample_employee):
        """Test federal tax calculation."""
        gross_pay = Decimal("2884.62")
        
        federal_tax = payroll_service.calculate_federal_tax(
            gross_pay=gross_pay,
            allowances=sample_employee.federal_tax_allowances,
            additional_withholding=sample_employee.additional_federal_withholding,
            pay_frequency=PayrollFrequency.BI_WEEKLY
        )
        
        # Federal tax should be calculated based on tax brackets
        assert isinstance(federal_tax, Decimal)
        assert federal_tax >= Decimal("0")
        assert federal_tax < gross_pay  # Tax shouldn't exceed gross pay
    
    def test_calculate_state_tax(self, payroll_service, sample_employee):
        """Test state tax calculation."""
        gross_pay = Decimal("2884.62")
        
        state_tax = payroll_service.calculate_state_tax(
            gross_pay=gross_pay,
            allowances=sample_employee.state_tax_allowances,
            additional_withholding=sample_employee.additional_state_withholding,
            pay_frequency=PayrollFrequency.BI_WEEKLY
        )
        
        # State tax should be calculated
        assert isinstance(state_tax, Decimal)
        assert state_tax >= Decimal("0")
        assert state_tax < gross_pay
    
    def test_calculate_social_security_tax(self, payroll_service):
        """Test Social Security tax calculation."""
        gross_pay = Decimal("2884.62")
        
        ss_tax = payroll_service.calculate_social_security_tax(gross_pay)
        
        # Social Security tax: 6.2% of gross pay
        expected_ss = gross_pay * Decimal(str(settings.SOCIAL_SECURITY_RATE))
        assert abs(ss_tax - expected_ss) < Decimal("0.01")
    
    def test_calculate_medicare_tax(self, payroll_service):
        """Test Medicare tax calculation."""
        gross_pay = Decimal("2884.62")
        
        medicare_tax = payroll_service.calculate_medicare_tax(gross_pay)
        
        # Medicare tax: 1.45% of gross pay
        expected_medicare = gross_pay * Decimal(str(settings.MEDICARE_RATE))
        assert abs(medicare_tax - expected_medicare) < Decimal("0.01")
    
    def test_calculate_social_security_wage_cap(self, payroll_service):
        """Test Social Security tax with wage cap."""
        # Test with income above Social Security wage base
        high_gross_pay = Decimal("10000.00")
        ytd_gross = Decimal("150000.00")  # Above 2024 SS wage base
        
        ss_tax = payroll_service.calculate_social_security_tax(
            gross_pay=high_gross_pay,
            ytd_gross=ytd_gross
        )
        
        # Should be $0 if already above wage base
        assert ss_tax == Decimal("0")
    
    def test_calculate_benefit_deductions(self, payroll_service, sample_employee):
        """Test benefit deduction calculations."""
        deductions = payroll_service.calculate_benefit_deductions(sample_employee)
        
        expected_health = Decimal(str(sample_employee.health_insurance_premium))
        expected_dental = Decimal(str(sample_employee.dental_insurance_premium))
        expected_vision = Decimal(str(sample_employee.vision_insurance_premium))
        
        assert deductions["health_insurance"] == expected_health
        assert deductions["dental_insurance"] == expected_dental
        assert deductions["vision_insurance"] == expected_vision
        assert deductions["total"] == expected_health + expected_dental + expected_vision
    
    def test_calculate_401k_deduction(self, payroll_service, sample_employee):
        """Test 401k deduction calculation."""
        gross_pay = Decimal("2884.62")
        
        deduction = payroll_service.calculate_401k_deduction(
            gross_pay=gross_pay,
            contribution_percent=sample_employee.retirement_401k_percent
        )
        
        # 5% of gross pay
        expected_401k = gross_pay * Decimal(str(sample_employee.retirement_401k_percent))
        assert abs(deduction - expected_401k) < Decimal("0.01")


@pytest.mark.unit
class TestPayrollValidation:
    """Test payroll validation logic."""
    
    @pytest.fixture
    def payroll_service(self):
        """Create a PayrollService instance."""
        mock_db = Mock()
        return PayrollService(db=mock_db)
    
    def test_validate_employee_active(self, payroll_service):
        """Test employee status validation."""
        active_employee = Employee(status=EmployeeStatus.ACTIVE)
        inactive_employee = Employee(status=EmployeeStatus.INACTIVE)
        
        assert payroll_service.validate_employee_for_payroll(active_employee) is True
        assert payroll_service.validate_employee_for_payroll(inactive_employee) is False
    
    def test_validate_employee_salary_data(self, payroll_service):
        """Test employee salary data validation."""
        # Full-time employee with salary
        ft_employee = Employee(
            employment_type=EmploymentType.FULL_TIME,
            salary=75000.00,
            status=EmployeeStatus.ACTIVE
        )
        
        # Part-time employee with hourly rate
        pt_employee = Employee(
            employment_type=EmploymentType.PART_TIME,
            hourly_rate=25.00,
            status=EmployeeStatus.ACTIVE
        )
        
        # Invalid: Full-time without salary
        invalid_employee = Employee(
            employment_type=EmploymentType.FULL_TIME,
            salary=None,
            hourly_rate=None,
            status=EmployeeStatus.ACTIVE
        )
        
        assert payroll_service.validate_employee_for_payroll(ft_employee) is True
        assert payroll_service.validate_employee_for_payroll(pt_employee) is True
        assert payroll_service.validate_employee_for_payroll(invalid_employee) is False
    
    def test_validate_pay_period(self, payroll_service):
        """Test pay period validation."""
        valid_period = PayPeriod(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 15),
            pay_date=date(2024, 1, 20),
            is_processed=False
        )
        
        processed_period = PayPeriod(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 15),
            pay_date=date(2024, 1, 20),
            is_processed=True
        )
        
        assert payroll_service.validate_pay_period(valid_period) is True
        assert payroll_service.validate_pay_period(processed_period) is False
    
    def test_validate_hours(self, payroll_service):
        """Test hours validation."""
        assert payroll_service.validate_hours(40, 0) is True
        assert payroll_service.validate_hours(40, 10) is True
        assert payroll_service.validate_hours(-5, 0) is False
        assert payroll_service.validate_hours(40, -5) is False
        assert payroll_service.validate_hours(200, 0) is False  # Too many hours


@pytest.mark.unit
class TestPayrollRecordCreation:
    """Test payroll record creation and processing."""
    
    @pytest.fixture
    def payroll_service(self):
        """Create a PayrollService instance."""
        mock_db = Mock()
        return PayrollService(db=mock_db)
    
    @pytest.fixture
    def sample_employee(self):
        """Create a sample employee."""
        return Employee(
            id=1,
            employee_id="EMP001",
            first_name="John",
            last_name="Doe",
            salary=75000.00,
            employment_type=EmploymentType.FULL_TIME,
            status=EmployeeStatus.ACTIVE,
            federal_tax_allowances=2,
            state_tax_allowances=1,
            health_insurance_premium=150.00,
            retirement_401k_percent=0.05
        )
    
    @pytest.fixture
    def sample_pay_period(self):
        """Create a sample pay period."""
        return PayPeriod(
            id=1,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 15),
            frequency=PayrollFrequency.BI_WEEKLY
        )
    
    def test_create_payroll_record(self, payroll_service, sample_employee, sample_pay_period):
        """Test payroll record creation."""
        with patch.object(payroll_service, 'calculate_gross_pay', return_value=Decimal("2884.62")):
            with patch.object(payroll_service, 'calculate_federal_tax', return_value=Decimal("400.00")):
                with patch.object(payroll_service, 'calculate_state_tax', return_value=Decimal("150.00")):
                    with patch.object(payroll_service, 'calculate_social_security_tax', return_value=Decimal("178.85")):
                        with patch.object(payroll_service, 'calculate_medicare_tax', return_value=Decimal("41.83")):
                            
                            record = payroll_service.create_payroll_record(
                                employee=sample_employee,
                                pay_period=sample_pay_period,
                                regular_hours=80,
                                overtime_hours=0
                            )
                            
                            assert isinstance(record, PayrollRecord)
                            assert record.employee_id == sample_employee.id
                            assert record.pay_period_id == sample_pay_period.id
                            assert record.gross_pay == Decimal("2884.62")
                            assert record.status == PayrollStatus.CALCULATED
    
    def test_calculate_net_pay(self, payroll_service):
        """Test net pay calculation."""
        gross_pay = Decimal("2884.62")
        federal_tax = Decimal("400.00")
        state_tax = Decimal("150.00")
        ss_tax = Decimal("178.85")
        medicare_tax = Decimal("41.83")
        benefit_deductions = Decimal("185.00")  # Health + dental + vision
        retirement_401k = Decimal("144.23")
        
        net_pay = payroll_service.calculate_net_pay(
            gross_pay=gross_pay,
            federal_tax=federal_tax,
            state_tax=state_tax,
            social_security_tax=ss_tax,
            medicare_tax=medicare_tax,
            benefit_deductions=benefit_deductions,
            retirement_401k=retirement_401k
        )
        
        expected_net = gross_pay - (federal_tax + state_tax + ss_tax + medicare_tax + benefit_deductions + retirement_401k)
        assert abs(net_pay - expected_net) < Decimal("0.01")
    
    def test_payroll_record_validation(self, payroll_service):
        """Test payroll record validation."""
        valid_record = PayrollRecord(
            employee_id=1,
            pay_period_id=1,
            gross_pay=Decimal("2884.62"),
            federal_tax=Decimal("400.00"),
            state_tax=Decimal("150.00"),
            social_security_tax=Decimal("178.85"),
            medicare_tax=Decimal("41.83"),
            net_pay=Decimal("2113.94")
        )
        
        # Test that net pay is calculated correctly
        calculated_net = (valid_record.gross_pay - 
                         valid_record.federal_tax - 
                         valid_record.state_tax - 
                         valid_record.social_security_tax - 
                         valid_record.medicare_tax)
        
        assert abs(valid_record.net_pay - calculated_net) < Decimal("0.01")


@pytest.mark.unit
class TestPayrollBusinessLogic:
    """Test payroll business logic and edge cases."""
    
    @pytest.fixture
    def payroll_service(self):
        """Create a PayrollService instance."""
        mock_db = Mock()
        return PayrollService(db=mock_db)
    
    def test_different_pay_frequencies(self, payroll_service):
        """Test calculations for different pay frequencies."""
        annual_salary = Decimal("75000.00")
        
        # Weekly (52 pay periods)
        weekly_gross = payroll_service.calculate_salary_gross_pay(
            annual_salary, PayrollFrequency.WEEKLY
        )
        assert abs(weekly_gross - (annual_salary / 52)) < Decimal("0.01")
        
        # Bi-weekly (26 pay periods)
        biweekly_gross = payroll_service.calculate_salary_gross_pay(
            annual_salary, PayrollFrequency.BI_WEEKLY
        )
        assert abs(biweekly_gross - (annual_salary / 26)) < Decimal("0.01")
        
        # Semi-monthly (24 pay periods)
        semimonthly_gross = payroll_service.calculate_salary_gross_pay(
            annual_salary, PayrollFrequency.SEMI_MONTHLY
        )
        assert abs(semimonthly_gross - (annual_salary / 24)) < Decimal("0.01")
        
        # Monthly (12 pay periods)
        monthly_gross = payroll_service.calculate_salary_gross_pay(
            annual_salary, PayrollFrequency.MONTHLY
        )
        assert abs(monthly_gross - (annual_salary / 12)) < Decimal("0.01")
    
    def test_zero_values_handling(self, payroll_service):
        """Test handling of zero values."""
        # Zero gross pay
        assert payroll_service.calculate_federal_tax(Decimal("0"), 0, 0, PayrollFrequency.BI_WEEKLY) == Decimal("0")
        assert payroll_service.calculate_social_security_tax(Decimal("0")) == Decimal("0")
        assert payroll_service.calculate_medicare_tax(Decimal("0")) == Decimal("0")
        
        # Zero rates
        assert payroll_service.calculate_401k_deduction(Decimal("1000"), 0.0) == Decimal("0")
    
    def test_rounding_precision(self, payroll_service):
        """Test that calculations maintain proper decimal precision."""
        gross_pay = Decimal("2884.627")  # Extra precision
        
        ss_tax = payroll_service.calculate_social_security_tax(gross_pay)
        medicare_tax = payroll_service.calculate_medicare_tax(gross_pay)
        
        # Results should be rounded to 2 decimal places
        assert ss_tax.as_tuple().exponent >= -2
        assert medicare_tax.as_tuple().exponent >= -2
    
    def test_maximum_values_handling(self, payroll_service):
        """Test handling of maximum values and edge cases."""
        # Very high gross pay
        high_gross = Decimal("50000.00")
        
        ss_tax = payroll_service.calculate_social_security_tax(high_gross)
        medicare_tax = payroll_service.calculate_medicare_tax(high_gross)
        
        # Taxes should still be calculated correctly
        assert ss_tax > Decimal("0")
        assert medicare_tax > Decimal("0")
        assert ss_tax < high_gross
        assert medicare_tax < high_gross


@pytest.mark.unit
class TestPayrollErrorHandling:
    """Test error handling in payroll calculations."""
    
    @pytest.fixture
    def payroll_service(self):
        """Create a PayrollService instance."""
        mock_db = Mock()
        return PayrollService(db=mock_db)
    
    def test_invalid_employee_data(self, payroll_service):
        """Test handling of invalid employee data."""
        invalid_employee = Employee(
            employment_type=EmploymentType.FULL_TIME,
            salary=None,  # Missing salary for full-time employee
            hourly_rate=None,
            status=EmployeeStatus.ACTIVE
        )
        
        with pytest.raises((ValueError, AttributeError)):
            payroll_service.validate_employee_for_payroll(invalid_employee)
    
    def test_negative_values(self, payroll_service):
        """Test handling of negative values."""
        with pytest.raises(ValueError):
            payroll_service.calculate_social_security_tax(Decimal("-1000"))
        
        with pytest.raises(ValueError):
            payroll_service.calculate_medicare_tax(Decimal("-1000"))
    
    def test_invalid_pay_frequency(self, payroll_service):
        """Test handling of invalid pay frequency."""
        with pytest.raises((ValueError, AttributeError)):
            payroll_service.calculate_salary_gross_pay(
                Decimal("75000"), 
                "INVALID_FREQUENCY"
            )
    
    def test_database_error_handling(self, payroll_service):
        """Test handling of database errors."""
        # Mock database error
        payroll_service.db.add.side_effect = Exception("Database error")
        
        employee = Employee(id=1, salary=75000.00, employment_type=EmploymentType.FULL_TIME)
        pay_period = PayPeriod(id=1, frequency=PayrollFrequency.BI_WEEKLY)
        
        with pytest.raises(Exception):
            payroll_service.create_payroll_record(employee, pay_period, 80, 0)