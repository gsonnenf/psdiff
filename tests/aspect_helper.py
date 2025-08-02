import functools

def log_aspect(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        print(f"\n[LOG] Entering {func.__name__}")
        result = func(*args, **kwargs)
        print(f"[LOG] Exiting {func.__name__}")
        return result
    return wrapper

def weave_aspect(cls):
    for attr_name in dir(cls):
        attr = getattr(cls, attr_name)
        if callable(attr) and not attr_name.startswith("__"):
            wrapped = log_aspect(attr)
            setattr(cls, attr_name, wrapped)
    return cls