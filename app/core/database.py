
from pymongo import MongoClient
from app.core.config import MONGO_URL,DATABASE_NAME

client= MongoClient(MONGO_URL)
database=client[DATABASE_NAME]

task_collection=database["tasks"]