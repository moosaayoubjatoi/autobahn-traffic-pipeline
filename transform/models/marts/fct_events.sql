-- Fact table: one row per event in OWL, built from all snapshots.
-- first_seen / last_seen come from the pipeline runs, so their accuracy
-- depends on how often the pipeline runs.

with events as (
    select * from {{ ref('stg_events') }}
    where is_in_owl
),

latest_run as (
    select max(fetched_at) as fetched_at from {{ ref('stg_events') }}
),

per_event as (
    select
        event_id,
        min(fetched_at)                as first_seen_at,
        max(fetched_at)                as last_seen_at,
        count(*)                       as snapshot_count,
        max(delay_minutes)             as max_delay_minutes,
        bool_or(is_blocked)            as was_blocked,
        -- descriptive fields: take the values from the most recent snapshot
        arg_max(road, fetched_at)      as road,
        arg_max(event_type, fetched_at)   as event_type,
        arg_max(display_type, fetched_at) as display_type,
        arg_max(stretch, fetched_at)   as stretch,
        arg_max(direction, fetched_at) as direction,
        arg_max(traffic_type, fetched_at) as traffic_type,
        arg_max(lat, fetched_at)       as lat,
        arg_max(lng, fetched_at)       as lng
    from events
    group by event_id
)

select
    per_event.*,
    per_event.last_seen_at = latest_run.fetched_at                         as is_active,
    date_diff('minute', per_event.first_seen_at, per_event.last_seen_at)   as observed_minutes
from per_event
cross join latest_run
