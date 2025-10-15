"""Tests for query rewriter filter qualification functionality.

This test file specifically tests the _qualify_filter_columns method
and related functionality for qualifying unqualified column references
in WHERE clauses.
"""

import pytest
from sqlglot import exp

from sidemantic.core.dimension import Dimension
from sidemantic.core.metric import Metric
from sidemantic.core.model import Model
from sidemantic.core.semantic_graph import SemanticGraph
from sidemantic.sql.query_rewriter import QueryRewriter


class TestQueryRewriterFilterQualification:
    """Test the qualification of unqualified column references in WHERE clauses."""

    @pytest.fixture
    def graph(self):
        """Create a semantic graph with test models."""
        graph = SemanticGraph()
        
        # Create orders model
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
    def rewriter(self, graph):
        """Create a query rewriter with the test graph."""
        return QueryRewriter(graph)

    def test_qualify_single_column_reference(self, rewriter):
        """Test qualifying a single unqualified column reference."""
        # Set inferred table
        rewriter.inferred_table = "orders"
        
        # Create a simple condition: status = 'completed'
        condition = exp.EQ(
            this=exp.Column(this="status"),
            expression=exp.Literal(this="completed", is_string=True)
        )
        
        result = rewriter._qualify_filter_columns(condition)
        
        # Should qualify the column reference
        assert "orders.status = 'completed'" == result

    def test_qualify_multiple_column_references(self, rewriter):
        """Test qualifying multiple unqualified column references."""
        # Set inferred table
        rewriter.inferred_table = "orders"
        
        # Create a compound condition: status = 'completed' AND customer_id = 123
        condition = exp.And(
            this=exp.EQ(
                this=exp.Column(this="status"),
                expression=exp.Literal(this="completed", is_string=True)
            ),
            expression=exp.EQ(
                this=exp.Column(this="customer_id"),
                expression=exp.Literal(this="123", is_string=True)
            )
        )
        
        result = rewriter._qualify_filter_columns(condition)
        
        # Should qualify both column references
        assert "orders.status = 'completed' AND orders.customer_id = '123'" == result

    def test_qualify_with_or_condition(self, rewriter):
        """Test qualifying column references in OR conditions."""
        # Set inferred table
        rewriter.inferred_table = "orders"
        
        # Create an OR condition: status = 'completed' OR status = 'pending'
        condition = exp.Or(
            this=exp.EQ(
                this=exp.Column(this="status"),
                expression=exp.Literal(this="completed", is_string=True)
            ),
            expression=exp.EQ(
                this=exp.Column(this="status"),
                expression=exp.Literal(this="pending", is_string=True)
            )
        )
        
        result = rewriter._qualify_filter_columns(condition)
        
        # Should qualify both column references
        assert "orders.status = 'completed' OR orders.status = 'pending'" == result

    def test_no_qualification_when_table_present(self, rewriter):
        """Test that already qualified columns are not modified."""
        # Set inferred table
        rewriter.inferred_table = "orders"
        
        # Create a condition with already qualified column: orders.status = 'completed'
        condition = exp.EQ(
            this=exp.Column(this="status", table="orders"),
            expression=exp.Literal(this="completed", is_string=True)
        )
        
        result = rewriter._qualify_filter_columns(condition)
        
        # Should not modify already qualified columns
        assert "orders.status = 'completed'" == result

    def test_no_qualification_when_no_inferred_table(self, rewriter):
        """Test that columns are not qualified when no inferred table is set."""
        # Don't set inferred table
        rewriter.inferred_table = None
        
        # Create a simple condition: status = 'completed'
        condition = exp.EQ(
            this=exp.Column(this="status"),
            expression=exp.Literal(this="completed", is_string=True)
        )
        
        result = rewriter._qualify_filter_columns(condition)
        
        # Should not qualify when no inferred table
        assert "status = 'completed'" == result

    def test_complex_nested_conditions(self, rewriter):
        """Test qualifying columns in complex nested conditions."""
        # Set inferred table
        rewriter.inferred_table = "orders"
        
        # Create complex condition: (status = 'completed' AND customer_id = 123) OR (status = 'pending' AND customer_id = 456)
        condition = exp.Or(
            this=exp.And(
                this=exp.EQ(
                    this=exp.Column(this="status"),
                    expression=exp.Literal(this="completed", is_string=True)
                ),
                expression=exp.EQ(
                    this=exp.Column(this="customer_id"),
                    expression=exp.Literal(this="123", is_string=True)
                )
            ),
            expression=exp.And(
                this=exp.EQ(
                    this=exp.Column(this="status"),
                    expression=exp.Literal(this="pending", is_string=True)
                ),
                expression=exp.EQ(
                    this=exp.Column(this="customer_id"),
                    expression=exp.Literal(this="456", is_string=True)
                )
            )
        )
        
        result = rewriter._qualify_filter_columns(condition)
        
        # Should qualify all column references
        expected = ("orders.status = 'completed' AND orders.customer_id = '123' OR "
                   "orders.status = 'pending' AND orders.customer_id = '456'")
        assert expected == result

    def test_extract_filters_with_qualification(self, rewriter):
        """Test that _extract_filters properly qualifies column references."""
        # Set inferred table
        rewriter.inferred_table = "orders"
        
        # Create a SELECT statement with WHERE clause
        select_stmt = exp.Select(
            expressions=[
                exp.Column(this="status"),
                exp.Column(this="revenue"),
            ],
            from_=exp.Table(this="orders"),
            where=exp.EQ(
                this=exp.Column(this="status"),
                expression=exp.Literal(this="completed", is_string=True)
            )
        )
        
        filters = rewriter._extract_filters(select_stmt)
        
        # Should return qualified filter
        assert ["orders.status = 'completed'"] == filters

    def test_extract_compound_filters_with_qualification(self, rewriter):
        """Test that _extract_compound_filters properly qualifies column references."""
        # Set inferred table
        rewriter.inferred_table = "orders"
        
        # Create a compound condition
        condition = exp.And(
            this=exp.EQ(
                this=exp.Column(this="status"),
                expression=exp.Literal(this="completed", is_string=True)
            ),
            expression=exp.EQ(
                this=exp.Column(this="customer_id"),
                expression=exp.Literal(this="123", is_string=True)
            )
        )
        
        filters = rewriter._extract_compound_filters(condition)
        
        # Should return qualified filters
        assert ["orders.status = 'completed'", "orders.customer_id = '123'"] == filters

    def test_qualify_filter_columns_preserves_original(self, rewriter):
        """Test that _qualify_filter_columns doesn't modify the original condition."""
        # Set inferred table
        rewriter.inferred_table = "orders"
        
        # Create a simple condition
        original_condition = exp.EQ(
            this=exp.Column(this="status"),
            expression=exp.Literal(this="completed", is_string=True)
        )
        
        # Store original SQL for comparison
        original_sql = original_condition.sql(dialect="duckdb")
        
        # Call the method
        result = rewriter._qualify_filter_columns(original_condition)
        
        # Original condition should be unchanged
        assert original_sql == original_condition.sql(dialect="duckdb")
        
        # But result should be qualified
        assert "orders.status = 'completed'" == result
