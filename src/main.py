from __future__ import annotations

import logging

from aiohttp import web

from src.nodes.base_node import create_app
from src.utils.config import load_config


def main() -> None:
    config = load_config()
    logging.basicConfig(level=getattr(logging, config.log_level.upper(), logging.INFO))
    web.run_app(create_app(config), host=config.host, port=config.port)


if __name__ == "__main__":
    main()
