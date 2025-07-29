from fastapi import APIRouter, Depends, status, UploadFile, File, Form, HTTPException
from typing import Optional, List
import json

from app.utils.role_handle import require_admin
from app.routes.users import get_current_user
from app.models.resource_model import ResourceOut
from app.controllers.resource_controller import (
    get_all_resources,
    get_resource_by_id,
    create_resource,
    update_resource,
    soft_delete_resource,
)

router = APIRouter(
    prefix="/resources",
    tags=["resources"]
)

@router.get("/", response_model=List[ResourceOut])
def read_resources(current_user: dict = Depends(get_current_user)):
    return get_all_resources()


@router.get("/{resource_id}", response_model=ResourceOut)
def read_resource(resource_id: int, current_user: dict = Depends(get_current_user)):
    resource = get_resource_by_id(resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    return resource

@router.post("/", response_model=ResourceOut, status_code=status.HTTP_201_CREATED)
async def create_new_resource(
    title: str = Form(...),
    content: str = Form(...),
    publisher: Optional[str] = Form(None),
    publication_date: Optional[str] = Form(None), 
    file_url: Optional[str] = Form(None),
    authors: str = Form("[]"),
    file: UploadFile = File(None),
    current_user: dict = Depends(require_admin),
):
    # Validating authors format
    try:
        authors_list = json.loads(authors)
        if not isinstance(authors_list, list):
            raise ValueError()
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid authors JSON format; must be a JSON array.")

    # Handle file upload if present
    if file:
        # Ensure that file is saved correctly
        valid_types = [
            'application/pdf', 
            'application/msword', 
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'text/plain'  # Added support for .txt files
        ]
        if file.content_type not in valid_types:
            raise HTTPException(status_code=400, detail="Invalid file type. Only PDF, Word documents, and .txt files are allowed.")
    
    resource_data = {
        "title": title,
        "content": content,
        "publisher": publisher,
        "publication_date": publication_date,  
        "file_url": file_url,
        "authors": authors_list,
    }

    # Creating the resource
    new_resource = create_resource(resource_data, uploaded_file=file)
    return new_resource

@router.patch("/{resource_id}", response_model=ResourceOut)
async def patch_resource(
    resource_id: int,
    title: Optional[str] = Form(None),
    content: Optional[str] = Form(None),
    file_url: Optional[str] = Form(None),
    publication_date: Optional[str] = Form(None),
    publisher: Optional[str] = Form(None),
    authors: Optional[str] = Form(None),  
    uploaded_file: Optional[UploadFile] = File(None)
):
    try:
        authors_list = json.loads(authors) if authors else []
        if authors and not isinstance(authors_list, list):
            raise ValueError()
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid authors JSON format; must be a JSON array.")

    valid_types = [
        'application/pdf', 
        'application/msword', 
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'text/plain'
    ]
    if uploaded_file and uploaded_file.content_type not in valid_types:
        raise HTTPException(status_code=400, detail="Invalid file type. Only PDF, Word documents, and .txt files are allowed.")

    resource_data = {}
    if title is not None:
        resource_data["title"] = title
    if content is not None:
        resource_data["content"] = content
    if file_url is not None:
        resource_data["file_url"] = file_url
    if publication_date is not None:
        resource_data["publication_date"] = publication_date
    if publisher is not None:
        resource_data["publisher"] = publisher
    if authors_list:
        resource_data["authors"] = authors_list

    return update_resource(resource_id, resource_data, uploaded_file)

@router.delete("/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resource(
    resource_id: int,
    current_user: dict = Depends(require_admin),
):
    deleted = soft_delete_resource(resource_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Resource not found")
    return None
