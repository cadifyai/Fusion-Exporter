from .commands import entry
from . import utility as futils


def run(context):
    try:
        entry.start()
    except Exception:
        futils.handle_error('run')


def stop(context):
    try:
        entry.stop()
    except Exception:
        futils.handle_error('stop')
