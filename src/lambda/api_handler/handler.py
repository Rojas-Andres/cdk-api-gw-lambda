from fastapi import FastAPI
from mangum import Mangum

app = FastAPI()


@app.get("/user")
def get_user():
    return {"status": "ok"}


handler = Mangum(app)
