import os
import sys

parent = os.path.dirname(os.path.dirname(__file__))
PATH = os.path.abspath(parent)
sys.path.insert(0, f"{PATH}/venv/Lib/site-packages")

EPS = 1e-8

ENV = os.environ.get("env_profile", "LOCAL").upper()
if ENV == "LOCAL":
    ANNUAL_TRADING_DAYS = 252
    POSTGRES_USER = os.environ.get("REVERIE_POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD = os.environ.get("REVERIE_POSTGRES_PASSWORD", "")
    POSTGRES_HOST = "127.0.0.1"
    POSTGRES_PORT = 5432
    POSTGRES_DATABASE = "postgres"
elif ENV == "STG":
    ...
elif ENV == "PRD":
    ...
else:
    raise ValueError(f"Unknown environment type: {ENV}. Set 'env_profile' to 'LOCAL', 'STG', or 'PRD'.")


if __name__ == "__main__":
    print(PATH)
