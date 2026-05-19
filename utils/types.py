from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class JobCardInfo:
    page: Optional[str]
    title: Optional[str]
    location: Optional[str]
    remote_type: Optional[str]
    posted_date: Optional[datetime]
    job_id: Optional[str]
    parsed_date: datetime
    link: Optional[str]

@dataclass
class JobDescriptionInfo:
    end_date: Optional[str]
    years_of_exp: Optional[str]