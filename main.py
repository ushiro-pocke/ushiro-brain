from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from sudachipy import dictionary, tokenizer
import random
import re

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
# エラー回避のため辞書指定を省略（デフォルトを使用）
tokenizer_obj = dictionary.Dictionary().create()
mode = tokenizer.Tokenizer.SplitMode.C 

# --- 📚 うしろぽっけ辞書 (強化版) ---

# 【名詞・カタカナ語】: 文脈に関係なく置き換えて良いもの
NOUN_DICT = {
    # ビジネス・硬い言葉
    "アジェンダ": ["今日のメニュー", "話し合うこと", "テーマ"],
    "エビデンス": ["証拠", "根拠", "裏付け"],
    "コンセンサス": ["みんなの合意", "納得感", "握手"],
    "コミット": ["約束", "本気出す", "誓う"],
    "ローンチ": ["公開", "スタート", "お披露目"],
    "ユーザー": ["使う人", "お客さん", "あなた"],
    "メリット": ["いいこと", "嬉しい点", "強み"],
    "デメリット": ["弱点", "気になるところ", "悩みどころ"],
    "コスト": ["お金", "費用", "出費"],
    "リスク": ["危険", "落とし穴", "怖いこと"],
    "プライオリティ": ["優先順位", "やる順番"],
    "バッファ": ["余裕", "ゆとり"],
    "リソース": ["人手", "時間", "体力"],
    "ナレッジ": ["知恵", "コツ", "ノウハウ"],
    "ノウハウ": ["コツ", "やり方", "秘訣"],
    "ソリューション": ["解決策", "答え", "処方箋"],
    "イノベーション": ["革新", "新しい風", "革命"],
    "パラダイムシフト": ["常識が変わること", "劇的変化"],
    "フィードバック": ["感想", "コメント", "意見"],
    "マイルストーン": ["節目", "通過点"],
    "デフォルト": ["標準", "基本", "初期設定"],
    "オプション": ["おまけ", "追加機能"],
    
    # 漢字熟語 -> 柔らかい言葉
    "提供": ["お渡し", "お届け", "プレゼント"],
    "開始": ["スタート", "はじめること"],
    "修正": ["手直し", "リライト", "書き直し"],
    "検討": ["考えること", "悩み"],
    "合意": ["握手", "OK"],
    "使用": ["使うこと"],
    "利用": ["活用", "使うこと"],
    "確認": ["チェック", "目を通すこと"],
    "決定": ["決断", "決めること"],
    "構築": ["組み立て", "作ること"],
    "作成": ["準備", "作ること"],
    "購入": ["ゲット", "お買い物"],
    "解決": ["クリア", "解消"],
    "理解": ["納得", "飲み込むこと"],
    "説明": ["お話", "解説"],
    "参加": ["ジョイン", "加わること"],
    "成長": ["レベルアップ", "伸びること"],
    "成功": ["大勝利", "うまくいったこと"],
    "失敗": ["ミス", "やらかし"],
    "最重要": ["一番大事", "キモ"],
    "重要": ["大事", "大切"],
    "必要": ["要る", "欠かせない"],
    "困難": ["ムズい", "厳しい"],
    "容易": ["カンタン", "楽勝"],
    "可能": ["できる", "OK"],
    "不可能": ["ムリ", "厳しい"],
    "明確": ["はっきり", "くっきり"],
    "詳細": ["詳しく", "細かいとこ"],
    "迅速": ["サクッと", "素早く"],
}

# 【口癖・フィラー】: 文頭にランダムで付与
FILLERS = [
    "えーっと、", "なんか、", "正直、", "ぶっちゃけ、", "ていうか、",
    "実は、", "個人的には、", "なんというか、", "そういえば、",
    "あ、そうそう、", "ま、", "要するに、"
]

# 【文末表現】: 正規表現で文末を狙い撃ち (Regex Patterns)
# Key: 検索パターン, Value: 置換候補リスト
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
    noise_lv = req.noise_level # 0.0 ~ 1.0
    human_lv = req.human_level # 0.0 ~ 1.0
    
    # 1. SudachiPyで形態素解析（単語にバラす）
    tokens = tokenizer_obj.tokenize(text, mode)
    
    result_buffer = ""
    
    for token in tokens:
        word = token.surface() # 単語そのもの
        
        # --- A. 名詞・カタカナ語の変換 ---
        # 辞書にあって、かつ「人間度」の確率で変換
        if word in NOUN_DICT and random.random() < (human_lv + 0.1):
            candidates = NOUN_DICT[word]
            word = random.choice(candidates)
            
        # --- B. ノイズ注入（フィラー） ---
        # 文頭や読点の後などに、ノイズレベルに応じて挿入
        # ここでは簡易的に「すべての単語の前」に確率判定を入れています
        if random.random() < (noise_lv * 0.05): # 頻出しすぎないよう調整
            word = random.choice(FILLERS) + word

        result_buffer += word
    
    processed_text = result_buffer
    
    # --- C. 文末（語尾）の調整 ---
    # 文章を「。」で区切って、それぞれの文末を処理します
    sentences = processed_text.split("。")
    final_sentences = []
    
    for s in sentences:
        if not s: continue # 空文字スキップ
        
        # 文末変換ロジック
        replaced = False
        for pattern, candidates in ENDING_PATTERNS:
            # マッチして、かつ確率に当選したら
            if re.search(pattern, s) and random.random() < (human_lv + 0.2):
                replacement = random.choice(candidates)
                s = re.sub(pattern, replacement, s)
                replaced = True
                break # 1回変換したらループを抜ける（多重変換防止）
        
        final_sentences.append(s)
        
    # 再結合
    processed_text = "。".join(final_sentences)
    
    # --- D. 仕上げの整形 ---
    # 連続する記号などを綺麗にする
    processed_text = processed_text.replace("。。", "。")
    processed_text = processed_text.replace("！！", "！")
    
    # 最後に「。」が消えていたら復活させる（splitの副作用対策）
    if text.endswith("。") and not processed_text.endswith("。"):
        processed_text += "。"

    # ★ 余計な装飾なしで、テキストだけを返す！
    return {"result": processed_text}

# 疎通確認用
@app.get("/")
def read_root():
    return {"status": "Ushiro-Brain V3 (Clean Output) is ready!"}
