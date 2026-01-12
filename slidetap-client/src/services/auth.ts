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

import loginApi from 'src/services/api/login_api'

function getCookie(name: string): string {
  const cookieName = name + '='
  const decodedCookie = decodeURIComponent(document.cookie)
  const ca = decodedCookie.split(';')
  for (let i = 0; i < ca.length; i++) {
    let c = ca[i]
    while (c.charAt(0) === ' ') {
      c = c.substring(1)
    }
    if (c.indexOf(cookieName) === 0) {
      return c.substring(cookieName.length, c.length)
    }
  }
  return ''
}

const setLoggedIn = (): void => {
  localStorage.setItem('isLoggedIn', 'true')
}

const clearLoggedIn = (): void => {
  localStorage.removeItem('isLoggedIn')
}

const getLoggedIn = (): boolean => {
  const LoggedIn = localStorage.getItem('isLoggedIn')
  return LoggedIn !== null
}

const BasicAuth = {
  login: () => {
    setLoggedIn()
  },

  logout: () => {
    clearLoggedIn()
  },

  isLoggedIn: () => {
    return getLoggedIn()
  },

  getHeaders: () => {
    return {
      'X-CSRF-TOKEN': getCookie('csrf_token'),
    }
  },

  keepAlive: () => {
    if (!getLoggedIn()) return false
    loginApi.keepAlive().catch((x) => {
      console.error('Failed to send keep alive. Logging out user', x)
      BasicAuth.logout()
      return false
    })
    return true
  },

  /**
   * Initialize cross-tab synchronization for login/logout events.
   * Call this once when the app starts.
   */
  initCrossTabSync: () => {
    window.addEventListener('storage', (e) => {
      if (e.key === 'isLoggedIn' && e.newValue === null) {
        // User logged out in another tab
        console.log('Logout detected in another tab')
        window.location.reload()
      }
    })
  },
}

export default BasicAuth
