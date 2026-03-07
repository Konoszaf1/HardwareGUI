import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src.logic.vu_service import VoltageUnitService

def test_ping():
    service = VoltageUnitService()
    
    # Test 1: Ping localhost (should succeed)
    print("Testing ping to 127.0.0.1...")
    service.set_targets("127.0.0.1", 0, 0, 0, 0)
    result = service.ping_scope()
    print(f"Result: {result}")
    if not result:
        print("FAIL: Could not ping localhost")
        return False

    # Test 2: Ping unreachable IP (should fail)
    # 192.0.2.0/24 is reserved for documentation and examples, should not be reachable
    print("Testing ping to 192.0.2.1...")
    service.set_targets("192.0.2.1", 0, 0, 0, 0)
    result = service.ping_scope()
    print(f"Result: {result}")
    if result:
        print("FAIL: Should not have reached 192.0.2.1")
        return False
        
    print("SUCCESS: All tests passed")
    return True

if __name__ == "__main__":
    test_ping()
