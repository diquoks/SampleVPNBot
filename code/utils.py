import logging


# TODO: добавить класс для взаимодействия с логами
def log_user_interaction(username: str | None, user_id: int, interaction: str) -> None:
    user_info = f"@{username} ({user_id})" if username else user_id
    logging.info(f"{user_info} - \"{interaction}\"")
