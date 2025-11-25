"""Unit tests for ConsolidationAgent base class (T019).

Tests the abstract base class functionality:
- Initialization with dry_run and rate_limit
- Confidence-based processing decisions
- Rate limiting integration
- Run method execution flow
"""

from __future__ import annotations

from typing import ClassVar

import pytest
from pydantic import BaseModel

from cortexgraph.agents.base import (
    ConfidenceConfig,
    ConsolidationAgent,
)
from cortexgraph.agents.models import ProcessingDecision

# =============================================================================
# Test Fixtures
# =============================================================================


class MockResult(BaseModel):
    """Mock result model for testing."""

    memory_id: str
    processed: bool = True
    dry_run: bool = False


class MockAgent(ConsolidationAgent[MockResult]):
    """Concrete implementation for testing base class."""

    scan_items: ClassVar[list[str]] = []
    fail_on: ClassVar[set[str]] = set()

    def scan(self) -> list[str]:
        """Return configured scan items."""
        return list(self.scan_items)

    def process_item(self, memory_id: str) -> MockResult:
        """Process item, optionally failing."""
        if memory_id in self.fail_on:
            raise ValueError(f"Simulated failure for {memory_id}")
        return MockResult(
            memory_id=memory_id,
            processed=True,
            dry_run=self.dry_run,
        )


@pytest.fixture
def mock_agent() -> MockAgent:
    """Create a fresh mock agent."""
    MockAgent.scan_items = []
    MockAgent.fail_on = set()
    return MockAgent(dry_run=False, rate_limit=100)


@pytest.fixture
def dry_run_agent() -> MockAgent:
    """Create a dry-run mock agent."""
    MockAgent.scan_items = []
    MockAgent.fail_on = set()
    return MockAgent(dry_run=True, rate_limit=100)


# =============================================================================
# ConfidenceConfig Tests
# =============================================================================


class TestConfidenceConfig:
    """Tests for ConfidenceConfig model."""

    def test_default_thresholds(self) -> None:
        """Test default threshold values."""
        config = ConfidenceConfig()
        assert config.auto_threshold == 0.9
        assert config.log_threshold == 0.7
        assert config.wait_below == 0.7

    def test_custom_thresholds(self) -> None:
        """Test custom threshold values."""
        config = ConfidenceConfig(auto_threshold=0.95, log_threshold=0.8)
        assert config.auto_threshold == 0.95
        assert config.log_threshold == 0.8
        assert config.wait_below == 0.8

    def test_decide_auto(self) -> None:
        """Test AUTO decision for high confidence."""
        config = ConfidenceConfig()
        assert config.decide(0.95) == ProcessingDecision.AUTO
        assert config.decide(0.9) == ProcessingDecision.AUTO

    def test_decide_log_only(self) -> None:
        """Test LOG_ONLY decision for medium confidence."""
        config = ConfidenceConfig()
        assert config.decide(0.85) == ProcessingDecision.LOG_ONLY
        assert config.decide(0.7) == ProcessingDecision.LOG_ONLY
        assert config.decide(0.75) == ProcessingDecision.LOG_ONLY

    def test_decide_wait_human(self) -> None:
        """Test WAIT_HUMAN decision for low confidence."""
        config = ConfidenceConfig()
        assert config.decide(0.69) == ProcessingDecision.WAIT_HUMAN
        assert config.decide(0.5) == ProcessingDecision.WAIT_HUMAN
        assert config.decide(0.0) == ProcessingDecision.WAIT_HUMAN

    def test_threshold_validation(self) -> None:
        """Test threshold boundary validation."""
        # Should accept valid values
        config = ConfidenceConfig(auto_threshold=0.0, log_threshold=0.0)
        assert config.auto_threshold == 0.0

        config = ConfidenceConfig(auto_threshold=1.0, log_threshold=1.0)
        assert config.auto_threshold == 1.0

        # Should reject invalid values
        with pytest.raises(ValueError):
            ConfidenceConfig(auto_threshold=-0.1)

        with pytest.raises(ValueError):
            ConfidenceConfig(log_threshold=1.1)


# =============================================================================
# ConsolidationAgent Initialization Tests
# =============================================================================


class TestAgentInitialization:
    """Tests for agent initialization."""

    def test_default_initialization(self, mock_agent: MockAgent) -> None:
        """Test default initialization values."""
        assert mock_agent.dry_run is False
        assert mock_agent.rate_limit == 100
        assert mock_agent.confidence_config.auto_threshold == 0.9

    def test_dry_run_initialization(self, dry_run_agent: MockAgent) -> None:
        """Test dry-run mode initialization."""
        assert dry_run_agent.dry_run is True

    def test_custom_rate_limit(self) -> None:
        """Test custom rate limit."""
        agent = MockAgent(rate_limit=50)
        assert agent.rate_limit == 50

    def test_custom_confidence_config(self) -> None:
        """Test custom confidence config."""
        config = ConfidenceConfig(auto_threshold=0.95)
        agent = MockAgent(confidence_config=config)
        assert agent.confidence_config.auto_threshold == 0.95

    def test_agent_name_property(self) -> None:
        """Test agent_name returns lowercase type."""
        agent = MockAgent()
        # MockAgent doesn't have a mapping, falls back to lowercase
        assert agent.agent_name == "mockagent"


# =============================================================================
# Run Method Tests
# =============================================================================


class TestAgentRun:
    """Tests for agent run() method."""

    def test_empty_scan(self, mock_agent: MockAgent) -> None:
        """Test run with no items to process."""
        MockAgent.scan_items = []
        results = mock_agent.run()
        assert results == []
        assert mock_agent._processed_count == 0

    def test_single_item(self, mock_agent: MockAgent) -> None:
        """Test run with single item."""
        MockAgent.scan_items = ["mem-1"]
        results = mock_agent.run()
        assert len(results) == 1
        assert results[0].memory_id == "mem-1"
        assert mock_agent._processed_count == 1

    def test_multiple_items(self, mock_agent: MockAgent) -> None:
        """Test run with multiple items."""
        MockAgent.scan_items = ["mem-1", "mem-2", "mem-3"]
        results = mock_agent.run()
        assert len(results) == 3
        assert mock_agent._processed_count == 3

    def test_error_handling(self, mock_agent: MockAgent) -> None:
        """Test that errors don't abort entire run."""
        MockAgent.scan_items = ["mem-1", "mem-2", "mem-3"]
        MockAgent.fail_on = {"mem-2"}

        results = mock_agent.run()

        # Should have processed 2 items (mem-1 and mem-3)
        assert len(results) == 2
        assert mock_agent._processed_count == 2
        assert mock_agent._error_count == 1

    def test_dry_run_flag_passed(self, dry_run_agent: MockAgent) -> None:
        """Test dry_run flag is passed to results."""
        MockAgent.scan_items = ["mem-1"]
        results = dry_run_agent.run()
        assert results[0].dry_run is True


# =============================================================================
# Should Process Tests
# =============================================================================


class TestShouldProcess:
    """Tests for should_process method."""

    def test_high_confidence(self, mock_agent: MockAgent) -> None:
        """Test high confidence returns True with AUTO."""
        should, decision = mock_agent.should_process(0.95)
        assert should is True
        assert decision == ProcessingDecision.AUTO

    def test_medium_confidence(self, mock_agent: MockAgent) -> None:
        """Test medium confidence returns True with LOG_ONLY."""
        should, decision = mock_agent.should_process(0.8)
        assert should is True
        assert decision == ProcessingDecision.LOG_ONLY

    def test_low_confidence(self, mock_agent: MockAgent) -> None:
        """Test low confidence returns False with WAIT_HUMAN."""
        should, decision = mock_agent.should_process(0.5)
        assert should is False
        assert decision == ProcessingDecision.WAIT_HUMAN


# =============================================================================
# Stats Tests
# =============================================================================


class TestAgentStats:
    """Tests for get_stats method."""

    def test_initial_stats(self, mock_agent: MockAgent) -> None:
        """Test initial stats are zero."""
        stats = mock_agent.get_stats()
        assert stats["processed"] == 0
        assert stats["skipped"] == 0
        assert stats["errors"] == 0

    def test_stats_after_run(self, mock_agent: MockAgent) -> None:
        """Test stats after successful run."""
        MockAgent.scan_items = ["mem-1", "mem-2"]
        mock_agent.run()

        stats = mock_agent.get_stats()
        assert stats["processed"] == 2
        assert stats["errors"] == 0

    def test_stats_with_errors(self, mock_agent: MockAgent) -> None:
        """Test stats after run with errors."""
        MockAgent.scan_items = ["mem-1", "mem-2"]
        MockAgent.fail_on = {"mem-1"}
        mock_agent.run()

        stats = mock_agent.get_stats()
        assert stats["processed"] == 1
        assert stats["errors"] == 1
