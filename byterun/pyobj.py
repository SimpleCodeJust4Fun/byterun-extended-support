"""Implementations of Python fundamental objects for Byterun."""

import collections
import inspect
import types

import six


def make_cell(value):
    # Thanks to Alex Gaynor for help with this bit of twistiness.
    # Construct an actual cell object by creating a closure right here,
    # and grabbing the cell object out of the function we create.
    fn = (lambda x: lambda: x)(value)
    return fn.__closure__[0]


class Function(object):
    __slots__ = [
        '__name__', '__dict__', '__doc__', '__defaults__', '__code__', '__closure__', '__globals__',
        '_vm', '_func',
    ]

    def __init__(self, name, code, globs, defaults, closure, vm):
        self._vm = vm

        # PY3 function attrs
        self.__name__ = name or code.co_name
        self.__defaults__ = tuple(defaults)
        self.__globals__ = globs
        self.__code__ = code
        self.__closure__ = closure

        # Sometimes, we need a real Python function.  This is for that.
        kw = {
            'argdefs': tuple(defaults)
        }
        self.__dict__ = {}
        self.__doc__ = code.co_consts[0] if code.co_consts else None

        if closure:
            kw['closure'] = tuple(make_cell(0) for _ in closure)
        self._func = types.FunctionType(code, globs, **kw)

    def __repr__(self):  # pragma: no cover
        return '<Function %s at 0x%08x>' % (
            self.__name__, id(self)
        )

    def __get__(self, instance, owner):
        if instance is not None:
            return Method(instance, owner, self)
            return self

    def __call__(self, *args, **kwargs):
        callargs = inspect.getcallargs(self._func, *args, **kwargs)
        frame = self._vm.make_frame(
            self.__code__, callargs, self.__globals__, {}
        )
        CO_GENERATOR = 32  # flag for "this code uses yield"
        if self.__code__.co_flags & CO_GENERATOR:
            gen = Generator(frame, self._vm)
            frame.generator = gen
            retval = gen
        else:
            retval = self._vm.run_frame(frame)
        return retval


class Method(object):
    def __init__(self, obj, _class, func):
        self.im_self = obj
        self.im_class = _class
        self.im_func = func

    def __repr__(self):  # pragma: no cover
        name = "%s.%s" % (self.im_class.__name__, self.im_func.__name__)
        if self.im_self is not None:
            return '<Bound Method %s of %s>' % (name, self.im_self)
        else:
            return '<Unbound Method %s>' % (name,)

    def __call__(self, *args, **kwargs):
        if self.im_self is not None:
            return self.im_func(self.im_self, *args, **kwargs)
        else:
            return self.im_func(*args, **kwargs)


class Cell(object):
    """A fake cell for closures.

    Closures keep names in scope by storing them not in a frame, but in a
    separate object called a cell.  Frames share references to cells, and
    the LOAD_DEREF and STORE_DEREF opcodes get and set the value from cells.

    This class acts as a cell, though it has to jump through two hoops to make
    the simulation complete:

        1. In order to create actual FunctionType functions, we have to have
           actual cell objects, which are difficult to make. See the twisty
           double-lambda in __init__.

        2. Actual cell objects can't be modified, so to implement STORE_DEREF,
           we store a one-element list in our cell, and then use [0] as the
           actual value.

    """

    def __init__(self, value):
        self.contents = value

    def get(self):
        return self.contents

    def set(self, value):
        self.contents = value


Block = collections.namedtuple("Block", "type, handler, level")


class Frame(object):
    def __init__(self, f_code, f_globals, f_locals, f_back):
        self.f_code = f_code
        self.f_globals = f_globals
        self.f_locals = f_locals
        self.f_back = f_back
        self.stack = []
        if f_back and f_back.f_globals is f_globals:
            # If we share the globals, we share the builtins.
            self.f_builtins = f_back.f_builtins
        else:
            try:
                self.f_builtins = f_globals['__builtins__']
                if hasattr(self.f_builtins, '__dict__'):
                    self.f_builtins = self.f_builtins.__dict__
            except KeyError:
                # No builtins! Make up a minimal one with None.
                self.f_builtins = {'None': None}

        self.f_lineno = f_code.co_firstlineno
        self.f_lasti = 0

        if f_code.co_cellvars:
            self.cells = {}
            if not f_back.cells:
                f_back.cells = {}
            for var in f_code.co_cellvars:
                # Make a cell for the variable in our locals, or None.
                cell = Cell(self.f_locals.get(var))
                f_back.cells[var] = self.cells[var] = cell
        else:
            self.cells = None

        if f_code.co_freevars:
            if not self.cells:
                self.cells = {}
            for var in f_code.co_freevars:
                assert self.cells is not None
                assert f_back.cells, "f_back.cells: %r" % (f_back.cells,)
                self.cells[var] = f_back.cells[var]

        self.block_stack = []
        self.generator = None

    def __repr__(self):  # pragma: no cover
        return '<Frame at 0x%08x: %r @ %d>' % (
            id(self), self.f_code.co_filename, self.f_lineno
        )

    def line_number(self):
        """Get the current line number the frame is executing."""
        # We don't keep f_lineno up to date, so calculate it based on the
        # instruction address and the line number table.
        lnotab = self.f_code.co_lnotab
        byte_increments = six.iterbytes(lnotab[0::2])
        line_increments = six.iterbytes(lnotab[1::2])

        byte_num = 0
        line_num = self.f_code.co_firstlineno

        for byte_incr, line_incr in zip(byte_increments, line_increments):
            byte_num += byte_incr
            if byte_num > self.f_lasti:
                break
            line_num += line_incr

        return line_num


class Generator(object):
    def __init__(self, g_frame, vm):
        self.gi_frame = g_frame
        self.vm = vm
        self.started = False
        self.finished = False

    def __iter__(self):
        return self

    def next(self):
        return self.send(None)

    def send(self, value=None):
        if not self.started and value is not None:
            raise TypeError("Can't send non-None value to a just-started generator")
        self.gi_frame.stack.append(value)
        self.started = True
        val = self.vm.resume_frame(self.gi_frame)
        if self.finished:
            raise StopIteration(val)
        return val

    __next__ = next
