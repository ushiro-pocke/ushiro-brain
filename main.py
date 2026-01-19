from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# WordPressからのアクセスを許可する設定
# 本番環境では ["https://ushiro-pocke.com"] に絞るのが理想ですが、
# まずはテスト用に全許可 ["*"] にしています。
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# データを受け取る型（リクエストの形）
class TextRequest(BaseModel):
    text: str
    noise_level: float = 0.5
    human_level: float = 0.5

@app.get("/")
def read_root():
    return {"status": "Ushiro-Brain is awake! 🧠"}

@app.post("/humanize")
def humanize_text(req: TextRequest):
    """
    ここにAI変換ロジックが入ります。
    """
    # とりあえず、Pythonが動いている証拠として文字を足して返します
    result_text = f"【Python変換済み】\n{req.text}\n\n（ノイズLv:{req.noise_level} / 人間Lv:{req.human_level}）"
    
    return {"result": result_text}