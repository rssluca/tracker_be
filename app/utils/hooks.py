from app.utils.notifications import send_slack_message


def notify_error(Task):
    if not Task.success:
        send_slack_message(
            f"ERROR! (Tracker ID: {Task.args[0]} - {Task.args[4]})",
            Task.result,
            "TestAppBot",
            "SLACK_KEY_ERROR_ALERTS",
        )
