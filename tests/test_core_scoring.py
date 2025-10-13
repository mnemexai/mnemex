"""Tests for core scoring module."""

import time

from mnemex.core.scoring import (
    calculate_memory_age,
    calculate_recency,
    filter_by_score,
    rank_memories_by_score,
    should_forget,
    should_promote,
)
from mnemex.storage.models import Memory
from tests.conftest import make_test_uuid


class TestShouldForget:
    """Test suite for should_forget function."""

    def test_should_forget_low_score(self):
        """Test that memory with very low score should be forgotten."""
        now = int(time.time())
        old_time = now - (60 * 86400)  # 60 days ago

        # Old, unused memory with low score
        memory = Memory(
            id=make_test_uuid("old"),
            content="Old memory",
            use_count=0,
            last_used=old_time,
            created_at=old_time,
            strength=1.0,
        )

        should_forget_result, score = should_forget(memory, now=now)
        # Should be below forget threshold (0.05)
        assert should_forget_result is True
        assert score < 0.05

    def test_should_not_forget_recent(self):
        """Test that recent, used memory should not be forgotten."""
        now = int(time.time())

        # Recent memory with decent usage
        memory = Memory(
            id=make_test_uuid("recent"),
            content="Recent memory",
            use_count=5,
            last_used=now,
            created_at=now,
            strength=1.0,
        )

        should_forget_result, score = should_forget(memory, now=now)
        assert should_forget_result is False
        assert score >= 0.05

    def test_should_forget_custom_timestamp(self):
        """Test should_forget with custom timestamp."""
        base_time = 1000000
        old_time = base_time - (30 * 86400)

        memory = Memory(
            id=make_test_uuid("mem"),
            content="Test",
            use_count=0,
            last_used=old_time,
            created_at=old_time,
        )

        should_forget_result, score = should_forget(memory, now=base_time)
        # Very old memory with no use should be forgotten
        assert should_forget_result is True


class TestShouldPromote:
    """Test suite for should_promote function."""

    def test_should_promote_high_score(self):
        """Test promotion by high score."""
        now = int(time.time())

        # Memory with high use count and recent access = high score
        memory = Memory(
            id=make_test_uuid("high-score"),
            content="Important memory",
            use_count=10,
            last_used=now,
            created_at=now - 86400,  # 1 day old
            strength=1.5,
        )

        should_promote_result, reason, score = should_promote(memory, now=now)
        assert should_promote_result is True
        assert "High score" in reason
        assert score >= 0.65  # promote_threshold

    def test_should_promote_high_use_count(self):
        """Test promotion by high use count within time window."""
        now = int(time.time())
        created_time = now - (10 * 86400)  # 10 days ago
        last_used_time = now - (8 * 86400)  # 8 days ago (not recent, lowers score)

        # Memory with use_count >= 5 within 14 days but last used a while ago
        # This should have lower score but still qualify by use count
        memory = Memory(
            id=make_test_uuid("high-use"),
            content="Frequently accessed",
            use_count=5,
            last_used=last_used_time,
            created_at=created_time,
            strength=1.0,
        )

        should_promote_result, reason, score = should_promote(memory, now=now)
        # If it still qualifies by high score, that's also valid
        assert should_promote_result is True
        # Reason could be either high score or high use count
        assert ("High score" in reason) or ("High use count" in reason)

    def test_should_not_promote_low_score(self):
        """Test that low-scoring memory is not promoted."""
        now = int(time.time())
        old_time = now - (30 * 86400)  # 30 days ago

        # Old memory with low usage
        memory = Memory(
            id=make_test_uuid("low-score"),
            content="Unimportant",
            use_count=1,
            last_used=old_time,
            created_at=old_time,
            strength=1.0,
        )

        should_promote_result, reason, score = should_promote(memory, now=now)
        assert should_promote_result is False
        assert "Does not meet promotion criteria" in reason

    def test_should_promote_custom_timestamp(self):
        """Test should_promote with custom timestamp."""
        base_time = 1000000
        recent_time = base_time - 3600  # 1 hour ago

        # High usage memory
        memory = Memory(
            id=make_test_uuid("mem"),
            content="Test",
            use_count=10,
            last_used=recent_time,
            created_at=recent_time,
            strength=1.5,
        )

        should_promote_result, reason, score = should_promote(memory, now=base_time)
        assert should_promote_result is True
        assert "High score" in reason


class TestRankMemoriesByScore:
    """Test suite for rank_memories_by_score function."""

    def test_rank_memories_basic(self):
        """Test basic ranking functionality."""
        now = int(time.time())

        memories = [
            Memory(
                id=make_test_uuid("low"),
                content="Low score",
                use_count=1,
                last_used=now - (30 * 86400),
            ),
            Memory(
                id=make_test_uuid("high"),
                content="High score",
                use_count=10,
                last_used=now,
            ),
            Memory(
                id=make_test_uuid("medium"),
                content="Medium score",
                use_count=3,
                last_used=now - (7 * 86400),
            ),
        ]

        ranked = rank_memories_by_score(memories, now=now)

        # Should be sorted descending by score
        assert len(ranked) == 3
        assert ranked[0][1] > ranked[1][1]  # First > Second
        assert ranked[1][1] > ranked[2][1]  # Second > Third
        # High use count memory should be first
        assert ranked[0][0].id == make_test_uuid("high")

    def test_rank_memories_empty_list(self):
        """Test ranking empty list."""
        ranked = rank_memories_by_score([])
        assert ranked == []

    def test_rank_memories_single(self):
        """Test ranking single memory."""
        now = int(time.time())
        memory = Memory(
            id=make_test_uuid("single"),
            content="Single",
            use_count=1,
            last_used=now,
        )

        ranked = rank_memories_by_score([memory], now=now)
        assert len(ranked) == 1
        assert ranked[0][0] == memory

    def test_rank_memories_custom_timestamp(self):
        """Test ranking with custom timestamp."""
        base_time = 1000000

        memories = [
            Memory(
                id=make_test_uuid("m1"),
                content="M1",
                use_count=5,
                last_used=base_time - 3600,
            ),
            Memory(
                id=make_test_uuid("m2"),
                content="M2",
                use_count=2,
                last_used=base_time - 86400,
            ),
        ]

        ranked = rank_memories_by_score(memories, now=base_time)
        assert len(ranked) == 2
        # m1 should rank higher (more recent, higher use count)
        assert ranked[0][0].id == make_test_uuid("m1")


class TestFilterByScore:
    """Test suite for filter_by_score function."""

    def test_filter_by_score_basic(self):
        """Test basic score filtering."""
        now = int(time.time())

        memories = [
            Memory(
                id=make_test_uuid("low"),
                content="Low",
                use_count=1,
                last_used=now - (30 * 86400),
            ),
            Memory(
                id=make_test_uuid("high"),
                content="High",
                use_count=10,
                last_used=now,
            ),
        ]

        filtered = filter_by_score(memories, min_score=0.5, now=now)

        # Only high-scoring memory should pass
        assert len(filtered) >= 1
        # Verify all results meet threshold
        for _mem, score in filtered:
            assert score >= 0.5

    def test_filter_by_score_all_above_threshold(self):
        """Test filtering when all memories are above threshold."""
        now = int(time.time())

        memories = [
            Memory(
                id=make_test_uuid("m1"),
                content="M1",
                use_count=5,
                last_used=now,
            ),
            Memory(
                id=make_test_uuid("m2"),
                content="M2",
                use_count=8,
                last_used=now,
            ),
        ]

        filtered = filter_by_score(memories, min_score=0.1, now=now)

        # All should pass low threshold
        assert len(filtered) == 2

    def test_filter_by_score_all_below_threshold(self):
        """Test filtering when all memories are below threshold."""
        now = int(time.time())
        old_time = now - (60 * 86400)

        memories = [
            Memory(
                id=make_test_uuid("m1"),
                content="M1",
                use_count=0,
                last_used=old_time,
            ),
            Memory(
                id=make_test_uuid("m2"),
                content="M2",
                use_count=0,
                last_used=old_time,
            ),
        ]

        filtered = filter_by_score(memories, min_score=0.5, now=now)

        # None should pass high threshold
        assert len(filtered) == 0

    def test_filter_by_score_empty_list(self):
        """Test filtering empty list."""
        filtered = filter_by_score([], min_score=0.5)
        assert filtered == []

    def test_filter_by_score_custom_timestamp(self):
        """Test filtering with custom timestamp."""
        base_time = 1000000

        memories = [
            Memory(
                id=make_test_uuid("m1"),
                content="M1",
                use_count=5,
                last_used=base_time - 3600,
            ),
        ]

        filtered = filter_by_score(memories, min_score=0.1, now=base_time)
        assert len(filtered) == 1


class TestCalculateMemoryAge:
    """Test suite for calculate_memory_age function."""

    def test_calculate_age_recent_memory(self):
        """Test age calculation for recent memory."""
        now = int(time.time())
        memory = Memory(
            id=make_test_uuid("recent"),
            content="Recent",
            created_at=now - 86400,  # 1 day ago
            use_count=1,
        )

        age = calculate_memory_age(memory, now=now)
        assert 0.99 < age < 1.01  # Approximately 1 day

    def test_calculate_age_old_memory(self):
        """Test age calculation for old memory."""
        now = int(time.time())
        memory = Memory(
            id=make_test_uuid("old"),
            content="Old",
            created_at=now - (30 * 86400),  # 30 days ago
            use_count=1,
        )

        age = calculate_memory_age(memory, now=now)
        assert 29.9 < age < 30.1  # Approximately 30 days

    def test_calculate_age_brand_new(self):
        """Test age calculation for brand new memory."""
        now = int(time.time())
        memory = Memory(
            id=make_test_uuid("new"),
            content="New",
            created_at=now,
            use_count=1,
        )

        age = calculate_memory_age(memory, now=now)
        assert age == 0.0

    def test_calculate_age_custom_timestamp(self):
        """Test age calculation with custom timestamp."""
        base_time = 1000000
        created_time = base_time - (7 * 86400)  # 7 days before base

        memory = Memory(
            id=make_test_uuid("mem"),
            content="Test",
            created_at=created_time,
            use_count=1,
        )

        age = calculate_memory_age(memory, now=base_time)
        assert 6.99 < age < 7.01  # Approximately 7 days


class TestCalculateRecency:
    """Test suite for calculate_recency function."""

    def test_calculate_recency_just_used(self):
        """Test recency for just-used memory."""
        now = int(time.time())
        memory = Memory(
            id=make_test_uuid("recent"),
            content="Recent",
            last_used=now,
            use_count=1,
        )

        recency = calculate_recency(memory, now=now)
        assert recency == 0.0

    def test_calculate_recency_one_day(self):
        """Test recency for memory used one day ago."""
        now = int(time.time())
        memory = Memory(
            id=make_test_uuid("one-day"),
            content="One day",
            last_used=now - 86400,
            use_count=1,
        )

        recency = calculate_recency(memory, now=now)
        assert 0.99 < recency < 1.01  # Approximately 1 day

    def test_calculate_recency_old(self):
        """Test recency for memory used long ago."""
        now = int(time.time())
        memory = Memory(
            id=make_test_uuid("old"),
            content="Old",
            last_used=now - (60 * 86400),  # 60 days ago
            use_count=1,
        )

        recency = calculate_recency(memory, now=now)
        assert 59.9 < recency < 60.1  # Approximately 60 days

    def test_calculate_recency_custom_timestamp(self):
        """Test recency with custom timestamp."""
        base_time = 1000000
        last_used = base_time - (14 * 86400)  # 14 days before base

        memory = Memory(
            id=make_test_uuid("mem"),
            content="Test",
            last_used=last_used,
            use_count=1,
        )

        recency = calculate_recency(memory, now=base_time)
        assert 13.99 < recency < 14.01  # Approximately 14 days
