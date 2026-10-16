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

/** Raised in this window when it logs in or out. Another window logging in or
 * out is told by the storage event instead. */
const AUTH_CHANGE_EVENT = 'slidetap-auth-change'

const setLoggedIn = (): void => {
  localStorage.setItem('isLoggedIn', 'true')
  window.dispatchEvent(new Event(AUTH_CHANGE_EVENT))
}

const clearLoggedIn = (): void => {
  localStorage.removeItem('isLoggedIn')
  window.dispatchEvent(new Event(AUTH_CHANGE_EVENT))
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

  /**
   * Call `listener` whenever this or another window logs in or out. Returns
   * the function that stops it, as `useSyncExternalStore` expects.
   */
  subscribe: (listener: () => void) => {
    const onStorage = (event: StorageEvent): void => {
      if (event.key === 'isLoggedIn' || event.key === null) {
        listener()
      }
    }
    window.addEventListener(AUTH_CHANGE_EVENT, listener)
    window.addEventListener('storage', onStorage)
    return () => {
      window.removeEventListener(AUTH_CHANGE_EVENT, listener)
      window.removeEventListener('storage', onStorage)
    }
  },

  getHeaders: () => {
    return {
      'X-CSRF-TOKEN': getCookie('csrf_token'),
    }
  },

  keepAlive: () => {
    if (!getLoggedIn()) return false
    return loginApi.keepAlive().then(() => true).catch((x) => {
      console.error('Failed to send keep alive. Logging out user', x)
      BasicAuth.logout()
      return false
    })
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
      }
    })
  },
}

export default BasicAuth
