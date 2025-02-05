
from pydantic import BaseModel, validator, conlist, constr, ValidationError, root_validator
from fastapi import status, HTTPException
from typing import List, Union, Optional
from modules import source
from fastapi import FastAPI, Request, Form,UploadFile,File
#from fastapi.middleware.cors import CORSMiddleware

    
from fastapi import APIRouter, status


class Structure(BaseModel):
    file_name : str
    sheet_name : List[str]
    sub_ques : List[List[str]]


router = APIRouter(tags=["Structuring"], prefix="/structure")

@router.post("/generated_schema/",summary ="List of file uploading and generate schema and structure the generated_schema",description="Structre the generated_schema")
async def schema_structure(check_structure : Structure):
    body = check_structure.model_dump()
    structure_schema = source.structure_schema(body)
    if structure_schema:
        return {"status": {"responseStatus": True, "responseCode": status.HTTP_202_ACCEPTED,"responseMessage": "Data Successfully retrieved as requested"}, "data":structure_schema }
    else:
        raise HTTPException(status_code=404, detail="Failed generate schema")