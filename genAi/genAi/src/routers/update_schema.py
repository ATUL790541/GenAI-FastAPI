
from pydantic import BaseModel, validator, conlist, constr, ValidationError, root_validator
from fastapi import status, HTTPException
from typing import List, Union, Optional
from modules import source
from fastapi import FastAPI, Request, Form,UploadFile,File
#from fastapi.middleware.cors import CORSMiddleware

    
from fastapi import APIRouter, status

class updateSchema(BaseModel):
    file_name : str
    sheet_name : List[str]
    sub_ques : List[List[str]]

class Question(BaseModel):
    sheet_name : List[str]
    ques : List[str]
    

router = APIRouter(tags=["Structuring"], prefix="/structure")


@router.post("/question/",summary="Subquestion based on selected question yes or no for sheet",description="Return sub question for selected question")
async def question(check_question : Question):
    body = check_question.model_dump()
    update_ques = source.update_question(body)
    if update_ques:
        return {"status": {"responseStatus": True, "responseCode": status.HTTP_202_ACCEPTED,"responseMessage": "Data Successfully retrieved as requested"}, "data":update_ques }
    else:
        raise HTTPException(status_code=404, detail="Failed to update schema")


@router.post("/schema_update/",summary="Update the generated schema based on selected question",description="Update schema of the uploaded file")
async def update_schema(check_schema : updateSchema):
    body = check_schema.model_dump()
    update_schema = source.update_schema(body)
    if update_schema:
        return {"status": {"responseStatus": True, "responseCode": status.HTTP_202_ACCEPTED,"responseMessage": "Data Successfully retrieved as requested"}, "data":update_schema }
    else:
        raise HTTPException(status_code=404, detail="Failed to update schema")