"""
Knowledge Base API Tests - Trading term glossary with tooltips
Tests: GET /api/v1/knowledge, GET /api/v1/knowledge/{term_id}, GET /api/v1/knowledge/category/{category}
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestKnowledgeBasePublicEndpoints:
    """Test public knowledge base endpoints (no auth required)"""
    
    def test_get_all_terms_returns_30_entries(self):
        """GET /api/v1/knowledge should return 30 trading terms"""
        response = requests.get(f"{BASE_URL}/api/v1/knowledge")
        assert response.status_code == 200
        data = response.json()
        assert "entries" in data
        assert "total" in data
        assert data["total"] == 30, f"Expected 30 entries, got {data['total']}"
        assert len(data["entries"]) == 30
        
    def test_get_all_terms_structure(self):
        """Each term should have required fields"""
        response = requests.get(f"{BASE_URL}/api/v1/knowledge")
        assert response.status_code == 200
        data = response.json()
        
        for entry in data["entries"]:
            assert "term_id" in entry
            assert "term" in entry
            assert "category" in entry
            assert "short_description" in entry
            assert "example" in entry
            # Verify no MongoDB _id field
            assert "_id" not in entry
            
    def test_get_rsi_term(self):
        """GET /api/v1/knowledge/rsi should return RSI term details"""
        response = requests.get(f"{BASE_URL}/api/v1/knowledge/rsi")
        assert response.status_code == 200
        data = response.json()
        
        assert data["term_id"] == "rsi"
        assert "RSI" in data["term"]
        assert data["category"] == "indicator"
        assert len(data["short_description"]) > 0
        assert len(data["example"]) > 0
        
    def test_get_nonexistent_term_returns_404(self):
        """GET /api/v1/knowledge/nonexistent should return 404"""
        response = requests.get(f"{BASE_URL}/api/v1/knowledge/nonexistent_term_xyz")
        assert response.status_code == 404
        
    def test_get_indicator_category(self):
        """GET /api/v1/knowledge/category/indicator should return indicator terms"""
        response = requests.get(f"{BASE_URL}/api/v1/knowledge/category/indicator")
        assert response.status_code == 200
        data = response.json()
        
        assert "entries" in data
        assert "total" in data
        assert data["total"] >= 10, f"Expected at least 10 indicator terms, got {data['total']}"
        
        # Verify all entries are indicators
        for entry in data["entries"]:
            assert entry["category"] == "indicator"
            
    def test_get_risk_management_category(self):
        """GET /api/v1/knowledge/category/risk_management should return risk management terms"""
        response = requests.get(f"{BASE_URL}/api/v1/knowledge/category/risk_management")
        assert response.status_code == 200
        data = response.json()
        
        assert "entries" in data
        assert data["total"] >= 5, f"Expected at least 5 risk management terms, got {data['total']}"
        
        # Verify all entries are risk_management
        for entry in data["entries"]:
            assert entry["category"] == "risk_management"
            
    def test_get_general_category(self):
        """GET /api/v1/knowledge/category/general should return general concept terms"""
        response = requests.get(f"{BASE_URL}/api/v1/knowledge/category/general")
        assert response.status_code == 200
        data = response.json()
        
        assert "entries" in data
        assert data["total"] >= 5, f"Expected at least 5 general terms, got {data['total']}"
        
        # Verify all entries are general
        for entry in data["entries"]:
            assert entry["category"] == "general"
            
    def test_get_empty_category_returns_empty_list(self):
        """GET /api/v1/knowledge/category/nonexistent should return empty list"""
        response = requests.get(f"{BASE_URL}/api/v1/knowledge/category/nonexistent_category")
        assert response.status_code == 200
        data = response.json()
        
        assert "entries" in data
        assert data["total"] == 0
        assert len(data["entries"]) == 0


class TestKnowledgeBaseSpecificTerms:
    """Test specific trading terms are present"""
    
    @pytest.mark.parametrize("term_id,expected_category", [
        ("rsi", "indicator"),
        ("sma", "indicator"),
        ("ema", "indicator"),
        ("macd", "indicator"),
        ("stochastic", "indicator"),
        ("adx", "indicator"),
        ("atr", "indicator"),
        ("bollinger", "indicator"),
        ("supertrend", "indicator"),
        ("vwap", "indicator"),
        ("stop_loss", "risk_management"),
        ("target_profit", "risk_management"),
        ("trailing_sl", "risk_management"),
        ("time_exit", "risk_management"),
        ("position_sizing", "risk_management"),
        ("win_rate", "general"),
        ("max_drawdown", "general"),
        ("sharpe_ratio", "general"),
        ("profit_factor", "general"),
        ("backtest", "general"),
    ])
    def test_specific_term_exists(self, term_id, expected_category):
        """Verify specific trading terms exist with correct category"""
        response = requests.get(f"{BASE_URL}/api/v1/knowledge/{term_id}")
        assert response.status_code == 200, f"Term {term_id} not found"
        data = response.json()
        assert data["category"] == expected_category, f"Term {term_id} has wrong category"


class TestKnowledgeBaseDataQuality:
    """Test data quality of knowledge base entries"""
    
    def test_all_terms_have_examples(self):
        """All terms should have non-empty examples"""
        response = requests.get(f"{BASE_URL}/api/v1/knowledge")
        assert response.status_code == 200
        data = response.json()
        
        for entry in data["entries"]:
            assert len(entry["example"]) > 20, f"Term {entry['term_id']} has too short example"
            
    def test_all_terms_have_descriptions(self):
        """All terms should have non-empty descriptions"""
        response = requests.get(f"{BASE_URL}/api/v1/knowledge")
        assert response.status_code == 200
        data = response.json()
        
        for entry in data["entries"]:
            assert len(entry["short_description"]) > 20, f"Term {entry['term_id']} has too short description"
            
    def test_terms_sorted_by_term_id(self):
        """Terms should be sorted alphabetically by term_id"""
        response = requests.get(f"{BASE_URL}/api/v1/knowledge")
        assert response.status_code == 200
        data = response.json()
        
        term_ids = [e["term_id"] for e in data["entries"]]
        assert term_ids == sorted(term_ids), "Terms are not sorted by term_id"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
