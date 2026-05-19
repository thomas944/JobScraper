# from sqlalchemy import Column, Integer, String, Text, DateTime
# from sqlalchemy.orm import declarative_base
# from datetime import datetime

# Base = declarative_base()

# class Job(Base):
#     __tablename__ = "jobs"

#     id = Column(Integer, primary_key=True)

#     company = Column(String)
#     title = Column(String)

#     job_id = Column(String, unique=True)

#     location = Column(String)
#     posted_date = Column(String)

#     years_min = Column(Integer)
#     years_max = Column(Integer)

#     salary = Column(String)

#     description = Column(Text)

#     link = Column(String)

#     scraped_date = Column(DateTime, default=datetime.utcnow