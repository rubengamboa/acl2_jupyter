from ipykernel.kernelbase import Kernel
from acl2_bridge import ACL2Bridge, ACL2Command, ACL2BridgeError

import os.path
import json
import re

__version__ = '0.3'


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
            self.bridge.acl2_command(ACL2Command.LISP, "(set-slow-alist-action nil)")
            self.bridge.acl2_command(ACL2Command.LISP, ":ubu acl2-bridge-start")
        return self._bridge

    def __init__(self, **kwargs):
        Kernel.__init__(self, **kwargs)
        self.log.warning("Started: " + self.banner)


    def process_output(self, output):
        if not self.silent:
            # Send standard output
            stream_content = {'name': 'stdout', 'text': output}
            self.send_response(self.iopub_socket, 'stream', stream_content)

    def token_letter(self, letter):
        return (letter in "!$%&*+-./:<=>?@[]^_{}~|" or (letter >= "0" and letter <= "9")
                or (letter >= "a" and letter <= "z") or (letter >= "A" and letter <= "Z"))

    def convert_package_to_acl2s(self, code):
        converted = ""
        level = 0
        i = 0
        fraction_regex = re.compile("^[-+]?\\d+(/\\d+)?$")
        decimal_regex = re.compile("^([-+]?)(\\d*)\\.(\\d*)$")
        while i < len(code):
            letter = code[i]
            if self.token_letter(letter):
                token = ""
                while i < len(code):
                    if code[i] == '|':
                        token += code[i]
                        i += 1
                        while i < len(code) and code[i] != '|':
                            token += code[i]
                            i += 1
                        if i < len(code):
                            token += code[i]
                            i += 1
                    elif code[i] == "#" and i+1<len(code) and code[i+1] == '\\':
                        token += code[i:i+2]
                        i += 2
                    elif self.token_letter(code[i]):
                        token += code[i]
                        i += 1
                    else:
                        break
                if token.find("::") >= 0:
                    converted += token
                elif token[0] == ":":
                    if level == 0:
                        converted += token
                    else:
                        converted += "ACL2S::" + token[1:]
                elif token == ".":
                    converted += token
                elif fraction_regex.match(token):
                    converted += token
                else:
                    m = decimal_regex.match(token)
                    if m and len(m.group(2) + m.group(3)) > 0:
                        converted += m.group(1) + m.group(2) + m.group(3) + "/1" + (len(m.group(3)) * "0")
                    else:
                        converted += "ACL2S::" + token
            elif letter == '"':
                token = ""
                token += code[i]
                i += 1
                while i < len(code) and code[i] != '"':
                    if code[i] == '\\' and i+1 < len(code) and code[i+1] == '"':
                        token += code[i:i+2]
                        i += 2
                    else:
                        token += code[i]
                        i += 1
                if i < len(code):
                    token += code[i]
                    i += 1
                converted += token
            elif letter == '(':
                level += 1
                converted += letter
                i += 1
            elif letter == ')':
                level -= 1
                converted += letter
                i += 1
            else:
                converted += letter
                i += 1
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
            code = "(ld '( " + self.convert_package_to_acl2s(code.strip()) + " ) :ld-pre-eval-print t :ld-verbose nil :current-package \"ACL2S\")"
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