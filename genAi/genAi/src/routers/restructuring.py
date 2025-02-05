
from pydantic import BaseModel, validator, conlist, constr, ValidationError, root_validator
from fastapi import status, HTTPException
from typing import List, Union, Optional
from modules import source
from fastapi import FastAPI, Request, Form,UploadFile,File
#from fastapi.middleware.cors import CORSMiddleware

    
from fastapi import APIRouter, status


class Schema(BaseModel):
    file_name : str
    sheet_name : List[str]


router = APIRouter(tags=["Structuring"], prefix="/structure")

@router.post("/file_system/",summary ="List of file uploading and generate schema",description="Generate the schema of uploaded file")
async def schema_generation(check_path : Schema):
    body = check_path.model_dump()
    schema_generation = source.generate_schema(body)
    if schema_generation:
        return {"status": {"responseStatus": True, "responseCode": status.HTTP_202_ACCEPTED,"responseMessage": "Data Successfully retrieved as requested"}, "data":schema_generation }
    else:
        raise HTTPException(status_code=404, detail="Failed generate schema")
    
