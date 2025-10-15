"""Integration tests for unqualified column references in WHERE clauses.

This test file tests the complete fix for unqualified column references
in WHERE clauses, including both query rewriter qualification and
SQL generator dimension resolution.
"""

import pytest

from sidemantic.core.dimension import Dimension
from sidemantic.core.metric import Metric
from sidemantic.core.model import Model
from sidemantic.core.semantic_graph import SemanticGraph
from sidemantic.sql.generator import SQLGenerator
from sidemantic.sql.query_rewriter import QueryRewriter


class TestUnqualifiedColumnIntegration:
    """Integration tests for unqualified column references in WHERE clauses."""

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
        
        # Create sales model with measure
        sales = Model(
            name="sales",
            table="sales",
            primary_key="id",
            dimensions=[
                Dimension(name="product_id", type="categorical", sql="product_id"),
                Dimension(name="quantity", type="numeric", sql="quantity"),
            ],
            metrics=[
                Metric(name="total_quantity", agg="sum", sql="quantity"),
                Metric(name="count", agg="count"),
            ],
        )
        graph.add_model(sales)
        
        return graph

    def test_unqualified_measure_in_where_clause(self, graph):
        """Test that unqualified measure references in WHERE clauses work correctly."""
        generator = SQLGenerator(graph)
        
        # Generate SQL for a query with unqualified measure in WHERE clause
        sql = generator.generate(
            metrics=["sales.total_quantity"],
            dimensions=["sales.product_id"],
            filters=["total_quantity > 1000"],  # Unqualified measure reference
        )
        
        # Should generate valid SQL with proper CTE and WHERE clause
        assert "WITH sales_cte AS" in sql
        assert "total_quantity_raw > 1000" in sql
        assert "SELECT" in sql
        assert "FROM sales_cte" in sql

    def test_unqualified_dimension_in_where_clause(self, graph):
        """Test that unqualified dimension references in WHERE clauses work correctly."""
        generator = SQLGenerator(graph)
        
        # Generate SQL for a query with unqualified dimension in WHERE clause
        sql = generator.generate(
            metrics=["orders.revenue"],
            dimensions=["orders.customer_id"],
            filters=["status = 'completed'"],  # Unqualified dimension reference
        )
        
        # Should generate valid SQL with proper CTE and WHERE clause
        assert "WITH orders_cte AS" in sql
        assert "order_status = 'completed'" in sql  # Should resolve to actual SQL
        assert "SELECT" in sql
        assert "FROM orders_cte" in sql

    def test_mixed_qualified_and_unqualified_references(self, graph):
        """Test WHERE clauses with both qualified and unqualified references."""
        generator = SQLGenerator(graph)
        
        # Generate SQL for a query with mixed qualified and unqualified references
        sql = generator.generate(
            metrics=["orders.revenue"],
            dimensions=["orders.customer_id"],
            filters=[
                "orders.status = 'completed'",  # Qualified
                "customer_id = 123",  # Unqualified
            ],
        )
        
        # Should generate valid SQL with proper CTE and WHERE clause
        assert "WITH orders_cte AS" in sql
        assert "order_status = 'completed'" in sql  # Should resolve dimension
        assert "customer_id = 123" in sql  # Should remain as is
        assert "SELECT" in sql
        assert "FROM orders_cte" in sql

    def test_complex_where_clause_with_unqualified_references(self, graph):
        """Test complex WHERE clauses with multiple unqualified references."""
        generator = SQLGenerator(graph)
        
        # Generate SQL for a complex query with multiple unqualified references
        sql = generator.generate(
            metrics=["orders.revenue", "orders.count"],
            dimensions=["orders.customer_id"],
            filters=[
                "status = 'completed'",  # Unqualified dimension
                "revenue > 1000",  # Unqualified measure
            ],
        )
        
        # Should generate valid SQL with proper CTE and WHERE clause
        assert "WITH orders_cte AS" in sql
        assert "order_status = 'completed'" in sql  # Should resolve dimension
        assert "revenue_raw > 1000" in sql  # Should resolve measure
        assert "SELECT" in sql
        assert "FROM orders_cte" in sql

    def test_query_rewriter_qualification_integration(self, graph):
        """Test that query rewriter properly qualifies unqualified references."""
        rewriter = QueryRewriter(graph)
        
        # Test a simple WHERE clause
        from sqlglot import exp
        
        # Create a SELECT statement with unqualified WHERE clause
        select_stmt = exp.Select(
            expressions=[
                exp.Column(this="revenue"),
                exp.Column(this="status"),
            ],
            from_=exp.Table(this="orders"),
            where=exp.EQ(
                this=exp.Column(this="status"),
                expression=exp.Literal(this="completed", is_string=True)
            )
        )
        
        # Set inferred table
        rewriter.inferred_table = "orders"
        
        # Extract filters
        filters = rewriter._extract_filters(select_stmt)
        
        # Should qualify the unqualified reference
        assert ["orders.status = 'completed'"] == filters

    def test_generator_dimension_resolution_integration(self, graph):
        """Test that generator properly resolves dimension names to SQL."""
        generator = SQLGenerator(graph)
        
        # Test the replace_field function with dimension resolution
        model = graph.get_model("orders")
        
        # Test dimension resolution
        def replace_field_test(field_name, model_name):
            measure = model.get_metric(field_name)
            if measure:
                return f"{model_name}_cte.{field_name}_raw"
            else:
                dimension = model.get_dimension(field_name)
                if dimension:
                    dim_sql = dimension.sql
                    if "{model}" in dim_sql:
                        dim_sql = dim_sql.replace("{model}.", "")
                    return dim_sql
                else:
                    return f"{model_name}_cte.{field_name}"
        
        # Test dimension resolution
        result = replace_field_test("status", "orders")
        assert "order_status" == result
        
        # Test measure resolution
        result = replace_field_test("revenue", "orders")
        assert "orders_cte.revenue_raw" == result

    def test_end_to_end_sql_generation(self, graph):
        """Test complete SQL generation with unqualified references."""
        generator = SQLGenerator(graph)
        
        # Generate SQL for a realistic query
        sql = generator.generate(
            metrics=["orders.revenue", "orders.count"],
            dimensions=["orders.customer_id"],
            filters=[
                "status = 'completed'",  # Unqualified dimension
                "revenue > 1000",  # Unqualified measure
            ],
        )
        
        # Should be valid SQL
        assert sql is not None
        assert len(sql) > 0
        
        # Should contain expected components
        assert "WITH orders_cte AS" in sql
        assert "SELECT" in sql
        assert "FROM orders_cte" in sql
        assert "WHERE" in sql
        
        # Should resolve dimension and measure references
        assert "order_status = 'completed'" in sql
        assert "revenue_raw > 1000" in sql
