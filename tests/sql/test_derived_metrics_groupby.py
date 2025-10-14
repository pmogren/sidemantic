"""Tests for derived metrics in GROUP BY queries.

This test file specifically tests the processing of derived metrics
in GROUP BY scenarios where the derived metric should be computed
in the CTE, not in the final SELECT clause.
"""

import pytest

from sidemantic.core.dimension import Dimension
from sidemantic.core.metric import Metric
from sidemantic.core.model import Model
from sidemantic.core.semantic_graph import SemanticGraph
from sidemantic.sql.generator import SQLGenerator


class TestDerivedMetricsGroupBy:
    """Test the processing of derived metrics in GROUP BY queries."""

    def test_derived_metric_in_groupby_query(self):
        """Test that derived metrics are computed in CTE for GROUP BY queries."""
        graph = SemanticGraph()
        
        # Create model with derived metric that references raw columns
        model = Model(
            name="sales",
            table="raw_sales",
            primary_key="id",
            dimensions=[
                Dimension(name="product_id", type="categorical", sql="product_id"),
                Dimension(name="amount", type="numeric", sql="amount"),
                Dimension(name="quantity", type="numeric", sql="quantity"),
            ],
            metrics=[
                Metric(name="total_amount", agg="sum", sql="amount"),
                Metric(name="total_quantity", agg="sum", sql="quantity"),
                Metric(name="avg_price", type="derived", sql="amount/quantity"),
            ],
        )
        graph.add_model(model)
        
        generator = SQLGenerator(graph)
        sql = generator.generate(
            metrics=["sales.total_amount", "sales.avg_price"],
            dimensions=["sales.product_id"],
        )
        
        # Verify derived metric is computed in CTE
        assert "amount/quantity AS avg_price_raw" in sql
        # Verify final SELECT aggregates from CTE
        assert "AVG(sales_cte.avg_price_raw) AS avg_price" in sql
        # Should NOT recompute in final SELECT
        assert "amount / quantity AS avg_price" not in sql

    def test_derived_metric_with_aggregation(self):
        """Test that derived metrics work with aggregation in GROUP BY queries."""
        graph = SemanticGraph()
        
        # Create model with derived metric
        model = Model(
            name="orders",
            table="raw_orders",
            primary_key="id",
            dimensions=[
                Dimension(name="customer_id", type="categorical", sql="customer_id"),
                Dimension(name="amount", type="numeric", sql="amount"),
                Dimension(name="tax_rate", type="numeric", sql="tax_rate"),
            ],
            metrics=[
                Metric(name="total_amount", agg="sum", sql="amount"),
                Metric(name="tax_amount", type="derived", sql="amount * tax_rate"),
            ],
        )
        graph.add_model(model)
        
        generator = SQLGenerator(graph)
        sql = generator.generate(
            metrics=["orders.total_amount", "orders.tax_amount"],
            dimensions=["orders.customer_id"],
        )
        
        # Verify derived metric is computed in CTE
        assert "amount * tax_rate AS tax_amount_raw" in sql
        # Verify final SELECT aggregates from CTE
        assert "AVG(orders_cte.tax_amount_raw) AS tax_amount" in sql

    def test_derived_metric_with_complex_expression(self):
        """Test that derived metrics with complex expressions work in GROUP BY queries."""
        graph = SemanticGraph()
        
        # Create model with complex derived metric
        model = Model(
            name="products",
            table="raw_products",
            primary_key="id",
            dimensions=[
                Dimension(name="category", type="categorical", sql="category"),
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
            dimensions=["products.category"],
        )
        
        # Verify derived metrics are computed in CTE
        assert "(price - cost) / price AS profit_margin_raw" in sql
        assert "price / quantity AS revenue_per_unit_raw" in sql
        # Verify final SELECT aggregates from CTE
        assert "AVG(products_cte.profit_margin_raw) AS profit_margin" in sql
        assert "AVG(products_cte.revenue_per_unit_raw) AS revenue_per_unit" in sql

    def test_derived_metric_with_nullif(self):
        """Test that derived metrics with NULLIF work in GROUP BY queries."""
        graph = SemanticGraph()
        
        # Create model with derived metric using NULLIF
        model = Model(
            name="sales",
            table="raw_sales",
            primary_key="id",
            dimensions=[
                Dimension(name="product_id", type="categorical", sql="product_id"),
                Dimension(name="amount", type="numeric", sql="amount"),
                Dimension(name="quantity", type="numeric", sql="quantity"),
            ],
            metrics=[
                Metric(name="total_amount", agg="sum", sql="amount"),
                Metric(name="total_quantity", agg="sum", sql="quantity"),
                Metric(name="avg_price", type="derived", sql="amount/nullif(quantity,0)"),
            ],
        )
        graph.add_model(model)
        
        generator = SQLGenerator(graph)
        sql = generator.generate(
            metrics=["sales.avg_price"],
            dimensions=["sales.product_id"],
        )
        
        # Verify derived metric is computed in CTE
        assert "amount/nullif(quantity,0) AS avg_price_raw" in sql
        # Verify final SELECT aggregates from CTE
        assert "AVG(sales_cte.avg_price_raw) AS avg_price" in sql
        # Should NOT recompute in final SELECT
        assert "amount / NULLIF(quantity, 0) AS avg_price" not in sql

    def test_derived_metric_with_case_statement(self):
        """Test that derived metrics with CASE statements work in GROUP BY queries."""
        graph = SemanticGraph()
        
        # Create model with derived metric using CASE
        model = Model(
            name="orders",
            table="raw_orders",
            primary_key="id",
            dimensions=[
                Dimension(name="status", type="categorical", sql="status"),
                Dimension(name="amount", type="numeric", sql="amount"),
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
        
        # Verify derived metric is computed in CTE
        assert "CASE WHEN status = 'completed' THEN amount ELSE 0 END AS completed_amount_raw" in sql
        # Verify final SELECT aggregates from CTE
        assert "AVG(orders_cte.completed_amount_raw) AS completed_amount" in sql

    def test_derived_metric_with_multiple_models(self):
        """Test that derived metrics work with multiple models in GROUP BY queries."""
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
                Metric(name="avg_order_value", type="derived", sql="amount"),
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
            metrics=["orders.avg_order_value", "customers.count"],
            dimensions=["orders.customer_id", "customers.region"],
        )
        
        # Verify derived metric is computed in CTE
        assert "amount AS avg_order_value_raw" in sql
        # Verify final SELECT aggregates from CTE
        assert "AVG(orders_cte.avg_order_value_raw) AS avg_order_value" in sql
