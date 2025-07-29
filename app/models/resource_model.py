from pydantic import BaseModel
from typing import List, Optional
from datetime import date, datetime


class AuthorBase(BaseModel):
    name: str
    title: Optional[str] = None
    degree: Optional[str] = None
    affiliation: Optional[str] = None

class AuthorOut(AuthorBase):
    id: int

    class Config:
        orm_mode = True


class ResourceBase(BaseModel):
    title: str
    content: str
    publication_date: Optional[date] = None
    publisher: Optional[str] = None

class ResourceCreate(ResourceBase):
    file_path: Optional[str] = None
    file_url: Optional[str] = None

class ResourceUpdate(ResourceBase):
    file_path: Optional[str] = None
    file_url: Optional[str] = None

class ResourceOut(ResourceBase):
    id: int
    file_path: Optional[str] = None
    file_url: Optional[str] = None
    publication_date: Optional[date] = None
    publisher: Optional[str] = None
    created_at: datetime
    authors: List[AuthorOut] = [] 
    updated_at: datetime

    class Config:
        orm_mode = True
        allow_population_by_field_name = True  


# Extend ResourceBase to optionally accept authors when creating/updating
class ResourceCreate(ResourceBase):
    file_path: Optional[str] = None
    file_url: Optional[str] = None
    authors: Optional[List[AuthorBase]] = []

class ResourceUpdate(ResourceBase):
    file_path: Optional[str] = None
    file_url: Optional[str] = None
    authors: Optional[List[AuthorBase]] = []
