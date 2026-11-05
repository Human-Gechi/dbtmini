{{ config(materialized='view') }}

select
    customer_id,
    min(order_date) as first_order_date,
    max(order_date) as last_order_date,
    count(order_id) as number_of_orders
from {{ ref('stg_orders') }}
group by customer_id
