# TradingAgents/prompts/init_langfuse.py
"""Script to initialize Langfuse with prompt templates.

Usage:
    python -m tradingagents.prompts.init_langfuse

This script uploads all fallback templates to Langfuse as the initial
production prompts. Run this once to seed your Langfuse instance.

Requirements:
    - LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY environment variables
    - Or pass them as command-line arguments
"""

import argparse
import logging
import os
import sys
from pathlib import Path

import yaml

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# templates/ 目录绝对路径
_TEMPLATES_DIR = Path(__file__).parent / "templates"


def _load_all_templates() -> dict[str, dict]:
    """从 YAML 文件加载全部模板，返回 {name: {template, label, ...}} 映射."""
    from .registry import PROMPT_LABELS, TEMPLATE_PATH_MAP

    templates = {}
    for name, rel_path in TEMPLATE_PATH_MAP.items():
        yaml_path = _TEMPLATES_DIR / rel_path
        try:
            with open(yaml_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            templates[name] = {
                "template": data.get("template", ""),
                "label": PROMPT_LABELS.get(name, name),
            }
        except Exception as exc:
            logger.warning("Failed to load %s: %s", yaml_path, exc)
    return templates


def upload_prompts(
    public_key: str,
    secret_key: str,
    host: str = "http://localhost:3000",
    dry_run: bool = False,
) -> None:
    """Upload all fallback templates to Langfuse.

    Args:
        public_key: Langfuse public key
        secret_key: Langfuse secret key
        host: Langfuse host URL
        dry_run: If True, only print what would be uploaded
    """
    all_templates = _load_all_templates()

    if dry_run:
        logger.info("DRY RUN - No prompts will be uploaded")
        for name, info in all_templates.items():
            preview = info["template"][:100].replace("\n", " ")
            logger.info("  [%s] %s: %s...", info["label"], name, preview)
        logger.info("Total: %d prompts", len(all_templates))
        return

    try:
        from langfuse import Langfuse
    except ImportError:
        logger.error("langfuse package not installed. Install with: pip install langfuse")
        sys.exit(1)

    client = Langfuse(
        public_key=public_key,
        secret_key=secret_key,
        host=host,
    )

    logger.info("Connected to Langfuse at %s", host)
    logger.info("Uploading %d prompts...", len(all_templates))

    success_count = 0
    error_count = 0

    for name, info in all_templates.items():
        label = info["label"]
        template = info["template"]
        try:
            client.create_prompt(
                name=name,
                prompt=template,
                labels=[label],
                is_active=True,
            )
            logger.info("  Uploaded: %s (%s)", name, label)
            success_count += 1
        except Exception as exc:
            try:
                logger.warning("  %s already exists, skipping: %s", name, exc)
                success_count += 1
            except Exception as update_exc:
                logger.error("  Failed to upload %s: %s", name, update_exc)
                error_count += 1

    client.flush()

    logger.info("")
    logger.info("Upload complete: %d success, %d errors", success_count, error_count)


def main():
    parser = argparse.ArgumentParser(
        description="Initialize Langfuse with TradingAgents prompt templates"
    )
    parser.add_argument(
        "--public-key",
        default=os.environ.get("LANGFUSE_PUBLIC_KEY"),
        help="Langfuse public key (or set LANGFUSE_PUBLIC_KEY env var)",
    )
    parser.add_argument(
        "--secret-key",
        default=os.environ.get("LANGFUSE_SECRET_KEY"),
        help="Langfuse secret key (or set LANGFUSE_SECRET_KEY env var)",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("LANGFUSE_HOST", "http://localhost:3000"),
        help="Langfuse host URL (default: http://localhost:3000)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be uploaded without actually uploading",
    )

    args = parser.parse_args()

    if not args.dry_run:
        if not args.public_key or not args.secret_key:
            logger.error(
                "Langfuse keys required. Set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY "
                "environment variables, or use --public-key and --secret-key arguments."
            )
            sys.exit(1)

    upload_prompts(
        public_key=args.public_key or "",
        secret_key=args.secret_key or "",
        host=args.host,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
