import { readonly, ref } from 'vue'

type RoleName = 'admin' | 'student' | 'professor'

type ClassRef = {
  id: number
  title: string
}

type AdminUser = {
  id: number
  mail: string
  name: string
  role: 'admin'
  rid: 0
  scope: { global: boolean }
}

type StudentUser = {
  id: number
  mail: string
  name: string
  role: 'student'
  rid: 1
  scope: { assistant_for: ClassRef[] }
}

type ProfessorUser = {
  id: number
  mail: string
  name: string
  role: 'professor'
  rid: 2
  scope: { classes: ClassRef[] }
}

export type CurrentUser = AdminUser | StudentUser | ProfessorUser

type Credentials = {
  mail: string
  password: string
}

type Registration = Credentials & {
  name: string
}

const user = ref<CurrentUser | null>(null)
const initialized = ref(false)

async function parseCurrentUser(res: Response): Promise<CurrentUser> {
  return await res.json() as CurrentUser
}

async function requestCurrentUser(): Promise<CurrentUser | null> {
  const res = await fetch('/api/me')

  if (res.status === 401) {
    return null
  }

  if (!res.ok) {
    throw new Error('Não foi possível carregar o usuário atual.')
  }

  return await parseCurrentUser(res)
}

export async function ensureCurrentUser(): Promise<CurrentUser | null> {
  if (!initialized.value) {
    user.value = await requestCurrentUser()
    initialized.value = true
  }

  return user.value
}

export async function login(credentials: Credentials): Promise<CurrentUser> {
  const res = await fetch('/api/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(credentials),
  })

  if (res.status === 401) {
    throw new Error('E-mail ou senha inválidos.')
  }

  if (!res.ok) {
    throw new Error('Não foi possível entrar agora.')
  }

  user.value = await parseCurrentUser(res)
  initialized.value = true

  return user.value
}

export async function register(registration: Registration): Promise<CurrentUser> {
  const res = await fetch('/api/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(registration),
  })

  if (res.status === 409) {
    throw new Error('Este e-mail já está cadastrado.')
  }

  if (res.status === 422) {
    throw new Error('Revise os dados do cadastro.')
  }

  if (!res.ok) {
    throw new Error('Não foi possível criar a conta agora.')
  }

  user.value = await parseCurrentUser(res)
  initialized.value = true

  return user.value
}

export async function logout(): Promise<void> {
  const res = await fetch('/api/logout', { method: 'POST' })

  if (!res.ok) {
    throw new Error('Não foi possível sair agora.')
  }

  user.value = null
  initialized.value = true
}

export function roleTitle(role: RoleName): string {
  return {
    admin: 'Administrador',
    student: 'Aluno',
    professor: 'Professor',
  }[role]
}

export const currentUser = readonly(user)
