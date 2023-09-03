import { post } from 'services/api/api_methods'

const loginApi = {
  login: async (username: string, password: string) => {
    return await post(
      'auth/login',
      {
        username,
        password,
      },
      false,
    )
  },

  logout: async () => {
    return await post('auth/logout')
  },

  keepAlive: async () => {
    return await post('auth/keepAlive')
  },
}

export default loginApi
