#!/usr/bin/env python3

import os
import sys
import socketio
import hashlib
from code import InteractiveConsole
from aiohttp import web
from datetime import datetime
from termcolor import cprint
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


def log_event(debug, sid, str_, color):
    if debug:
        tm = datetime.now().strftime('%I:%M:%S %p')
        if sid:
            sid_short = sid[:8]
            cprint(f"{tm} ({sid_short}) : {str_}", color)
        else:
            sid_space = ' ' * 10
            cprint(f"{tm} {sid_soace} : {str_}", color)


class PythonConsole(InteractiveConsole):
    """Subclassed console that captures stdout

    adapted from https://stackoverflow.com/a/15311213
    """

    def __init__(self):
        InteractiveConsole.__init__(self)

    def write(self, data):
        self.runResult += data

    def showtraceback(self):
        self.exception_happened = True
        InteractiveConsole.showtraceback(self)

    def showsyntaxerror(self, filename=None):
        self.exception_happened = True
        InteractiveConsole.showsyntaxerror(self, filename)

    def push(self, expression):
        """Evaluate an expression"""
        self.exception_happened = False
        sys.stdout = self
        self.runResult = ''
        InteractiveConsole.push(self, expression)
        sys.stdout = sys.__stdout__
        return self.runResult

    def eval(self, cmd):
        """Alias for push"""
        return self.push(cmd)

    def call(self, method, args=None):
        """Execute method and return results"""
        self.locals['__temp_method__'] = self.locals[method]
        if args:
            self.locals['myargs'] = args
            self.push("__temp_return__ = __temp_method__(args)")
        else:
            self.push("__temp_return__ = __temp_method__()")
        return self.locals['__temp_return__']

    def get(self, variable):
        return self.locals[variable]

    def set(self, variable, value):
        self.locals[variable] = value


class AppWatcher(FileSystemEventHandler):
    """
    Watch a python module and re-import in an associated console when changes
    are detected.
    """

    hash_ = None
    debug = False
    py_file = None
    console = None

    def __init__(self, debug, console, py_file, watch_dir='.'):
        self.console = console
        self.py_file = py_file
        self.on_modified(None)
        self.debug = debug
        observer = Observer()
        observer.schedule(self, watch_dir, recursive=True)
        observer.start()

    def get_py_file_hash(self):
        with open(self.py_file, "rb") as fid:
            data = fid.read()
            return hashlib.md5(data).hexdigest()

    def on_modified(self, event):
        new_hash = self.get_py_file_hash()
        if new_hash != self.hash_:
            py_mod = self.py_file.replace(".py", "")
            lines = [
                f'import sys',
                f'if "{py_mod}" in sys.modules:'
                f'    del sys.modules["{py_mod}"]',
                f'from {py_mod} import *',
            ]
            list(map(self.console.runcode, lines))
            self.hash_ = new_hash
            if self.debug:
                print(f"Detected change and reloaded <{self.py_file}>")


class MainNamespace(socketio.AsyncNamespace):
    """Handle sio messaging"""

    debug = False
    active_users = set()
    console = None

    def __init__(self, namespace, debug, console):
        super().__init__(namespace)
        self.debug = debug
        self.console = console

    def on_connect(self, sid, environ=None):
        self.active_users.add(sid)
        log_event(self.debug, sid, "connected", "grey")

    def on_disconnect(self, sid, environ=None):
        self.active_users.remove(sid)
        log_event(self.debug, sid, "disconnected", "grey")

    def handle_call(self, request):
        kwargs = request.get("args") or {}
        call_return = self.console.call(request["call"])
        return {"result": "success", "return": call_return}

    def handle_eval(self, request):
        kwargs = request.get("args") or {}
        eval_result = self.console.eval(request["eval"])
        if self.console.exception_happened:
            return {"result": "exception", "return": eval_result}
        else:
            response = {
                "result": "success",
                "return": eval_result,
            }
            if request["eval"] in ["clear()", "update()"]:
                # hard-wired for debugging
                modules = self.console.locals.get("modules", [])
                connections = self.console.locals.get("connections", [])
                response["state"] = {
                    "modules": modules,
                    "connections": connections,
                }
            return response

    def handle_get(self, request):
        try:
            kwargs = request.get("args") or {}
            value = self.console.get(request["get"])
            return {"result": "success", "return": value}
        except KeyError:
            return {"result": "error", "description": "no such variable"}

    def handle_set(self, request):
        try:
            variable = request["set"]
            value = request["value"]
            self.console.set(variable, value)
            return {"result": "success"}
        except KeyError:
            return {"result": "error", "description": "could not set variable"}

    async def on_msg(self, sid, request):
        log_event(self.debug, sid, str(request), "green")
        call_table = {
            "call": self.handle_call,
            "eval": self.handle_eval,
            "get" : self.handle_get,
            "set" : self.handle_set,
        }
        for call_type, handle_func in call_table.items():
            if call_type in request:
                response = handle_func(request)
                log_event(self.debug, sid, response, "cyan")
                return response
        else:
            return {"result": "error", "description": "invalid request"}


def main():
    debug = True
    py_file = sys.argv[1]
    app = web.Application()
    sio = socketio.AsyncServer()
    console = PythonConsole()
    app_watcher = AppWatcher(debug, console, py_file)
    sio.register_namespace(MainNamespace("/", debug, console))
    sio.attach(app)
    print("Server started")
    web.run_app(app, host='127.0.0.1', port=8000, print=(lambda _: None),
                handle_signals=True)


if __name__ == '__main__':
    main()
