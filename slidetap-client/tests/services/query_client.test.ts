//    Copyright 2026 SECTRA AB
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

import { MutationObserver, type MutationOptions } from '@tanstack/react-query'
import { describe, expect, it, vi } from 'vitest'
import { AuthenticationError } from 'src/services/api/api_methods'
import { createQueryClient } from 'src/services/query_client'

/** Runs a mutation that fails with `error` on a client reporting to `showError`. */
async function failMutation(
  showError: (message: string, error?: unknown) => void,
  error: unknown,
  options: Partial<MutationOptions<unknown, unknown, void>> = {},
): Promise<void> {
  const queryClient = createQueryClient(showError)
  const observer = new MutationObserver<unknown, unknown, void>(queryClient, {
    mutationFn: async () => {
      throw error
    },
    ...options,
  })
  await observer.mutate().catch(() => {})
}

describe('createQueryClient', () => {
  it('reports a failed mutation', async () => {
    // Arrange
    const showError = vi.fn()
    const error = new Error('Could not save the tag')

    // Act
    await failMutation(showError, error)

    // Assert
    expect(showError).toHaveBeenCalledExactlyOnceWith('Could not save the tag', error)
  })

  it('reports a failure that is not an error with a message of its own', async () => {
    // Arrange
    const showError = vi.fn()

    // Act
    await failMutation(showError, 'not an error')

    // Assert
    expect(showError).toHaveBeenCalledExactlyOnceWith('Request failed', 'not an error')
  })

  it('leaves a mutation with an onError of its own to report itself', async () => {
    // Arrange
    const showError = vi.fn()
    const onError = vi.fn()

    // Act
    await failMutation(showError, new Error('Could not save the tag'), { onError })

    // Assert
    expect(onError).toHaveBeenCalledOnce()
    expect(showError).not.toHaveBeenCalled()
  })

  it('leaves a mutation that says it handles the error to report itself', async () => {
    // Arrange
    const showError = vi.fn()

    // Act
    await failMutation(showError, new Error('Could not save the tag'), {
      meta: { handlesError: true },
    })

    // Assert
    expect(showError).not.toHaveBeenCalled()
  })

  it('does not report a request turned away as unauthenticated', async () => {
    // Arrange
    const showError = vi.fn()

    // Act
    await failMutation(showError, new AuthenticationError(401, 'Unauthorized'))

    // Assert
    expect(showError).not.toHaveBeenCalled()
  })
})
