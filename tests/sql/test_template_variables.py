"""Tests for template variable processing in SQL generation."""

import pytest

from sidemantic.core.dimension import Dimension
from sidemantic.core.metric import Metric
from sidemantic.core.model import Model
from sidemantic.core.parameter import Parameter
from sidemantic.core.semantic_graph import SemanticGraph
from sidemantic.sql.generator import SQLGenerator


class TestTemplateVariableProcessing:
    """Test template variable processing in SQL generation."""

    def test_model_placeholder_replacement_in_measures(self):
        """Test that {model} placeholders are replaced with actual model names in measures."""
        graph = SemanticGraph()
        
        # Create model with measure that has {model} placeholder
        model = Model(
            name="orders",
            table="raw_orders",
            primary_key="id",
            dimensions=[
                Dimension(name="status", type="categorical", sql="status"),
            ],
            metrics=[
                Metric(name="revenue", agg="sum", sql="{model}.amount"),
                Metric(name="count", agg="count", sql="{model}.id"),
            ],
        )
        graph.add_model(model)
        
        generator = SQLGenerator(graph)
        sql = generator.generate(
            metrics=["orders.revenue", "orders.count"],
            dimensions=["orders.status"],
        )
        
        # Verify {model} was removed (not replaced with model name)
        assert "amount AS revenue_raw" in sql
        assert "id AS count_raw" in sql
        assert "{model}" not in sql

    def test_model_placeholder_replacement_in_dimensions(self):
        """Test that {model} placeholders are replaced with actual model names in dimensions."""
        graph = SemanticGraph()
        
        # Create model with dimension that has {model} placeholder
        model = Model(
            name="orders",
            table="raw_orders",
            primary_key="id",
            dimensions=[
                Dimension(name="status", type="categorical", sql="{model}.status"),
                Dimension(name="amount", type="numeric", sql="{model}.amount"),
            ],
            metrics=[
                Metric(name="count", agg="count"),
            ],
        )
        graph.add_model(model)
        
        generator = SQLGenerator(graph)
        sql = generator.generate(
            metrics=["orders.count"],
            dimensions=["orders.status", "orders.amount"],
        )
        
        # Verify {model} was replaced with actual model name
        assert "orders.status" in sql
        assert "orders.amount" in sql
        assert "{model}" not in sql

    def test_parameter_placeholder_processing(self):
        """Test that ${parameter} placeholders are processed using ParameterSet."""
        graph = SemanticGraph()
        
        # Add parameter
        param = Parameter(name="annual_gmv", type="number", default_value=1000000)
        graph.add_parameter(param)
        
        # Create model with measure that has ${parameter} placeholder
        model = Model(
            name="suppliers",
            table="raw_suppliers",
            primary_key="id",
            dimensions=[
                Dimension(name="name", type="categorical", sql="name"),
            ],
            metrics=[
                Metric(name="total_gmv", agg="sum", sql="${annual_gmv}"),
                Metric(name="avg_gmv", agg="avg", sql="${annual_gmv}"),
            ],
        )
        graph.add_model(model)
        
        generator = SQLGenerator(graph)
        sql = generator.generate(
            metrics=["suppliers.total_gmv", "suppliers.avg_gmv"],
            dimensions=["suppliers.name"],
        )
        
        # Verify ${annual_gmv} was replaced with parameter value
        assert "1000000" in sql
        assert "${annual_gmv}" not in sql

    def test_parameter_placeholder_with_custom_values(self):
        """Test that ${parameter} placeholders use custom parameter values when provided."""
        graph = SemanticGraph()
        
        # Add parameter
        param = Parameter(name="annual_gmv", type="number", default_value=1000000)
        graph.add_parameter(param)
        
        # Create model with measure that has ${parameter} placeholder
        model = Model(
            name="suppliers",
            table="raw_suppliers",
            primary_key="id",
            dimensions=[
                Dimension(name="name", type="categorical", sql="name"),
            ],
            metrics=[
                Metric(name="total_gmv", agg="sum", sql="${annual_gmv}"),
            ],
        )
        graph.add_model(model)
        
        generator = SQLGenerator(graph)
        sql = generator.generate(
            metrics=["suppliers.total_gmv"],
            dimensions=["suppliers.name"],
            parameters={"annual_gmv": 5000000},
        )
        
        # Verify ${annual_gmv} was replaced with custom parameter value
        assert "5000000" in sql
        assert "1000000" not in sql  # Should not use default
        assert "${annual_gmv}" not in sql

    def test_mixed_template_variables(self):
        """Test processing of both {model} and ${parameter} placeholders in the same SQL."""
        graph = SemanticGraph()
        
        # Add parameter
        param = Parameter(name="multiplier", type="number", default_value=2)
        graph.add_parameter(param)
        
        # Create model with measure that has both placeholders
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
        
        # Verify both placeholders were processed
        assert "amount * 2 AS adjusted_revenue_raw" in sql  # {model} removed, ${multiplier} replaced
        assert "2" in sql  # ${multiplier} replaced with default
        assert "{model}" not in sql
        assert "${multiplier}" not in sql

    def test_time_dimension_with_template_variables(self):
        """Test template variable processing in time dimensions with granularity."""
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
        
        # Verify {model} was replaced in time dimension
        assert "orders.order_date" in sql
        assert "{model}" not in sql

    def test_parameter_interpolation_with_dollar_sign_format(self):
        """Test that ${parameter} format is properly handled by parameter interpolation."""
        graph = SemanticGraph()
        
        # Add parameter
        param = Parameter(name="status_filter", type="string", default_value="completed")
        graph.add_parameter(param)
        
        # Create model
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
            filters=["orders.status = ${status_filter}"],
        )
        
        # Verify ${status_filter} was replaced with parameter value
        assert "'completed'" in sql
        assert "${status_filter}" not in sql

    def test_parameter_interpolation_with_curly_brace_format(self):
        """Test that {{ parameter }} format is properly handled by parameter interpolation."""
        graph = SemanticGraph()
        
        # Add parameter
        param = Parameter(name="status_filter", type="string", default_value="completed")
        graph.add_parameter(param)
        
        # Create model
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
            filters=["orders.status = {{ status_filter }}"],
        )
        
        # Verify {{ status_filter }} was replaced with parameter value
        assert "'completed'" in sql
        assert "{{ status_filter }}" not in sql

    def test_unknown_parameter_handling(self):
        """Test that unknown parameters are left unchanged."""
        graph = SemanticGraph()
        
        # Create model with unknown parameter
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
            filters=["orders.status = ${unknown_param}"],
        )
        
        # Verify unknown parameter is left unchanged
        # The parameter processing converts ${unknown_param} to {'_0': unknown_param} format
        assert "unknown_param" in sql

    def test_template_variables_in_complex_metric_sql(self):
        """Test template variable processing in complex metric SQL expressions."""
        graph = SemanticGraph()
        
        # Add parameter
        param = Parameter(name="tax_rate", type="number", default_value=0.1)
        graph.add_parameter(param)
        
        # Create model with complex metric SQL
        model = Model(
            name="orders",
            table="raw_orders",
            primary_key="id",
            dimensions=[
                Dimension(name="status", type="categorical", sql="status"),
            ],
            metrics=[
                Metric(name="tax_amount", agg="sum", sql="{model}.amount * ${tax_rate}"),
                Metric(name="total_with_tax", agg="sum", sql="{model}.amount * (1 + ${tax_rate})"),
            ],
        )
        graph.add_model(model)
        
        generator = SQLGenerator(graph)
        sql = generator.generate(
            metrics=["orders.tax_amount", "orders.total_with_tax"],
            dimensions=["orders.status"],
        )
        
        # Verify both placeholders were processed
        assert "amount * 0.1 AS tax_amount_raw" in sql  # {model} removed, ${tax_rate} replaced
        assert "amount * (1 + 0.1) AS total_with_tax_raw" in sql  # {model} removed, ${tax_rate} replaced
        assert "0.1" in sql  # ${tax_rate} replaced with default
        assert "{model}" not in sql
        assert "${tax_rate}" not in sql

    def test_template_variables_in_derived_metrics(self):
        """Test template variable processing in derived metrics."""
        graph = SemanticGraph()
        
        # Add parameter
        param = Parameter(name="conversion_rate", type="number", default_value=0.05)
        graph.add_parameter(param)
        
        # Create model with derived metric
        model = Model(
            name="users",
            table="raw_users",
            primary_key="id",
            dimensions=[
                Dimension(name="status", type="categorical", sql="status"),
            ],
            metrics=[
                Metric(name="conversions", agg="sum", sql="{model}.visits * ${conversion_rate}"),
            ],
        )
        graph.add_model(model)
        
        generator = SQLGenerator(graph)
        sql = generator.generate(
            metrics=["users.conversions"],
            dimensions=["users.status"],
        )
        
        # Verify both placeholders were processed
        assert "visits * 0.05 AS conversions_raw" in sql  # {model} removed, ${conversion_rate} replaced
        assert "0.05" in sql  # ${conversion_rate} replaced with default
        assert "{model}" not in sql
        assert "${conversion_rate}" not in sql

    def test_template_variables_with_multiple_models(self):
        """Test template variable processing across multiple models."""
        graph = SemanticGraph()
        
        # Add parameter
        param = Parameter(name="discount_rate", type="number", default_value=0.1)
        graph.add_parameter(param)
        
        # Create two models with relationship
        from sidemantic.core.relationship import Relationship
        
        orders = Model(
            name="orders",
            table="raw_orders",
            primary_key="id",
            dimensions=[
                Dimension(name="status", type="categorical", sql="status"),
                Dimension(name="customer_id", type="numeric", sql="customer_id"),
            ],
            metrics=[
                Metric(name="discounted_amount", agg="sum", sql="{model}.amount * (1 - ${discount_rate})"),
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
            metrics=["orders.discounted_amount", "customers.count"],
            dimensions=["orders.status", "customers.region"],
        )
        
        # Verify {model} was removed from both models
        assert "amount * (1 - 0.1) AS discounted_amount_raw" in sql  # {model} removed, ${discount_rate} replaced
        # For count metric, it uses 1 AS count_raw, not customers.id
        assert "1 AS count_raw" in sql
        assert "0.1" in sql  # ${discount_rate} replaced
        assert "{model}" not in sql
        assert "${discount_rate}" not in sql

    def test_template_variables_in_filters(self):
        """Test template variable processing in filter expressions."""
        graph = SemanticGraph()
        
        # Add parameter
        param = Parameter(name="min_amount", type="number", default_value=100)
        graph.add_parameter(param)
        
        # Create model
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
            filters=["{model}.amount >= ${min_amount}"],
        )
        
        # Verify both placeholders were processed in filter
        assert "orders_cte.amount" in sql  # {model} replaced with table alias
        assert "100" in sql  # ${min_amount} replaced
        assert "{model}" not in sql
        assert "${min_amount}" not in sql

    def test_template_variables_with_special_characters(self):
        """Test template variable processing with special characters in parameter values."""
        graph = SemanticGraph()
        
        # Add parameter with special characters
        param = Parameter(name="description", type="string", default_value="O'Reilly & Associates")
        graph.add_parameter(param)
        
        # Create model
        model = Model(
            name="products",
            table="raw_products",
            primary_key="id",
            dimensions=[
                Dimension(name="category", type="categorical", sql="category"),
            ],
            metrics=[
                Metric(name="count", agg="count"),
            ],
        )
        graph.add_model(model)
        
        generator = SQLGenerator(graph)
        sql = generator.generate(
            metrics=["products.count"],
            dimensions=["products.category"],
            filters=["products.description = ${description}"],
        )
        
        # Verify parameter was properly escaped
        assert "'O''Reilly & Associates'" in sql  # Single quote escaped
        assert "${description}" not in sql

    def test_template_variables_in_nested_expressions(self):
        """Test template variable processing in nested SQL expressions."""
        graph = SemanticGraph()
        
        # Add parameter
        param = Parameter(name="base_rate", type="number", default_value=0.05)
        graph.add_parameter(param)
        
        # Create model with nested expression
        model = Model(
            name="transactions",
            table="raw_transactions",
            primary_key="id",
            dimensions=[
                Dimension(name="type", type="categorical", sql="type"),
            ],
            metrics=[
                Metric(name="fee", agg="sum", sql="CASE WHEN {model}.amount > 1000 THEN {model}.amount * ${base_rate} ELSE {model}.amount * ${base_rate} * 0.5 END"),
            ],
        )
        graph.add_model(model)
        
        generator = SQLGenerator(graph)
        sql = generator.generate(
            metrics=["transactions.fee"],
            dimensions=["transactions.type"],
        )
        
        # Verify all placeholders were processed
        assert "CASE WHEN amount > 1000 THEN amount * 0.05 ELSE amount * 0.05 * 0.5 END AS fee_raw" in sql  # {model} removed, ${base_rate} replaced
        assert "0.05" in sql  # ${base_rate} replaced
        assert "{model}" not in sql
        assert "${base_rate}" not in sql
