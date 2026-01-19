from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from sudachipy import dictionary, tokenizer
import random
import re
import csv
import os

app = FastAPI()

# --- CORS設定 ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 🧠 解析エンジンの準備 ---
# エラーが出にくいよう、一番シンプルな記述に変えました
tokenizer_obj = dictionary.Dictionary().create()
mode = tokenizer.Tokenizer.SplitMode.C 

# --- 📚 辞書データの構築 ---
NOUN_DICT = {}

if os.path.exists("dict.csv"):
    with open("dict.csv", mode="r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2:
                key = row[0]
                candidates = row[1:]
                NOUN_DICT[key] = [c for c in candidates if c.strip()]

# --- 🗣 フィラー（ノイズ） ---
FILLERS = ["えーっと、", "なんか、", "正直、", "ぶっちゃけ、", "ていうか、", "実は、"]

# --- 🔚 文末表現パターン ---
ENDING_PATTERNS = [
    (r"です。$", ["ですね。", "ですよ。", "なんです。", "だね。"]),
    (r"ます。$", ["ますね。", "ますよ。", "ちゃうかも。", "ます〜。"]),
    (r"である。$", ["です。", "だね。", "なんだよね。"]),
]

# --- 🏥 文法整形ルール ---
GRAMMAR_FIXES = [
    (r"こと(する|します|した|して)", r"ことに\1"), 
    (r"([うくすつぬむる])する", r"\1"),
    (r"うた", r"った"), (r"つた", r"った"), (r"るた", r"た"),
    (r"くた", r"いた"), (r"ぐた", r"いだ"), (r"むた", r"んだ"),
    (r"うます", r"います"), (r"つます", r"ちます"), (r"るます", r"ます"),
]

class TextRequest(BaseModel):
    text: str
    noise_level: float = 0.5
    human_level: float = 0.5

@app.post("/humanize")
def humanize_text(req: TextRequest):
    text = req.text
    noise_lv = req.noise_level
    human_lv = req.human_level
    
    tokens = tokenizer_obj.tokenize(text, mode)
    result_buffer = ""
    
    for token in tokens:
        word = token.surface()
        if word in NOUN_DICT and random.random() < (human_lv + 0.1):
            word = random.choice(NOUN_DICT[word])
        if random.random() < (noise_lv * 0.05):
            word = random.choice(FILLERS) + word
        result_buffer += word
    
    processed_text = result_buffer
    
    # 文末調整
    sentences = processed_text.split("。")
    final_sentences = []
    for s in sentences:
        if not s: continue
        for pattern, candidates in ENDING_PATTERNS:
            if re.search(pattern, s) and random.random() < (human_lv + 0.2):
                s = re.sub(pattern, random.choice(candidates), s)
                break
        final_sentences.append(s)
        
    processed_text = "。".join(final_sentences)
    
    # 文法整形
    for pattern, replacement in GRAMMAR_FIXES:
        processed_text = re.sub(pattern, replacement, processed_text)
    
    if text.endswith("。") and not processed_text.endswith("。"):
        processed_text += "。"

    return {"result": processed_text}

@app.get("/")
def read_root():
    return {"status": "Ushiro-Brain V5 Stable"}
