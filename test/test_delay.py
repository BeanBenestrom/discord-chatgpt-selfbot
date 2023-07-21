import pytest
from delay import NaturalDelay


def test_NaturalDelay_ping():
    delay: NaturalDelay = NaturalDelay()
    for i in range(3):
        ping: float = delay.ping()
        print(f"Ping {i}: {ping} minutes")