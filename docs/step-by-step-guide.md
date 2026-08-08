# Step-by-Step Execution Guide

This guide explains how to run the repository end to end and highlights the operational flow used to generate synthetic trades, load them into Snowflake, and validate them through dbt business rules.

## 1. Prerequisites

Before running the pipeline, make sure the required Python dependencies are available.

Install project requirements:

```bash
pip install -r requirements.txt
```

The repository expects Snowflake connectivity details to be provided through:

- the YAML configuration under [config/snowflake_config.yml](../config/snowflake_config.yml)
- or command-line arguments passed to the Snowflake loading script

The dbt project also needs a working Snowflake profile, defined in [snowflake/dbt/profiles.yml](../snowflake/dbt/profiles.yml).

## 2. Create the warehouse objects

Create the required database and schema objects first.

Run the DDL scripts in order:

1. [snowflake/ddl/create_database_schema.sql](../snowflake/ddl/create_database_schema.sql)
2. [snowflake/ddl/create_raw_trades_table.sql](../snowflake/ddl/create_raw_trades_table.sql)
3. [snowflake/ddl/create_valid_trades_table.sql](../snowflake/ddl/create_valid_trades_table.sql)
4. [snowflake/ddl/create_rejected_trades_table.sql](../snowflake/ddl/create_rejected_trades_table.sql)

These objects establish the Snowflake landing zone and the target tables used for the storage of accepted and rejected records.

## 3. Generate synthetic trades

The generation entry point is the Python script at [ingestion/trade_generator/generate_trades.py](../ingestion/trade_generator/generate_trades.py).

Run the generator with a CSV output file:

```bash
python ingestion/trade_generator/generate_trades.py --count 100 --output tmp_trades.csv
```

What happens:

- The script creates a randomized set of trade records.
- Each record contains the common fields expected in the Snowflake raw feed.
- The output is a CSV file that can be staged into Snowflake for ingestion.

The generator payload is meant to mirror a production-style trade structure, including:

- `trade_id`
- `timestamp`
- `symbol`
- `side`
- `quantity`
- `price`
- `currency`
- `venue`
- `version`
- `maturity_date`
- `status`
- `rejection_reason`
- `source_file`
- `load_ts`

## 4. Load the generated CSV into Snowflake

The ingestion script used to transfer the file is [ingestion/loader/stage_to_snowflake.py](../ingestion/loader/stage_to_snowflake.py).

A representative command looks like this:

```bash
python ingestion/loader/stage_to_snowflake.py \
  --file tmp_trades.csv \
  --format csv \
  --table RAW_TRADES \
  --config config/snowflake_config.yml
```

Operationally, the loader performs two Snowflake steps:

1. `PUT` the local CSV file into a Snowflake table stage using the table name as the stage scope.
2. `COPY INTO` the staged file into the raw table using the configured file format options.

The raw Snowflake table receives the freshly landed records in a semi-structured ingestion-friendly form.

## 5. Inspect or validate the raw landing table

Once the `COPY INTO` finishes, the raw data is visible in the Snowflake raw table created by [snowflake/ddl/create_raw_trades_table.sql](../snowflake/ddl/create_raw_trades_table.sql).

That raw table acts as the source for the dbt transformation layer.

## 6. Run dbt staging and transformation models

The dbt project is located in [snowflake/dbt](../snowflake/dbt).

The workflow is driven by the command script [scripts/run_dbt_tests.sh](../scripts/run_dbt_tests.sh):

```bash
bash scripts/run_dbt_tests.sh
```

The script runs these dbt operations in sequence:

1. `dbt deps`
2. `dbt run`
3. `dbt test`

The dbt models defined in the repository are:

- [snowflake/dbt/models/stg_raw_trades.sql](../snowflake/dbt/models/stg_raw_trades.sql)
- [snowflake/dbt/models/valid_trades.sql](../snowflake/dbt/models/valid_trades.sql)
- [snowflake/dbt/models/rejected_trades.sql](../snowflake/dbt/models/rejected_trades.sql)

They read from the raw landings table and classify records according to business logic.

## 7. Business validation rules used by dbt

The dbt models implement the acceptance and rejection logic for trades.

### Valid-trade business rules

From [snowflake/dbt/models/valid_trades.sql](../snowflake/dbt/models/valid_trades.sql):

- The model looks at all records for each `trade_id`.
- It ranks records by descending `version` and newest `load_ts`.
- It keeps only the latest-version candidate.
- It applies maturity-date logic.
- It writes the surviving source record to the valid-trade dataset.

A valid record is emitted as:

- `ACTIVE` when the maturity date is at or after the current business date context
- `EXPIRED` when the maturity date is earlier than the operational date boundary

### Rejection business rules

From [snowflake/dbt/models/rejected_trades.sql](../snowflake/dbt/models/rejected_trades.sql):

A record is rejected when one or more of the following conditions occur:

- `version < max_version` for its trade family
- `maturity_date < date_trunc('day', load_ts)`
- a duplicate same-version record is replaced by a newer row

The rejection reason is assigned to one of the accepted classification values in the schema contract, such as:

- `LOWER_VERSION_THAN_EXISTING`
- `MATURITY_DATE_EARLIER_THAN_LOAD_DATE`
- `REPLACED_BY_SAME_VERSION`
- `UNKNOWN_REJECTION_REASON`

## 8. Accepted and rejected output tables

The SQL DDL files define the target physical tables:

- [snowflake/ddl/create_valid_trades_table.sql](../snowflake/ddl/create_valid_trades_table.sql)
- [snowflake/ddl/create_rejected_trades_table.sql](../snowflake/ddl/create_rejected_trades_table.sql)

In the operational flow:

- the valid-trade model loads records that pass the business rules into the valid-trades table
- the rejected-trade model loads records that fail the business rules into the rejected-trades table

## 9. Data quality checks

The dbt contract file [snowflake/dbt/models/schema.yml](../snowflake/dbt/models/schema.yml) defines source and model tests. These tests ensure that key fields are populated and that trade-side values remain within the allowed domain.

dbt will run tests such as:

- `not_null`
- `accepted_values` checks on `side` and `status`
- source validation checks over the raw feed contract

## 10. End-to-end summary

The flow is:

```text
Generate CSV trades
    -> Land CSV into Snowflake via stage loader
    -> Raw_TRADES table receives records
    -> dbt stg_raw_trades reads from source
    -> valid_trades.sql selects accepted records
    -> rejected_trades.sql assigns rejection reason for excluded records
    -> dbt tests enforce schema and domain quality rules
```

This is the repository’s intended high-level operational lifecycle for a sample trade-data ingestion and validation pipeline.
