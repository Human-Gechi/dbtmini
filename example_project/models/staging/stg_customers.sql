{{ config(materialization='table') }}

-- testing waters
select * from {{ ref('customers') }}
