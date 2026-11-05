{{ config(materialized='view') }}

select
    orders.customer_id,
    sum(payments.amount) as total_amount
from {{ ref('stg_orders') }} as orders
left join {{ ref('stg_payments') }} as payments
    on orders.order_id = payments.order_id
group by orders.customer_id
