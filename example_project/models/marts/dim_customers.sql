{{ config(materialized='table') }}

select
    customers.customer_id,
    customers.name,
    customers.email,
    customer_orders.first_order_date,
    customer_orders.last_order_date,
    coalesce(customer_orders.number_of_orders, 0) as number_of_orders,
    coalesce(customer_payments.total_amount, 0) as lifetime_value
from {{ ref('stg_customers') }} as customers
left join {{ ref('int_customer_orders') }} as customer_orders
    on customers.customer_id = customer_orders.customer_id
left join {{ ref('int_customer_payments') }} as customer_payments
    on customers.customer_id = customer_payments.customer_id
