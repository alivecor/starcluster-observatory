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
        self.subprocesses = []
        self.error_queue = []

    def run_command(self, command_args, identifier=None):
        """Run a command in the background.

        Args:
            command_args ([string]) - Array of command arguments to run.
            identifier (string) - A human-readable string to identify this process.
        """
        if identifier is None:
            identifier = command_args[0]
        p = subprocess.Popen(command_args)
        self.subprocesses.append(Subprocess(identifier, p))

    def poll(self):
        """Check subprocesses, add errors to error queue."""
        running = []
        for subprocess in self.subprocesses:
            state = subprocess.p.poll()
            if state is None:
                running.append(subprocess)
            elif state == 0:
                print('%s completed' % subprocess.identifier)
            else:
                self.error_queue.append(subprocess)
