from enum import Enum
from datetime import datetime
from pydantic import BaseModel, HttpUrl
from typing import Optional, List, Dict, Any

class ApplicationStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    REJECTED = "rejected"
    INTERVIEWING = "interviewing"
    OFFERED = "offered"

class JobListing(BaseModel):
    """Represents a job listing from workatastartup.com"""
    id: str
    title: str
    company: str
    location: str
    url: str
    description: str
    posted_at: Optional[datetime] = None
    skills: List[str] = []
    experience_level: Optional[str] = None
    created_at: datetime = datetime.utcnow()
    
    @property
    def is_junior(self) -> bool:
        """Check if this is a junior/entry-level position"""
        if not self.experience_level:
            return False
        return any(term in self.experience_level.lower() 
                  for term in ["entry", "junior", "0-1", "0-2", "1+"])

class Application(BaseModel):
    """Represents a job application"""
    id: str
    job_id: str
    status: ApplicationStatus = ApplicationStatus.DRAFT
    cover_letter: str
    applied_at: Optional[datetime] = None
    updated_at: datetime = datetime.utcnow()
    notes: Optional[str] = None
    
    # Metadata for cloud sync
    synced: bool = False
    last_sync_attempt: Optional[datetime] = None

class JobFilter(BaseModel):
    """Filter criteria for job search"""
    experience_level: str = "0-1"  # Default to entry-level
    roles: List[str] = ["Software Engineer", "Developer", "Engineer"]
    remote_only: bool = True
    max_applications: int = 10  # Max applications per run
