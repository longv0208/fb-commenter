# -*- coding: utf-8 -*-
# PhoBERT local filter thay the jev_client (LLM API ben ngoai).
# Tra ve (label, confidence) giong review_post: ("comment", p) hoac ("skip", p).
# Inference torch chay trong thread pool de khong block asyncio event loop.

import asyncio
import json
import logging
import os
import threading
from pathlib import Path

logger = logging.getLogger("fb_commenter")

MODEL_DIR = Path(__file__).resolve().parent / "models" / "phobert-filter"
DEFAULT_THRESHOLD = 0.7

_model_lock = threading.Lock()
_model = None
_tokenizer = None
_positive_label = 1
_device = None
_load_error = None


class PhobertError(RuntimeError):
    pass


def _load():
    """Lazy-load model 1 lan, thread-safe."""
    global _model, _tokenizer, _positive_label, _device, _load_error
    if _model is not None or _load_error is not None:
        return
    with _model_lock:
        if _model is not None or _load_error is not None:
            return
        try:
            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
            _device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            _tokenizer = AutoTokenizer.from_pretrained(str(MODEL_DIR))
            _model = AutoModelForSequenceClassification.from_pretrained(str(MODEL_DIR)).to(_device)
            _model.eval()
            labels_file = MODEL_DIR / "labels.json"
            if labels_file.exists():
                labels = json.loads(labels_file.read_text(encoding="utf-8"))
                for idx, name in labels.items():
                    if str(name).lower() == "true":
                        _positive_label = int(idx)
            logger.info("PhoBERT loaded from %s on %s", MODEL_DIR, _device)
        except Exception as exc:
            _load_error = exc
            raise PhobertError(f"Không load được PhoBERT: {exc}") from exc


def _predict_sync(texts):
    """Blocking torch predict — goi tu thread pool."""
    import torch
    _load()
    if _load_error:
        raise _load_error
    with torch.no_grad():
        inputs = _tokenizer(
            texts, padding=True, truncation=True,
            max_length=256, return_tensors="pt",
        ).to(_device)
        probs = torch.softmax(_model(**inputs).logits, dim=-1)
        return [float(p[_positive_label]) for p in probs.cpu()]


async def review_post(text, subjects=None, threshold=DEFAULT_THRESHOLD):
    """API tuong duong jev_client.review_post.
    Tra ve ("comment", P_true) neu P_true >= threshold, nguoc lai ("skip", P_true).
    `subjects` duoc giu de tuong thich chu ky ham; PhoBERT da hoc san pattern."""
    text = (text or "")[:1500]
    if not text.strip():
        return "skip", 0.0
    loop = asyncio.get_running_loop()
    probs = await loop.run_in_executor(None, _predict_sync, [text])
    p_true = probs[0]
    return ("comment", p_true) if p_true >= float(threshold) else ("skip", p_true)


async def review_posts_batch(texts, threshold=DEFAULT_THRESHOLD):
    """Batch version — hieu qua hon khi can loc nhieu bai."""
    if not texts:
        return []
    loop = asyncio.get_running_loop()
    probs = await loop.run_in_executor(None, _predict_sync, list(texts))
    out = []
    for t, p in zip(texts, probs):
        label = "comment" if p >= float(threshold) else "skip"
        out.append((label, p))
    return out


def available():
    """Check model co san khong (khong load neu chua can)."""
    try:
        _load()
        return _load_error is None
    except PhobertError:
        return False
