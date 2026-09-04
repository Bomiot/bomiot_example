import os
import requests

def example_job(**kwargs):
    """Scheduled example job"""
    from datetime import datetime
    print(os.environ.get('AUTHED', 'false'))
    print(os.environ.get('IS_LAN', 'false'))
    print(f"This is a scheduled task test ----------- {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    # Your business logic here