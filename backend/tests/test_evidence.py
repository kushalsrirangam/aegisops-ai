from app.orchestration.evidence import migration_signals


def test_migration_evidence_requires_same_service_and_column():
    logs = [
        "payments-api deploy v4 completed",
        "orders-api DatabaseError: column legacy_flag does not exist",
        "orders-api migration add_legacy_flag pending",
    ]
    assert migration_signals(logs, "orders-api")["corroborated_migration"] is False
    logs[0] = "orders-api deploy v4 completed"
    assert migration_signals(logs, "orders-api")["corroborated_migration"] is True
    logs[-1] = "orders-api migration add_other_flag pending"
    assert migration_signals(logs, "orders-api")["corroborated_migration"] is False


def test_migration_evidence_uses_event_order_and_latest_status():
    logs = [
        "orders-api DatabaseError: column legacy_flag does not exist",
        "orders-api deploy v4 completed",
        "orders-api migration add_legacy_flag pending",
    ]
    assert migration_signals(logs, "orders-api")["corroborated_migration"] is False
    logs[0], logs[1] = logs[1], logs[0]
    assert migration_signals(logs, "orders-api")["corroborated_migration"] is True
    logs.append("orders-api migration add_legacy_flag completed")
    assert migration_signals(logs, "orders-api")["corroborated_migration"] is False


def test_stale_deploy_is_not_corroboration():
    logs = [
        "last week: orders-api deploy v4 completed",
        "today: orders-api DatabaseError: column legacy_flag does not exist",
        "today: orders-api migration add_legacy_flag pending",
    ]
    assert migration_signals(logs, "orders-api")["corroborated_migration"] is False
