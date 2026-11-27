import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from vnlegal.agents.contracts import LegalQuery,evidence_envelope,require_query,AgentInputError
from vnlegal.agents.local_model import OllamaJsonModel

class AgentContracts(unittest.TestCase):
    def test_rejects_cross_query_evidence(self):
        q=LegalQuery('q1','Mô tả vụ việc')
        with self.assertRaises(AgentInputError):require_query({'query_id':'q2'},q)
    def test_rejects_duplicate_evidence(self):
        q=LegalQuery('q1','Facts')
        with self.assertRaises(AgentInputError):evidence_envelope(q,[{'id':'x'},{'id':'x'}],'ok')
    def test_invalid_dates(self):
        with self.assertRaises(ValueError):LegalQuery('q1','Facts','2020-02-31')
    def test_remote_model_cannot_be_selected_accidentally(self):
        with self.assertRaises(ValueError):OllamaJsonModel('m','https://api.example.com')
        with self.assertRaises(ValueError):OllamaJsonModel('m','http://user:secret@localhost:11434')

if __name__=='__main__':unittest.main()
