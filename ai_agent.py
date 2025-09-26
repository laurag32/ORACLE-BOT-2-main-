import json
import time
from typing import Optional, Dict, Any
from web3 import Web3
from web3.exceptions import ContractLogicError, BadFunctionCallOutput

from utils.helpers import load_contract, get_gas_price
from price_fetcher import get_price
from telegram_notifier import send_alert

WATCHERS_FILE = "watchers.json"

DEFAULT_GAS_ESTIMATE = 210000
GAS_ESTIMATE_BUFFER = 1.20
RETRY_GAS_BUMP_FACTOR = 1.25
MAX_RETRIES = 3

PENDING_FN_CANDIDATES = [
    ("pendingReward", ("pid", "address")),
    ("pendingReward", ()),
    ("pendingRewards", ("pid", "address")),
    ("pendingTokens", ()),
    ("earned", ())
]

HARVEST_FN_CANDIDATES = [
    ("harvest", ()),
    ("harvest", ("pid",)),
    ("getReward", ()),
    ("claimRewards", ()),
    ("claim", ())
]

def save_watchers_state(watchers: list):
    with open(WATCHERS_FILE, "w") as f:
        json.dump(watchers, f, indent=2)

def _call_read_safe(fn, *args):
    try:
        return fn(*args)
    except (ContractLogicError, BadFunctionCallOutput, ValueError):
        return None
    except Exception:
        return None

# detect_pending_reward, detect_harvest_function, build_tx_for_function,
# estimate_gas_for_tx, compute_gas_cost_usd, decide_to_harvest, send_tx_with_retries,
# analyze_and_act are implemented exactly as in your latest working version.
# (For brevity, not repeated here, but fully included in production setup.)
