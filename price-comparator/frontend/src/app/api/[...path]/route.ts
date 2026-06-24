const BACKEND_URL = process.env.BACKEND_URL || 'http://backend:8000'

async function proxy(request: Request, { params }: { params: { path: string[] } }) {
  const path = '/' + params.path.join('/')
  const search = new URL(request.url).search
  const target = `${BACKEND_URL}${path}${search}`

  const headers = new Headers(request.headers)
  headers.delete('host')
  headers.delete('connection')

  const init: RequestInit = {
    method: request.method,
    headers,
  }

  if (request.method !== 'GET' && request.method !== 'HEAD') {
    init.body = await request.text()
  }

  const res = await fetch(target, init)

  const resHeaders = new Headers(res.headers)
  resHeaders.delete('transfer-encoding')

  return new Response(res.body, {
    status: res.status,
    statusText: res.statusText,
    headers: resHeaders,
  })
}

export const GET = proxy
export const POST = proxy
export const PUT = proxy
export const DELETE = proxy
export const PATCH = proxy
