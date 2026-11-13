-- If no event falls inside OWL, the region filter or the API has probably broken.
select 1 as problem
where (select count(*) from {{ ref('fct_events') }}) = 0
