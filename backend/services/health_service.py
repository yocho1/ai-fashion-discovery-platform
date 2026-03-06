from db.session import check_database_connection, check_redis_connection


def get_live_status() -> dict:
    return {"status": "ok"}


def get_readiness_status() -> dict:
    db_ok = check_database_connection()
    redis_ok = check_redis_connection()
    is_ready = db_ok and redis_ok

    return {
        "status": "ready" if is_ready else "not_ready",
        "database": "ok" if db_ok else "unavailable",
        "redis": "ok" if redis_ok else "unavailable",
    }
