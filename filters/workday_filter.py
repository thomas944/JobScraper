from datetime import datetime
from utils.types import JobCardInfo, JobDescriptionInfo
from utils.utils import STATE_NAMES, STATE_ABBR, DESIRED_COUNTRY


def passes_preliminary_filters(job: JobCardInfo, BLOCKED_TITLE_WORDS, BLOCKED_COUNTRIES) -> bool:
    if job.posted_date == datetime(1999, 1, 1):
        return False
    title = job.title.lower()
    for word in BLOCKED_TITLE_WORDS:
        if word in title:
            return False
    
    location = job.location.lower()
    for word in BLOCKED_COUNTRIES:
        if word in location:
            return False
    for abbr in STATE_ABBR:
        if abbr in location:
            return True
        
    for state in STATE_NAMES:
        if state in location:
            return True
        
    for country in DESIRED_COUNTRY:
        if country in location:
            return True
    
    return False

def passes_secondary_filters(job: JobDescriptionInfo, DEGREES, MIN_YOE, MAX_YOE) -> bool:
    if "Master's" in job.degrees and "Master's" not in DEGREES:
        return False
    if "PhD" in job.degrees and "PhD" not in DEGREES:
        return False
    
    if job.min_yoe and job.max_yoe:
        if not max(job.min_yoe, MIN_YOE) <= min(job.max_yoe, MAX_YOE):
            return False
    
    return True

