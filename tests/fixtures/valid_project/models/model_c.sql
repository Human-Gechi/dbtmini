select
    id,
    length(name) as name_len
from {{ ref('model_a') }}
