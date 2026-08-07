{{ config(materialized='view') }}

select
  trade_id,
  timestamp,
  symbol,
  side,
  quantity,
  price,
  currency,
  venue,
  version,
  maturity_date,
  status,
  rejection_reason,
  source_file,
  load_ts
from {{ source('trade_data_pipeline', 'raw_trades') }}
