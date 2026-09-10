import sys
from datetime import timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from jobs import MAX_RETRY_DELAY, retry_delay


def test_retry_delay_uses_exponential_backoff():
    assert retry_delay(1) == timedelta(minutes=1)
    assert retry_delay(2) == timedelta(minutes=2)
    assert retry_delay(3) == timedelta(minutes=4)


def test_retry_delay_is_bounded():
    assert retry_delay(20) == MAX_RETRY_DELAY


@pytest.mark.parametrize("attempt_count", [0, -1])
def test_retry_delay_handles_initial_attempt(attempt_count):
    assert retry_delay(attempt_count) == timedelta(minutes=1)
