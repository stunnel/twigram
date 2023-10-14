# -*- coding: utf-8 -*-

import fcntl


class FileLock:
    def __init__(self, file_path):
        self.file_path = file_path
        self.lock_file = None

    def acquire(self) -> bool:
        self.lock_file = open(self.file_path, 'w')
        try:
            fcntl.lockf(self.lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except IOError:
            self.lock_file.close()
            return False

    def release(self):
        if self.lock_file:
            fcntl.lockf(self.lock_file, fcntl.LOCK_UN)
            self.lock_file.close()
            self.lock_file = None
