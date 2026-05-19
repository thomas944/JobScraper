from utils.types import JobCardInfo

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

def passes_preliminary_filters(job: JobCardInfo, page) -> bool:
    for word in BLOCKED_TITLE_WORDS:
        if word in job.title.lower():
            print(f"Removing from page {page}: {job.title}")
            return False
    
    for word in BLOCKED_COUNTRIES:
        if word in job.location.lower():
            print(f"Removing from page {page}: {job.title}")
            return False
    
    return True
