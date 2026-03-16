from celery import Celery
from dotenv import load_dotenv
import os

load_dotenv() 

broker = os.environ.get("BROKER")
backend = os.environ.get("BACKEND")

celery = Celery(
    "tasks",
    broker=broker,
    backend=backend,
)