{{ config(materialized='table') }}

with raw as (
    select *
    from {{ ref('stg_raw_trades') }}
),
ranked_trades as (
    select
        *,
        max(version) over (partition by trade_id) as max_version,
        row_number() over (
            partition by trade_id
            order by version desc, load_ts desc
        ) as version_rank
    from raw
),
valid_candidates as (
    select *
    from ranked_trades
    where version_rank = 1
),
valid_records as (
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
        case
            when maturity_date < current_date() then 'EXPIRED'
            else 'ACTIVE'
        end as status,
        source_file,
        load_ts
    from valid_candidates
    where maturity_date >= date_trunc('day', load_ts)
)

select * from valid_records
