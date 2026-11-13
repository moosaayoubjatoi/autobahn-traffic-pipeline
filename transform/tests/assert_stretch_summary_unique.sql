-- The summary must have exactly one row per road, stretch and direction.
select road, stretch, direction, count(*) as n
from {{ ref('agg_stretch_summary') }}
group by all
having count(*) > 1
