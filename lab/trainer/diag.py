import traceback

def log(message: str) -> None:
    print(f'[Trainer] {message}')

def log_error(message: str) -> None:
    print(f'[Trainer][错误] {message}')

def log_exception(message: str, exc: BaseException) -> None:
    log_error(f'{message}: {exc}')
    traceback.print_exception(type(exc), exc, exc.__traceback__)
