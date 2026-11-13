-- Summary per road stretch and direction: how many roadworks, closures and
-- warnings, and the worst delay seen.

select
    road,
    stretch,
    direction,
    count(*) filter (where event_type = 'roadworks') as roadworks_count,
    count(*) filter (where event_type = 'closure')   as closure_count,
    count(*) filter (where event_type = 'warning')   as warning_count,
    count(*) filter (where is_active)                as active_count,
    max(max_delay_minutes)                           as max_delay_minutes
from {{ ref('fct_events') }}
group by road, stretch, direction
order by closure_count desc, roadworks_count desc
