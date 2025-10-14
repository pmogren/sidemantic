"""Tests for the model placeholder fix in SQL generation.

This test file specifically tests the fix for the model-to-table name mapping issue
where {model} placeholders were being replaced with model names instead of being
handled properly for table references.
"""

import pytest

from sidemantic.core.dimension import Dimension
from sidemantic.core.metric import Metric
from sidemantic.core.model import Model
from sidemantic.core.semantic_graph import SemanticGraph
from sidemantic.sql.generator import SQLGenerator


class TestModelPlaceholderFix:
    """Test the fix for model placeholder processing in SQL generation."""

    def test_model_placeholder_removal_in_dimensions(self):
        """Test that {model} placeholders are removed from dimension SQL expressions."""
        graph = SemanticGraph()
        
        # Create model with dimension that has {model} placeholder (like from LookML)
        model = Model(
            name="networkdiscovery_supplier",
            table="`de-prod-us`.bronze_ch_networkdiscovery.bronze_ch_networkdiscovery_supplier",
            primary_key="supplier_id",
            dimensions=[
                Dimension(name="avg_order_value_ytd", type="numeric", sql="{model}.avg_order_value_ytd"),
                Dimension(name="avg_unit_retail_price", type="numeric", sql="{model}.avg_unit_retail_price"),
                Dimension(name="supplier_id", type="categorical", sql="{model}.supplier_id"),
            ],
            metrics=[
                Metric(name="count", agg="count"),
            ],
        )
        graph.add_model(model)
        
        generator = SQLGenerator(graph)
        sql = generator.generate(
            metrics=["networkdiscovery_supplier.count"],
            dimensions=["networkdiscovery_supplier.avg_order_value_ytd", "networkdiscovery_supplier.avg_unit_retail_price"],
        )
        
        # Verify {model} was removed from CTE SELECT clause
        assert "avg_order_value_ytd AS avg_order_value_ytd" in sql
        assert "avg_unit_retail_price AS avg_unit_retail_price" in sql
        assert "supplier_id AS supplier_id" in sql
        # Should NOT contain {model} placeholders
        assert "{model}" not in sql
        # The final SELECT clause should reference the CTE correctly
        assert "networkdiscovery_supplier_cte.avg_order_value_ytd" in sql
        assert "networkdiscovery_supplier_cte.avg_unit_retail_price" in sql

    def test_model_placeholder_removal_in_metrics(self):
        """Test that {model} placeholders are removed from metric SQL expressions."""
        graph = SemanticGraph()
        
        # Create model with metric that has {model} placeholder (like from LookML)
        model = Model(
            name="networkdiscovery_supplier",
            table="`de-prod-us`.bronze_ch_networkdiscovery.bronze_ch_networkdiscovery_supplier",
            primary_key="supplier_id",
            dimensions=[
                Dimension(name="supplier_id", type="categorical", sql="supplier_id"),
            ],
            metrics=[
                Metric(name="total_annual_gmv", agg="sum", sql="{model}.annual_gmv"),
                Metric(name="average_annual_gmv", agg="avg", sql="{model}.annual_gmv"),
            ],
        )
        graph.add_model(model)
        
        generator = SQLGenerator(graph)
        sql = generator.generate(
            metrics=["networkdiscovery_supplier.total_annual_gmv", "networkdiscovery_supplier.average_annual_gmv"],
            dimensions=["networkdiscovery_supplier.supplier_id"],
        )
        
        # Verify {model} was removed from metric SQL
        assert "annual_gmv AS total_annual_gmv_raw" in sql
        assert "annual_gmv AS average_annual_gmv_raw" in sql
        # Should NOT contain model name as table qualifier
        assert "networkdiscovery_supplier.annual_gmv" not in sql
        assert "{model}" not in sql

    def test_model_placeholder_removal_in_time_dimensions(self):
        """Test that {model} placeholders are removed from time dimension SQL expressions."""
        graph = SemanticGraph()
        
        # Create model with time dimension that has {model} placeholder
        model = Model(
            name="orders",
            table="raw_orders",
            primary_key="id",
            dimensions=[
                Dimension(name="order_date", type="time", sql="{model}.order_date"),
            ],
            metrics=[
                Metric(name="count", agg="count"),
            ],
        )
        graph.add_model(model)
        
        generator = SQLGenerator(graph)
        sql = generator.generate(
            metrics=["orders.count"],
            dimensions=["orders.order_date__month"],
        )
        
        # Verify {model} was removed from time dimension SQL in CTE
        assert "order_date AS order_date" in sql
        # Should NOT contain {model} placeholders
        assert "{model}" not in sql
        # The final SELECT clause should reference the CTE correctly
        assert "orders_cte.order_date" in sql

    def test_model_placeholder_removal_with_complex_sql(self):
        """Test that {model} placeholders are removed from complex SQL expressions."""
        graph = SemanticGraph()
        
        # Create model with complex SQL expressions
        model = Model(
            name="suppliers",
            table="raw_suppliers",
            primary_key="id",
            dimensions=[
                Dimension(name="company_name", type="categorical", sql="{model}.company_name"),
                Dimension(name="avg_order_value", type="numeric", sql="CASE WHEN {model}.order_count > 0 THEN {model}.total_gmv / {model}.order_count ELSE 0 END"),
            ],
            metrics=[
                Metric(name="total_suppliers", agg="count", sql="{model}.id"),
                Metric(name="total_gmv", agg="sum", sql="{model}.annual_gmv"),
            ],
        )
        graph.add_model(model)
        
        generator = SQLGenerator(graph)
        sql = generator.generate(
            metrics=["suppliers.total_suppliers", "suppliers.total_gmv"],
            dimensions=["suppliers.company_name", "suppliers.avg_order_value"],
        )
        
        # Verify {model} was removed from all SQL expressions in CTE
        assert "company_name AS company_name" in sql
        assert "CASE WHEN order_count > 0 THEN total_gmv / order_count ELSE 0 END AS avg_order_value" in sql
        assert "id AS total_suppliers_raw" in sql
        assert "annual_gmv AS total_gmv_raw" in sql
        # Should NOT contain {model} placeholders
        assert "{model}" not in sql
        # The final SELECT clause should reference the CTE correctly
        assert "suppliers_cte.company_name" in sql
        assert "suppliers_cte.avg_order_value" in sql

    def test_model_placeholder_removal_with_multiple_models(self):
        """Test that {model} placeholders are removed correctly across multiple models."""
        graph = SemanticGraph()
        
        # Create two models with relationships
        from sidemantic.core.relationship import Relationship
        
        orders = Model(
            name="orders",
            table="raw_orders",
            primary_key="id",
            dimensions=[
                Dimension(name="status", type="categorical", sql="{model}.status"),
                Dimension(name="customer_id", type="numeric", sql="{model}.customer_id"),
            ],
            metrics=[
                Metric(name="revenue", agg="sum", sql="{model}.amount"),
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
                Dimension(name="region", type="categorical", sql="{model}.region"),
            ],
            metrics=[
                Metric(name="count", agg="count"),
            ],
        )
        
        graph.add_model(orders)
        graph.add_model(customers)
        
        generator = SQLGenerator(graph)
        sql = generator.generate(
            metrics=["orders.revenue", "customers.count"],
            dimensions=["orders.status", "customers.region"],
        )
        
        # Verify {model} was removed from both models in CTE
        assert "status AS status" in sql
        assert "customer_id AS customer_id" in sql
        assert "amount AS revenue_raw" in sql
        assert "region AS region" in sql
        # Should NOT contain {model} placeholders
        assert "{model}" not in sql
        # The final SELECT clause should reference the CTEs correctly
        assert "orders_cte.status" in sql
        assert "orders_cte.customer_id" in sql
        assert "orders_cte.revenue" in sql
        assert "customers_cte.region" in sql

    def test_model_placeholder_removal_with_filters(self):
        """Test that {model} placeholders are removed from filter expressions."""
        graph = SemanticGraph()
        
        # Create model with filters that have {model} placeholders
        model = Model(
            name="orders",
            table="raw_orders",
            primary_key="id",
            dimensions=[
                Dimension(name="status", type="categorical", sql="status"),
                Dimension(name="amount", type="numeric", sql="amount"),
            ],
            metrics=[
                Metric(name="count", agg="count"),
            ],
        )
        graph.add_model(model)
        
        generator = SQLGenerator(graph)
        sql = generator.generate(
            metrics=["orders.count"],
            dimensions=["orders.status"],
            filters=["{model}.amount > 100"],
        )
        
        # Verify {model} was removed from filter expressions
        # The filter should be processed and the {model} placeholder removed
        assert "amount > 100" in sql
        # Should NOT contain model name as table qualifier in filter
        assert "orders.amount" not in sql
        assert "{model}" not in sql

    def test_model_placeholder_removal_with_derived_metrics(self):
        """Test that {model} placeholders are removed from derived metric SQL expressions."""
        graph = SemanticGraph()
        
        # Create model with derived metric that references another metric
        model = Model(
            name="orders",
            table="raw_orders",
            primary_key="id",
            dimensions=[
                Dimension(name="status", type="categorical", sql="status"),
            ],
            metrics=[
                Metric(name="revenue", agg="sum", sql="{model}.amount"),
                Metric(name="tax_amount", type="derived", sql="orders.revenue * 0.1"),  # Reference another metric
            ],
        )
        graph.add_model(model)
        
        generator = SQLGenerator(graph)
        sql = generator.generate(
            metrics=["orders.revenue", "orders.tax_amount"],
            dimensions=["orders.status"],
        )
        
        # Verify {model} was removed from derived metric SQL
        assert "amount AS revenue_raw" in sql
        # Should NOT contain {model} placeholders
        assert "{model}" not in sql
        # The final SELECT clause should reference the CTE correctly
        assert "orders_cte.revenue" in sql
        assert "tax_amount" in sql  # Derived metric in final SELECT

    def test_model_placeholder_removal_with_parameters(self):
        """Test that {model} placeholders are removed while preserving parameter processing."""
        graph = SemanticGraph()
        
        # Add parameter
        from sidemantic.core.parameter import Parameter
        param = Parameter(name="tax_rate", type="number", default_value=0.1)
        graph.add_parameter(param)
        
        # Create model with both {model} and ${parameter} placeholders
        model = Model(
            name="orders",
            table="raw_orders",
            primary_key="id",
            dimensions=[
                Dimension(name="status", type="categorical", sql="status"),
            ],
            metrics=[
                Metric(name="tax_amount", agg="sum", sql="{model}.amount * ${tax_rate}"),
            ],
        )
        graph.add_model(model)
        
        generator = SQLGenerator(graph)
        sql = generator.generate(
            metrics=["orders.tax_amount"],
            dimensions=["orders.status"],
        )
        
        # Verify {model} was removed but ${tax_rate} was processed
        assert "amount * 0.1 AS tax_amount_raw" in sql
        # Should NOT contain model name as table qualifier
        assert "orders.amount" not in sql
        assert "{model}" not in sql
        # Parameter should be processed
        assert "0.1" in sql
        assert "${tax_rate}" not in sql

    def test_model_placeholder_removal_with_no_placeholders(self):
        """Test that SQL without {model} placeholders is unchanged."""
        graph = SemanticGraph()
        
        # Create model with SQL that doesn't have {model} placeholders
        model = Model(
            name="orders",
            table="raw_orders",
            primary_key="id",
            dimensions=[
                Dimension(name="status", type="categorical", sql="status"),
            ],
            metrics=[
                Metric(name="count", agg="count"),
            ],
        )
        graph.add_model(model)
        
        generator = SQLGenerator(graph)
        sql = generator.generate(
            metrics=["orders.count"],
            dimensions=["orders.status"],
        )
        
        # Verify SQL is unchanged when no {model} placeholders exist
        assert "status AS status" in sql
        assert "1 AS count_raw" in sql
        assert "{model}" not in sql

    def test_model_placeholder_removal_with_mixed_placeholders(self):
        """Test that {model} placeholders are removed while other placeholders are preserved."""
        graph = SemanticGraph()
        
        # Add parameter
        from sidemantic.core.parameter import Parameter
        param = Parameter(name="multiplier", type="number", default_value=2)
        graph.add_parameter(param)
        
        # Create model with mixed placeholders
        model = Model(
            name="orders",
            table="raw_orders",
            primary_key="id",
            dimensions=[
                Dimension(name="status", type="categorical", sql="status"),
            ],
            metrics=[
                Metric(name="adjusted_revenue", agg="sum", sql="{model}.amount * ${multiplier}"),
            ],
        )
        graph.add_model(model)
        
        generator = SQLGenerator(graph)
        sql = generator.generate(
            metrics=["orders.adjusted_revenue"],
            dimensions=["orders.status"],
        )
        
        # Verify {model} was removed but ${multiplier} was processed
        assert "amount * 2 AS adjusted_revenue_raw" in sql
        # Should NOT contain model name as table qualifier
        assert "orders.amount" not in sql
        assert "{model}" not in sql
        # Parameter should be processed
        assert "2" in sql
        assert "${multiplier}" not in sql
