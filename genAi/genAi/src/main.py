



tags_metadata = [
    {
        "name": "GenAI",
        "description": "GenAI based app",
    },
  
]




from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from routers.api import app as api_router


def get_application() -> FastAPI:
    
    app = FastAPI(openapi_tags=tags_metadata)

    origins = ["*"]

    app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    )   

    
    app.include_router(api_router)
    return app


app = get_application()



if __name__ == "__main__":
    import uvicorn
    from uvicorn import run

    uvicorn.run(app, host="127.0.0.1", port=8000)
    
