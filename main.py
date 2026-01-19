from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from sudachipy import dictionary, tokenizer
import random

app = FastAPI()

# --- CORS設定（WordPressからのアクセス許可） ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # 本番ではドメイン指定推奨
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 🧠 日本語解析エンジンの準備 (SudachiPy) ---
tokenizer_obj = dictionary.Dictionary(dict="core").create()
mode = tokenizer.Tokenizer.SplitMode.C # Cモードは単語を長く区切る（複合語扱い）

# --- 📚 うしろぽっけ辞書 (Python移植版) ---
# ここに変換したい言葉を追加していきます
REPLACE_DICT = {
    # 【名詞・サ変名詞】
    "提供": ["お渡し", "お届け", "プレゼント"],
    "開始": ["スタート", "はじめること", "やりだすこと"],
    "修正": ["手直し", "リライト", "書き直し"],
    "検討": ["考えること", "悩み"],
    "合意": ["握手", "OKすること"],
    "使用": ["使うこと", "活用"],
    "利用": ["使うこと"],
    "確認": ["チェック", "見てみる"],
    "決定": ["決めること", "決断"],
    "構築": ["作ること", "組み立て"],
    "作成": ["作ること", "書くこと"],
    "購入": ["ゲット", "買うこと"],
    "販売": ["売ること"],
    "解決": ["クリア", "やっつけること"],
    "理解": ["わかること", "飲み込むこと"],
    "説明": ["お話", "伝えること"],
    "参加": ["ジョイン", "混ざること"],
    "成長": ["伸びること", "レベルアップ"],
    "成功": ["うまくいったこと", "大勝利"],
    "失敗": ["ミス", "やらかし"],
    
    # 【カタカナ語・ビジネス語】
    "アジェンダ": ["今日のメニュー", "話し合うこと"],
    "エビデンス": ["証拠", "根拠"],
    "ローンチ": ["公開", "スタート"],
    "ユーザー": ["使う人", "あなた"],
    "メリット": ["いいこと", "嬉しい点"],
    "デメリット": ["弱点", "気になるところ"],
    "コスト": ["お金", "費用"],
    "リスク": ["危険", "やばいこと"],
    "コンセンサス": ["みんなの合意", "納得"],
    "コミット": ["約束", "本気出す"],
    
    # 【形容詞的表現】
    "迅速": ["サクッと", "素早く"],
    "重要": ["大事", "大切"],
    "必要": ["要る", "欠かせない"],
    "困難": ["難しい", "ムズい"],
    "容易": ["カンタン", "楽勝"],
    "可能": ["できる", "OK"],
    "不可能": ["ムリ", "厳しい"],
    "明確": ["はっきり", "くっきり"],
    "詳細": ["詳しく", "細かいとこ"],
}

# --- 🗣 口癖・フィラー（ノイズ） ---
FILLERS = [
    "えーっと、", "なんか、", "正直、", "ぶっちゃけ、", "ていうか、",
    "実は、", "個人的には、", "なんというか、", "そういえば、"
]

# --- 🔚 文末の崩し（語尾） ---
ENDINGS = {
    "です。": ["ですね。", "ですよ。", "なんです。", "だね。", "です（笑）"],
    "ます。": ["ますね。", "ますよ。", "ちゃうかも。", "ます〜。"],
    "だ。": ["だね。", "だよ。", "なんだよね。"],
    "ない。": ["ないです。", "ありません。", "ないかも。"],
    "たい。": ["たいですね。", "たいな〜。", "たいかも。"],
}

class TextRequest(BaseModel):
    text: str
    noise_level: float = 0.5
    human_level: float = 0.5

@app.post("/humanize")
def humanize_text(req: TextRequest):
    text = req.text
    noise_lv = req.noise_level
    human_lv = req.human_level
    
    # 1. 形態素解析で分解する
    # 
    # 例: "資料を提供する" -> ["資料", "を", "提供", "する"] と分解されます
    tokens = tokenizer_obj.tokenize(text, mode)
    
    result_words = []
    
    for token in tokens:
        word = token.surface() # 元の単語
        
        # --- A. 辞書変換（名詞・動詞の幹） ---
        # 辞書にあって、かつ「人間度」の確率に当選したら変換
        if word in REPLACE_DICT and random.random() < (human_lv + 0.2):
            candidates = REPLACE_DICT[word]
            word = random.choice(candidates)
            
        # --- B. ノイズ注入（文頭など） ---
        # ノイズレベルに応じて、たまにフィラーを入れる
        if random.random() < (noise_lv * 0.1): # 10% * Lvの確率
            word = random.choice(FILLERS) + word

        result_words.append(word)
    
    # 結合して文章に戻す
    processed_text = "".join(result_words)
    
    # --- C. 文末（語尾）の調整 ---
    # Pythonなら正規表現も強力に使えます
    for key, candidates in ENDINGS.items():
        if key in processed_text and random.random() < human_lv:
            replacement = random.choice(candidates)
            # 文末の"です。"などを置換
            processed_text = processed_text.replace(key, replacement)

    # 仕上げ：連続した句読点の整理など
    processed_text = processed_text.replace("。。", "。")
    
    return {"result": processed_text}

# Render起動用
@app.get("/")
def read_root():
    return {"status": "Ushiro-Brain V2 (Sudachi) is ready!"}
