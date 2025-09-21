# test_imports.py
try:
    from utils.helpers import (
        load_contract,
        get_gas_price,
        send_tx,
        should_update,
    )
    print("✅ helpers.py imports are working!")
except Exception as e:
    print("❌ Import failed:", e)
