{{ config(materialized='view') }}

select
    id as customer_id,
    name,
    email
from {{ ref('customers') }}
