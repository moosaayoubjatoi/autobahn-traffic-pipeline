-- A delay can never be negative. Returns the bad rows; the test passes when none come back.
select * from {{ ref('stg_events') }}
where delay_minutes < 0
