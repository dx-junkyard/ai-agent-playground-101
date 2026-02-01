"""
青梅市向けの設定ファイル
報告内容整理機能用のカテゴリ定義とスロット定義
"""

# ============================================================================
# カテゴリ定義（青梅市向け、獣害中心）
# ============================================================================

CATEGORIES = [
    {
        "key": "wildlife_damage",
        "name": "獣害",
        "description": "野生動物による被害",
        "dept_resolver": "wildlife_city",  # 後で拡張可能
        "required_slots": [
            "location",      # 場所（GPS座標または住所）
            "time",          # 発見日時
            "species",       # 動物種
            "details",       # 詳細状況
            "damage_type",   # 被害種別
        ],
        "optional_slots": [
            "urgency",       # 緊急度
            "photo_url",     # 写真URL
            "witness_info",  # 目撃者情報
            "contact_info"   # 連絡先
        ],
        "keywords": ["イノシシ", "サル", "カラス", "シカ", "動物", "獣害", "野生", "害獣"]
    },
    {
        "key": "infrastructure_damage",
        "name": "インフラ損傷",
        "description": "道路、橋梁、公共施設などの損傷",
        "dept_resolver": "infra_city",
        "required_slots": [
            "location",
            "time",
            "details",
            "damage_type"
        ],
        "optional_slots": [
            "hazard_level",
            "photo_url"
        ],
        "keywords": ["道路", "橋", "施設", "破損", "損傷", "陥没"]
    },
    {
        "key": "garbage_issue",
        "name": "ごみ問題",
        "description": "ごみ散乱、不法投棄など",
        "dept_resolver": "env_city",
        "required_slots": [
            "location",
            "time",
            "details"
        ],
        "optional_slots": [
            "photo_url",
            "evidence"
        ],
        "keywords": ["ごみ", "散乱", "不法投棄", "廃棄物"]
    },
    {
        "key": "other",
        "name": "その他",
        "description": "その他の通報",
        "dept_resolver": "general",
        "required_slots": [
            "location",
            "details"
        ],
        "optional_slots": [
            "time",
            "photo_url"
        ],
        "keywords": []
    }
]


# ============================================================================
# スロット定義
# ============================================================================

SLOT_DEFINITIONS = {
    "location": {
        "type": "location",
        "question": "場所を教えてください（住所またはGPS座標）。例：青梅市勝沼123、または緯度経度",
        "validation": "location_validator",
        "extraction_keywords": ["場所", "どこ", "地点", "位置", "住所", "GPS", "座標"],
        "priority": 1
    },
    "time": {
        "type": "datetime",
        "question": "いつ発見しましたか？例：2026年1月20日 14時30分、または「今日の朝」「昨日」など",
        "validation": "datetime_validator",
        "extraction_keywords": ["いつ", "時間", "日時", "発見", "気づいた", "見た"],
        "priority": 2
    },
    "species": {
        "type": "enum",
        "question": "どんな動物ですか？選択肢：イノシシ、サル、カラス、シカ、その他",
        "options": ["イノシシ", "サル", "カラス", "シカ", "その他"],
        "validation": "enum_validator",
        "extraction_keywords": ["動物", "種", "種類", "何"],
        "priority": 3
    },
    "details": {
        "type": "text",
        "question": "状況をもう少し詳しく教えてください。何が、どのくらい、どんな状態か",
        "validation": "text_validator",
        "extraction_keywords": ["状況", "詳細", "どう", "何が"],
        "priority": 4
    },
    "damage_type": {
        "type": "enum",
        "question": "被害の種類を教えてください。選択肢：農作物、人身、建物、その他",
        "options": ["農作物", "人身", "建物", "その他"],
        "validation": "enum_validator",
        "extraction_keywords": ["被害", "種類", "何"],
        "priority": 5
    },
    "urgency": {
        "type": "enum",
        "question": "緊急度を教えてください。選択肢：緊急、高、中、低",
        "options": ["緊急", "高", "中", "低"],
        "validation": "enum_validator",
        "extraction_keywords": ["緊急", "急", "優先度"],
        "priority": 6
    },
    "photo_url": {
        "type": "url",
        "question": "写真や動画のURLがあれば教えてください",
        "validation": "url_validator",
        "extraction_keywords": ["写真", "画像", "動画", "URL", "リンク"],
        "priority": 7
    },
    "witness_info": {
        "type": "text",
        "question": "目撃者情報があれば教えてください",
        "validation": "text_validator",
        "extraction_keywords": ["目撃", "見た", "証人"],
        "priority": 8
    },
    "contact_info": {
        "type": "text",
        "question": "連絡先を教えてください（任意）",
        "validation": "text_validator",
        "extraction_keywords": ["連絡先", "電話", "メール"],
        "priority": 9
    },
    "hazard_level": {
        "type": "enum",
        "question": "危険度はどの程度ですか？選択肢：通行に支障あり、転倒しそう、危険は小さい",
        "options": ["通行に支障あり", "転倒しそう", "危険は小さい"],
        "validation": "enum_validator",
        "extraction_keywords": ["危険", "危険度", "支障"],
        "priority": 5
    },
    "evidence": {
        "type": "text",
        "question": "証拠となる情報があれば教えてください",
        "validation": "text_validator",
        "extraction_keywords": ["証拠", "根拠", "確認"],
        "priority": 7
    }
}


# ============================================================================
# スロット優先順位（質問順序）
# ============================================================================

SLOT_PRIORITY = [
    "location",
    "time",
    "species",
    "details",
    "damage_type",
    "urgency",
    "photo_url",
    "witness_info",
    "contact_info",
    "hazard_level",
    "evidence"
]


# ============================================================================
# 質問テンプレート（カテゴリ別にカスタマイズ可能）
# ============================================================================

CATEGORY_SPECIFIC_QUESTIONS = {
    "wildlife_damage": {
        "location": "イノシシなどの動物を発見した場所を教えてください（住所またはGPS座標）",
        "species": "どんな動物でしたか？（イノシシ/サル/カラス/シカ/その他）",
        "damage_type": "どのような被害がありましたか？（農作物/人身/建物/その他）"
    }
}


# ============================================================================
# 青梅市の担当部署（暫定、後で拡張）
# ============================================================================

OUME_CITY_CONTACTS = {
    "wildlife_city": {
        "dept": "青梅市 環境部 環境課",
        "tel": "0428-22-1111",  # 仮の番号
        "email": "kankyo@city.ome.tokyo.jp"  # 仮のメール
    },
    "infra_city": {
        "dept": "青梅市 建設部 道路課",
        "tel": "0428-22-1111",
        "email": "doro@city.ome.tokyo.jp"
    },
    "env_city": {
        "dept": "青梅市 環境部 環境課",
        "tel": "0428-22-1111",
        "email": "kankyo@city.ome.tokyo.jp"
    },
    "general": {
        "dept": "青梅市 総合案内",
        "tel": "0428-22-1111",
        "email": "sodan@city.ome.tokyo.jp"
    }
}
