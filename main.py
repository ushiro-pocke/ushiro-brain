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
tokenizer_obj = dictionary.Dictionary().create()
mode = tokenizer.Tokenizer.SplitMode.C 

# --- 📚 辞書データの構築 ---
NOUN_DICT = {}

# 1. 起動時にCSVファイルを読み込む
# GitHubに 'dict.csv' があればそれを読み込みます
if os.path.exists("dict.csv"):
    with open("dict.csv", mode="r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2:
                key = row[0]       # 1列目が「元の言葉」
                candidates = row[1:] # 2列目以降が「変換候補」
                # 空文字などを除去して登録
                NOUN_DICT[key] = [c for c in candidates if c.strip()]
else:
    print("Warning: dict.csv not found. Using empty dict.")

# --- 🗣 口癖・フィラー ---
FILLERS = [
    "えーっと、", "なんか、", "正直、", "ぶっちゃけ、", "ていうか、",
    "実は、", "個人的には、", "なんというか、", "そういえば、",
    "あ、そうそう、", "ま、", "要するに、"
]

# --- 🔚 文末表現パターン ---
ENDING_PATTERNS = [
    (r"です。$", ["ですね。", "ですよ。", "なんです。", "だね。", "です（笑）", "なんですよ。"]),
    (r"ます。$", ["ますね。", "ますよ。", "ちゃうかも。", "ます〜。", "ます！"]),
    (r"である。$", ["です。", "だね。", "なんだよね。", "であります。"]),
    (r"ない。$", ["ないです。", "ありません。", "ないかも。", "ないですね。"]),
    (r"たい。$", ["たいですね。", "たいな〜。", "たいかも。", "たいところ。"]),
    (r"ください。$", ["くださいね。", "してほしいな。", "お願いします！"]),
    (r"しょう。$", ["しょうね。", "だよね。", "かもね。"]),
    (r"ました。$", ["ましたよ。", "たんです。", "たね。", "ちゃいました。"]),
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
    
    # 1. SudachiPyで形態素解析
    tokens = tokenizer_obj.tokenize(text, mode)
    
    result_buffer = ""
    
    for token in tokens:
        word = token.surface() # 単語
        
        # --- A. 辞書変換 (CSVベース) ---
        if word in NOUN_DICT and random.random() < (human_lv + 0.1):
            candidates = NOUN_DICT[word]
            word = random.choice(candidates)
            
        # --- B. ノイズ注入 ---
        if random.random() < (noise_lv * 0.05):
            word = random.choice(FILLERS) + word

        result_buffer += word
    
    processed_text = result_buffer
    
    # --- C. 文末調整 ---
    sentences = processed_text.split("。")
    final_sentences = []
    for s in sentences:
        if not s: continue
        for pattern, candidates in ENDING_PATTERNS:
            if re.search(pattern, s) and random.random() < (human_lv + 0.2):
                replacement = random.choice(candidates)
                s = re.sub(pattern, replacement, s)
                break
        final_sentences.append(s)
        
    processed_text = "。".join(final_sentences)
    
    # --- D. 仕上げ ---
    processed_text = processed_text.replace("。。", "。")
    processed_text = processed_text.replace("！！", "！")
    
    if text.endswith("。") and not processed_text.endswith("。"):
        processed_text += "。"

    return {"result": processed_text}

@app.get("/")
def read_root():
    # 辞書が何語入っているか確認用
    return {"status": f"Ushiro-Brain V4 with CSV. Loaded {len(NOUN_DICT)} words."}
