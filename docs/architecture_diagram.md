# Trade Data Pipeline Architecture Diagram

## System Context

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Trade Data Pipeline                                │
└─────────────────────────────────────────────────────────────────────────────┘

                                       │
                                       │ Synthetic trade generation
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ ingestion/trade_generator/generate_trades.py                                │
│ Generates synthetic CSV trade records                                       │
│ - trade_id, timestamp, symbol, side, quantity, price, currency, venue       │
│ - version, maturity_date, status, source_file, load_ts                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       │ Output file: CSV
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ ingestion/loader/stage_to_snowflake.py                                     │
│ Snowflake ingestion orchestration                                          │
│ - load YAML configuration                                                   │
│ - connect to Snowflake                                                      │
│ - PUT staged file into table stage                                          │
│ - COPY INTO raw trade table                                                │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       │ Snowflake SQL / COPY INTO
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Snowflake Warehouse                                                        │
│                                                                            │
│  RAW_TRADES                                                                │
│  --------------------------------------------------------------------------  │
│  Incoming raw CSV payload loaded into Snowflake raw staging table           │
│                                                                            │
│  VALID_TRADES                                                               │
│  Business-valid latest-version records                                    │
│                                                                            │
│  REJECTED_TRADES                                                            │
│  Business-invalid records and rejection classification                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       │ dbt reads raw source
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ dbt transformation layer                                                    │
│ snowflake/dbt/models                                                        │
│                                                                            │
│ stg_raw_trades.sql     -> raw source staging view                          │
│ valid_trades.sql       -> deduped valid business-record output              │
│ rejected_trades.sql   -> rejected business-record output                   │
│                                                                            │
│ schema.yml             -> dbt source/model contracts and tests             │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       │ dbt run / dbt test
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Quality & governance gates                                                 │
│ - not_null tests                                                            │
│ - accepted_values tests                                                     │
│ - source contract checks                                                    │
│ - downstream model validation                                               │
└─────────────────────────────────────────────────────────────────────────────┘

## Layered View

```text
┌──────────────────────────────┐
│  Application / Orchestration  │
│  scripts/deploy_snowflake_obj │
│  scripts/run_dbt_tests.sh     │
└──────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────┐
│  Ingestion Layer              │
│  generate_trades.py           │
│  stage_to_snowflake.py        │
└──────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────┐
│  Snowflake Raw Landing        │
│  raw_trades                   │
└──────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────┐
│  dbt Transformations          │
│  stg_raw_trades               │
│  valid_trades                 │
│  rejected_trades              │
└──────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────┐
│  Data Quality / Validation    │
│  dbt tests + schema.yml       │
└──────────────────────────────┘
```

## Data Classification flow

```text
Input CSV         →       Snowflake RAW_TRADES        →       dbt stg_raw_trades
                                                           │
                                                           ├────► valid_trades.sql
                                                           │
                                                           └────► rejected_trades.sql
```

## Notes

- The pipeline is intentionally synthetic and should be adapted to real source inputs if productionized.
- The DDL files create the warehouse objects that the pipeline contracts against.
- The loader uses environment, YAML config, and CLI argument resolution to connect to Snowflake.
