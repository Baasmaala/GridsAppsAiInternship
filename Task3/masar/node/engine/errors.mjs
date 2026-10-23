// bad lesson data. never retry this one.
export class ValidationError extends Error {
  constructor(message) {
    super(message);
    this.name = 'ValidationError';
  }
}

// the workflow file itself is wrong, so nothing runs
export class WorkflowError extends Error {
  constructor(errors) {
    super(errors.join('; '));
    this.name = 'WorkflowError';
    this.errors = [...errors];
  }
}

// the drafts file is broken
export class StoreError extends Error {
  constructor(message) {
    super(message);
    this.name = 'StoreError';
  }
}
