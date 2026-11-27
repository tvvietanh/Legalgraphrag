import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from vnlegal.agents.local_model import OllamaJsonModel, LocalModelError
from vnlegal.construction_model import CommunitySummarizer


class Response:
    def __init__(self, value): self.raw = json.dumps(value).encode()
    def read(self, *args): return self.raw
    def __enter__(self): return self
    def __exit__(self, *args): pass


class ConstructionTests(unittest.TestCase):
    digest = 'sha256:' + 'a' * 64

    def tags(self, digest=None):
        return Response({'models': [{'name': 'qwen3:8b', 'digest': digest or self.digest}]})

    def test_pin_and_bounded_json_generation(self):
        reply = Response({'message': {'content': '{"summary":"Tóm tắt"}'}, 'done_reason': 'stop'})
        with patch('vnlegal.agents.local_model.urlopen', side_effect=[self.tags(), reply, self.tags()]) as call:
            client = OllamaJsonModel('qwen3:8b', revision=self.digest, max_output_tokens=321)
            provider = CommunitySummarizer(client)
            self.assertEqual(provider.summarize(['Hành vi A'], ['case:A']), 'Tóm tắt')
            body = json.loads(call.call_args_list[1].args[0].data)
            self.assertEqual(body['options']['num_predict'], 321)
            self.assertFalse(body['think'])
            self.assertFalse(provider.outputs_verified)
            self.assertEqual(provider.revision, self.digest)

    def test_generation_digest_drift_rejected(self):
        reply = Response({'message': {'content': '{}'}})
        with patch('vnlegal.agents.local_model.urlopen', side_effect=[self.tags(), reply, self.tags('sha256:'+'b'*64)]):
            with self.assertRaises(LocalModelError):
                OllamaJsonModel('qwen3:8b', revision=self.digest).generate_json('role', {})

    def test_input_limit_rejects_without_transport(self):
        with patch('vnlegal.agents.local_model.urlopen') as call:
            with self.assertRaises(LocalModelError):
                OllamaJsonModel('qwen3:8b', max_input_chars=3).generate_json('role', {'facts': 'long'})
            call.assert_not_called()

    def test_output_limit_rejects_even_valid_partial_object(self):
        reply = Response({'message': {'content': '{}'}, 'done_reason': 'length'})
        with patch('vnlegal.agents.local_model.urlopen', return_value=reply):
            with self.assertRaises(LocalModelError):
                OllamaJsonModel('qwen3:8b').generate_json('role', {})

    def test_provider_requires_pin(self):
        with self.assertRaises(ValueError):
            CommunitySummarizer(OllamaJsonModel('qwen3:8b'))

    def test_summary_contract_rejects_invented_fields(self):
        class Client:
            model_id='fixture'; revision='fixture'; is_test_double=True
            def generate_json(self, *args): return {'summary':'x', 'charge':'invented'}
        provider=CommunitySummarizer(Client())
        self.assertTrue(provider.is_test_double)
        with self.assertRaises(LocalModelError): provider.summarize(['text'], ['case'])


if __name__ == '__main__': unittest.main()
