# bad lesson data. never retry this one.
class ValidationError(Exception):
    pass


# the workflow file itself is wrong, so nothing runs
class WorkflowError(Exception):
    def __init__(self, errors):
        self.errors = list(errors)
        super().__init__("; ".join(self.errors))


# the drafts file is broken
class StoreError(Exception):
    pass
