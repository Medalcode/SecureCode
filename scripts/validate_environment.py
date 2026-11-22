import json

from securecode.config import validate_environment


def main() -> None:
    validated = validate_environment()
    print(
        json.dumps(
            {
                "status": "ok",
                "app_env": validated.app_env,
                "database_dialect": "sqlite" if validated.database_url.startswith("sqlite://") else "postgresql",
                "cors_origin_count": len(validated.cors_origins),
                "login_max_failures": validated.login_max_failures,
                "login_window_seconds": validated.login_window_seconds,
                "trust_proxy_headers": validated.trust_proxy_headers,
                "github_token_configured": validated.github_token_configured,
                "seed_user_configured": validated.seed_user_configured,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
