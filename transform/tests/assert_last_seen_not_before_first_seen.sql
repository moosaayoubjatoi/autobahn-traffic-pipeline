-- An event cannot end before it starts.
select * from {{ ref('fct_events') }}
where last_seen_at < first_seen_at
