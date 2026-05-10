from __future__ import annotations

import os
import tempfile

from celery import shared_task


@shared_task(bind=True, name='equipment_ergonomics.import_dataset_csv')
def import_dataset_csv_task(
    self,
    *,
    source_path: str,
    apply_cleaning: bool = False,
    near_duplicate_threshold: float = 0.8,
) -> dict:
    from ..scripts.build_dataset import import_dataset_from_csv
    from ..services.csv_cleaning import clean_csv_text, decode_csv_bytes

    in_path = source_path
    work_path = in_path
    tmp_clean_path = None

    try:
        if apply_cleaning:
            with open(in_path, 'rb') as f:
                raw = f.read()
            text = decode_csv_bytes(raw)
            clean = clean_csv_text(text, near_duplicate_threshold=near_duplicate_threshold)
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.csv',
                delete=False,
                encoding='utf-8',
                newline='',
            ) as tmp:
                tmp.write(clean.csv_text)
                tmp_clean_path = tmp.name
            work_path = tmp_clean_path
            cleaning_report = clean.report
        else:
            cleaning_report = None

        created, skipped = import_dataset_from_csv(work_path, skip_duplicates=False)
        payload = {'created': created, 'skipped': skipped}
        if cleaning_report is not None:
            payload['cleaning_report'] = cleaning_report
        return payload
    finally:
        for p in (tmp_clean_path, in_path):
            if p:
                try:
                    os.unlink(p)
                except OSError:
                    pass

