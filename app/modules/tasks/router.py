from fastapi import APIRouter , status

from app.modules.tasks.schema import TaskCreate,TaskResponse
from app.modules.tasks.service import create_task , get_tasks

#Create API router 
router =APIRouter()

# create a new Task
@router.post("/",response_model=TaskCreate,status_code=status.HTTP_201_CREATED)
def add_task(data:TaskCreate):
    return create_task(data)

# Get all Task

@router.get("/",response_model=list[TaskResponse])
def list_task(arg):
    return get_tasks()

