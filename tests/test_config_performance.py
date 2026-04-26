import time
import pytest
import os
from core.config_loader import load_tenant_config

def test_load_config_performance():
    # Setup required env vars
    os.environ["TICKETING_WEBHOOK_URL"] = "http://mock"
    os.environ["CRM_WEBHOOK_URL"] = "http://mock"
    os.environ["SMTP_HOST"] = "mock"
    os.environ["SMTP_FROM_EMAIL"] = "mock@mock.com"
    os.environ["DATABASE_DSN"] = "postgresql://mock"
    
    # Warm up
    load_tenant_config()
    
    start = time.perf_counter()
    for _ in range(100):
        load_tenant_config()
    end = time.perf_counter()
    
    avg_time = (end - start) / 100
    print(f"Average lookup time: {avg_time*1000:.4f}ms")
    # Cached lookup should be well under 0.1ms. 
    assert avg_time < 0.001
