#  Copyright 2022 by Autodesk, Inc.
#  Permission to use, copy, modify, and distribute this software in object code form
#  for any purpose and without fee is hereby granted, provided that the above copyright
#  notice appears in all copies and that both that copyright notice and the limited
#  warranty and restricted rights notice below appear in all supporting documentation.
#
#  AUTODESK PROVIDES THIS PROGRAM "AS IS" AND WITH ALL FAULTS. AUTODESK SPECIFICALLY
#  DISCLAIMS ANY IMPLIED WARRANTY OF MERCHANTABILITY OR FITNESS FOR A PARTICULAR USE.
#  AUTODESK, INC. DOES NOT WARRANT THAT THE OPERATION OF THE PROGRAM WILL BE
#  UNINTERRUPTED OR ERROR FREE.

import sys
import traceback
from typing import Callable

import adsk.core
import adsk.fusion


try:
    from . import config
    DEBUG = config.DEBUG
except:
    DEBUG = False


def app() -> adsk.core.Application:
    """Returns the Application object."""
    return adsk.core.Application.get()


def ui() -> adsk.core.UserInterface:
    """Returns the UserInterface object."""
    return app().userInterface


def design() -> adsk.fusion.Design:
    """Returns the active Design object."""
    return adsk.fusion.Design.cast(app().activeProduct)


def log(
    message: str,
    level: adsk.core.LogLevels = adsk.core.LogLevels.InfoLogLevel,
    force_console: bool = False
) -> None:
    """
    Utility function to easily handle logging in your app.
    :param message: The message to log.
    :param level: The logging severity level.
    :param force_console: Forces the message to be written to the Text Command window.
    """
    # Always print to console, only seen through IDE.
    print(message)

    # Log all errors to Fusion log file.
    if level == adsk.core.LogLevels.ErrorLogLevel:
        log_type = adsk.core.LogTypes.FileLogType
        app().log(message, level, log_type)

    # If config.DEBUG is True write all log messages to the console.
    if DEBUG or force_console:
        log_type = adsk.core.LogTypes.ConsoleLogType
        app().log(message, level, log_type)


def handle_error(name: str, show_message_box: bool = False):
    """Utility function to simplify error handling.
    :param name: A name used to label the error.
    :param show_message_box: Indicates if the error should be shown in the message box.
                             If False, it will only be shown in the Text Command window
                             and logged to the log file.
    """

    log('===== Error =====', adsk.core.LogLevels.ErrorLogLevel)
    log(f'{name}\n{traceback.format_exc()}', adsk.core.LogLevels.ErrorLogLevel)

    # If desired you could show an error as a message box.
    if show_message_box:
        ui().messageBox(f'{name}\n{traceback.format_exc()}')


# Global Variable to hold Event Handlers
_handlers = []


def add_handler(
        event: adsk.core.Event,
        callback: Callable,
        *,
        name: str = None,
        local_handlers: list = None
):
    """
    Adds an event handler to the specified event.
    :param event: The event object you want to connect a handler to.
    :param callback: The function that will handle the event.
    :param name: A name to use in logging errors associated with this event.
                 Otherwise the name of the event object is used. This argument
                 must be specified by its keyword.
    :param local_handlers: A list of handlers you manage that is used to maintain
                           a reference to the handlers so they aren't released.
                           This argument must be specified by its keyword. If not
                           specified the handler is added to a global list and can
                           be cleared using the clear_handlers function. You may want
                           to maintain your own handler list so it can be managed
                           independently for each command.

    :returns: The event handler that was created. You don't often need this reference,
              but it can be useful in some cases.
    """
    module = sys.modules[event.__module__]
    handler_type = module.__dict__[event.add.__annotations__['handler']]
    handler = _create_handler(handler_type, callback, event, name, local_handlers)
    event.add(handler)
    return handler


def clear_handlers():
    """Clears the global list of handlers.
    """
    global _handlers
    _handlers = []


def _create_handler(
        handler_type,
        callback: Callable,
        event: adsk.core.Event,
        name: str = None,
        local_handlers: list = None
):
    handler = _define_handler(handler_type, callback, name)()
    (local_handlers if local_handlers is not None else _handlers).append(handler)
    return handler


def _define_handler(handler_type, callback, name: str = None):
    name = name or handler_type.__name__

    class Handler(handler_type):
        def __init__(self):
            super().__init__()

        def notify(self, args):
            try:
                callback(args)
            except:
                handle_error(name)

    return Handler
