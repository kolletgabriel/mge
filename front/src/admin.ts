export type ClassRef = {
  id: number
  title: string
}

export type ProfessorRef = {
  id: number
  mail: string
  name: string
}

export type StudentRef = {
  id: number
  mail: string
  name: string
}

export type AdminClass = ClassRef & {
  professors: ProfessorRef[]
  assistants: StudentRef[]
}

export type AdminProfessor = ProfessorRef & {
  role_id: 2
  role_title: 'Professor'
  classes: ClassRef[]
}

async function parseJson<T>(res: Response, conflictMessage?: string): Promise<T> {
  if (res.status === 409 && conflictMessage) {
    throw new Error(conflictMessage)
  }

  if (!res.ok) {
    throw new Error('Não foi possível completar a operação.')
  }

  return await res.json() as T
}

export async function fetchClasses(): Promise<AdminClass[]> {
  return await parseJson(await fetch('/api/classes'))
}

export async function fetchProfessors(): Promise<AdminProfessor[]> {
  return await parseJson(await fetch('/api/professors'))
}

export async function fetchStudents(): Promise<StudentRef[]> {
  return await parseJson(await fetch('/api/students'))
}

export async function createClass(
  title: string,
  professorIds: number[],
  assistantIds: number[],
): Promise<AdminClass> {
  return await parseJson(await fetch('/api/classes', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      title,
      professor_ids: professorIds,
      assistant_ids: assistantIds,
    }),
  }), 'Já existe uma disciplina com este título')
}

export async function createProfessor(
  name: string,
  mail: string,
  classIds: number[],
): Promise<AdminProfessor> {
  return await parseJson(await fetch('/api/professors', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, mail, class_ids: classIds }),
  }), 'Já existe um professor com este email')
}

export async function associateProfessor(classId: number, professorId: number): Promise<void> {
  await parseJson(await fetch(`/api/classes/${classId}/professors`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ professor_id: professorId }),
  }))
}

export async function associateAssistant(classId: number, studentId: number): Promise<void> {
  await parseJson(await fetch(`/api/classes/${classId}/assistants`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ student_id: studentId }),
  }))
}
