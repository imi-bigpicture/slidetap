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

import { renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useObjectUrl } from 'src/hooks/use_object_url'

describe('useObjectUrl', () => {
  let createdUrls: string[]

  beforeEach(() => {
    createdUrls = []
    // jsdom has no object URLs, so each blob is given one of its own.
    vi.spyOn(URL, 'createObjectURL').mockImplementation(() => {
      const url = `blob:test/${createdUrls.length}`
      createdUrls.push(url)
      return url
    })
    vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {})
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('makes a url for the blob', () => {
    // Arrange
    const blob = new Blob(['image'])

    // Act
    const { result } = renderHook(() => useObjectUrl(blob))

    // Assert
    expect(result.current).toBe('blob:test/0')
  })

  it('has no url without a blob', () => {
    // Act
    const { result } = renderHook(() => useObjectUrl(undefined))

    // Assert
    expect(result.current).toBeUndefined()
    expect(URL.createObjectURL).not.toHaveBeenCalled()
  })

  it('makes the url once for a blob shown again', () => {
    // Arrange
    const blob = new Blob(['image'])
    const { rerender } = renderHook(({ shown }) => useObjectUrl(shown), {
      initialProps: { shown: blob },
    })

    // Act
    rerender({ shown: blob })

    // Assert
    expect(URL.createObjectURL).toHaveBeenCalledTimes(1)
    expect(URL.revokeObjectURL).not.toHaveBeenCalled()
  })

  it('revokes the url of a blob no longer shown', () => {
    // Arrange
    const { result, rerender } = renderHook(({ shown }) => useObjectUrl(shown), {
      initialProps: { shown: new Blob(['first']) },
    })

    // Act
    rerender({ shown: new Blob(['second']) })

    // Assert
    expect(URL.revokeObjectURL).toHaveBeenCalledExactlyOnceWith('blob:test/0')
    expect(result.current).toBe('blob:test/1')
  })

  it('shows a url that is not revoked under StrictMode', () => {
    // Arrange
    const blob = new Blob(['image'])

    // Act
    const { result } = renderHook(() => useObjectUrl(blob), { reactStrictMode: true })

    // Assert
    expect(result.current).toBeDefined()
    expect(URL.revokeObjectURL).not.toHaveBeenCalledWith(result.current)
  })

  it('revokes the url when unmounted', () => {
    // Arrange
    const blob = new Blob(['image'])
    const { unmount } = renderHook(() => useObjectUrl(blob))

    // Act
    unmount()

    // Assert
    expect(URL.revokeObjectURL).toHaveBeenCalledExactlyOnceWith('blob:test/0')
  })
})
