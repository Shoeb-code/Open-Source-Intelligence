
from app.modules.tasks.schema import TaskCreate

tasks =[]
next_id=1

def create_task(data:TaskCreate):
    global next_id
    
    task={
        "id":next_id,
        "title":data.title,
        "description":data.description 
    }
    
    tasks.append(task)
    next_id+=1
    
    return task

def get_tasks():
    return tasks