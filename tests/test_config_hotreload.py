import time
import os
from core.config_loader import ConfigManager, TENANTS_PATH

def test_hot_reload_logic():
    # Setup required env vars for first load
    os.environ["TICKETING_WEBHOOK_URL"] = "http://mock"
    os.environ["CRM_WEBHOOK_URL"] = "http://mock"
    os.environ["SMTP_HOST"] = "mock"
    os.environ["SMTP_FROM_EMAIL"] = "mock@mock.com"
    os.environ["DATABASE_DSN"] = "postgresql://mock"
    
    manager = ConfigManager.instance()
    initial_tenants = manager._tenants
    assert initial_tenants is not None
    
    # Manually trigger reload logic to verify it doesn't crash
    manager.reload()
    assert manager._tenants is not None
