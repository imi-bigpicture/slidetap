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

function buildUrl(path: string, args?: Map<string, string | undefined>): string {
  let url = '/api/' + path
  if (args !== undefined) {
    let query = ''
    args.forEach((value, key) => {
      if (value === undefined || value === null || value === '') {
        return
      }
      if (query === '') {
        query += '?'
      } else {
        query += '&'
      }
      query += `${key}=${value}`
    })
    url += query
  }
  return url
}

async function http(
  method: string,
  url: string,
  data?: FormData | string,
  logoutOnFail: boolean = true,
  contentType: string = 'application/json',
): Promise<Response> {
  return await fetch(url, {
    body: data,
    headers: {
      'Content-Type': contentType,
      ...auth.getHeaders(),
    },
    method,
    credentials: 'include',
  }).then((response) => checkResponse(response, logoutOnFail))
}

function checkResponse(response: Response, logoutOnFail: boolean): Response {
  if (response.status === 422 || response.status === 401 || response.status === 403) {
    console.error('Got error', response.status, response.statusText)
    if (logoutOnFail) {
      auth.logout()
      window.location.reload()
    } else {
      throw new Error(response.statusText)
    }
  }
  return response
}

export async function post(
  path: string,
  data?: object,
  query?: Map<string, string | undefined>,
  logoutOnFail = true,
): Promise<Response> {
  const url = buildUrl(path, query)
  return await http('POST', url, JSON.stringify(data), logoutOnFail)
}

export async function delete_(path: string, logoutOnFail = true): Promise<Response> {
  const url = buildUrl(path)
  return await http('DELETE', url, undefined, logoutOnFail)
}

export async function postFile(
  path: string,
  file: File,
  logoutOnFail = true,
): Promise<Response> {
  const url = buildUrl(path)
  const uploadData = new FormData()
  uploadData.append('file', file)
  return await fetch(url, {
    body: uploadData,
    headers: auth.getHeaders(),
    method: 'POST',
    credentials: 'include',
  }).then((response) => checkResponse(response, logoutOnFail))
}

export async function get(
  path: string,
  args?: Map<string, string | undefined>,
  logoutOnFail = true,
): Promise<Response> {
  const url = buildUrl(path, args)
  return await http('GET', url, undefined, logoutOnFail)
}


export async function del(
  path: string,
  args? : Map<string, string>,
  logoutOnFail = true,
): Promise<Response> {
  const url = buildUrl(path, args)
  return await http('DELETE', url, undefined, logoutOnFail)
}
