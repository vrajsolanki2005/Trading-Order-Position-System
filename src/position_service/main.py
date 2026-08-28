
import argparse

import uvicorn

from src.common.logger import configure_logging


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Position Maintaining Service")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    configure_logging(args.log_level)
    uvicorn.run(
        "src.position_service.server:app",
        host=args.host,
        port=args.port,
        log_level=args.log_level.lower(),
    )


if __name__ == "__main__":
    main()
