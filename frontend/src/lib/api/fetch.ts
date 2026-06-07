/**
 * 自定义 API 错误类，用于携带后端返回的详细错误信息或 HTTP 状态码
 */
export class ApiError extends Error {
  public status: number;
  public details?: unknown;

  constructor(message: string, status: number, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}

interface FetchOptions extends RequestInit {
  timeoutMs?: number;
}

/**
 * 封装的底层 API Fetch 函数，包含：
 * - 默认 Headers 注入
 * - 统一错误处理与 JSON 转换
 * - 可选的超时控制
 */
export async function apiFetch<T>(url: string, options: FetchOptions = {}): Promise<T> {
  const { timeoutMs, headers, ...restOptions } = options;
  
  const controller = new AbortController();
  const id = timeoutMs ? setTimeout(() => controller.abort(), timeoutMs) : null;

  try {
    const response = await fetch(url, {
      ...restOptions,
      headers: {
        "Content-Type": "application/json",
        ...headers,
      },
      signal: controller.signal,
    });

    if (id) clearTimeout(id);

    // 解析 JSON
    let data;
    try {
      data = await response.json();
    } catch {
      data = null; // 可能返回 204 No Content，或者非 JSON
    }

    if (!response.ok) {
      // 提取后端的明确错误信息 (如 FastAPI 常见的 detail)
      const errorMessage = data?.detail || data?.error || data?.message || response.statusText;
      throw new ApiError(errorMessage, response.status, data);
    }

    return data as T;
  } catch (error: unknown) {
    if (id) clearTimeout(id);
    if (error instanceof Error && error.name === "AbortError") {
      throw new ApiError("Request Timeout", 408);
    }
    // 让自定义错误原样冒泡
    if (error instanceof ApiError) {
      throw error;
    }
    // 处理不可预知的网络错误 (如 CORS 失败, 断网)
    const message = error instanceof Error ? error.message : "Network Error";
    throw new ApiError(message, 0);
  }
}
