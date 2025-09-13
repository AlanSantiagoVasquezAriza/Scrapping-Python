import fastapi
from routes.news import router as news_router

app = fastapi.FastAPI()
app.include_router(news_router)