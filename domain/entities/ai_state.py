from pydantic import BaseModel


class AIState(BaseModel):
    id: int
    last_message: str | None = None
    data_state: bytes | None = None
    data_storage: bytes | None = None
    data_writes: bytes | None = None
    data_default: bytes | None = None

    model_config = {
        "from_attributes": True
    }