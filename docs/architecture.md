# Trade Data Pipeline Architecture

This repository implements a small end-to-end data platform for synthetic trade data. The design follows a classic lakehouse-style ingestion and transformation pattern:

1. Generate synthetic trade files locally.
2. Land or stage those files to Snowflake.
3. Persist raw trade events in a Snowflake raw table.
4. Use dbt models to validate, rank, and split the feed into valid and rejected trade datasets.

The repository is organized around three main architectural layers:

- Ingestion layer
- Snowflake warehouse layer
- Transformation and validation layer

## 1. Repository structure

### Ingestion

The ingestion folder provides the runtime components used to produce and send data into Snowflake.

- [ingestion/trade_generator/generate_trades.py](../ingestion/trade_generator/generate_trades.py)
  - Produces synthetic trade records in CSV format.
  - Accepts arguments such as row count, symbol selection, quantity and price constraints, and optional output location.
  - Writes rows with a normalized trade schema used by the downstream warehouse model.

- [ingestion/loader/stage_to_snowflake.py](../ingestion/loader/stage_to_snowflake.py)
  - Connects to Snowflake using the connection details from YAML config or argument overrides.
  - Uses Snowflake SQL commands to execute a `PUT` into a table stage and a `COPY INTO` load from that staged file.
  - Maps the generated CSV feed into the configured target Snowflake table.

### Configuration

- [config/snowflake_config.yml](../config/snowflake_config.yml)
  - Contains the default Snowflake credentials and warehouse/database/schema contract.

### DDL

The DDL folder contains the database objects required by the warehouse layer:

- [snowflake/ddl/create_database_schema.sql](../snowflake/ddl/create_database_schema.sql)
  - Creates the database and schema.

- [snowflake/ddl/create_raw_trades_table.sql](../snowflake/ddl/create_raw_trades_table.sql)
  - Defines the raw landings table for source records.

- [snowflake/ddl/create_valid_trades_table.sql](../snowflake/ddl/create_valid_trades_table.sql)
  - Defines the curated valid trade output table.

- [snowflake/ddl/create_rejected_trades_table.sql](../snowflake/ddl/create_rejected_trades_table.sql)
  - Defines the rejection table that captures records filtered from the active business-valid set.

### dbt models

The dbt project in the Snowflake folder implements the transformation logic after ingestion:

- [snowflake/dbt/dbt_project.yml](../snowflake/dbt/dbt_project.yml)
  - dbt project metadata and configuration.

- [snowflake/dbt/profiles.yml](../snowflake/dbt/profiles.yml)
  - dbt connection profile used to target Snowflake.

- [snowflake/dbt/models/stg_raw_trades.sql](../snowflake/dbt/models/stg_raw_trades.sql)
  - A staging view that reads from the raw Snowflake source table.

- [snowflake/dbt/models/valid_trades.sql](../snowflake/dbt/models/valid_trades.sql)
  - Selects the latest version per trade_id and enforces business validity such as maturity-date handling.
  - Produces a curated `ACTIVE` or `EXPIRED` valid-trade table.

- [snowflake/dbt/models/rejected_trades.sql](../snowflake/dbt/models/rejected_trades.sql)
  - Produces a table of rejected records based on version and maturity-date business rules.

- [snowflake/dbt/models/schema.yml](../snowflake/dbt/models/schema.yml)
  - Declares source and model contract, column descriptions, and dbt test expectations.

### Operational scripts

- [scripts/deploy_snowflake_objects.sh](../scripts/deploy_snowflake_objects.sh)
  - Orchestrates the generation of sample trade data and the Snowflake load operation.
  - Intended as a deployment-style helper for moving a generated feed into Snowflake.

- [scripts/run_dbt_tests.sh](../scripts/run_dbt_tests.sh)
  - Executes the dbt workflow (`deps`, `run`, and `test`) for the transformed trade datasets.

### Test layer

- [tests/test_generate_trades.py](../tests/test_generate_trades.py)
  - Tests the synthetic trade generator contract.

## 2. End-to-end data flow

A typical run works as follows:

1. The developer invokes the synthetic generator from the generator module.
2. This produces a CSV payload containing trade attributes such as `trade_id`, `timestamp`, `symbol`, `side`, `quantity`, `price`, `currency`, `venue`, `version`, `maturity_date`, `status`, `rejection_reason`, `source_file`, and `load_ts`.
3. The Snowflake staging loader accepts that file and uploads it to Snowflake with a `PUT` command.
4. The loader performs a `COPY INTO` operation from the staged file into the Snowflake raw-trades table.
5. dbt reads the raw table through the source definition in the schema.
6. dbt staging, valid, and rejected models transform and validate the incoming source feed.
7. dbt tests enforce data-quality constraints on columns and accepted values.

## 3. High-level architecture diagram

The repository is structurally organized as a simple pipeline:

```text
Python trade generator
    -> CSV trade file
    -> Snowflake stage via PUT / COPY INTO
    -> raw_trades table
    -> dbt staging model (stg_raw_trades)
    -> valid_trades model
    -> rejected_trades model
    -> dbt validation tests
```

## 4. Core design principles

- Synthetic-first development: the repository is designed to generate realistic-looking trade records without requiring an external source system.
- Snowflake-centered warehouse design: Snowflake is the operational sink and source of truth for persisted trade data.
- Separation of concerns: generator, loader, SQL DDL, dbt transformations, and deployment scripts are split into independent repository areas.
- Data quality through dbt: dbt tests and model logic express a business-quality layer over the raw ingestion layer.

## 5. Deployment model

The repository is not a containerized SaaS application; it is a code-first data engineering workspace. It depends on local Python execution and Snowflake connectivity. The script folder provides a lightweight operational wrapper around ingestion and transformation execution.
