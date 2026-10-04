"""Fail closed when numerical oracle code or matched inputs change on resume."""
import hashlib

def fingerprints(paths):
 return {str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}

def verify(saved,current):
 if saved is None:raise ValueError('Checkpoint lacks dependency fingerprints; explicit audited adoption required')
 if saved!=current:raise ValueError('Checkpoint dependency fingerprints changed; isolate a new run')
