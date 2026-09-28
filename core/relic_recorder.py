"""Immediate append-only match history; persistence never changes qualification."""
import json
import os
import threading
from dataclasses import asdict
from datetime import datetime, timezone
from core.utils import get_user_data_path

_WRITE_LOCK = threading.Lock()


class RelicRecorder:
    def __init__(self, path=None):
        self.path = path
        self.last_error = None

    def record(self, source, mode, index, observation, result):
        if not result.qualified:
            return False
        try:
            best = result.best_match
            record = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'source': source, 'mode': mode, 'index': index,
                'preset': best.preset_name, 'best_match': asdict(best),
                'matched_presets': [asdict(m) for m in result.qualified_matches],
                'effective_count': best.effective_count, 'perfect': result.perfect,
                'affixes': [a.get('cleaned_text', '') for a in observation.get('affixes', [])],
                'required_matches': best.required_matches,
                'blacklist_exceptions_used': best.blacklist_exceptions_used,
                'unknown_count': result.unknown_count,
                'destructive_action_allowed': result.destructive_action_allowed,
                'uncertainty_reasons': result.uncertainty_reasons,
                'correction_failed_affixes': observation.get('correction_failed_affixes', []),
                'failed_lines': observation.get('failed_lines', []),
            }
            # Resolving the helper can create directories and must also be caught.
            path = self.path if self.path is not None else get_user_data_path('data/relic_history.jsonl')
            payload = json.dumps(record, ensure_ascii=False) + '\n'
            with _WRITE_LOCK:
                os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
                with open(path, 'a', encoding='utf-8') as stream:
                    stream.write(payload)
                    stream.flush()
                    os.fsync(stream.fileno())
            self.last_error = None
            return True
        except Exception as exc:
            self.last_error = str(exc)
            return False
