select
    b.id,
    b.name_upper,
    c.name_len
from {{ ref('model_b') }} as b
join {{ ref('model_c') }} as c
    on b.id = c.id
