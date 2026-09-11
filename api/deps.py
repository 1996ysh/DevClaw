from fastapi import Request


def get_checkpointer(request: Request):
    """取在 lifespan 里建好的 AsyncPostgresSaver。"""
    return request.app.state.checkpointer


def get_store(request: Request):
    """取在 lifespan 里建好的 AsyncPostgresStore。"""
    return request.app.state.store