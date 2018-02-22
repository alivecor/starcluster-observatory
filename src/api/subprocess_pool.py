"""Manages a list of asynchronous tasks as subprocesses."""
import subprocess


class Subprocess:
    def __init__(self, identifier, p):
        """Constructor

        Args:
            identifier (string) - An identifier for this process
            p (subprocess.Popen) - A popen object representing the running process.
        """
        self.identifier = identifier
        self.p = p


class SubprocessPool:
    def __init__(self):
        self._subprocesses = []
        self._error_queue = []

    def run_command(self, command_args, identifier=None):
        """Run a command in the background.

        Args:
            command_args ([string]) - Array of command arguments to run.
            identifier (string) - A human-readable string to identify this process.
        """
        if identifier is None:
            identifier = command_args[0]
        p = subprocess.Popen(command_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self._subprocesses.append(Subprocess(identifier, p))

    def pop_errors(self):
        """Poll for errors, return all from queue."""
        self.poll()
        errors = []
        for failed_sp in self._error_queue:
            exit_code = failed_sp.p.poll()
            stdout = ''
            if failed_sp.p.stdout:
                stdout = failed_sp.p.stdout.read().decode('utf-8')
            stderr = ''
            if failed_sp.p.stderr:
                stderr = failed_sp.p.stderr.read().decode('utf-8')
            errors.append({
                'code': str(exit_code),
                'error': stderr,
                'output': stdout,
            })
        self._error_queue = []
        return errors

    def poll(self):
        """Check subprocesses, add failed processes to error queue."""
        completed_indices = []
        for i, subprocess in enumerate(self._subprocesses):
            state = subprocess.p.poll()
            if state is None:
                print('%s still running' % subprocess.identifier)
            elif state == 0:
                print('%s completed' % subprocess.identifier)
                completed_indices.append(i)
            else:
                self._error_queue.append(subprocess)
                completed_indices.append(i)
        for i in reversed(completed_indices):
            del self._subprocesses[i]
