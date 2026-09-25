# -*- coding: utf-8 -*-
#
# rcparser.py
#
# Author:   Toke Høiland-Jørgensen (toke@toke.dk)
# Date:     20 March 2018
# Copyright (c) 2018, Toke Høiland-Jørgensen
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import pprint
import shlex
import sys


class ParseError(RuntimeError):
    pass


class RcParser(shlex.shlex):

    def __init__(self, filename):
        self.lexer = shlex.shlex(open(filename, "rt"), infile=filename,
                                 posix=True)
#        self.lexer.whitespace = " \t"
        self.lexer.wordchars += "-."
        self.lexer.source = "include"

        self.global_container = Container("global")
        self.batches = {}
        self.argsets = {}
        self.current_container = self.global_container

    def parse_error(self, msg):
        raise ParseError(self.lexer.error_leader() + msg)

    def get_value(self, tok=None):
        if tok is None:
            tok = self.lexer.get_token()
        if not tok:
            self.parse_error("Value expected")

        try:
            return int(tok)
        except ValueError:
            try:
                return float(tok)
            except ValueError:
                return tok

    def check_name(self, tok):
        if not all((i in self.lexer.wordchars for i in tok)):
            self.parse_error("Invalid name: '%s'" % tok)

    def _parse_assignment(self, name):
        self.check_name(name)
        tok = self.lexer.get_token()
        key = None
        if tok == "[":
            key = self.lexer.get_token()
            if self.lexer.get_token() != ']':
                self.parse_error("Expected ']'")
            tok = self.lexer.get_token()

        if tok != "=":
            self.parse_error("Expected '=', got '%s'" % tok)

        value = self.get_value()
        if value == "[":
            value = []
            tok = self.get_value()
            while True:
                value.append(tok)
                tok = self.get_value()
                if tok == ']':
                    break
                elif tok == ',':
                    tok = self.lexer.get_token()
                else:
                    self.parse_error("Expected ',' or ']'")

        print("Setting %s[%s]=%s" % (name, key, value))
        return name, key, value

    def parse_var(self):
        name = self.lexer.get_token()
        self.current_container.set_var(*self._parse_assignment(name))

    def parse_batch(self):
        name = self.lexer.get_token()
        self.check_name(name)
        if name in self.batches:
            self.parse_error("Duplicate batch name: %s" % name)

        tok = self.lexer.get_token()
        if tok == 'inherits':
            parent = self.lexer.get_token()
            if parent not in self.batches:
                self.parse_error("Inherit from undefined batch '%s'" % parent)
            parent = self.batches[parent]
        else:
            self.lexer.push_token(tok)
            parent = None
        self.batches[name] = Batch(name, parent)
        self.current_container = self.batches[name]

    def parse_argset(self):
        name = self.lexer.get_token()
        self.check_name(name)
        if name in self.argsets:
            self.parse_eror("Duplicate argset name: %s" % name)

        self.argsets[name] = Argset(name)
        self.current_container = self.argsets[name]

    def parse_end(self):
        typ = self.lexer.get_token()
        if typ == "batch":
            if not isinstance(self.current_container, Batch):
                self.parse_error("Batch end with no begin")
            self.current_container = self.global_container
            print("Ended batch")
        elif typ == "argset":
            if not isinstance(self.current_container, Argset):
                self.parse_error("Argset end with no begin")
            self.current_container = self.global_container
            print("Ended argset")
        else:
            self.parse_error("Invalid end type '%s'" % typ)

    def _parse_exec(self, check):
        typ = self.lexer.get_token()
        if typ not in ("pre", "post"):
            self.parse_error("Invalid exec type '%s'" % typ)

        cmd = self.lexer.get_token()
        try:
            self.current_container.add_exec(cmd, typ, check)
            print("Added %s%s command: '%s'" % (("checked " if check else ""),
                                                typ, cmd))
        except NotImplementedError:
            self.parse_error("Exec not allowed here")

    def parse_exec(self):
        self._parse_exec(False)

    def parse_exec_check(self):
        self._parse_exec(True)

    def get_loop_vals(self):
        vals = [self.get_value()]
        tok = self.lexer.get_token()
        while tok == ',':
            vals.append(self.get_value())
            tok = self.lexer.get_token()

        self.lexer.push_token(tok)

        return vals

    def parse_loop(self):
        name = self.lexer.get_token()
        self.check_name(name)
        if self.lexer.get_token() != "as":
            self.parse_error("Expected 'as'")

        vals = self.get_loop_vals()
        print("Parsed loop: %s as %s" % (name, vals))

    def parse_loop_argset(self):
        vals = self.get_loop_vals()
        print("Parsed loop_argset: %s" % vals)

    def parse(self):
        tok = self.lexer.get_token()
        while tok is not None:
            if hasattr(self, "parse_%s" % tok):
                getattr(self, "parse_%s" % tok)()
            else:
                self.current_container.set_option(*self._parse_assignment(tok))
            tok = self.lexer.get_token()


class Container(object):
    def __init__(self, name):
        self.name = name
        self.vars = {}
        self.options = {}

    def set(self, container, name, key, value):
        if key:
            if name in container:
                container[name][key] = value
            else:
                container[name] = {key: value}
        else:
            container[name] = value

    def set_option(self, name, key, value):
        self.set(self.options, name, key, value)

    def set_var(self, name, key, value):
        self.set(self.vars, name, key, value)

    def __str__(self):
        return "%s(%s):\n Options: %s\n Vars: %s" % (self.__class__.__name__,
                                                     self.name,
                                                     pprint.pformat(self.options),
                                                     pprint.pformat(self.vars))

    def add_exec(self, cmd, typ, check=False):
        raise NotImplementedError()


class Batch(Container):

    def __init__(self, name, parent=None):
        super(Batch, self).__init__(name)
        self.parent = parent
        print("Starting batch %s%s" % (name,
                                       ("(%s)" % parent.name) if parent else ""))

    def add_exec(self, cmd, typ, check=False):
        pass


class Argset(Container):

    def __init__(self, name):
        super(Argset, self).__init__(name)
        print("Starting argset %s" % name)


if __name__ == "__main__":
    parser = RcParser(sys.argv[1])
    parser.parse()
    print(parser.global_container)
