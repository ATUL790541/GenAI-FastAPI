
from fastapi import FastAPI, Request, Form,UploadFile,File
from fastapi.middleware.cors import CORSMiddleware
import json
from pydantic import BaseModel, validator, conlist, constr, ValidationError, root_validator
from typing import List, Union, Optional



from fastapi import APIRouter

from routers import (
    structuring,
    restructuring,
    file_details,
    update_schema,
    database,
    chatbot,
    mapping,
    #calc,
)


router_home = APIRouter(tags=["Welcome"], prefix="")



@router_home.get("/")
def homecall():
    # print("Welcome to Genarative AI API")
    return "Welcome to Genarative AI API!"



app = APIRouter()


# Home call

app.include_router(router_home)





app.include_router(
    restructuring.router
    
)

app.include_router(
    file_details.router
)


app.include_router(
    update_schema.router
    )

app.include_router(
    structuring.router
)

app.include_router(
    database.router
)


app.include_router(
    chatbot.router
)

app.include_router(
    mapping.router
)
'''
app.include_router(
    calc.router
)
'''
