import os
from subprocess import Popen
import sys

from .resource_proxy import ResourceProxy


try:
    from cptbox import SecurePopen, PIPE, CHROOTSecurity
except ImportError:
    SecurePopen, PIPE, CHROOTSecurity = None, None, None
    from wbox import WBoxPopen
else:
    WBoxPopen = None


class BaseExecutor(ResourceProxy):
    ext = None
    network_block = True
    address_grace = 4096
    command = None
    name = '(unknown)'
    test_program = ''
    test_time = 1
    test_memory = 65536

    def __init__(self, problem_id, source_code, *args, **kwargs):
        super(BaseExecutor, self).__init__()
        self._init(problem_id, source_code, *args, **kwargs)
        self._code = self._file(problem_id + self.ext)
        self.create_files(problem_id, source_code)
        self.process_files()

    def _init(self, problem_id, source_code, *args, **kwargs):
        pass

    def create_files(self, problem_id, source_code):
        with open(self._code, 'wb') as fo:
            fo.write(source_code)

    def process_files(self):
        pass

    def get_fs(self):
        return ['.*\.so', '/proc/meminfo', '/dev/null']

    def get_security(self):
        if CHROOTSecurity is None:
            raise NotImplementedError('No security manager on Windows')
        return CHROOTSecurity(self.get_fs())

    def get_executable(self):
        raise None

    def get_cmdline(self):
        raise NotImplementedError

    def get_env(self):
        if WBoxPopen is not None:
            return None
        return {'LANG': 'C'}

    def get_network_block(self):
        assert WBoxPopen is not None
        return self.network_block

    def get_address_grace(self):
        assert SecurePopen is not None
        return self.address_grace

    if SecurePopen is None:
        def launch(self, *args, **kwargs):
            return WBoxPopen(self.get_cmdline() + list(args),
                             time=kwargs.get('time'), memory=kwargs.get('memory'),
                             cwd=self._dir, executable=self.get_executable(),
                             network_block=True, env=self.get_env())
    else:
        def launch(self, *args, **kwargs):
            return SecurePopen(self.get_cmdline() + list(args),
                               security=self.get_security(), address_grace=self.get_address_grace(),
                               time=kwargs.get('time'), memory=kwargs.get('memory'),
                               stderr=(PIPE if kwargs.get('pipe_stderr', False) else None),
                               env=self.get_env(), cwd=self._dir)

    def launch_unsafe(self, *args, **kwargs):
        return Popen(self.get_cmdline() + list(args),
                     env=self.get_env(), executable=self.get_executable(),
                     cwd=self._dir, **kwargs)

    @classmethod
    def get_command(cls):
        return cls.command

    @classmethod
    def initialize(cls):
        if cls.get_command() is None:
            return False
        if not os.path.isfile(cls.get_command()):
            return False
        if not cls.test_program:
            return True

        print 'Self-testing: %s executor:' % cls.name,
        try:
            executor = cls('self_test', cls.test_program)
            proc = executor.launch(time=cls.test_time, memory=cls.test_memory)
            test_message = 'echo: Hello, World!'
            stdout, stderr = proc.communicate(test_message)
            res = stdout.strip() == test_message and not stderr
            print ['Failed', 'Success'][res]
            if stderr:
                print>>sys.stderr, stderr
            return res
        except Exception:
            print 'Failed'
            import traceback
            traceback.print_exc()
            return False
