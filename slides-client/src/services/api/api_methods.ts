import auth from 'services/auth'

function buildUrl (path: string, args?: Map<string, string>): string {
    let url = '/api/' + path
    if (args !== undefined) {
        let query = ''
        args.forEach((value, key) => {
            if (query === '') {
                query += '?'
            } else {
                query += '&'
            }
            query += `${key}=${value}`
        })
        url += query
    }
    console.log(url)
    return url
}

async function http (
    method: string,
    url: string,
    data?: FormData | string,
    logoutOnFail: boolean = true,
    contentType: string = 'application/json'
): Promise<Response> {
    return await fetch(url, {
        body: data,
        headers: {
            'Content-Type': contentType,
            ...auth.getHeaders()
        },
        method,
        credentials: 'include'
    })
        .then(response => checkResponse(response, logoutOnFail))
}

function checkResponse (response: Response, logoutOnFail: boolean): Response {
    if (response.status === 422 || response.status === 401) {
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

export async function post (
    path: string,
    data?: any,
    logoutOnFail = true
): Promise<Response> {
    const url = buildUrl(path)
    return await http('POST', url, JSON.stringify(data), logoutOnFail)
}

export async function postFile (
    path: string,
    file: File,
    logoutOnFail = true
): Promise<Response> {
    const url = buildUrl(path)
    const uploadData = new FormData()
    uploadData.append('file', file)
    return await fetch(url, {
        body: uploadData,
        headers: auth.getHeaders(),
        method: 'POST',
        credentials: 'include'
    })
        .then(response => checkResponse(response, logoutOnFail))
}

export async function get (
    path: string,
    args?: Map<string, string>,
    logoutOnFail = true
): Promise<Response> {
    const url = buildUrl(path, args)
    return await http('GET', url, undefined, logoutOnFail)
}
