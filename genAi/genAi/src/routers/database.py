
from pydantic import BaseModel, validator, conlist, constr, ValidationError, root_validator
from fastapi import status, HTTPException
from typing import List, Union, Optional
from modules import source
from fastapi import FastAPI, Request, Form,UploadFile,File
#from fastapi.middleware.cors import CORSMiddleware

    
from fastapi import APIRouter, status


    
router = APIRouter(tags=["Structuring"], prefix="/path")

class Dbdetails(BaseModel):
    sector : str
    retailer : str
    
    


@router.post("/db_details/",summary ="Get the database details for selected retailer",description="Fetching the database details based on selected reatailer")
async def file_path(dbdetails : Dbdetails):
    body =  dbdetails.model_dump()
    get_db_question = source.get_db_details(body)
    if get_db_question:
        return {"status": {"responseStatus": True, "responseCode": status.HTTP_202_ACCEPTED,"responseMessage": "Data Successfully retrieved as requested"}, "data":get_db_question }
    else:
        raise HTTPException(status_code=404, detail="Failed return database details")