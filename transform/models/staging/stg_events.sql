-- Staging: clean names and types, split the title, flag events inside Ostwestfalen-Lippe.
-- Still one row per event per snapshot.

with source as (
    select * from {{ source('raw', 'raw_events') }}
)

select
    event_id,
    fetched_at,
    road,
    event_type,
    display_type,

    -- Roadworks/warnings: title looks like "A2 | Bielefeld-Ost - Herford" -> keep the part after "|".
    -- Closures often have free text like "Fahrbahninstandsetzung" -> keep the whole title.
    -- Closure titles often repeat the road ("A44 - Sanierung ..."): drop that prefix.
    regexp_replace(
        case
            when title like '%|%' then trim(split_part(title, '|', 2))
            else trim(title)
        end,
        '^A[0-9]+\s*-\s*', ''
    )                                              as stretch,
    -- subtitle: a direction ("Dortmund -> Hannover") or a junction ("AS Büren (aus Richtung ...)")
    nullif(trim(subtitle), '')                     as direction,

    coalesce(is_blocked, false)                    as is_blocked,
    coalesce(is_future, false)                     as is_future,
    lat,
    lng,
    start_timestamp,
    delay_minutes,
    traffic_type,
    description,

    -- Approximate OWL area as two boxes (OWL is wider in the south, around Höxter):
    --   north: Gütersloh/Bielefeld/Herford/Minden-Lübbecke
    --   south: Paderborn/Höxter
    -- Excludes Osnabrück, Soest and Hannover region. Border towns can still slip in.
    coalesce(
        (lat between 51.90 and 52.55 and lng between 8.30 and 9.05)
        or (lat between 51.45 and 51.90 and lng between 8.50 and 9.50),
        false
    )                                              as is_in_owl

from source
