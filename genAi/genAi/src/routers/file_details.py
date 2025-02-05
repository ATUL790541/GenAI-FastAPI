
from pydantic import BaseModel, validator, conlist, constr, ValidationError, root_validator
from fastapi import status, HTTPException
from typing import List, Union, Optional
from modules import source
from fastapi import FastAPI, Request, Form,UploadFile,File
#from fastapi.middleware.cors import CORSMiddleware

    
from fastapi import APIRouter, status


class Filepath(BaseModel):
    file_path : str

class Filename(BaseModel):
    file_name : str
    
router = APIRouter(tags=["Structuring"], prefix="/path")

@router.post("/file_system/",summary ="File path of the file",description="Getting the file path of file")
async def file_path(check_path : Filepath):
    body = check_path.model_dump()
    file_path = source.get_file_path(body)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File does not exist.")
    elif not file_path.is_file():
        raise HTTPException(status_code=400, detail="Provided path is not a file.")
    else:
        return {"status": {"responseStatus": True, "responseCode": status.HTTP_202_ACCEPTED,"responseMessage": "Data Successfully retrieved as requested"}, "data":file_path }
    

@router.post("/sheet_name/",summary ="Sheet name of the file",description="Getting the sheet name of file")
async def file_path(check_path :Filename):
    body = check_path.model_dump()
    get_sheet_name = source.get_sheet_name(body)
    if get_sheet_name:
        return {"status": {"responseStatus": True, "responseCode": status.HTTP_202_ACCEPTED,"responseMessage": "Data Successfully retrieved as requested"}, "data":get_sheet_name }
    else:
        raise HTTPException(status_code=404, detail="Failed to get sheet name")
    
 