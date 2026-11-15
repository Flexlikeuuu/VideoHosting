// Helper API client using fetch with credentials: 'include' for httpOnly cookies

const BASE_URL = '/api/v1';

export class ApiError extends Error {
  status: number;
  data: any;

  constructor(status: number, message: string, data?: any) {
    super(message);
    this.status = status;
    this.data = data;
  }
}

export async function apiRequest<T = any>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${BASE_URL}${endpoint}`;
  const headers = new Headers(options.headers || {});

  if (!(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(url, {
    ...options,
    headers,
    credentials: 'include', // sends cookies
  });

  if (!response.ok) {
    let errorData: any = null;
    let errorMsg = `HTTP Error ${response.status}`;
    try {
      errorData = await response.json();
      errorMsg = errorData.detail || errorMsg;
    } catch {
      // not json
    }
    throw new ApiError(response.status, errorMsg, errorData);
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}
