"""Run HA's tests on Windows with platform compatibility adaptations.

Linux CI runs pytest directly. Only Unix process-lock/resource APIs and the
Windows loopback socket pair need adaptation; integration behavior is real.
"""

import os
import sys

if os.name == "nt":
    import asyncio
    from unittest.mock import MagicMock

    import pytest_socket

    sys.modules["fcntl"] = MagicMock()
    sys.modules["resource"] = MagicMock()

    def _loopback_only(*args, **kwargs):
        pytest_socket.socket_allow_hosts(["127.0.0.1", "::1"])

    pytest_socket.disable_socket = _loopback_only
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import pytest

if __name__ == "__main__":
    sys.exit(pytest.main(sys.argv[1:]))
