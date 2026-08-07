{{ config(materialized='table') }}

with raw as (
    select *
    from {{ ref('stg_raw_trades') }}
),
versioned as (
    select
        *,
        max(version) over (partition by trade_id) as max_version,
        row_number() over (
            partition by trade_id
            order by version desc, load_ts desc
        ) as version_rank
    from raw
),
rejected as (
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
            when version < max_version then 'LOWER_VERSION_THAN_EXISTING'
            when maturity_date < date_trunc('day', load_ts) then 'MATURITY_DATE_EARLIER_THAN_LOAD_DATE'
            when version_rank > 1 and version = max_version then 'REPLACED_BY_SAME_VERSION'
            else 'UNKNOWN_REJECTION_REASON'
        end as rejection_reason,
        source_file,
        load_ts
    from versioned
    where
        version < max_version
        or maturity_date < date_trunc('day', load_ts)
        or (version_rank > 1 and version = max_version)
)

select * from rejected
