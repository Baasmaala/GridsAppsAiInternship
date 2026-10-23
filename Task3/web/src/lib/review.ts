// the same rules as the engine: a name of only spaces is no name
export const hasText = (s: string | null | undefined) => typeof s === 'string' && s.trim() !== '';

export const canApprove = (name: string) => hasText(name);

export const canReject = (name: string, reason: string) => hasText(name) && hasText(reason);
