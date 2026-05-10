from __future__ import annotations

import hashlib
import json
from typing import Any

from django.utils import timezone

from ...models import AnalysisRun, AnalysisCoefficient, AnalysisMetric, CustomDataset


SUPPORTED_METHODS = {'logreg', 'svm', 'rf', 'nb', 'linreg', 'kmeans'}


def _stable_hash(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def build_config_hash(payload: dict) -> str:
    method = (payload.get('method') or '').strip().lower()
    dataset_id = payload.get('dataset_id') or None
    coef_keys = payload.get('coefficients') or {}
    metric_keys = payload.get('metrics') or []
    preprocess = payload.get('preprocess') or {}
    target = (payload.get('target') or '').strip()
    features = payload.get('features') or []
    n_clusters = payload.get('n_clusters')
    classification = payload.get('classification') or {}
    return _stable_hash(
        {
            'method': method,
            'dataset_id': dataset_id,
            'coefficients': coef_keys,
            'metrics': metric_keys,
            'preprocess': preprocess,
            'target': target,
            'features': features,
            'n_clusters': n_clusters,
            'classification': classification,
        }
    )


def create_or_reuse_run_and_enqueue(*, user, payload: dict) -> AnalysisRun:
    method = (payload.get('method') or '').strip().lower()
    if method not in SUPPORTED_METHODS:
        raise ValueError(f'Unsupported method: {method}. Supported: {sorted(SUPPORTED_METHODS)}')

    dataset_id = payload.get('dataset_id')
    dataset_ref = None
    if dataset_id:
        dataset_ref = CustomDataset.objects.filter(id=dataset_id, created_by=user).first()
        if not dataset_ref:
            raise ValueError('Custom dataset not found or not accessible.')

    config_hash = build_config_hash(payload)

    existing = (
        AnalysisRun.objects.filter(
            created_by=user,
            method=method,
            config_hash=config_hash,
            dataset_ref=dataset_ref,
            status=AnalysisRun.STATUS_DONE,
        )
        .order_by('-created_at')
        .first()
    )
    if existing:
        # MVP: переиспользуем существующий запуск, чтобы гарантировать наличие AnalysisResult.
        return existing

    run = AnalysisRun.objects.create(
        method=method,
        config_json=payload,
        config_hash=config_hash,
        dataset_ref=dataset_ref,
        created_by=user,
        status=AnalysisRun.STATUS_QUEUED,
    )

    from ...tasks.analytics import run_classification_analysis

    async_result = run_classification_analysis.delay(str(run.run_id))
    run.task_id = async_result.id or ''
    run.started_at = timezone.now()
    run.status = AnalysisRun.STATUS_RUNNING
    run.save(update_fields=['task_id', 'started_at', 'status'])
    return run

