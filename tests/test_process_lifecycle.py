import os
import sys
import time
import socket
import subprocess
import pytest

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from core import start_fastsd, stop_fastsd, is_port_in_use

def test_process_cleanup_on_startup():
    """
    Test that if a process is already using the port,
    the system can (after we implement the fix) clean it up.
    Currently, this test might fail or show the bug.
    """
    TEST_PORT = 8999
    # Start a dummy 'zombie' process listening on TEST_PORT
    # We use a simple python command that stays alive
    zombie = subprocess.Popen(
        [sys.executable, "-c", f"import socket, time; s = socket.socket(); s.bind(('127.0.0.1', {TEST_PORT})); s.listen(1); time.sleep(60)"],
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    )
    
    time.sleep(1) # Give it a moment to bind
    assert is_port_in_use(TEST_PORT), "Failed to start dummy zombie process"
    
    # Now, we want a function that can clean this up.
    # We'll implement 'force_cleanup_port' in core.py
    from core import force_cleanup_port
    force_cleanup_port(TEST_PORT)
    
    time.sleep(2)
    assert not is_port_in_use(TEST_PORT), "force_cleanup_port failed to kill the zombie"
    
    if zombie.poll() is None:
        zombie.kill() # Cleanup if test failed

def test_stop_fastsd_is_thorough():
    """Verify that stop_fastsd kills the process even if it's 'stuck'."""
    # We'll use a real-ish start but mock the path
    # Actually, let's just test the logic of killing it.
    p = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    import core
    core.fastsd_process = p
    stop_fastsd()
    assert p.poll() is not None, "Process was not killed by stop_fastsd"
