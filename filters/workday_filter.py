from utils.types import JobCardInfo, JobDescriptionInfo

BLOCKED_TITLE_WORDS = [
    "principal",
    "staff",
    "senior",
    "sr.",
    "lead",
    "manager"
]

BLOCKED_COUNTRIES = [
    "india",
    "poland",
    "mexico"
]

DESIRED_COUNTRY = [
    "US",
    "USA",
    "United States",
    "United States of America"
]

DESIRED_KEYWORDS = [

]

DEGREES = [
    "Bachelor's"
]

MIN_YOE = 0
MAX_YOE = 3

def passes_preliminary_filters(job: JobCardInfo, page) -> bool:
    for word in BLOCKED_TITLE_WORDS:
        if word in job.title.lower():
            # print(f"Removing from page {page}: {job.title}")
            return False
    
    for word in BLOCKED_COUNTRIES:
        if word in job.location.lower():
            # print(f"Removing from page {page}: {job.title}")
            return False
    
    return True

def passes_secondary_filters(job: JobDescriptionInfo) -> bool:
    if "Master's" in job.degrees and "Master's" not in DEGREES:
        return False
    if "PhD" in job.degrees and "PhD" not in DEGREES:
        return False
    
    if not max(job.min_yoe, MIN_YOE) <= min(job.max_yoe, MAX_YOE):
        return False
    
    return True