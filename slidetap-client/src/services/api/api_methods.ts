//    Copyright 2024 SECTRA AB
//
//    Licensed under the Apache License, Version 2.0 (the "License");
//    you may not use this file except in compliance with the License.
//    You may obtain a copy of the License at
//
//        http://www.apache.org/licenses/LICENSE-2.0
//
//    Unless required by applicable law or agreed to in writing, software
//    distributed under the License is distributed on an "AS IS" BASIS,
//    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
//    See the License for the specific language governing permissions and
//    limitations under the License.

import auth from 'src/services/auth'

/**
 * Custom error class for API errors with additional context
 */
export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly statusText: string,
    public readonly body?: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

/**
 * Custom error class for authentication errors
 */
export class AuthenticationError extends ApiError {
  constructor(status: number, statusText: string) {
    super('Authentication failed. Please log in again.', status, statusText)
    this.name = 'AuthenticationError'
  }
}

type QueryValue = string | string[] | undefined | null

function buildUrl(path: string, args?: Map<string, QueryValue>): string {
  let url = '/api/' + path
  if (args !== undefined) {
    const parts: string[] = []
    args.forEach((value, key) => {
      if (value === undefined || value === null || value === '') {
        return
      }
      const encodedKey = encodeURIComponent(key)
      if (Array.isArray(value)) {
        for (const entry of value) {
          if (entry === undefined || entry === null || entry === '') continue
          parts.push(`${encodedKey}=${encodeURIComponent(entry)}`)
        }
      } else {
        parts.push(`${encodedKey}=${encodeURIComponent(value)}`)
      }
    })
    if (parts.length > 0) {
      url += '?' + parts.join('&')
    }
  }
  return url
}

async function http(
  method: string,
  url: string,
  data?: FormData | string,
  contentType: string = 'application/json',
): Promise<Response> {
  const response = await fetch(url, {
    body: data,
    headers: {
      'Content-Type': contentType,
      ...auth.getHeaders(),
    },
    method,
    credentials: 'include',
  })
  return await checkResponse(response)
}

async function checkResponse(response: Response): Promise<Response> {
  if (response.status === 401 || response.status === 403) {
    auth.logout()
    throw new AuthenticationError(response.status, response.statusText)
  }

  if (!response.ok) {
    // Try to extract error message from response body
    let errorBody: string | undefined
    try {
      const contentType = response.headers.get('content-type')
      if (contentType?.includes('application/json')) {
        const jsonBody = await response.json()
        errorBody = jsonBody.detail ?? jsonBody.message ?? JSON.stringify(jsonBody)
      } else {
        errorBody = await response.text()
      }
    } catch {
      // Ignore parsing errors for error body
    }

    const message = errorBody ?? response.statusText ?? 'Unknown error'
    throw new ApiError(
      `API request failed: ${message}`,
      response.status,
      response.statusText,
      errorBody,
    )
  }

  return response
}

/**
 * Safely parse JSON from a response, with proper error handling for non-JSON responses
 */
export async function parseJsonResponse<T>(response: Response): Promise<T> {
  const contentType = response.headers.get('content-type')

  if (!contentType?.includes('application/json')) {
    const text = await response.text()
    throw new ApiError(
      `Expected JSON response but received ${contentType ?? 'unknown content type'}`,
      response.status,
      response.statusText,
      text,
    )
  }

  try {
    return await response.json() as T
  } catch (error) {
    const text = await response.text().catch(() => 'Unable to read response body')
    throw new ApiError(
      `Failed to parse JSON response: ${error instanceof Error ? error.message : 'Unknown error'}`,
      response.status,
      response.statusText,
      text,
    )
  }
}

export async function post(
  path: string,
  data?: object,
  query?: Map<string, string | string[] | undefined>,
): Promise<Response> {
  const url = buildUrl(path, query)
  const response = await http('POST', url, JSON.stringify(data))
  checkResponse(response)
  return response
}

export async function delete_(
  path: string,
  args?: Map<string, string | string[] | undefined | null>,
): Promise<Response> {
  const url = buildUrl(path, args)
  const response = await http('DELETE', url, undefined)
  checkResponse(response)
  return response
}

export async function postFile(
  path: string,
  file: File,
): Promise<Response> {
  const url = buildUrl(path)
  const uploadData = new FormData()
  uploadData.append('file', file)
  const response = await fetch(url, {
    body: uploadData,
    headers: auth.getHeaders(),
    method: 'POST',
    credentials: 'include',
  })
  return await checkResponse(response)
}

export async function get(
  path: string,
  args?: Map<string, string | null | undefined>,
): Promise<Response> {
  const url = buildUrl(path, args)
  const response = await http('GET', url, undefined)
  checkResponse(response)
  return response
}
