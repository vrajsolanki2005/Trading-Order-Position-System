import argparse
import os

import uvicorn

from src.common.logger import configure_logging
from src.position_service.server import create_app
from src.position_service.tracker import PositionTracker


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Position Maintaining Service")
    parser.add_argument("--host", default=os.getenv("HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8000")))
    parser.add_argument("--db-path", default=os.getenv("DB_PATH", "trading_positions.db"), help="Path to SQLite database file")
    parser.add_argument("--log-level", default=os.getenv("LOG_LEVEL", "INFO"))
    args = parser.parse_args()

    configure_logging(args.log_level)
    
    tracker = PositionTracker(db_path=args.db_path)
    app = create_app(tracker=tracker)

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level=args.log_level.lower(),
    )


if __name__ == "__main__":
    main()
