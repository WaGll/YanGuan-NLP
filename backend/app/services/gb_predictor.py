"""
梯度提升预测服务

使用 XGBoost / LightGBM / CatBoost 进行情感分类预测。
以 SnowNLP 伪标签训练，Pipeline + GridSearchCV 评估，
最佳模型持久化到磁盘供推理使用。
"""

import logging
from pathlib import Path

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import GridSearchCV
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder
from sqlalchemy import select

from app.config import settings
from app.database import async_session_factory
from app.models.comment import Comment
from app.models.sentiment import SentimentResult

logger = logging.getLogger(__name__)

# 情感阈值（与 SentimentService 保持一致）
NEGATIVE_THRESHOLD = 0.3
POSITIVE_THRESHOLD = 0.7

MODEL_DIR = settings.data_dir / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_MODELS = {"best", "xgboost", "lightgbm", "catboost"}


def _make_label(score: float) -> str:
    """将 SnowNLP 得分映射为三分类标签。"""
    if score <= NEGATIVE_THRESHOLD:
        return "negative"
    elif score >= POSITIVE_THRESHOLD:
        return "positive"
    return "neutral"


async def load_training_data() -> tuple[list[str], np.ndarray, LabelEncoder]:
    """从数据库加载训练数据（清洗后文本 + SnowNLP 伪标签）。"""
    async with async_session_factory() as session:
        result = await session.execute(
            select(Comment.cleaned_content, SentimentResult.snownlp_score)
            .join(SentimentResult)
            .where(
                Comment.cleaned_content.isnot(None),
                Comment.cleaned_content != "",
            )
        )
        rows = result.all()

    texts: list[str] = []
    labels: list[str] = []
    for content, score in rows:
        if content and score is not None:
            texts.append(content)
            labels.append(_make_label(score))

    le = LabelEncoder()
    y = le.fit_transform(labels)
    logger.info("训练数据: %d 条，类别: %s", len(texts), le.classes_.tolist())
    return texts, y, le


def build_models() -> dict[str, tuple[Pipeline, dict]]:
    """构建三个梯度提升模型及其超参数网格。

    每个模型通过 Pipeline 封装 TfidfVectorizer + classifier。
    """
    from xgboost import XGBClassifier

    from lightgbm import LGBMClassifier

    from catboost import CatBoostClassifier

    return {
        "xgboost": (
            Pipeline([
                ("tfidf", TfidfVectorizer(max_features=5000)),
                ("clf", XGBClassifier(
                    objective="multi:softprob",
                    random_state=42,
                    verbosity=0,
                )),
            ]),
            {
                "clf__n_estimators": [100, 200],
                "clf__max_depth": [3, 6],
                "clf__learning_rate": [0.05, 0.1],
            },
        ),
        "lightgbm": (
            Pipeline([
                ("tfidf", TfidfVectorizer(max_features=5000)),
                ("clf", LGBMClassifier(
                    objective="multiclass",
                    random_state=42,
                    verbose=-1,
                )),
            ]),
            {
                "clf__n_estimators": [100, 200],
                "clf__max_depth": [3, 6],
                "clf__learning_rate": [0.05, 0.1],
            },
        ),
        "catboost": (
            Pipeline([
                ("tfidf", TfidfVectorizer(max_features=5000)),
                ("clf", CatBoostClassifier(
                    random_seed=42,
                    silent=True,
                )),
            ]),
            {
                "clf__iterations": [100, 200],
                "clf__depth": [3, 6],
                "clf__learning_rate": [0.05, 0.1],
            },
        ),
    }


async def train_models() -> dict:
    """训练全部梯度提升模型，选择最佳模型并持久化。

    Returns:
        {model_name: {cv_mean, cv_std, best_params, is_best}}
    """
    texts, y, le = load_training_data()
    model_specs = build_models()
    results: dict = {}
    best_score = 0.0
    best_name = ""

    for name, (pipe, param_grid) in model_specs.items():
        logger.info("训练 %s ...", name)
        gs = GridSearchCV(
            pipe, param_grid, cv=5, scoring="accuracy",
            n_jobs=1, verbose=0,
        )
        gs.fit(texts, y)

        cv_mean = float(gs.best_score_)
        cv_std = float(gs.cv_results_["std_test_score"][gs.best_index_])
        results[name] = {
            "cv_mean": round(cv_mean, 4),
            "cv_std": round(cv_std, 4),
            "best_params": {k.replace("clf__", ""): v for k, v in gs.best_params_.items()},
            "is_best": False,
        }

        # 保存模型
        model_path = MODEL_DIR / f"gb_sentiment_{name}.joblib"
        joblib.dump(gs.best_estimator_, model_path)
        logger.info(
            "  %s: cv_mean=%.4f (±%.4f) → %s",
            name, cv_mean, cv_std, model_path,
        )

        if cv_mean > best_score:
            best_score = cv_mean
            best_name = name

    # 标记最佳模型并保存标签编码器
    if best_name:
        results[best_name]["is_best"] = True
        joblib.dump(le, MODEL_DIR / "gb_sentiment_label_encoder.joblib")
        # 复制最佳模型为 "best"
        best_src = MODEL_DIR / f"gb_sentiment_{best_name}.joblib"
        best_dst = MODEL_DIR / "gb_sentiment_best.joblib"
        best_dst.write_bytes(best_src.read_bytes())
        logger.info("最佳模型: %s (cv_mean=%.4f)", best_name, best_score)

    return results


def list_models() -> dict:
    """列出已训练的模型及其指标。

    Returns:
        {models: [{name, path, is_best}], has_trained: bool}
    """
    if not MODEL_DIR.exists():
        return {"models": [], "has_trained": False}

    trained = sorted(MODEL_DIR.glob("gb_sentiment_*.joblib"))
    best_path = MODEL_DIR / "gb_sentiment_best.joblib"
    models = []
    for p in trained:
        if p.name == "gb_sentiment_best.joblib":
            continue
        name = p.stem.replace("gb_sentiment_", "")
        models.append({
            "name": name,
            "path": str(p),
            "is_best": best_path.exists() and p.read_bytes() == best_path.read_bytes(),
        })

    return {"models": models, "has_trained": len(models) > 0}


def predict(text: str, model_name: str = "best") -> dict:
    """单条文本预测。

    Args:
        text: 待预测文本
        model_name: 模型名 (best / xgboost / lightgbm / catboost)

    Returns:
        {sentiment_class, probabilities, model_used}
    """
    if model_name not in ALLOWED_MODELS:
        raise ValueError(f"无效模型名: {model_name}，可选: {sorted(ALLOWED_MODELS)}")

    model_path = MODEL_DIR / f"gb_sentiment_{model_name}.joblib"
    le_path = MODEL_DIR / "gb_sentiment_label_encoder.joblib"

    if not model_path.exists():
        available = [p.stem for p in MODEL_DIR.glob("*.joblib")]
        raise FileNotFoundError(
            f"模型 {model_name} 未找到。可用: {available}"
        )

    pipe = joblib.load(model_path)
    le = joblib.load(le_path)

    proba = pipe.predict_proba([text])[0]
    pred_idx = int(proba.argmax())

    return {
        "sentiment_class": str(le.inverse_transform([pred_idx])[0]),
        "probabilities": {
            str(le.inverse_transform([i])[0]): round(float(p), 4)
            for i, p in enumerate(proba)
        },
        "model_used": model_name,
    }


def predict_batch(texts: list[str], model_name: str = "best") -> list[dict]:
    """批量预测。

    Args:
        texts: 文本列表
        model_name: 模型名

    Returns:
        [{index, text, sentiment_class, probabilities}, ...]
    """
    if model_name not in ALLOWED_MODELS:
        raise ValueError(f"无效模型名: {model_name}，可选: {sorted(ALLOWED_MODELS)}")

    model_path = MODEL_DIR / f"gb_sentiment_{model_name}.joblib"
    le_path = MODEL_DIR / "gb_sentiment_label_encoder.joblib"

    if not model_path.exists():
        raise FileNotFoundError(f"模型 {model_name} 未找到")

    pipe = joblib.load(model_path)
    le = joblib.load(le_path)
    probas = pipe.predict_proba(texts)

    results = []
    for i, (text, proba) in enumerate(zip(texts, probas)):
        pred_idx = int(proba.argmax())
        results.append({
            "index": i,
            "text": text[:100],
            "sentiment_class": str(le.inverse_transform([pred_idx])[0]),
            "probabilities": {
                str(le.inverse_transform([j])[0]): round(float(p), 4)
                for j, p in enumerate(proba)
            },
        })

    return results
