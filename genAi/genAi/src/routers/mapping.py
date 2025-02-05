from pydantic import BaseModel, validator, conlist, constr, ValidationError, root_validator
from fastapi import status, HTTPException
from typing import List, Union, Optional
from modules import source
from fastapi import FastAPI, Request, Form,UploadFile,File
#from fastapi.middleware.cors import CORSMiddleware
from fastapi import APIRouter, status


class Filename(BaseModel):
    file_name : str
    
class FileDetails(BaseModel):
    file_name : str
    retailer : str
    sector : str
    table : str  

class Dbupdate(BaseModel):
    file_name : str
    operation : str
    retailer : str
    sector : str
    table : str
    
class Dbview(BaseModel):
    retailer : str
    sector : str
    table : str
    
class Dbedit(BaseModel):
    retailer : str
    sector : str
    table : str
    
router = APIRouter(tags=["Mapping"], prefix="/mapping")


@router.post("/file_content/",summary ="Display the content of uploaded file",description="Getting the content of uploaded file")
async def file_path(check_path : Filename):
    body = check_path.model_dump()
    get_content = source.get_file_content(body)
    print("get",get_content)
    if get_content:
        return {"status": {"responseStatus": True, "responseCode": status.HTTP_202_ACCEPTED,"responseMessage": "Data Successfully retrieved as requested"}, "data":get_content }
    else:
        raise HTTPException(status_code=404, detail="Failed to read the file")




@router.post("/validation/",summary ="Validation of content of uploaded file",description="Checks whether the content of uploaded file are validated or not")
async def file_validation(check_path : FileDetails):
    body = check_path.model_dump()
    get_content = source.validate_file(body)
    #print("get",get_content)
    if get_content:
        return {"status": {"responseStatus": True, "responseCode": status.HTTP_202_ACCEPTED,"responseMessage": "Data Successfully retrieved as requested"}, "data":get_content }
    else:
        raise HTTPException(status_code=404, detail="Failed to validate the content of file")

@router.post("/update/",summary ="Overwrite or replace the database",description="Based the file validated update the content of database overwrite or replace")
async def file_updation(check_path : Dbupdate):
    body = check_path.model_dump()
    get_content = source.update_database(body)
    print("get",get_content)
    if get_content:
        return {"status": {"responseStatus": True, "responseCode": status.HTTP_202_ACCEPTED,"responseMessage": "Data Successfully retrieved as requested"}, "data":get_content }
    else:
        raise HTTPException(status_code=404, detail="Failed update the database")
    
    
@router.post("/view/",summary ="View the database for selected sector and retailer",description="Based on selected sector and retailer and type of mapping see the database content")
async def file_updation(check_path : Dbview):
    body = check_path.model_dump()
    get_content = source.view_database(body)
    #print("get",get_content)
    if get_content:
        return {"status": {"responseStatus": True, "responseCode": status.HTTP_202_ACCEPTED,"responseMessage": "Data Successfully retrieved as requested"}, "data":get_content }
    else:
        raise HTTPException(status_code=404, detail="Failed to view the database")
    
    
    
@router.post("/edit/",summary ="Edit the database for selected sector and retailer",description="Based on selected sector and retailer and type of mapping edit the database content")
async def file_updation(check_path : Dbedit):
    body = check_path.model_dump()
    get_content = source.edit_database(body)
    #print("get",get_content)
    if get_content:
        return {"status": {"responseStatus": True, "responseCode": status.HTTP_202_ACCEPTED,"responseMessage": "Data Successfully retrieved as requested"}, "data":get_content }
    else:
        raise HTTPException(status_code=404, detail="Failed to edit the database")
    
    
@router.post("/save/",summary ="Save the database for selected sector and retailer",description="Based on selected sector and retailer and type of mapping Save the database content")
async def file_updation(check_path : Dbedit):
    body = check_path.model_dump()
    get_content = source.save_database(body)
    #print("get",get_content)
    if get_content:
        return {"status": {"responseStatus": True, "responseCode": status.HTTP_202_ACCEPTED,"responseMessage": "Data Successfully retrieved as requested"}, "data":get_content }
    else:
        raise HTTPException(status_code=404, detail="Failed to Save the database")
    
    
@router.post("/generate_map/",summary ="Generate the mapping for uploaded file",description="Based on uploaded file generate the scheme for generate mapping")
async def generate_map(check_path : Filename):
    body = check_path.model_dump()
    get_content = await source.generate_mapping_schema(body)
    #print("get",get_content)
    if get_content:
        return {"status": {"responseStatus": True, "responseCode": status.HTTP_202_ACCEPTED,"responseMessage": "Data Successfully retrieved as requested"}, "data":get_content }
    else:
        raise HTTPException(status_code=404, detail="Failed to generate the schema")