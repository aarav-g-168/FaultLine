import type { components } from './schema';

export type User = components['schemas']['UserOut'];
export type Tokens = components['schemas']['Tokens'];
export type Workspace = components['schemas']['WorkspaceOut'];
export type Project = components['schemas']['ProjectOut'];
export type Environment = components['schemas']['EnvironmentOut'];
export type Member = components['schemas']['MemberOut'];
export type Audit = components['schemas']['AuditOut'];
export type Registration = components['schemas']['Registration'];
export type Login = components['schemas']['Login'];
export type ProjectRole = components['schemas']['GrantInput']['role'];

export interface TokenVault {
  get(): Promise<string | null>;
  set(token: string): Promise<void>;
  clear(): Promise<void>;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

export class Client {
  private access: string | null = null;
  private rotating: Promise<Tokens> | null = null;
  onExpired: () => void = () => {};
  constructor(
    public baseUrl: string,
    private vault: TokenVault,
  ) {
    if (!/^https?:\/\//.test(baseUrl))
      throw new Error('Set EXPO_PUBLIC_API_URL to an HTTP(S) API URL.');
  }

  private async send<T>(
    path: string,
    method: string,
    body?: unknown,
    access?: string | null,
  ): Promise<T> {
    let response: Response;
    try {
      response = await fetch(this.baseUrl.replace(/\/$/, '') + path, {
        method,
        headers: {
          'Content-Type': 'application/json',
          ...(access ? { Authorization: `Bearer ${access}` } : {}),
        },
        body: body === undefined ? undefined : JSON.stringify(body),
        signal: AbortSignal.timeout(15000),
      });
    } catch {
      throw new ApiError(
        0,
        'Cannot reach Faultline. Check your connection and API address, then retry.',
      );
    }
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      const detail = error.detail;
      const message =
        typeof detail === 'string'
          ? detail
          : Array.isArray(detail)
            ? detail
                .map((issue: { loc: string[]; msg: string }) => `${issue.loc.at(-1)}: ${issue.msg}`)
                .join('\n')
            : `Request failed (${response.status}). Please retry.`;
      throw new ApiError(response.status, message);
    }
    return response.status === 204 ? (undefined as T) : response.json();
  }

  async authenticate(mode: 'login' | 'register', body: Registration | Login) {
    const tokens = await this.send<Tokens>('/auth/' + mode, 'POST', body);
    await this.vault.set(tokens.refresh_token);
    this.access = tokens.access_token;
    return tokens.user;
  }

  private async refresh() {
    if (!this.rotating) {
      this.rotating = (async () => {
        const token = await this.vault.get();
        if (!token) throw new ApiError(401, 'Please sign in to continue.');
        const tokens = await this.send<Tokens>('/auth/refresh', 'POST', { refresh_token: token });
        await this.vault.set(tokens.refresh_token);
        this.access = tokens.access_token;
        return tokens;
      })()
        .catch(async (error) => {
          if (error instanceof ApiError && error.status === 401) {
            this.access = null;
            await this.vault.clear();
            this.onExpired();
          }
          throw error;
        })
        .finally(() => {
          this.rotating = null;
        });
    }
    return this.rotating;
  }

  async restore(): Promise<User | null> {
    if (!(await this.vault.get())) return null;
    try {
      return (await this.refresh()).user;
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) return null;
      throw error;
    }
  }

  async request<T>(path: string, method = 'GET', body?: unknown): Promise<T> {
    const usedAccess = this.access;
    try {
      return await this.send<T>(path, method, body, usedAccess);
    } catch (error) {
      if (!(error instanceof ApiError) || error.status !== 401) throw error;
      // Another request may already have rotated. Reuse its result before refreshing again.
      if (this.access === usedAccess) await this.refresh();
      try {
        return await this.send<T>(path, method, body, this.access);
      } catch (retryError) {
        if (retryError instanceof ApiError && retryError.status === 401) {
          this.access = null;
          await this.vault.clear();
          this.onExpired();
        }
        throw retryError;
      }
    }
  }

  async logout() {
    const token = await this.vault.get();
    if (token) await this.send<void>('/auth/logout', 'POST', { refresh_token: token });
    this.access = null;
    await this.vault.clear();
  }

  workspaces = () => this.request<Workspace[]>('/workspaces');
  createWorkspace = (name: string) => this.request<Workspace>('/workspaces', 'POST', { name });
  projects = (id: string) => this.request<Project[]>(`/workspaces/${id}/projects`);
  createProject = (id: string, name: string) =>
    this.request<Project>(`/workspaces/${id}/projects`, 'POST', { name });
  environments = (id: string) => this.request<Environment[]>(`/projects/${id}/environments`);
  createEnvironment = (id: string, name: string) =>
    this.request<Environment>(`/projects/${id}/environments`, 'POST', { name });
  members = (id: string) => this.request<Member[]>(`/workspaces/${id}/members`);
  addMember = (id: string, email: string, role: 'admin' | 'member') =>
    this.request<Member>(`/workspaces/${id}/members`, 'POST', { email, role });
  removeMember = (id: string, user: string) =>
    this.request<void>(`/workspaces/${id}/members/${user}`, 'DELETE');
  grant = (project: string, user: string, role: ProjectRole) =>
    this.request(`/projects/${project}/grants/${user}`, 'PUT', { role });
  revoke = (project: string, user: string) =>
    this.request(`/projects/${project}/grants/${user}`, 'DELETE');
  audit = (id: string) => this.request<Audit[]>(`/workspaces/${id}/audit`);
}
