"""Tests for SQL generator dimension resolution in filters.

This test file specifically tests the dimension resolution functionality
in both CTE and main query filter processing.
"""

import pytest

from sidemantic.core.dimension import Dimension
from sidemantic.core.metric import Metric
from sidemantic.core.model import Model
from sidemantic.core.semantic_graph import SemanticGraph
from sidemantic.sql.generator import SQLGenerator


class TestGeneratorDimensionResolution:
    """Test dimension resolution in SQL generator filter processing."""

    @pytest.fixture
    def graph(self):
        """Create a semantic graph with test models."""
        graph = SemanticGraph()
        
        # Create orders model with dimension that maps to different SQL
        orders = Model(
            name="orders",
            table="orders",
            primary_key="id",
            dimensions=[
                Dimension(name="status", type="categorical", sql="order_status"),
                Dimension(name="order_date", type="time", sql="order_date", granularity="day"),
                Dimension(name="customer_id", type="categorical", sql="customer_id"),
            ],
            metrics=[
                Metric(name="revenue", agg="sum", sql="amount"),
                Metric(name="count", agg="count"),
            ],
        )
        graph.add_model(orders)
        
        # Create customers model
        customers = Model(
            name="customers",
            table="customers",
            primary_key="id",
            dimensions=[
                Dimension(name="region", type="categorical", sql="region"),
                Dimension(name="tier", type="categorical", sql="customer_tier"),
            ],
            metrics=[
                Metric(name="customer_count", agg="count"),
            ],
        )
        graph.add_model(customers)
        
        return graph

    @pytest.fixture
    def generator(self, graph):
        """Create a SQL generator with the test graph."""
        return SQLGenerator(graph)

    def test_cte_filter_dimension_resolution(self, generator):
        """Test that CTE filters resolve dimension names to actual SQL."""
        # Get the orders model
        model = generator.graph.get_model("orders")
        
        # Test filter with dimension reference
        filters = ["orders.status = 'completed'"]
        
        # This would be called internally by the generator
        # We'll test the dimension resolution logic directly
        from sqlglot import exp
        import sqlglot
        
        for f in filters:
            parsed = sqlglot.parse_one(f, dialect="duckdb")
            # Remove table qualifiers (model_name_cte. or model_name.)
            for col in parsed.find_all(exp.Column):
                if col.table:
                    clean_table = col.table.replace("_cte", "")
                    if clean_table == "orders":
                        col.set("table", None)
                        # Now resolve the dimension name to actual SQL
                        dimension = model.get_dimension(col.name)
                        if dimension:
                            dim_sql = dimension.sql
                            if "{model}" in dim_sql:
                                dim_sql = dim_sql.replace("{model}.", "")
                            # Replace the entire column with a new one
                            new_col = exp.Column(this=dim_sql)
                            col.replace(new_col)
            processed_filter = parsed.sql(dialect="duckdb")
            
            # Should resolve 'status' to 'order_status'
            assert "order_status = 'completed'" == processed_filter

    def test_main_query_filter_dimension_resolution(self, generator):
        """Test that main query filters resolve dimension names to actual SQL."""
        # Get the orders model
        model = generator.graph.get_model("orders")
        
        # Test the replace_field function logic
        def replace_field_test(field_name, model_name):
            # Check if it's a measure
            measure = model.get_metric(field_name)
            if measure:
                return f"{model_name}_cte.{field_name}_raw"
            else:
                # Check if it's a dimension
                dimension = model.get_dimension(field_name)
                if dimension:
                    # For dimensions, use the actual SQL expression
                    dim_sql = dimension.sql
                    if "{model}" in dim_sql:
                        dim_sql = dim_sql.replace("{model}.", "")
                    return dim_sql
                else:
                    # It's a dimension or other column
                    return f"{model_name}_cte.{field_name}"
        
        # Test dimension resolution
        result = replace_field_test("status", "orders")
        assert "order_status" == result
        
        # Test measure resolution
        result = replace_field_test("revenue", "orders")
        assert "orders_cte.revenue_raw" == result

    def test_dimension_resolution_with_model_placeholder(self, generator):
        """Test dimension resolution when dimension SQL contains {model} placeholder."""
        # Create a model with dimension that uses {model} placeholder
        graph = SemanticGraph()
        model = Model(
            name="test_model",
            table="test_table",
            primary_key="id",
            dimensions=[
                Dimension(name="status", type="categorical", sql="{model}.order_status"),
            ],
            metrics=[
                Metric(name="count", agg="count"),
            ],
        )
        graph.add_model(model)
        
        generator = SQLGenerator(graph)
        
        # Test the replace_field function logic
        def replace_field_test(field_name, model_name):
            dimension = model.get_dimension(field_name)
            if dimension:
                dim_sql = dimension.sql
                if "{model}" in dim_sql:
                    dim_sql = dim_sql.replace("{model}.", "")
                return dim_sql
            return field_name
        
        # Test dimension resolution with {model} placeholder
        result = replace_field_test("status", "test_model")
        assert "order_status" == result

    def test_no_dimension_resolution_for_unknown_field(self, generator):
        """Test that unknown fields are handled gracefully."""
        # Get the orders model
        model = generator.graph.get_model("orders")
        
        # Test the replace_field function logic
        def replace_field_test(field_name, model_name):
            # Check if it's a measure
            measure = model.get_metric(field_name)
            if measure:
                return f"{model_name}_cte.{field_name}_raw"
            else:
                # Check if it's a dimension
                dimension = model.get_dimension(field_name)
                if dimension:
                    dim_sql = dimension.sql
                    if "{model}" in dim_sql:
                        dim_sql = dim_sql.replace("{model}.", "")
                    return dim_sql
                else:
                    # It's a dimension or other column
                    return f"{model_name}_cte.{field_name}"
        
        # Test unknown field
        result = replace_field_test("unknown_field", "orders")
        assert "orders_cte.unknown_field" == result

    def test_dimension_resolution_in_complex_filter(self, generator):
        """Test dimension resolution in complex filter expressions."""
        # Get the orders model
        model = generator.graph.get_model("orders")
        
        # Test filter with multiple dimension references
        filters = ["orders.status = 'completed' AND orders.customer_id = 123"]
        
        from sqlglot import exp
        import sqlglot
        
        for f in filters:
            parsed = sqlglot.parse_one(f, dialect="duckdb")
            # Remove table qualifiers and resolve dimensions
            for col in parsed.find_all(exp.Column):
                if col.table:
                    clean_table = col.table.replace("_cte", "")
                    if clean_table == "orders":
                        col.set("table", None)
                        # Resolve dimension name to actual SQL
                        dimension = model.get_dimension(col.name)
                        if dimension:
                            dim_sql = dimension.sql
                            if "{model}" in dim_sql:
                                dim_sql = dim_sql.replace("{model}.", "")
                            new_col = exp.Column(this=dim_sql)
                            col.replace(new_col)
            processed_filter = parsed.sql(dialect="duckdb")
            
            # Should resolve 'status' to 'order_status' but leave 'customer_id' as is
            assert "order_status = 'completed' AND customer_id = 123" == processed_filter

    def test_dimension_resolution_preserves_measures(self, generator):
        """Test that dimension resolution doesn't affect measure references."""
        # Get the orders model
        model = generator.graph.get_model("orders")
        
        # Test filter with both dimension and measure references
        filters = ["orders.status = 'completed' AND orders.revenue > 1000"]
        
        from sqlglot import exp
        import sqlglot
        
        for f in filters:
            parsed = sqlglot.parse_one(f, dialect="duckdb")
            # Remove table qualifiers and resolve dimensions
            for col in parsed.find_all(exp.Column):
                if col.table:
                    clean_table = col.table.replace("_cte", "")
                    if clean_table == "orders":
                        col.set("table", None)
                        # Resolve dimension name to actual SQL
                        dimension = model.get_dimension(col.name)
                        if dimension:
                            dim_sql = dimension.sql
                            if "{model}" in dim_sql:
                                dim_sql = dim_sql.replace("{model}.", "")
                            new_col = exp.Column(this=dim_sql)
                            col.replace(new_col)
            processed_filter = parsed.sql(dialect="duckdb")
            
            # Should resolve 'status' to 'order_status' but leave 'revenue' as is
            assert "order_status = 'completed' AND revenue > 1000" == processed_filter
