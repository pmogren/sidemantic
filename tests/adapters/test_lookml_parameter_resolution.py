"""Tests for LookML adapter parameter resolution functionality."""

import pytest
from pathlib import Path

from sidemantic.adapters.lookml import LookMLAdapter
from sidemantic.core.semantic_graph import SemanticGraph


class TestLookMLParameterResolution:
    """Test parameter resolution in LookML adapter."""

    def test_parameter_resolution_in_measures(self):
        """Test that ${param_name} is resolved to actual dimension SQL in measures."""
        # Create a temporary LookML file with parameter references
        lookml_content = """
view: test_view {
  sql_table_name: test_table ;;
  
  dimension: annual_gmv {
    type: number
    sql: ${TABLE}.annual_gmv ;;
  }
  
  dimension: supplier_id {
    type: number
    sql: ${TABLE}.supplier_id ;;
  }
  
  measure: total_annual_gmv {
    type: sum
    sql: ${annual_gmv} ;;
  }
  
  measure: average_annual_gmv {
    type: sum
    sql: ${annual_gmv} ;;
  }
}
"""
        
        # Write to temporary file
        test_file = Path("test_parameter_resolution.lkml")
        test_file.write_text(lookml_content)
        
        try:
            # Parse with LookML adapter
            adapter = LookMLAdapter()
            graph = adapter.parse(test_file)
            
            # Get the model
            model = graph.get_model("test_view")
            assert model is not None
            
            # Check that measures have resolved SQL
            total_gmv_measure = model.get_metric("total_annual_gmv")
            assert total_gmv_measure is not None
            assert total_gmv_measure.sql == "annual_gmv"  # {model} placeholder removed
            
            avg_gmv_measure = model.get_metric("average_annual_gmv")
            assert avg_gmv_measure is not None
            assert avg_gmv_measure.sql == "annual_gmv"  # {model} placeholder removed
            
        finally:
            # Clean up
            test_file.unlink()

    def test_parameter_resolution_with_multiple_dimensions(self):
        """Test parameter resolution when multiple dimensions are available."""
        lookml_content = """
view: test_view {
  sql_table_name: test_table ;;
  
  dimension: revenue {
    type: number
    sql: ${TABLE}.revenue ;;
  }
  
  dimension: cost {
    type: number
    sql: ${TABLE}.cost ;;
  }
  
  dimension: profit {
    type: number
    sql: ${TABLE}.profit ;;
  }
  
  measure: total_revenue {
    type: sum
    sql: ${revenue} ;;
  }
  
  measure: total_cost {
    type: sum
    sql: ${cost} ;;
  }
  
  measure: total_profit {
    type: sum
    sql: ${profit} ;;
  }
}
"""
        
        test_file = Path("test_multiple_params.lkml")
        test_file.write_text(lookml_content)
        
        try:
            adapter = LookMLAdapter()
            graph = adapter.parse(test_file)
            
            model = graph.get_model("test_view")
            assert model is not None
            
            # Check all measures have resolved SQL
            revenue_measure = model.get_metric("total_revenue")
            assert revenue_measure.sql == "revenue"
            
            cost_measure = model.get_metric("total_cost")
            assert cost_measure.sql == "cost"
            
            profit_measure = model.get_metric("total_profit")
            assert profit_measure.sql == "profit"
            
        finally:
            test_file.unlink()

    def test_parameter_resolution_with_complex_sql(self):
        """Test parameter resolution in complex SQL expressions."""
        lookml_content = """
view: test_view {
  sql_table_name: test_table ;;
  
  dimension: amount {
    type: number
    sql: ${TABLE}.amount ;;
  }
  
  dimension: tax_rate {
    type: number
    sql: ${TABLE}.tax_rate ;;
  }
  
  measure: total_with_tax {
    type: sum
    sql: ${amount} * (1 + ${tax_rate}) ;;
  }
  
  measure: tax_amount {
    type: sum
    sql: ${amount} * ${tax_rate} ;;
  }
}
"""
        
        test_file = Path("test_complex_sql.lkml")
        test_file.write_text(lookml_content)
        
        try:
            adapter = LookMLAdapter()
            graph = adapter.parse(test_file)
            
            model = graph.get_model("test_view")
            assert model is not None
            
            # Check complex expressions are resolved
            total_measure = model.get_metric("total_with_tax")
            assert total_measure.sql == "amount * (1 + tax_rate)"
            
            tax_measure = model.get_metric("tax_amount")
            assert tax_measure.sql == "amount * tax_rate"
            
        finally:
            test_file.unlink()

    def test_parameter_resolution_with_unknown_parameter(self):
        """Test that unknown parameters are left unchanged."""
        lookml_content = """
view: test_view {
  sql_table_name: test_table ;;
  
  dimension: amount {
    type: number
    sql: ${TABLE}.amount ;;
  }
  
  measure: total_amount {
    type: sum
    sql: ${amount} + ${unknown_param} ;;
  }
}
"""
        
        test_file = Path("test_unknown_param.lkml")
        test_file.write_text(lookml_content)
        
        try:
            adapter = LookMLAdapter()
            graph = adapter.parse(test_file)
            
            model = graph.get_model("test_view")
            assert model is not None
            
            # Check that unknown parameter is left unchanged
            total_measure = model.get_metric("total_amount")
            assert total_measure.sql == "amount + ${unknown_param}"
            
        finally:
            test_file.unlink()

    def test_parameter_resolution_with_table_replacement(self):
        """Test that ${TABLE} is properly replaced with {model} placeholder."""
        lookml_content = """
view: test_view {
  sql_table_name: test_table ;;
  
  dimension: amount {
    type: number
    sql: ${TABLE}.amount ;;
  }
  
  measure: total_amount {
    type: sum
    sql: ${amount} ;;
  }
}
"""
        
        test_file = Path("test_table_replacement.lkml")
        test_file.write_text(lookml_content)
        
        try:
            adapter = LookMLAdapter()
            graph = adapter.parse(test_file)
            
            model = graph.get_model("test_view")
            assert model is not None
            
            # Check that ${TABLE} was replaced and {model} removed
            amount_dim = model.get_dimension("amount")
            assert amount_dim.sql == "amount"
            
            # Check that parameter resolution works
            total_measure = model.get_metric("total_amount")
            assert total_measure.sql == "amount"
            
        finally:
            test_file.unlink()

    def test_parameter_resolution_in_derived_table(self):
        """Test parameter resolution in derived table views."""
        lookml_content = """
view: test_view {
  derived_table: {
    sql: SELECT 
             supplier_id,
             annual_gmv,
             amount
         FROM raw_suppliers ;;
  }
  
  dimension: supplier_id {
    type: number
    sql: ${TABLE}.supplier_id ;;
  }
  
  dimension: annual_gmv {
    type: number
    sql: ${TABLE}.annual_gmv ;;
  }
  
  measure: total_annual_gmv {
    type: sum
    sql: ${annual_gmv} ;;
  }
}
"""
        
        test_file = Path("test_derived_table.lkml")
        test_file.write_text(lookml_content)
        
        try:
            adapter = LookMLAdapter()
            graph = adapter.parse(test_file)
            
            model = graph.get_model("test_view")
            assert model is not None
            
            # Check that parameter resolution works in derived tables
            total_measure = model.get_metric("total_annual_gmv")
            assert total_measure.sql == "annual_gmv"
            
        finally:
            test_file.unlink()

    def test_parameter_resolution_with_nested_references(self):
        """Test parameter resolution with nested parameter references."""
        lookml_content = """
view: test_view {
  sql_table_name: test_table ;;
  
  dimension: base_amount {
    type: number
    sql: ${TABLE}.base_amount ;;
  }
  
  dimension: multiplier {
    type: number
    sql: ${TABLE}.multiplier ;;
  }
  
  measure: calculated_amount {
    type: sum
    sql: ${base_amount} * ${multiplier} ;;
  }
  
  measure: double_calculated {
    type: sum
    sql: ${calculated_amount} * 2 ;;
  }
}
"""
        
        test_file = Path("test_nested_params.lkml")
        test_file.write_text(lookml_content)
        
        try:
            adapter = LookMLAdapter()
            graph = adapter.parse(test_file)
            
            model = graph.get_model("test_view")
            assert model is not None
            
            # Check that parameter resolution works for nested references
            calculated_measure = model.get_metric("calculated_amount")
            assert calculated_measure.sql == "base_amount * multiplier"
            
            # Note: ${calculated_amount} gets resolved to the actual SQL expression
            double_measure = model.get_metric("double_calculated")
            assert double_measure.sql == "base_amount * multiplier * 2"
            
        finally:
            test_file.unlink()

    def test_parameter_resolution_with_special_characters(self):
        """Test parameter resolution with special characters in dimension names."""
        lookml_content = """
view: test_view {
  sql_table_name: test_table ;;
  
  dimension: amount_usd {
    type: number
    sql: ${TABLE}.amount_usd ;;
  }
  
  dimension: tax_rate_percent {
    type: number
    sql: ${TABLE}.tax_rate_percent ;;
  }
  
  measure: total_amount {
    type: sum
    sql: ${amount_usd} * (1 + ${tax_rate_percent}) ;;
  }
}
"""
        
        test_file = Path("test_special_chars.lkml")
        test_file.write_text(lookml_content)
        
        try:
            adapter = LookMLAdapter()
            graph = adapter.parse(test_file)
            
            model = graph.get_model("test_view")
            assert model is not None
            
            # Check that parameter resolution works with quoted identifiers
            total_measure = model.get_metric("total_amount")
            assert total_measure.sql == 'amount_usd * (1 + tax_rate_percent)'
            
        finally:
            test_file.unlink()

    def test_parameter_resolution_with_case_sensitivity(self):
        """Test parameter resolution with case-sensitive dimension names."""
        lookml_content = """
view: test_view {
  sql_table_name: test_table ;;
  
  dimension: Amount {
    type: number
    sql: ${TABLE}.Amount ;;
  }
  
  dimension: amount {
    type: number
    sql: ${TABLE}.amount ;;
  }
  
  measure: total_Amount {
    type: sum
    sql: ${Amount} ;;
  }
  
  measure: total_amount {
    type: sum
    sql: ${amount} ;;
  }
}
"""
        
        test_file = Path("test_case_sensitivity.lkml")
        test_file.write_text(lookml_content)
        
        try:
            adapter = LookMLAdapter()
            graph = adapter.parse(test_file)
            
            model = graph.get_model("test_view")
            assert model is not None
            
            # Check that parameter resolution is case-sensitive
            total_Amount_measure = model.get_metric("total_Amount")
            assert total_Amount_measure.sql == "Amount"
            
            total_amount_measure = model.get_metric("total_amount")
            assert total_amount_measure.sql == "amount"
            
        finally:
            test_file.unlink()
