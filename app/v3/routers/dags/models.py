from datetime import datetime
from typing import List
from croniter import croniter
from pydantic import BaseModel, Field, validator


class DAG(BaseModel):
    dag_id: str
    description: str
    start_date: datetime | None = datetime.now()
    schedule_interval: str | None = Field(
        description="cron expression = * * * * *", default="* * * * *"
    )
    sources: List[int] = Field(...)

    class Config:
        use_enum_values = True

    @validator("schedule_interval")
    def check_schedule_interval(cls, schedule_interval):
        available_values = [
            None,
            "@once",
            "@hourly",
            "@daily",
            "@weekly",
            "@monthly",
            "@yearly",
        ]
        if schedule_interval in available_values:
            return schedule_interval

        if croniter.is_valid(schedule_interval):
            return schedule_interval

        raise ValueError(
            f"schedule_interval can be a cron expression '* * * * *', or one of the values: {available_values}"
        )
