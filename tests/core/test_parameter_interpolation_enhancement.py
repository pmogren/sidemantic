"""Tests for enhanced parameter interpolation functionality."""

import pytest

from sidemantic.core.parameter import Parameter, ParameterSet


class TestParameterInterpolationEnhancement:
    """Test enhanced parameter interpolation with both {{ }} and ${ } formats."""

    def test_dollar_sign_parameter_interpolation(self):
        """Test that ${param} format is properly interpolated."""
        params = {
            "status": Parameter(name="status", type="string", default_value="pending"),
            "amount": Parameter(name="amount", type="number", default_value=0),
        }
        
        param_set = ParameterSet(params, {"status": "completed", "amount": 100})
        
        sql = "SELECT * FROM orders WHERE status = ${status} AND amount >= ${amount}"
        result = param_set.interpolate(sql)
        
        assert result == "SELECT * FROM orders WHERE status = 'completed' AND amount >= 100"

    def test_curly_brace_parameter_interpolation(self):
        """Test that {{ param }} format is properly interpolated."""
        params = {
            "status": Parameter(name="status", type="string", default_value="pending"),
            "amount": Parameter(name="amount", type="number", default_value=0),
        }
        
        param_set = ParameterSet(params, {"status": "completed", "amount": 100})
        
        sql = "SELECT * FROM orders WHERE status = {{ status }} AND amount >= {{ amount }}"
        result = param_set.interpolate(sql)
        
        assert result == "SELECT * FROM orders WHERE status = 'completed' AND amount >= 100"

    def test_mixed_parameter_formats(self):
        """Test interpolation with both {{ }} and ${ } formats in the same SQL."""
        params = {
            "status": Parameter(name="status", type="string", default_value="pending"),
            "amount": Parameter(name="amount", type="number", default_value=0),
            "region": Parameter(name="region", type="string", default_value="US"),
        }
        
        param_set = ParameterSet(params, {"status": "completed", "amount": 100, "region": "EU"})
        
        sql = "SELECT * FROM orders WHERE status = ${status} AND amount >= {{ amount }} AND region = ${region}"
        result = param_set.interpolate(sql)
        
        assert result == "SELECT * FROM orders WHERE status = 'completed' AND amount >= 100 AND region = 'EU'"

    def test_parameter_interpolation_with_spacing_variations(self):
        """Test parameter interpolation with various spacing patterns."""
        params = {
            "status": Parameter(name="status", type="string", default_value="pending"),
        }
        
        param_set = ParameterSet(params, {"status": "completed"})
        
        # Test various spacing patterns for both formats
        test_cases = [
            ("${status}", "'completed'"),
            ("${ status }", "'completed'"),
            ("${  status  }", "'completed'"),
            ("{{status}}", "'completed'"),
            ("{{ status }}", "'completed'"),
            ("{{  status  }}", "'completed'"),
        ]
        
        for sql, expected in test_cases:
            result = param_set.interpolate(sql)
            assert result == expected

    def test_parameter_interpolation_with_unknown_parameters(self):
        """Test that unknown parameters are left unchanged."""
        params = {
            "status": Parameter(name="status", type="string", default_value="pending"),
        }
        
        param_set = ParameterSet(params, {"status": "completed"})
        
        sql = "SELECT * FROM orders WHERE status = ${status} AND region = ${region} AND type = {{ type }}"
        result = param_set.interpolate(sql)
        
        # Known parameter should be interpolated, unknown ones left unchanged
        assert result == "SELECT * FROM orders WHERE status = 'completed' AND region = ${region} AND type = {{ type }}"

    def test_parameter_interpolation_with_default_values(self):
        """Test parameter interpolation using default values when not provided."""
        params = {
            "status": Parameter(name="status", type="string", default_value="pending"),
            "amount": Parameter(name="amount", type="number", default_value=100),
        }
        
        param_set = ParameterSet(params, {})  # No values provided
        
        sql = "SELECT * FROM orders WHERE status = ${status} AND amount >= ${amount}"
        result = param_set.interpolate(sql)
        
        # Should use default values
        assert result == "SELECT * FROM orders WHERE status = 'pending' AND amount >= 100"

    def test_parameter_interpolation_with_mixed_defaults_and_values(self):
        """Test parameter interpolation with some values provided and some using defaults."""
        params = {
            "status": Parameter(name="status", type="string", default_value="pending"),
            "amount": Parameter(name="amount", type="number", default_value=100),
            "region": Parameter(name="region", type="string", default_value="US"),
        }
        
        param_set = ParameterSet(params, {"status": "completed"})  # Only status provided
        
        sql = "SELECT * FROM orders WHERE status = ${status} AND amount >= ${amount} AND region = ${region}"
        result = param_set.interpolate(sql)
        
        # status should use provided value, others should use defaults
        assert result == "SELECT * FROM orders WHERE status = 'completed' AND amount >= 100 AND region = 'US'"

    def test_parameter_interpolation_with_complex_sql(self):
        """Test parameter interpolation with complex SQL expressions."""
        params = {
            "min_amount": Parameter(name="min_amount", type="number", default_value=100),
            "max_amount": Parameter(name="max_amount", type="number", default_value=1000),
            "status": Parameter(name="status", type="string", default_value="completed"),
        }
        
        param_set = ParameterSet(params, {"min_amount": 200, "max_amount": 800, "status": "pending"})
        
        sql = """
        SELECT 
            COUNT(*) as order_count,
            SUM(amount) as total_amount
        FROM orders 
        WHERE amount BETWEEN ${min_amount} AND ${max_amount}
        AND status = {{ status }}
        AND created_at >= '2024-01-01'
        """
        result = param_set.interpolate(sql)
        
        assert "200" in result
        assert "800" in result
        assert "'pending'" in result
        assert "${min_amount}" not in result
        assert "${max_amount}" not in result
        assert "{{ status }}" not in result

    def test_parameter_interpolation_with_nested_expressions(self):
        """Test parameter interpolation with nested SQL expressions."""
        params = {
            "base_rate": Parameter(name="base_rate", type="number", default_value=0.1),
            "multiplier": Parameter(name="multiplier", type="number", default_value=2),
        }
        
        param_set = ParameterSet(params, {"base_rate": 0.15, "multiplier": 1.5})
        
        sql = "SELECT amount * (${base_rate} * ${multiplier}) as adjusted_amount FROM orders"
        result = param_set.interpolate(sql)
        
        assert result == "SELECT amount * (0.15 * 1.5) as adjusted_amount FROM orders"

    def test_parameter_interpolation_with_string_escaping(self):
        """Test parameter interpolation with string parameters that need escaping."""
        params = {
            "description": Parameter(name="description", type="string", default_value="O'Reilly"),
            "company": Parameter(name="company", type="string", default_value="Smith & Associates"),
        }
        
        param_set = ParameterSet(params, {"description": "O'Reilly & Associates", "company": "Johnson's Company"})
        
        sql = "SELECT * FROM products WHERE description = ${description} AND company = {{ company }}"
        result = param_set.interpolate(sql)
        
        # Check that single quotes are properly escaped
        assert "'O''Reilly & Associates'" in result
        assert "'Johnson''s Company'" in result
        assert "${description}" not in result
        assert "{{ company }}" not in result

    def test_parameter_interpolation_with_boolean_parameters(self):
        """Test parameter interpolation with boolean parameters."""
        params = {
            "include_tax": Parameter(name="include_tax", type="yesno", default_value=False),
            "is_active": Parameter(name="is_active", type="yesno", default_value=True),
        }
        
        param_set = ParameterSet(params, {"include_tax": True, "is_active": False})
        
        sql = "SELECT * FROM orders WHERE include_tax = ${include_tax} AND is_active = {{ is_active }}"
        result = param_set.interpolate(sql)
        
        assert result == "SELECT * FROM orders WHERE include_tax = TRUE AND is_active = FALSE"

    def test_parameter_interpolation_with_date_parameters(self):
        """Test parameter interpolation with date parameters."""
        params = {
            "start_date": Parameter(name="start_date", type="date", default_value="2024-01-01"),
            "end_date": Parameter(name="end_date", type="date", default_value="2024-12-31"),
        }
        
        param_set = ParameterSet(params, {"start_date": "2024-06-01", "end_date": "2024-06-30"})
        
        sql = "SELECT * FROM orders WHERE order_date >= ${start_date} AND order_date <= {{ end_date }}"
        result = param_set.interpolate(sql)
        
        assert result == "SELECT * FROM orders WHERE order_date >= '2024-06-01' AND order_date <= '2024-06-30'"

    def test_parameter_interpolation_with_unquoted_parameters(self):
        """Test parameter interpolation with unquoted parameters."""
        params = {
            "table_name": Parameter(name="table_name", type="unquoted", default_value="orders"),
            "column_name": Parameter(name="column_name", type="unquoted", default_value="status"),
        }
        
        param_set = ParameterSet(params, {"table_name": "customers", "column_name": "region"})
        
        sql = "SELECT * FROM ${table_name} WHERE ${column_name} = 'active'"
        result = param_set.interpolate(sql)
        
        assert result == "SELECT * FROM customers WHERE region = 'active'"

    def test_parameter_interpolation_with_regex_special_characters(self):
        """Test parameter interpolation with parameter names that contain regex special characters."""
        params = {
            "param.with.dots": Parameter(name="param.with.dots", type="string", default_value="value1"),
            "param-with-dashes": Parameter(name="param-with-dashes", type="string", default_value="value2"),
            "param_with_underscores": Parameter(name="param_with_underscores", type="string", default_value="value3"),
        }
        
        param_set = ParameterSet(params, {
            "param.with.dots": "test1",
            "param-with-dashes": "test2", 
            "param_with_underscores": "test3"
        })
        
        sql = "SELECT ${param.with.dots}, ${param-with-dashes}, ${param_with_underscores}"
        result = param_set.interpolate(sql)
        
        assert result == "SELECT 'test1', 'test2', 'test3'"

    def test_parameter_interpolation_performance_with_many_parameters(self):
        """Test parameter interpolation performance with many parameters."""
        # Create many parameters
        params = {}
        values = {}
        for i in range(100):
            param_name = f"param_{i}"
            params[param_name] = Parameter(name=param_name, type="number", default_value=i)
            values[param_name] = i * 2
        
        param_set = ParameterSet(params, values)
        
        # Create SQL with many parameter references
        sql_parts = []
        for i in range(100):
            sql_parts.append(f"${param_name} = {i * 2}")
        
        sql = "SELECT * FROM test WHERE " + " AND ".join(sql_parts)
        
        result = param_set.interpolate(sql)
        
        # Verify all parameters were interpolated
        for i in range(100):
            assert str(i * 2) in result
            assert f"${{param_{i}}}" not in result

    def test_parameter_interpolation_with_empty_sql(self):
        """Test parameter interpolation with empty SQL string."""
        params = {
            "status": Parameter(name="status", type="string", default_value="pending"),
        }
        
        param_set = ParameterSet(params, {"status": "completed"})
        
        result = param_set.interpolate("")
        assert result == ""

    def test_parameter_interpolation_with_no_parameters(self):
        """Test parameter interpolation with SQL that has no parameter references."""
        params = {
            "status": Parameter(name="status", type="string", default_value="pending"),
        }
        
        param_set = ParameterSet(params, {"status": "completed"})
        
        sql = "SELECT * FROM orders WHERE amount > 100"
        result = param_set.interpolate(sql)
        
        assert result == sql  # Should be unchanged
