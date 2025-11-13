from src.utils.db_utils_sqlite import get_account_balance, get_position, fetch_trades

print("balance:", get_account_balance("USD"))
print("pos:", get_position("BTCUSD"))
print("recent trades:", fetch_trades(5))
