from __future__ import annotations

import io
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler, StandardScaler

KEY_COLUMNS = ('country_code', 'year', 'indicator_name')
VALUE_COL = 'value'
MAX_BLOCK_FOR_PAIRWISE = 400


def _similarity(a: str, b: str) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _row_signature(row: pd.Series, columns: list[str]) -> str:
    parts: list[str] = []
    for c in columns:
        if c not in row.index:
            parts.append('')
            continue
        v = row[c]
        if pd.isna(v):
            parts.append('')
        else:
            parts.append(str(v).strip().lower())
    return '|'.join(parts)


class UnionFind:
    __slots__ = ('parent',)

    def __init__(self, n: int) -> None:
        self.parent = list(range(n))

    def find(self, i: int) -> int:
        p = self.parent
        while p[i] != i:
            p[i] = p[p[i]]
            i = p[i]
        return i

    def union(self, i: int, j: int) -> None:
        pi, pj = self.find(i), self.find(j)
        if pi != pj:
            self.parent[pj] = pi


@dataclass
class CleanCsvOutcome:
    csv_text: str
    report: dict[str, Any]


def _normalize_headers(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    return df


def _coerce_types(df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    issues: list[dict[str, Any]] = []
    out = df.copy()

    if 'country_code' in out.columns:
        out['country_code'] = out['country_code'].astype(str).str.strip().str.upper()
        bad = out['country_code'].str.len() != 3
        if bad.any():
            for idx in out.index[bad].tolist()[:50]:
                issues.append({'row': int(idx), 'column': 'country_code', 'detail': 'expected ISO3 (3 chars)'})
            out.loc[bad, 'country_code'] = out.loc[bad, 'country_code'].str[:3]

    if 'year' in out.columns:
        y = pd.to_numeric(out['year'], errors='coerce')
        bad_year = y.isna() & out['year'].notna() & (out['year'].astype(str).str.strip() != '')
        if bad_year.any():
            for idx in out.index[bad_year].tolist()[:50]:
                issues.append({'row': int(idx), 'column': 'year', 'detail': 'not an integer'})
        out['year'] = y

    if VALUE_COL in out.columns:
        s = out[VALUE_COL].astype(str).str.replace(',', '.', regex=False)
        v = pd.to_numeric(s, errors='coerce')
        bad_val = v.isna() & out[VALUE_COL].notna() & (s.str.strip() != '') & (s.str.lower() != 'nan')
        if bad_val.any():
            for idx in out.index[bad_val].tolist()[:50]:
                issues.append({'row': int(idx), 'column': VALUE_COL, 'detail': 'not numeric'})
        out[VALUE_COL] = v

    for col in ('unit', 'equipment_class_code', 'source_notes'):
        if col in out.columns:
            out[col] = out[col].apply(lambda x: '' if pd.isna(x) else str(x).strip())

    return out, issues


def _drop_exact_row_dupes(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    before = len(df)
    out = df.drop_duplicates(keep='first').reset_index(drop=True)
    return out, before - len(out)


def _drop_key_dupes(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    cols = [c for c in KEY_COLUMNS if c in df.columns]
    if len(cols) < 2:
        return df, 0
    before = len(df)
    out = df.drop_duplicates(subset=list(cols), keep='first').reset_index(drop=True)
    return out, before - len(out)


def _remove_near_duplicates(
    df: pd.DataFrame,
    *,
    threshold: float,
    max_block: int,
) -> tuple[pd.DataFrame, int, int]:
    text_cols = [c for c in df.columns if c not in ('value_imputed',)]
    sigs = [_row_signature(df.loc[i], list(text_cols)) for i in range(len(df))]

    def block_key(i: int) -> tuple[Any, ...]:
        row = df.iloc[i]
        cc = row['country_code'] if 'country_code' in df.columns else ''
        ind = row['indicator_name'] if 'indicator_name' in df.columns else ''
        if pd.isna(cc):
            cc = ''
        if pd.isna(ind):
            ind = ''
        return (str(cc), str(ind))

    buckets: dict[tuple[Any, ...], list[int]] = {}
    for i in range(len(df)):
        buckets.setdefault(block_key(i), []).append(i)

    uf = UnionFind(len(df))
    comparisons = 0
    max_cmp = max_block * max_block

    for _bk, idxs in buckets.items():
        if len(idxs) < 2:
            continue
        if len(idxs) > max_block:
            idxs = idxs[:max_block]
        n = len(idxs)
        for a in range(n):
            for b in range(a + 1, n):
                comparisons += 1
                if comparisons > max_cmp:
                    break
                ia, ib = idxs[a], idxs[b]
                if _similarity(sigs[ia], sigs[ib]) >= threshold:
                    uf.union(ia, ib)
            if comparisons > max_cmp:
                break

    roots: dict[int, list[int]] = {}
    for i in range(len(df)):
        r = uf.find(i)
        roots.setdefault(r, []).append(i)

    drop_idx: set[int] = set()
    clusters = 0
    for _r, members in roots.items():
        if len(members) < 2:
            continue
        clusters += 1
        members_sorted = sorted(members)
        drop_idx.update(members_sorted[1:])

    if not drop_idx:
        return df.reset_index(drop=True), 0, clusters

    keep_mask = [i not in drop_idx for i in range(len(df))]
    out = df.iloc[keep_mask].reset_index(drop=True)
    return out, len(drop_idx), clusters


def _impute_value_with_mean(
    df: pd.DataFrame,
    *,
    group_col: str | None = 'indicator_name',
) -> tuple[pd.DataFrame, int]:
    if VALUE_COL not in df.columns:
        return df, 0

    out = df.copy()
    mask = out[VALUE_COL].isna()
    if not mask.any():
        out['value_imputed'] = False
        return out, 0

    out['value_imputed'] = False
    filled = 0

    if group_col and group_col in out.columns:
        gmeans = out.groupby(group_col, dropna=False)[VALUE_COL].transform('mean')
        use_group = mask & gmeans.notna()
        out.loc[use_group, VALUE_COL] = gmeans[use_group]
        out.loc[use_group, 'value_imputed'] = True
        filled = int(use_group.sum())
        mask = out[VALUE_COL].isna()

    if mask.any():
        overall = out[VALUE_COL].mean()
        if pd.notna(overall):
            out.loc[mask, VALUE_COL] = overall
            out.loc[mask, 'value_imputed'] = True
            filled += int(mask.sum())

    return out, filled


def _add_derived_and_normalized(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    out = df.copy()
    added: list[str] = []

    if VALUE_COL in out.columns:
        v = pd.to_numeric(out[VALUE_COL], errors='coerce')
        out['value_log1p'] = np.log1p(v.clip(lower=0))
        added.append('value_log1p')

    if 'year' in out.columns:
        y = pd.to_numeric(out['year'], errors='coerce')
        ym = y.mean()
        if pd.notna(ym):
            out['year_centered'] = y - ym
            added.append('year_centered')

    if VALUE_COL in out.columns and 'indicator_name' in out.columns:
        out['value_minmax_by_indicator'] = np.nan
        out['value_zscore_by_indicator'] = np.nan
        for name, grp in out.groupby('indicator_name', dropna=False):
            idx = grp.index
            vals = pd.to_numeric(grp[VALUE_COL], errors='coerce').values.reshape(-1, 1)
            if np.isfinite(vals).sum() < 2:
                continue
            finite = np.isfinite(vals.flatten())
            if finite.sum() < 2:
                continue
            mm = MinMaxScaler()
            zs = StandardScaler()
            try:
                mm_vals = mm.fit_transform(vals)
                zs_vals = zs.fit_transform(vals)
                out.loc[idx, 'value_minmax_by_indicator'] = mm_vals.flatten()
                out.loc[idx, 'value_zscore_by_indicator'] = zs_vals.flatten()
            except ValueError:
                continue
        added.extend(['value_minmax_by_indicator', 'value_zscore_by_indicator'])

    return out, added


def clean_csv_text(
    raw_text: str,
    *,
    near_duplicate_threshold: float = 0.8,
    delimiter: str = ',',
) -> CleanCsvOutcome:
    buf = io.StringIO(raw_text)
    df = pd.read_csv(buf, delimiter=delimiter)
    df = _normalize_headers(df)

    report: dict[str, Any] = {
        'row_count_in': len(df),
        'exact_row_duplicates_removed': 0,
        'key_duplicates_removed': 0,
        'near_duplicate_rows_removed': 0,
        'near_duplicate_clusters': 0,
        'type_coercion_issues': [],
        'value_imputed_count': 0,
        'new_columns': [],
    }

    df, type_issues = _coerce_types(df)
    report['type_coercion_issues'] = type_issues

    df, n_exact = _drop_exact_row_dupes(df)
    report['exact_row_duplicates_removed'] = n_exact

    df, n_key = _drop_key_dupes(df)
    report['key_duplicates_removed'] = n_key

    df, n_near, n_clusters = _remove_near_duplicates(
        df,
        threshold=near_duplicate_threshold,
        max_block=MAX_BLOCK_FOR_PAIRWISE,
    )
    report['near_duplicate_rows_removed'] = n_near
    report['near_duplicate_clusters'] = n_clusters

    df, n_imp = _impute_value_with_mean(df)
    report['value_imputed_count'] = n_imp

    df, derived_cols = _add_derived_and_normalized(df)
    report['new_columns'] = derived_cols
    if 'value_imputed' in df.columns and 'value_imputed' not in report['new_columns']:
        report['new_columns'] = ['value_imputed'] + report['new_columns']

    report['row_count_out'] = len(df)

    out_buf = io.StringIO()
    df.to_csv(out_buf, index=False, lineterminator='\n')
    return CleanCsvOutcome(csv_text=out_buf.getvalue(), report=report)


def decode_csv_bytes(raw: bytes) -> str:
    text: str | None = None
    for enc in ('utf-8-sig', 'utf-8', 'cp1251'):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        text = raw.decode('utf-8', errors='replace')
    return text


def clean_csv_bytes(
    raw: bytes,
    *,
    near_duplicate_threshold: float = 0.8,
    delimiter: str = ',',
) -> CleanCsvOutcome:
    return clean_csv_text(
        decode_csv_bytes(raw),
        near_duplicate_threshold=near_duplicate_threshold,
        delimiter=delimiter,
    )
