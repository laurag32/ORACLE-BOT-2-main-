# ORACLE-BOT-2-main-
# Oracle Bot (Polygon)

A **modular Polygon keeper/harvester bot** with watchers (Autofarm, Balancer, QuickSwap), Oracle feeds, profit/gas safety rules, auto-profiler, Telegram alerts, and GitHub → Render deployment.

---

## Features

- **Vault Watchers**: 2 Autofarm, 2 Balancer, 2 QuickSwap  
- **Oracle Jobs**: USDC/USD & ETH/USD Chainlink price feeds  
- **Safety Rules**:
  - Gas cap: skip tx if > 20 gwei
  - Min reward: $1 or 2× gas cost
  - Idle time: skip feeds updated < 20 minutes
  - Max failed tx: pause 10 mins after 2 fails  
- **Auto-profiler**: adjusts profit thresholds depending on gas price  
- **Logging & Tracking**: daily profit log + monthly rotation  
- **Telegram Alerts**: real-time notifications + daily summary `/summary`  
- **RPC Failover**: primary + backup Polygon RPC  

---

## Setup

1. Clone repo:  
```bash
git clone https://github.com/yourusername/oracle_bot.git
cd oracle_bot
