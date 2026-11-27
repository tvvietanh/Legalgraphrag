"""Local pinned construction providers; generated content remains unreviewed."""
from .agents.local_model import LocalModelError


class CommunitySummarizer:
    outputs_verified = False
    is_test_double = False

    def __init__(self, client):
        if not getattr(client, 'model_id', None) or not getattr(client, 'revision', None):
            raise ValueError('Community generation requires an explicitly pinned model')
        self.client = client
        self.model_id = client.model_id
        self.revision = client.revision
        self.is_test_double = bool(getattr(client, 'is_test_double', False))

    def summarize(self, texts, case_ids):
        if not texts or len(texts) != len(case_ids) or len(set(case_ids)) != len(case_ids):
            raise ValueError('Distinct case IDs must match representative feature texts')
        if not all(isinstance(t, str) and t.strip() for t in texts):
            raise ValueError('Representative text must be nonempty')
        result = self.client.generate_json('community_summary', {
            'instruction': 'Tóm tắt điểm chung của các đặc trưng được cung cấp, không suy '
                           'tội danh, hình phạt hoặc thêm tình tiết. Trả {"summary": "..."}.',
            'representatives': [dict(case_id=i, feature_text=t) for i, t in zip(case_ids, texts)]
        })
        if set(result) != {'summary'} or not isinstance(result['summary'], str) or not result['summary'].strip():
            raise LocalModelError('Expected nonempty summary only')
        return result['summary']
