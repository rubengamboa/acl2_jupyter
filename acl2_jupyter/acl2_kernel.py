from ipykernel.kernelbase import Kernel
from acl2_bridge import ACL2Bridge, ACL2Command, ACL2BridgeError

import os.path
import json
import re

__version__ = '1.0'

def get_sexpr (pkg, code, i, canon=None):
    fraction_regex = re.compile("^[-+]?\\d+(/\\d+)?$")
    decimal_regex = re.compile("^([-+]?)(\\d*)\\.(\\d*)$")
    tree = None
    sexp = ""
    i = skip_whitespace(code, i)
    if i >= len(code):
        return "", None, i
    if i+3 < len(code) and code[i] == ':' and code[i+1] == '#' and code[i+3] == '#':
        sexp = code[i:i+4]
        tree = sexp
        i += 4
        return sexp, tree, i
    elif token_letter(code[i]) or code[i] == "\\":
        token = ""
        pkg_index = None
        while i < len(code) and (token_letter(code[i]) or code[i] == "\\"):
            if code[i] == "\\":
                if i+1 < len(code):
                    token += code[i:i+2]
                    i += 2
                else:
                    raise ValueError("Found EOF while processinig escaped character")
            elif code[i] == '|':
                token += code[i]
                i += 1
                while i < len(code) and code[i] != '|':
                    token += code[i]
                    i += 1
                if i < len(code):
                    token += code[i]
                    i += 1
            elif code[i] == ':' and i+1<len(code) and code[i+1] == ':' and pkg_index is not None:
                pkg_index = i
                token += code[i:i+2]
                i += 2
            else:
                token += code[i].upper()
                i += 1
        m = decimal_regex.match(token)
        if m and len(m.group(2) + m.group(3)) > 0:
            token += m.group(1) + m.group(2) + m.group(3) + "/1" + (len(m.group(3)) * "0")
        elif token[0] == ':':
            token = "keyword:" + token
        elif not fraction_regex.match(token):
            if pkg_index is None:
                token = pkg + "::" + token
            if canon is not None:
                token = canon.lookup_symbol(token)
        sexp = token
        tree = token
        return sexp, tree, i
    elif code[i] == "#":
        token = ""
        if i+1<len(code):
            if code[i+1] == '\\':
                token += code[i:i+2]
                i += 2
                if i >= len(code):
                    raise ValueError("Found EOF while processinig #char")
                if alpha_letter(code[i]):
                    while i<len(code) and alpha_letter(code[i]):
                        token += code[i]
                        i += 1
                else:
                    token += code[i]
                    i += 1
            elif code[i+1] in ('x', 'X'):
                token += code[i:i+2]
                i += 2
                while i<len(code) and hex_letter(code[i]):
                    token += code[i]
                    i += 1
            elif code[i+1] in ('o', 'O'):
                token += code[i:i+2]
                i += 2
                while i<len(code) and octal_letter(code[i]):
                    token += code[i]
                    i += 1
            elif code[i+1] in ('c', 'C'):
                token += code[i:i+2]
                i += 2
                if i < len(code) and code[i] == '(':
                    token += code[i]
                    i += 1
                    x, child, i = get_sexpr(pkg, code, i, canon)
                    if isinstance(child, str) and fraction_regex.match(child):
                        token += x
                        token += " "
                        i = skip_whitespace(code, i)
                        y, child, i = get_sexpr(pkg, code, i, canon)
                        if isinstance(child, str) and fraction_regex.match(child):
                            token += y
                            if i < len(code) and code[i] == ')':
                                token += code[i]
                                i += 1
                            else:
                                raise ValueError("Syntax error: Missing ')' in #C(...) expression")
                        else:
                            raise ValueError("Syntax error: Invalid imagpart in #C(...) expression")
                    else:
                        raise ValueError("Syntax error: Invalid realpart in #C(...) expression")
                else:
                    raise ValueError("Syntax error: Missing '(' in #C(...) expression")
            elif i+2 < len(code) and code[i:i+2] == '#(':
                token += code[i:i+2]
                i += 2
                found = False
                nest = 1
                while i < len(code):
                    if code[i] == ')':
                        token += code[i]
                        i += 1
                        nest -= 1
                        if nest == 0:
                            found = True
                            break
                    elif i+1 < len(code) and code[i:i+2] == '#(':
                        token += code[i:i+2]
                        i += 2
                        nest += 1
                    else:
                        token += code[i]
                        i += 1
                if not found:
                    raise ValueError("Syntax error: Unterminated #{...} quoted expression")
            elif i+4 < len(code) and code[i:i+5] == '#{"""':
                token += code[i:i+5]
                i += 5
                found = False
                while i+3 < len(code):
                    if code[i:i+4] == '"""}':
                        token += code[i:i+4]
                        i += 4
                        found = True
                        break
                    token += code[i]
                    i += 1
                if not found:
                    raise ValueError("Syntax error: Unterminated #{...} quoted expression")
            elif token_letter(code[i+1]) or code[i+1]=="'":
                token += code[i]
                i += 1
                if code[i] == "'":
                    token += code[i]
                    i += 1
                while i<len(code) and token_letter(code[i]):
                    token += code[i]
                    i += 1
            else:
                raise ValueError("Syntax error: Unrecognized # expr", code[i:i+200])
        else:
            raise ValueError("Syntax error: # at end of file")
        if token.startswith("#!"):
            return get_sexpr(token[2:].upper(), code, i, canon)
        else:
            sexp = token
            tree = token
            return sexp, tree, i
    elif code[i] == '"':
        token = ""
        token += code[i]
        i += 1
        while i < len(code) and code[i] != '"':
            if code[i] == '\\' and i+1 < len(code):
                token += code[i:i+2]
                i += 2
            else:
                token += code[i]
                i += 1
        if i < len(code):
            token += code[i]
            i += 1
        else:
            raise ValueError("Syntax error: Unterminated string starting at", token)
        # print("STRING:", token)
        sexp = token
        tree = token
        return sexp, tree, i
    elif code[i] == '(':
        sexp += '('
        i += 1
        tree = []
        while True:
            token, child, i = get_sexpr(pkg, code, i, canon)
            if child is None:
                raise ValueError("Syntax error: Unterminated list", sexp, tree)
            if token == ')':
                return sexp+")", tree, i
            elif token == '.':
                if len(tree) == 0:
                    raise ValueError("Syntax error: Headless cons pair")
                token, child, i = get_sexpr(pkg, code, i, canon)
                if i >= len(code) or token == ')':
                    raise ValueError("Syntax error: Unterminated cons pair")
                sexp += " . " + token
                tree.reverse()
                for branch in tree:
                    child = ["cons", branch, child]
                tree = child
                token, child, i = get_sexpr(pkg, code, i, canon)
                if i >= len(code):
                    raise ValueError("Syntax error: Unterminated cons pair")
                if token == ')':
                    return sexp+")", tree, i
                raise ValueError("Syntax error: Invalid cons pair")
            else:
                if sexp[-1] == '(':
                    sexp += token
                else:
                    sexp += " " + token
                tree.append(child)
    elif code[i] in "'`,":
        esc = code[i]
        i += 1
        sexp, child, i = get_sexpr(pkg, code, i, canon)
        return esc+sexp, [esc, child], i
    else:
        token = code[i].upper()
        i += 1
        sexp = token
        tree = token
        return sexp, tree, i

def token_letter(letter):
    return (letter in "!$%&*+-./:<=>?@[]^_{}~|" or (letter >= "0" and letter <= "9")
            or (letter >= "a" and letter <= "z") or (letter >= "A" and letter <= "Z"))

def alpha_letter(letter):
    return ((letter >= "a" and letter <= "z") or (letter >= "A" and letter <= "Z"))

def hex_letter(letter):
    return ((letter >= "0" and letter <= "9")
            or (letter >= "a" and letter <= "f") or (letter >= "A" and letter <= "F"))

def octal_letter(letter):
    return (letter >= "0" and letter <= "7")

def skip_whitespace (code, i):
    while i < len(code):
        if code[i] == ';':
            i += 1
            while i < len(code) and code[i] != '\n':
                i += 1
        elif i+1 < len(code) and code[i] == '#' and code[i+1] == '|':
            level = 1
            i += 2
            while i+1 < len(code):
                if code[i]=='|' and code[i+1]=='#':
                    level -= 1
                    if level == 0:
                        break
                    i += 2
                elif code[i] == '#' and code[i+1] == '|':
                    level += 1
                    i += 2
                else:
                    i += 1
            if i+1 < len(code):
                i += 2
        elif code[i].isspace():
            i += 1
        else:
            break
    return i


class Acl2Kernel(Kernel):
    implementation = 'acl2_kernel'
    implementation_version = __version__

    @property
    def language_version(self):
        m = re.search('ACL2 Version (.*)"', self.banner)
        return m.group(1)

    language_info = {'name': 'acl2',
                     'codemirror_mode': 'Common Lisp',
                     'mimetype': 'text/x-common-lisp',
                     'file_extension': '.lisp'}

    _banner = None

    @property
    def banner(self):
        if self._banner is None:
            response = self.bridge.acl2_command(ACL2Command.JSON, "(cdr (assoc 'acl2-version *initial-global-table*))")
            self._banner = response["RETURN"]
        return self._banner

    _bridge = None

    @property
    def bridge(self):
        if self._bridge is None:
            self._bridge = ACL2Bridge(log=self.log)
            self.bridge.acl2_command(ACL2Command.LISP, ":ubu acl2-bridge-start")
            self.bridge.acl2_command(ACL2Command.LISP, "(set-slow-alist-action nil)")
            self.bridge.acl2_command(ACL2Command.LISP, "(assign slow-array-action nil)")
        return self._bridge

    def __init__(self, **kwargs):
        Kernel.__init__(self, **kwargs)
        self.log.warning("Started: " + self.banner)


    def process_output(self, output):
        if not self.silent:
            # Send standard output
            stream_content = {'name': 'stdout', 'text': output}
            self.send_response(self.iopub_socket, 'stream', stream_content)

    # def token_letter(self, letter):
    #     return (letter in "!$%&*+-./:<=>?@[]^_{}~|" or (letter >= "0" and letter <= "9")
    #             or (letter >= "a" and letter <= "z") or (letter >= "A" and letter <= "Z"))

    # def convert_package_to_acl2s(self, code):
    #     converted = ""
    #     level = 0
    #     i = 0
    #     fraction_regex = re.compile("^[-+]?\\d+(/\\d+)?$")
    #     decimal_regex = re.compile("^([-+]?)(\\d*)\\.(\\d*)$")
    #     while i < len(code):
    #         letter = code[i]
    #         if self.token_letter(letter):
    #             token = ""
    #             while i < len(code):
    #                 if code[i] == '|':
    #                     token += code[i]
    #                     i += 1
    #                     while i < len(code) and code[i] != '|':
    #                         token += code[i]
    #                         i += 1
    #                     if i < len(code):
    #                         token += code[i]
    #                         i += 1
    #                 elif code[i] == "#" and i+1<len(code) and code[i+1] == '\\':
    #                     token += code[i:i+2]
    #                     i += 2
    #                 elif self.token_letter(code[i]):
    #                     token += code[i]
    #                     i += 1
    #                 else:
    #                     break
    #             if token.find("::") >= 0:
    #                 converted += token
    #             elif token[0] == ":":
    #                 converted += "keyword::" + token[1:]
    #                 # if level == 0:
    #                 #     converted += token
    #                 # else:
    #                 #     converted += "ACL2S::" + token[1:]
    #             elif token == ".":
    #                 converted += token
    #             elif fraction_regex.match(token):
    #                 converted += token
    #             else:
    #                 m = decimal_regex.match(token)
    #                 if m and len(m.group(2) + m.group(3)) > 0:
    #                     converted += m.group(1) + m.group(2) + m.group(3) + "/1" + (len(m.group(3)) * "0")
    #                 else:
    #                     converted += "ACL2S::" + token
    #         elif letter == '"':
    #             token = ""
    #             token += code[i]
    #             i += 1
    #             while i < len(code) and code[i] != '"':
    #                 if code[i] == '\\' and i+1 < len(code) and code[i+1] == '"':
    #                     token += code[i:i+2]
    #                     i += 2
    #                 else:
    #                     token += code[i]
    #                     i += 1
    #             if i < len(code):
    #                 token += code[i]
    #                 i += 1
    #             converted += token
    #         elif letter == '(':
    #             level += 1
    #             converted += letter
    #             i += 1
    #         elif letter == ')':
    #             level -= 1
    #             converted += letter
    #             i += 1
    #         else:
    #             converted += letter
    #             i += 1
    #     return converted

    def canonize_acl2 (self, code):
        i = 0
        pkg = "ACL2S"
        converted = ""
        while i < len(code):
            sexp, tree, i = get_sexpr(pkg, code, i)
            if tree is None:
                break
            # print(sexp)
            # print(tree)
            if (sexp.startswith(":") or
                (sexp.startswith("#") and sexp[1] not in "\\oOxX")):
                cmd = sexp
                sexp, tree, i = get_sexpr(pkg, code, i)
                if tree is None:
                    raise ValueError("Syntax error: :cmd or #-expr at end of file")
                sexp = cmd + " " + sexp
            converted += cmd + "\n\n"
        return converted

    def do_execute(self, code, silent, store_history=True,
                   user_expressions=None, allow_stdin=False):
        self.silent = silent
        self.status = 1
        if not code.strip():
            return {'status': 'ok', 'execution_count': self.execution_count,
                    'payload': [], 'user_expressions': {}}

        interrupted = False
        try:
            code = "(ld '( " + self.canonize_acl2(code.strip()) + " ) :ld-pre-eval-print t :ld-verbose nil :current-package \"ACL2S\")"
            self.log.info(">>> " + code)
            response = self.bridge.acl2_command(ACL2Command.LISP, code)
            self.log.info("<<< " + json.dumps(response, indent=2))
        except ACL2BridgeError as e:
            self.process_output("ACL2 Bridge Error: " + e.message)
            self.status = 0
        except KeyboardInterrupt:
            self._bridge = None
            self.bridge
            self.process_output("KeyboardInterrupt: Restarting ACL2")
            interrupted = True
        except ValueError as e:
            self.process_output("ACL2 Syntax Error: " + e.message)
            self.status = 0
        except:
            self._bridge = None
            self.bridge
            self.process_output("RuntimeException: Restarting ACL2")
            self.status = 0

        if interrupted:
            return {'status': 'abort', 'execution_count': self.execution_count}

        if self.status == 0:
            error_content = {'execution_count': self.execution_count,
                             'ename': '', 'evalue': '', 'traceback': []}
            self.send_response(self.iopub_socket, 'error', error_content)
            error_content['status'] = 'error'
            return error_content
        else:
            if ACL2Command.ERROR in response:
                stream_content = {'name': 'stderr', 'text': response[ACL2Command.ERROR]}
                self.send_response(self.iopub_socket, 'stream', stream_content)
                return {'status': 'error', 'execution_count': self.execution_count,
                        'ename': '', 'evalue': '', 'traceback': []}
            else:
                if ACL2Command.STDOUT in response:
                    output = response[ACL2Command.STDOUT]
                    output = re.sub(r'\nACL2.? !>+Bye.*\n', "", output, flags=re.M)
                    output = re.sub(r'\nTTAG NOTE:.*\n', "", output, flags=re.M)
                    self.process_output(output)
                # self.process_output("----return----\n")
                # self.process_output(response[ACL2Command.RETURN])
                exprs = {}
                for name, expr in user_expressions.items():
                    try:
                        response = self.bridge.acl2_command(ACL2Command.LISP, expr)
                        if ACL2Command.ERROR in response:
                            exprs[name] = response[ACL2Command.ERROR]
                        else:
                            exprs[name] = response[ACL2Command.RETURN]
                    except:
                        exprs[name] = "ACL2Bridge Exception"
                return {'status': 'ok', 'execution_count': self.execution_count,
                        'payload': [], 'user_expressions': exprs}

    # def do_complete(self, code, cursor_pos):
    #     code = code[:cursor_pos]
    #     default = {'matches': [], 'cursor_start': 0,
    #                'cursor_end': cursor_pos, 'metadata': dict(),
    #                'status': 'ok'}

    #     if not code or code[-1] == ' ':
    #         return default

    #     tokens = code.replace(';', ' ').split()
    #     if not tokens:
    #         return default

    #     matches = []
    #     token = tokens[-1]
    #     start = cursor_pos - len(token)

    #     if token[0] == '$':
    #         # complete variables
    #         cmd = 'compgen -A arrayvar -A export -A variable %s' % token[1:] # strip leading $
    #         output = self.bashwrapper.run_command(cmd).rstrip()
    #         completions = set(output.split())
    #         # append matches including leading $
    #         matches.extend(['$'+c for c in completions])
    #     else:
    #         # complete functions and builtins
    #         cmd = 'compgen -cdfa %s' % token
    #         output = self.bashwrapper.run_command(cmd).rstrip()
    #         matches.extend(output.split())

    #     if not matches:
    #         return default
    #     matches = [m for m in matches if m.startswith(token)]

    #     return {'matches': sorted(matches), 'cursor_start': start,
    #             'cursor_end': cursor_pos, 'metadata': dict(),
    #             'status': 'ok'}

if __name__ == '__main__':
    from ipykernel.kernelapp import IPKernelApp
    IPKernelApp.launch_instance(kernel_class=Acl2Kernel)
