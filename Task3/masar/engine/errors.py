# bad lesson data. never retry this one.
class ValidationError(Exception):
    pass


# a short outside problem (timeout, 503). ok to retry.
class TransientError(Exception):
    def __init__(self, message, retry_after=None):
        super().__init__(message)
        self.retry_after = retry_after


# the workflow file itself is wrong, so nothing runs
class WorkflowError(Exception):
    def __init__(self, errors):
        self.errors = list(errors)
        super().__init__("; ".join(self.errors))


# the drafts file is broken
class StoreError(Exception):
    pass


# a resume or reject that cannot happen (no name, no reason, already decided...)
class ResumeError(Exception):
    pass
