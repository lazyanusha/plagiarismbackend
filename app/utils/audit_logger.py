from app.controllers import audit_log_controller

def log_action(
    actor_id: int,
    action: str,
    target_table: str,
    target_id: int,
    old_data: dict = None,
    new_data: dict = None
):
    log_entry = {
        "actor_id": actor_id,
        "action": action,
        "target_table": target_table,
        "target_id": target_id,
        "old_data": old_data,
        "new_data": new_data
    }
    return audit_log_controller.create_audit_log(log_entry)
