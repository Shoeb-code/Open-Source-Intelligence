from fastapi import FastAPI
from app.modules.tasks.router import router as tasks_router

app=FastAPI(title="My backend API")

@app.get("/")
def home():
    return {"message":"Welcome to my API"}



@app.get("/about")   
def about():
    return {"message":"this is my fastAPI project"}

app.include_router(
    tasks_router,
    prefix="/api/v1/tasks",
    tags=["Tasks"]
)    
