// Responsibility: the ONE place that builds fetch() calls to the
// backend -- attaches the JWT, parses errors into a consistent shape,
// and centralizes the base URL. Every page calls through this, never
// fetch() directly, so auth handling and error shape stay in one place.

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api"

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

function getToken(): string | null {
  return localStorage.getItem("access_token")
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem("access_token", token)
  else localStorage.removeItem("access_token")
}

async function request<T>(
  path: string,
  options: { method?: string; body?: unknown; isFormData?: boolean } = {}
): Promise<T> {
  const headers: Record<string, string> = {}
  const token = getToken()
  if (token) headers["Authorization"] = `Bearer ${token}`

  let body: BodyInit | undefined
  if (options.body !== undefined) {
    if (options.isFormData) {
      body = options.body as FormData
      // Deliberately no Content-Type header for FormData -- the browser
      // sets the multipart boundary itself; setting it manually breaks
      // the upload.
    } else {
      headers["Content-Type"] = "application/json"
      body = JSON.stringify(options.body)
    }
  }

  const response = await fetch(`${BASE_URL}${path}`, {
    method: options.method ?? "GET",
    headers,
    body,
  })

  if (!response.ok) {
    let detail = response.statusText
    try {
      const errorBody = await response.json()
      detail = errorBody.detail ?? detail
    } catch {
      // response wasn't JSON -- fall back to statusText
    }
    throw new ApiError(response.status, detail)
  }

  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) => request<T>(path, { method: "POST", body }),
  patch: <T>(path: string, body?: unknown) => request<T>(path, { method: "PATCH", body }),
  postForm: <T>(path: string, formData: FormData) =>
    request<T>(path, { method: "POST", body: formData, isFormData: true }),
}
