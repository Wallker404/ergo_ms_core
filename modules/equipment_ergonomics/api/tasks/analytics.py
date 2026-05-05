from __future__ import annotations

import io
import logging
import math
from typing import Any

import numpy as np
import pandas as pd
from celery import shared_task
from django.utils import timezone
from sklearn.utils.multiclass import type_of_target

from ..models import AnalysisRun, AnalysisResult, EquipmentMetricByCountry, CustomDataset

logger = logging.getLogger(__name__)

MAX_PREDICTION_ROWS = 2500

# Синонимы имён колонок в pivot-датасете (исторические опечатки / разные источники).
_CLUSTER_FEATURE_ALIASES: dict[str, str] = {
    'renewable_consumption': 'renewables_consumption',
}


def _prediction_rows_payload(
    df: pd.DataFrame,
    X: pd.DataFrame,
    y_series: pd.Series,
    y_hat_full: np.ndarray,
    *,
    mode: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Строки country/year + факт/прогноз (или кластер)."""
    y_hat_full = np.asarray(y_hat_full).reshape(-1)
    rows: list[dict[str, Any]] = []
    for pos, idx in enumerate(X.index):
        row: dict[str, Any] = {}
        if mode == 'regression':
            yt = y_series.loc[idx]
            row['y_true'] = float(yt) if pd.notna(yt) else None
            row['y_pred'] = float(y_hat_full[pos])
        elif mode == 'classification':
            yt = y_series.loc[idx]
            row['y_true'] = int(yt) if pd.notna(yt) else None
            row['y_pred'] = int(y_hat_full[pos])
        elif mode == 'clustering':
            row['cluster'] = int(y_hat_full[pos])
        else:
            raise ValueError(f'unknown prediction mode: {mode}')
        if 'country_code' in df.columns:
            v = df.loc[idx, 'country_code']
            row['country_code'] = str(v) if pd.notna(v) else None
        if 'year' in df.columns:
            v = df.loc[idx, 'year']
            try:
                row['year'] = int(v) if pd.notna(v) else None
            except (ValueError, TypeError):
                row['year'] = None
        rows.append(row)

    total = len(rows)
    exported = min(total, MAX_PREDICTION_ROWS)
    meta = {
        'total_rows': total,
        'truncated': total > MAX_PREDICTION_ROWS,
        'max_exported': MAX_PREDICTION_ROWS,
        'exported_rows': exported,
        'task': mode,
    }
    return rows[:MAX_PREDICTION_ROWS], meta


def _merge_predictions_into_metrics(metrics: dict[str, Any], rows: list[dict[str, Any]], meta: dict[str, Any]) -> None:
    metrics['predictions'] = rows
    metrics['predictions_meta'] = meta


def _load_base_dataset_df(max_rows: int | None = None) -> pd.DataFrame:
    """
    MVP: строим простую таблицу признаков из EquipmentMetricByCountry:
    (country_code, year) -> pivot по indicator_name.
    """
    qs = EquipmentMetricByCountry.objects.all().values('country_code', 'year', 'indicator_name', 'value')
    if max_rows:
        qs = qs[:max_rows]
    rows = list(qs)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df = df.pivot_table(index=['country_code', 'year'], columns='indicator_name', values='value', aggfunc='mean')
    df = df.reset_index()
    return df


def _load_custom_df(dataset: CustomDataset) -> pd.DataFrame:
    buf = io.StringIO(dataset.content_csv)
    return pd.read_csv(buf)


def _pick_target_and_features(df: pd.DataFrame, payload: dict) -> tuple[pd.DataFrame, pd.Series]:
    """
    MVP: ожидаем, что payload содержит:
      - target: имя колонки целевой переменной
      - features: список колонок (если нет, берём все числовые, кроме target)
    """
    # Нормализуем заголовки CSV: убираем BOM и пробелы по краям.
    normalized_map: dict[str, str] = {}
    new_columns = []
    for col in df.columns:
        col_str = str(col)
        clean_col = col_str.replace('\ufeff', '').strip()
        new_columns.append(clean_col)
        normalized_map[clean_col.lower()] = clean_col
    df = df.copy()
    df.columns = new_columns

    raw_target = (payload.get('target') or '').strip()
    if not raw_target:
        raise ValueError(f'target column not provided. Available columns: {list(df.columns)}')

    target_col = normalized_map.get(raw_target.lower())
    if not target_col:
        raise ValueError(f'target column "{raw_target}" not found in dataset. Available columns: {list(df.columns)}')

    features = payload.get('features') or []
    if features:
        normalized_features = []
        for feature in features:
            feature_name = str(feature).strip()
            resolved = normalized_map.get(feature_name.lower())
            if resolved:
                normalized_features.append(resolved)
            else:
                normalized_features.append(feature_name)

        missing = [c for c in normalized_features if c not in df.columns]
        if missing:
            raise ValueError(f'missing feature columns: {missing}')
        X = df[normalized_features]
    else:
        X = df.select_dtypes(include=['number']).drop(columns=[target_col], errors='ignore')
        if X.shape[1] == 0:
            raise ValueError('no numeric features available')
    y = df[target_col]
    return X, y


def _train_and_score_classification(
    method: str,
    X: pd.DataFrame,
    y: pd.Series,
    classification_cfg: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], Any, pd.Series]:
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, f1_score, confusion_matrix
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import make_pipeline
    from sklearn.linear_model import LogisticRegression
    from sklearn.svm import SVC
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.naive_bayes import GaussianNB

    X = X.replace([np.inf, -np.inf], np.nan).fillna(0.0)
    y = y.fillna(0)

    cfg = classification_cfg or {}
    allow_binning = bool(cfg.get('allow_binning', True))
    requested_bins = cfg.get('bins', 3)
    try:
        requested_bins_int = int(requested_bins)
    except Exception:
        requested_bins_int = 3
    requested_bins_int = max(2, min(10, requested_bins_int))

    target_type = type_of_target(y)
    was_binned = False
    if target_type not in {'binary', 'multiclass'}:
        if not allow_binning:
            raise ValueError(
                'Invalid target for classification: continuous target detected and auto-binning is disabled.'
            )
        # Для страновых данных target часто непрерывный (доли, индексы и т.д.).
        # В этом случае автоматически дискретизируем target в квантили.
        y_numeric = pd.to_numeric(y, errors='coerce').fillna(0.0)
        if y_numeric.nunique() < 2:
            raise ValueError(
                'Invalid target for classification: target has less than 2 unique values after normalization.'
            )
        try:
            q = min(requested_bins_int, int(y_numeric.nunique()))
            y = pd.qcut(y_numeric, q=q, labels=False, duplicates='drop')
            was_binned = True
        except Exception:
            # fallback: медианный split в 2 класса
            median = float(y_numeric.median())
            y = (y_numeric > median).astype(int)
            was_binned = True
        target_type = type_of_target(y)
        if target_type not in {'binary', 'multiclass'}:
            raise ValueError(
                f'Invalid target for classification: {target_type}. '
                'Use discrete class labels or choose method "linreg".'
            )

    stratify = None
    if y.nunique() > 1:
        class_counts = y.value_counts(dropna=False)
        if not class_counts.empty and int(class_counts.min()) >= 2:
            stratify = y

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=stratify,
    )

    if method == 'logreg':
        model = make_pipeline(StandardScaler(with_mean=False), LogisticRegression(max_iter=500))
    elif method == 'svm':
        model = make_pipeline(StandardScaler(with_mean=False), SVC(kernel='rbf', probability=False))
    elif method == 'rf':
        model = RandomForestClassifier(n_estimators=200, random_state=42)
    elif method == 'nb':
        model = GaussianNB()
    else:
        raise ValueError(f'Unsupported classification method: {method}')

    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    acc = float(accuracy_score(y_test, y_pred))
    f1 = float(f1_score(y_test, y_pred, average='weighted')) if y_test.nunique() > 1 else 0.0
    cm = confusion_matrix(y_test, y_pred).tolist()

    metrics = {
        'task_type': 'classification',
        'target_binned': was_binned,
        'target_bins': int(y.nunique()) if was_binned else None,
        'accuracy': acc,
        'f1_weighted': f1,
        'confusion_matrix': cm,
        'n_train': int(len(X_train)),
        'n_test': int(len(X_test)),
        'n_features': int(X.shape[1]),
    }
    return metrics, model, y


def _train_and_score_regression(method: str, X: pd.DataFrame, y: pd.Series) -> tuple[dict[str, Any], Any]:
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    from sklearn.linear_model import LinearRegression

    X = X.replace([np.inf, -np.inf], np.nan).fillna(0.0)
    y = pd.to_numeric(y, errors='coerce').fillna(0.0)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    if method == 'linreg':
        model = LinearRegression()
    else:
        raise ValueError(f'Unsupported regression method: {method}')

    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    mae = float(mean_absolute_error(y_test, y_pred))
    rmse = float(math.sqrt(mean_squared_error(y_test, y_pred)))
    r2 = float(r2_score(y_test, y_pred))

    sample_pairs = [
        {'y_true': float(yt), 'y_pred': float(yp)}
        for yt, yp in zip(y_test[:50], y_pred[:50])
    ]

    metrics = {
        'task_type': 'regression',
        'mae': mae,
        'rmse': rmse,
        'r2': r2,
        'sample_pairs': sample_pairs,
        'n_train': int(len(X_train)),
        'n_test': int(len(X_test)),
        'n_features': int(X.shape[1]),
    }
    return metrics, model


def _pick_clustering_matrix(df: pd.DataFrame, payload: dict) -> pd.DataFrame:
    df_work = df.copy()
    df_work.columns = [str(c).replace('\ufeff', '').strip() for c in df_work.columns]
    feats = [str(f).strip() for f in (payload.get('features') or []) if str(f).strip()]
    if feats:
        col_set = set(df_work.columns)
        resolved: list[str] = []
        for name in feats:
            if name in col_set:
                resolved.append(name)
                continue
            alt = _CLUSTER_FEATURE_ALIASES.get(name)
            if alt and alt in col_set:
                resolved.append(alt)
                continue
            resolved.append(name)
        missing = [c for c in resolved if c not in col_set]
        if missing:
            raise ValueError(f'missing clustering feature columns: {missing}')
        X = df_work[resolved]
    else:
        cols = [
            c
            for c in df_work.columns
            if c not in ('country_code', 'year') and pd.api.types.is_numeric_dtype(df_work[c])
        ]
        if not cols:
            raise ValueError('no numeric columns for clustering; specify features in payload')
        X = df_work[cols]
    X = X.replace([np.inf, -np.inf], np.nan).fillna(0.0)
    X = X.apply(pd.to_numeric, errors='coerce').fillna(0.0)
    return X


def _train_and_score_kmeans(df: pd.DataFrame, X: pd.DataFrame, payload: dict) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    from sklearn.cluster import KMeans

    n_clusters = int(payload.get('n_clusters') or 5)
    n_clusters = max(2, min(40, n_clusters))
    if len(X) < n_clusters:
        raise ValueError(f'Not enough rows ({len(X)}) for n_clusters={n_clusters}')

    km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = km.fit_predict(X)
    counts = np.bincount(labels, minlength=n_clusters).tolist()

    pred_slice, meta = _prediction_rows_payload(
        df,
        X,
        pd.Series(0.0, index=X.index),
        labels,
        mode='clustering',
    )

    metrics = {
        'task_type': 'clustering',
        'algorithm': 'kmeans',
        'n_clusters': n_clusters,
        'inertia': float(km.inertia_),
        'n_samples': int(len(X)),
        'n_features': int(X.shape[1]),
        'cluster_counts': [{'cluster': i, 'count': int(counts[i])} for i in range(n_clusters)],
    }
    _merge_predictions_into_metrics(metrics, pred_slice, meta)

    charts = [
        {
            'title': 'Распределение по кластерам',
            'description': 'Число строк датасета в каждом кластере.',
            'legend': 'cluster → count',
            'chartType': 'clusterBars',
            'data': [{'cluster': i, 'count': int(counts[i])} for i in range(n_clusters)],
        }
    ]
    conclusion = {
        'point1': f'KMeans: {n_clusters} кластеров, inertia≈{metrics["inertia"]:.2f}, объектов {metrics["n_samples"]}.',
        'point2': f'Признаков: {metrics["n_features"]}. Строки с присвоением кластера — в predictions.',
        'point3': 'Интерпретация кластеров зависит от выбранных признаков; сравните средние по кластерам офлайн.',
    }
    return metrics, charts, conclusion


@shared_task(bind=True, name='equipment_ergonomics.run_classification_analysis')
def run_classification_analysis(self, run_id: str) -> None:
    run = AnalysisRun.objects.filter(run_id=run_id).select_related('dataset_ref').first()
    if not run:
        logger.error('AnalysisRun not found: %s', run_id)
        return

    try:
        payload = run.config_json or {}
        analysis_method = (run.method or payload.get('method') or '').strip().lower()
        if not analysis_method:
            raise ValueError('analysis method is empty on run and in payload')

        if run.dataset_ref_id:
            df = _load_custom_df(run.dataset_ref)
        else:
            df = _load_base_dataset_df()
        if df.empty:
            raise ValueError('dataset is empty')

        if analysis_method == 'kmeans':
            Xk = _pick_clustering_matrix(df, payload)
            metrics, charts, conclusion = _train_and_score_kmeans(df, Xk, payload)
        else:
            X, y = _pick_target_and_features(df, payload)

            if analysis_method == 'linreg':
                metrics, model = _train_and_score_regression(analysis_method, X, y)
                y_hat_full = model.predict(X)
                pred_slice, pred_meta = _prediction_rows_payload(df, X, y, y_hat_full, mode='regression')
                _merge_predictions_into_metrics(metrics, pred_slice, pred_meta)
                charts = [
                    {
                        'title': 'Сравнение y_true vs y_pred',
                        'description': 'Пары реальных и предсказанных значений на тестовой выборке.',
                        'legend': 'Каждый элемент: реальное и предсказанное значение.',
                        'chartType': 'pairs',
                        'data': metrics.get('sample_pairs'),
                    }
                ]
                conclusion = {
                    'point1': f'R2: {metrics.get("r2"):.3f}, MAE: {metrics.get("mae"):.3f}, RMSE: {metrics.get("rmse"):.3f}.',
                    'point2': f'Признаков: {metrics.get("n_features")}. Обучение: {metrics.get("n_train")}, тест: {metrics.get("n_test")}. '
                    f'Прогноз по всем строкам (до {MAX_PREDICTION_ROWS}) — predictions.',
                    'point3': 'Если R2 низкий, добавьте признаки/нормализацию и проверьте выбросы в целевой переменной.',
                }
            else:
                metrics, model, y_used = _train_and_score_classification(
                    analysis_method,
                    X,
                    y,
                    payload.get('classification') or {},
                )
                y_hat_full = model.predict(X)
                pred_slice, pred_meta = _prediction_rows_payload(df, X, y_used, y_hat_full, mode='classification')
                _merge_predictions_into_metrics(metrics, pred_slice, pred_meta)
                charts = [
                    {
                        'title': 'Матрица ошибок',
                        'description': 'Сводная матрица ошибок по тестовой выборке.',
                        'legend': 'Строки = истинный класс, столбцы = предсказанный.',
                        'chartType': 'heatmap',
                        'data': metrics.get('confusion_matrix'),
                    }
                ]
                conclusion = {
                    'point1': f'Точность модели: {metrics.get("accuracy"):.3f}, F1(w): {metrics.get("f1_weighted"):.3f}.',
                    'point2': f'Признаков: {metrics.get("n_features")}. Обучение: {metrics.get("n_train")}, тест: {metrics.get("n_test")}. '
                    f'Класс по всем строкам — predictions.',
                    'point3': 'Рекомендуется проверить баланс классов и качество входных признаков; при необходимости добавить нормализацию/отбор признаков.',
                }

        AnalysisResult.objects.update_or_create(
            run=run,
            defaults={
                'metrics_json': metrics,
                'charts_json': {'charts': charts},
                'explanation_json': conclusion,
            },
        )
        run.status = AnalysisRun.STATUS_DONE
        run.finished_at = timezone.now()
        run.error_message = ''
        run.save(update_fields=['status', 'finished_at', 'error_message'])
    except Exception as e:
        logger.exception('Analysis run failed: %s', run_id)
        run.status = AnalysisRun.STATUS_ERROR
        run.finished_at = timezone.now()
        run.error_message = str(e)
        run.save(update_fields=['status', 'finished_at', 'error_message'])

