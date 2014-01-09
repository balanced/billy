"""Auto rebuild documents when file is changed

"""
import time
import logging
import subprocess

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class Rebuilder(FileSystemEventHandler):
    """Document file rebuilder
    
    """
    
    def __init__(self, src_dir, build_dir, type, logger=None):
        self.logger = logger
        if self.logger is None:
            self.logger = logging.getLogger(__name__)
        self.src_dir = src_dir
        self.build_dir = build_dir
        self.type = type
    
    def build(self):
        """Rebuild document
        
        """
        self.logger.info('Building document ...')
        subprocess.check_call([
            'sphinx-build', 
            '-W',
            '-b', 
            self.type, 
            self.src_dir, 
            self.build_dir
        ])
        
    def on_modified(self, event):
        self.build()

    def run(self):
        """Sync to remote server
        
        """
        self.build()
        self.logger.info('Monitoring %s ...', self.src_dir)
        observer = Observer()
        observer.schedule(self, path=self.src_dir, recursive=True)
        observer.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    builder = Rebuilder('source', '_build/html', 'html')
    builder.run()
