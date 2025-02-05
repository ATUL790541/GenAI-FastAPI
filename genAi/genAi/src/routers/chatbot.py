
from pydantic import BaseModel, validator, conlist, constr, ValidationError, root_validator
from fastapi import status, HTTPException
from typing import List, Union, Optional
from modules import source
from fastapi import FastAPI, Request, Form,UploadFile,File
#from fastapi.middleware.cors import CORSMiddleware

    
from fastapi import APIRouter, status


    
router = APIRouter(tags=["File"], prefix="/path")

class Dbdetail(BaseModel):
    sector : str
    retailer : str
    
    


@router.post("/chat_question/",summary ="Process the question fetched in chatbot",description="Fetching the question and process them in chatbot")
async def file_path(dbdetails : Dbdetail):
    body =  dbdetails.model_dump()
    get_question = source.get_db_question(body)
    if get_question:
        return {"status": {"responseStatus": True, "responseCode": status.HTTP_202_ACCEPTED,"responseMessage": "Data Successfully retrieved as requested"}, "data":get_question }
    else:
        raise HTTPException(status_code=404, detail="Failed return question details")