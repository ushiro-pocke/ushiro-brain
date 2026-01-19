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
# core を small に書き換えます
tokenizer_obj = dictionary.Dictionary(dict="small").create()
mode = tokenizer.Tokenizer.SplitMode.C
except Exception as e:
    print(f"Dictionary Load Error: {e}")
    # フォールバック（万が一辞書が読み込めない場合）
    tokenizer_obj = None

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
else:
    print("Warning: dict.csv not found.")

# --- 🗣 フィラー（ノイズ） ---
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

# --- 🏥 文法整形ルール（ここが重要！） ---
# 正規表現を使って「不自然な接続」を「自然な口語」に直します
GRAMMAR_FIXES = [
    # 1. 「こと」＋「する」問題の解消
    # 例: 考えることする → 考えることにする / 考えちゃう
    (r"こと(する|します|した|して)", r"ことに\1"), 
    
    # 2. 「動詞の辞書形」＋「する」問題（サ変接続のバグ修正）
    # 例: 使うする → 使う / 使うね / 使っちゃう
    # ※ 文脈によるが、単純に「する」を取るか、口語的な助動詞に変える
    (r"([うくすつぬむる])する", r"\1"),        # 使うする -> 使う
    (r"([うくすつぬむる])します", r"\1ます"),  # 使うします -> 使うます(後で修正) -> 使います
    (r"([うくすつぬむる])した", r"\1た"),      # 使うした -> 使うた(後で修正) -> 使った
    
    # 3. 助詞「の」＋ 動詞 の不自然さ
    # 例: 機能の使う → 機能を使う
    (r"の([うくすつぬむる])", r"を\1"),
    
    # 4. 過去形の活用パッチ（五段活用・一段活用を無理やり直す）
    # 「使うた」→「使った」、「書くた」→「書いた」など
    (r"うた", r"った"), (r"つた", r"った"), (r"るた", r"た"),
    (r"くた", r"いた"), (r"ぐた", r"いだ"), (r"むた", r"んだ"),
    (r"ぶた", r"んだ"), (r"ぬた", r"んだ"), (r"すた", r"した"),
    
    # 5. 丁寧語「ます」の活用パッチ
    # 「使うます」→「使います」
    (r"うます", r"います"), (r"つます", r"ちます"), (r"るます", r"ます"),
    (r"くます", r"きます"), (r"ぐます", r"ぎます"), (r"むます", r"みます"),
    (r"ぶます", r"びます"), (r"ぬます", r"にます"), (r"すます", r"します"),

    # 6. 「こと」の重複削除
    (r"ことこと", r"こと"),
    
    # 7. 「てにをは」の微調整（AI語→口語）
    (r"について", r"のこと"),
    (r"に対して", r"に"),
    (r"において", r"で"),
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
    
    # 1. 形態素解析（もし失敗したら原文をそのまま使う）
    if tokenizer_obj:
        tokens = tokenizer_obj.tokenize(text, mode)
    else:
        # 辞書ロード失敗時の緊急避難（空白で区切るなど最低限の処理）
        return {"result": text}
    
    result_buffer = ""
    
    for token in tokens:
        word = token.surface() # 単語
        
        # --- A. 辞書変換 ---
        # 確率判定: Human Levelが高いほど置換しやすい
        if word in NOUN_DICT and random.random() < (human_lv + 0.1):
            candidates = NOUN_DICT[word]
            word = random.choice(candidates)
            
        # --- B. ノイズ注入 ---
        # 文頭や句点のあとにフィラーを入れる確率
        if random.random() < (noise_lv * 0.05):
            word = random.choice(FILLERS) + word

        result_buffer += word
    
    processed_text = result_buffer
    
    # --- C. 文末調整 ---
    sentences = processed_text.split("。")
    final_sentences = []
    for s in sentences:
        if not s: continue
        
        # 文末変換
        replaced = False
        for pattern, candidates in ENDING_PATTERNS:
            if re.search(pattern, s) and random.random() < (human_lv + 0.2):
                replacement = random.choice(candidates)
                s = re.sub(pattern, replacement, s)
                replaced = True
                break
        
        final_sentences.append(s)
        
    processed_text = "。".join(final_sentences)
    
    # --- D. 文法整形手術（ここを実行！） ---
    for pattern, replacement in GRAMMAR_FIXES:
        processed_text = re.sub(pattern, replacement, processed_text)
    
    # --- E. 仕上げ ---
    processed_text = processed_text.replace("。。", "。")
    processed_text = processed_text.replace("！！", "！")
    
    if text.endswith("。") and not processed_text.endswith("。"):
        processed_text += "。"

    return {"result": processed_text}

@app.get("/")
def read_root():
    return {"status": f"Ushiro-Brain V5 (Grammar Fixer). Loaded {len(NOUN_DICT)} words."}

