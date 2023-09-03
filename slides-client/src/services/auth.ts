import loginApi from 'services/api/login_api'

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
  sessionStorage.setItem('isLoggedIn', 'true')
}

const clearLoggedIn = (): void => {
  sessionStorage.removeItem('isLoggedIn')
}

const getLoggedIn = (): boolean => {
  const LoggedIn = sessionStorage.getItem('isLoggedIn')
  return LoggedIn !== null
}

const SectraAuth = {
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
      'X-CSRF-TOKEN': getCookie('csrf_access_token'),
    }
  },

  keepAlive: () => {
    if (!getLoggedIn()) return
    loginApi.keepAlive().catch((x) => {
      console.error('Failed to send keep alive. Logging out user', x)
      SectraAuth.logout()
    })
  },
}

export default SectraAuth
