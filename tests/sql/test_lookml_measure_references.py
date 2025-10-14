"""Tests for LookML measure reference processing in SQL generation.

This test file specifically tests the processing of LookML measure references
like ${measure_name} in derived metrics.
"""

import pytest

from sidemantic.core.dimension import Dimension
from sidemantic.core.metric import Metric
from sidemantic.core.model import Model
from sidemantic.core.semantic_graph import SemanticGraph
from sidemantic.sql.generator import SQLGenerator


class TestLookMLMeasureReferences:
    """Test the processing of LookML measure references in SQL generation."""

    def test_lookml_measure_reference_processing(self):
        """Test that LookML measure references like ${measure_name} are processed correctly."""
        graph = SemanticGraph()
        
        # Create model with measure references (like from LookML)
        model = Model(
            name="sales_by_product",
            table="raw_sales",
            primary_key="id",
            dimensions=[
                Dimension(name="gmv", type="numeric", sql="gmv"),
                Dimension(name="order_count", type="numeric", sql="order_count"),
            ],
            metrics=[
                Metric(name="gmv_usd", agg="sum", sql="gmv"),
                Metric(name="order_count", agg="sum", sql="order_count"),
                Metric(name="avg_unit_retail", type="derived", sql="gmv/nullif(order_count,0)"),
            ],
        )
        graph.add_model(model)
        
        generator = SQLGenerator(graph)
        sql = generator.generate(
            metrics=["sales_by_product.avg_unit_retail"],
            dimensions=["sales_by_product.gmv"],
        )
        
        # Verify the SQL is generated correctly
        assert "gmv/nullif(order_count,0) AS avg_unit_retail_raw" in sql
        assert "{model}" not in sql
        # Should NOT contain unprocessed measure references
        assert "${gmv_usd}" not in sql
        assert "${order_count}" not in sql

    def test_lookml_measure_reference_with_parameter_resolution(self):
        """Test that LookML measure references are processed with parameter resolution."""
        graph = SemanticGraph()
        
        # Create model with measure references that need parameter resolution
        model = Model(
            name="orders",
            table="raw_orders",
            primary_key="id",
            dimensions=[
                Dimension(name="amount", type="numeric", sql="amount"),
                Dimension(name="quantity", type="numeric", sql="quantity"),
            ],
            metrics=[
                Metric(name="revenue", agg="sum", sql="amount"),
                Metric(name="total_quantity", agg="sum", sql="quantity"),
                Metric(name="avg_price", type="derived", sql="amount/quantity"),
            ],
        )
        graph.add_model(model)
        
        generator = SQLGenerator(graph)
        sql = generator.generate(
            metrics=["orders.avg_price"],
            dimensions=["orders.amount"],
        )
        
        # Verify the SQL is generated correctly
        assert "amount/quantity AS avg_price_raw" in sql
        assert "{model}" not in sql
        # Should NOT contain unprocessed measure references
        assert "${revenue}" not in sql
        assert "${total_quantity}" not in sql

    def test_lookml_measure_reference_with_complex_expressions(self):
        """Test that LookML measure references work with complex expressions."""
        graph = SemanticGraph()
        
        # Create model with complex measure references
        model = Model(
            name="products",
            table="raw_products",
            primary_key="id",
            dimensions=[
                Dimension(name="price", type="numeric", sql="price"),
                Dimension(name="cost", type="numeric", sql="cost"),
                Dimension(name="quantity", type="numeric", sql="quantity"),
            ],
            metrics=[
                Metric(name="total_revenue", agg="sum", sql="price"),
                Metric(name="total_cost", agg="sum", sql="cost"),
                Metric(name="total_quantity", agg="sum", sql="quantity"),
                Metric(name="profit_margin", type="derived", sql="(price - cost) / price"),
                Metric(name="revenue_per_unit", type="derived", sql="price / quantity"),
            ],
        )
        graph.add_model(model)
        
        generator = SQLGenerator(graph)
        sql = generator.generate(
            metrics=["products.profit_margin", "products.revenue_per_unit"],
            dimensions=["products.price"],
        )
        
        # Verify the SQL is generated correctly
        assert "(price - cost) / price AS profit_margin_raw" in sql
        assert "price / quantity AS revenue_per_unit_raw" in sql
        assert "{model}" not in sql
        # Should NOT contain unprocessed measure references
        assert "${total_revenue}" not in sql
        assert "${total_cost}" not in sql
        assert "${total_quantity}" not in sql

    def test_lookml_measure_reference_with_nested_expressions(self):
        """Test that LookML measure references work with nested expressions."""
        graph = SemanticGraph()
        
        # Create model with nested measure references
        model = Model(
            name="transactions",
            table="raw_transactions",
            primary_key="id",
            dimensions=[
                Dimension(name="amount", type="numeric", sql="amount"),
                Dimension(name="tax_rate", type="numeric", sql="tax_rate"),
            ],
            metrics=[
                Metric(name="total_amount", agg="sum", sql="amount"),
                Metric(name="tax_amount", type="derived", sql="amount * tax_rate"),
                Metric(name="total_with_tax", type="derived", sql="amount * (1 + tax_rate)"),
            ],
        )
        graph.add_model(model)
        
        generator = SQLGenerator(graph)
        sql = generator.generate(
            metrics=["transactions.tax_amount", "transactions.total_with_tax"],
            dimensions=["transactions.amount"],
        )
        
        # Verify the SQL is generated correctly
        assert "amount * tax_rate AS tax_amount_raw" in sql
        assert "amount * (1 + tax_rate) AS total_with_tax_raw" in sql
        assert "{model}" not in sql
        # Should NOT contain unprocessed measure references
        assert "${total_amount}" not in sql

    def test_lookml_measure_reference_with_case_statements(self):
        """Test that LookML measure references work with CASE statements."""
        graph = SemanticGraph()
        
        # Create model with CASE statement measure references
        model = Model(
            name="orders",
            table="raw_orders",
            primary_key="id",
            dimensions=[
                Dimension(name="amount", type="numeric", sql="amount"),
                Dimension(name="status", type="categorical", sql="status"),
            ],
            metrics=[
                Metric(name="total_amount", agg="sum", sql="amount"),
                Metric(name="completed_amount", type="derived", sql="CASE WHEN status = 'completed' THEN amount ELSE 0 END"),
            ],
        )
        graph.add_model(model)
        
        generator = SQLGenerator(graph)
        sql = generator.generate(
            metrics=["orders.completed_amount"],
            dimensions=["orders.status"],
        )
        
        # Verify the SQL is generated correctly
        assert "CASE WHEN status = 'completed' THEN amount ELSE 0 END AS completed_amount_raw" in sql
        assert "{model}" not in sql
        # Should NOT contain unprocessed measure references
        assert "${total_amount}" not in sql

    def test_lookml_measure_reference_with_multiple_models(self):
        """Test that LookML measure references work across multiple models."""
        graph = SemanticGraph()
        
        # Create two models with cross-model references
        from sidemantic.core.relationship import Relationship
        
        orders = Model(
            name="orders",
            table="raw_orders",
            primary_key="id",
            dimensions=[
                Dimension(name="customer_id", type="numeric", sql="customer_id"),
                Dimension(name="amount", type="numeric", sql="amount"),
            ],
            metrics=[
                Metric(name="total_amount", agg="sum", sql="amount"),
            ],
            relationships=[
                Relationship(name="customers", type="many_to_one", foreign_key="customer_id"),
            ],
        )
        
        customers = Model(
            name="customers",
            table="raw_customers",
            primary_key="id",
            dimensions=[
                Dimension(name="region", type="categorical", sql="region"),
            ],
            metrics=[
                Metric(name="count", agg="count"),
            ],
        )
        
        graph.add_model(orders)
        graph.add_model(customers)
        
        generator = SQLGenerator(graph)
        sql = generator.generate(
            metrics=["orders.total_amount", "customers.count"],
            dimensions=["orders.customer_id", "customers.region"],
        )
        
        # Verify the SQL is generated correctly
        assert "amount AS total_amount_raw" in sql
        assert "1 AS count_raw" in sql
        assert "{model}" not in sql
        # Should NOT contain unprocessed measure references
        assert "${total_amount}" not in sql
