// #/replay?run=abc&item=DOR-CAT-001  ->  { page: 'replay', params: { run: 'abc', item: 'DOR-CAT-001' } }
export function parseHash(hash: string): { page: string; params: URLSearchParams } {
  const body = hash.replace(/^#\/?/, '');
  const [page, query = ''] = body.split('?');
  return { page, params: new URLSearchParams(query) };
}

export function link(page: string, params: Record<string, string> = {}): string {
  const q = new URLSearchParams(params).toString();
  return `#/${page}${q ? `?${q}` : ''}`;
}
