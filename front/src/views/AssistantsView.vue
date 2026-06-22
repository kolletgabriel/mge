<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import {
  associateAssistant,
  fetchClasses,
  fetchStudents,
  type AdminClass,
  type StudentRef,
} from '@/admin'
import AppShell from '@/components/AppShell.vue'

const classes = ref<AdminClass[]>([])
const students = ref<StudentRef[]>([])
const selectedClassId = ref<number | ''>('')
const selectedStudentIds = ref<number[]>([])
const viewedClass = ref<AdminClass | null>(null)
const loading = ref(false)
const saving = ref(false)
const message = ref('')
const error = ref('')

const selectedClass = computed(() => (
  selectedClassId.value === ''
    ? null
    : classes.value.find((class_) => class_.id === Number(selectedClassId.value)) ?? null
))

const availableStudents = computed(() => {
  const associatedIds = new Set(selectedClass.value?.assistants.map((assistant) => assistant.id) ?? [])
  return students.value.filter((student) => !associatedIds.has(student.id))
})

const canSubmit = computed(() => (
  selectedClass.value !== null
  && selectedStudentIds.value.length > 0
  && !saving.value
))

function assistantSummary(class_: AdminClass): string {
  if (class_.assistants.length === 0) {
    return 'Sem monitor associado'
  }

  if (class_.assistants.length === 1) {
    return class_.assistants[0]?.name ?? '1 monitor'
  }

  return `${class_.assistants.length} monitores`
}

async function loadData(): Promise<void> {
  loading.value = true
  error.value = ''

  try {
    const [classList, studentList] = await Promise.all([
      fetchClasses(),
      fetchStudents(),
    ])
    classes.value = classList
    students.value = studentList
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Não foi possível carregar os dados.'
  } finally {
    loading.value = false
  }
}

async function submitAssistants(): Promise<void> {
  if (!selectedClass.value || selectedStudentIds.value.length === 0) {
    return
  }

  saving.value = true
  error.value = ''
  message.value = ''

  try {
    const classId = selectedClass.value.id
    await Promise.all(
      selectedStudentIds.value.map((studentId) => associateAssistant(classId, Number(studentId))),
    )
    const classList = await fetchClasses()
    classes.value = classList
    selectedClassId.value = classList.some((class_) => class_.id === classId) ? classId : ''
    selectedStudentIds.value = []
    message.value = 'Monitores associados.'
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Não foi possível associar os monitores.'
  } finally {
    saving.value = false
  }
}

function openAssistantsPopup(class_: AdminClass): void {
  viewedClass.value = class_
  message.value = ''
  error.value = ''
}

function closeAssistantsPopup(): void {
  viewedClass.value = null
}

onMounted(loadData)
</script>

<template>
  <AppShell>
    <main class="admin-page">
      <section class="panel">
        <header>
          <div>
            <p class="eyebrow">Administração</p>
            <h1>Monitores</h1>
          </div>
        </header>

        <form class="entity-form" @submit.prevent="submitAssistants">
          <label>
            Disciplinas:
            <select v-model="selectedClassId" required @change="selectedStudentIds = []">
              <option value="" disabled>Selecione uma disciplina</option>
              <option v-for="class_ in classes" :key="class_.id" :value="class_.id">
                {{ class_.title }}
              </option>
            </select>
          </label>
          <label>
            Alunos:
            <select v-model="selectedStudentIds" multiple :disabled="!selectedClass">
              <option v-for="student in availableStudents" :key="student.id" :value="student.id">
                {{ student.name }} - {{ student.mail }}
              </option>
            </select>
            <button
              class="clear-selection"
              type="button"
              :disabled="selectedStudentIds.length === 0"
              @click="selectedStudentIds = []"
            >
              Limpar alunos selecionados
            </button>
          </label>
          <button class="submit-button" type="submit" :disabled="!canSubmit">
            {{ saving ? 'Salvando...' : 'Associar monitores' }}
          </button>
        </form>

        <p v-if="message" class="success" role="status">{{ message }}</p>
        <p v-if="error" class="error" role="alert">{{ error }}</p>

        <p v-if="loading" class="empty">Carregando monitores...</p>
        <p v-else-if="classes.length === 0" class="empty">
          Nenhuma disciplina cadastrada ainda.
        </p>
        <table v-else>
          <tbody>
            <tr
              v-for="class_ in classes"
              :key="class_.id"
              class="clickable-row"
              tabindex="0"
              @click="openAssistantsPopup(class_)"
              @keyup.enter="openAssistantsPopup(class_)"
            >
              <td>
                <strong>{{ class_.title }}</strong>
              </td>
              <td class="right">
                {{ assistantSummary(class_) }}
              </td>
            </tr>
          </tbody>
        </table>
      </section>

      <div v-if="viewedClass" class="modal-backdrop" @click.self="closeAssistantsPopup">
        <section class="modal-panel" role="dialog" aria-modal="true" aria-labelledby="assistants-modal-title">
          <header>
            <div>
              <p class="eyebrow">Monitores</p>
              <h2 id="assistants-modal-title">{{ viewedClass.title }}</h2>
            </div>
            <button class="close-button" type="button" @click="closeAssistantsPopup">Fechar</button>
          </header>

          <p v-if="viewedClass.assistants.length === 0" class="empty">
            Nenhum monitor associado.
          </p>
          <ul v-else class="assistant-list">
            <li v-for="assistant in viewedClass.assistants" :key="assistant.id">
              <strong>{{ assistant.name }}</strong>
              <span>{{ assistant.mail }}</span>
            </li>
          </ul>
        </section>
      </div>
    </main>
  </AppShell>
</template>

<style scoped>
.admin-page {
  padding: 1.5rem;
}

.panel {
  background: #fff;
  border: 1px solid #d9dfeb;
  display: grid;
  gap: 1rem;
  padding: 1.25rem;
}

.modal-panel {
  background: #fff;
  border: 1px solid #d9dfeb;
  box-shadow: 0 1.5rem 4rem rgb(0 0 0 / 0.24);
  display: grid;
  gap: 1.25rem;
  max-height: calc(100vh - 3rem);
  overflow: auto;
  padding: 1.25rem;
  width: min(42rem, calc(100vw - 2rem));
}

header {
  align-items: center;
  display: flex;
  justify-content: space-between;
}

.eyebrow {
  color: #526276;
  font-size: 0.8rem;
  font-weight: 800;
  letter-spacing: 0.12em;
  margin: 0 0 0.2rem;
  text-transform: uppercase;
}

h1,
h2 {
  color: #032562;
  margin: 0;
}

.entity-form {
  display: grid;
  gap: 0.9rem;
  justify-self: center;
  max-width: 32rem;
  width: min(100%, 32rem);
}

label {
  align-items: start;
  display: grid;
  font-size: 0.9rem;
  font-weight: 800;
  gap: 0.35rem;
  grid-template-columns: 8rem minmax(0, 1fr);
}

select {
  border: 1px solid #b7c0cf;
  font: inherit;
  padding: 0.7rem;
}

select[multiple] {
  min-height: 7rem;
}

select:disabled {
  background: #f4f6fb;
  color: #8b97a8;
}

.submit-button {
  justify-self: center;
  background: #032562;
  border: 0;
  color: #fff;
  cursor: pointer;
  font: inherit;
  font-weight: 800;
  padding: 0.8rem 1rem;
}

.submit-button:disabled {
  cursor: default;
  opacity: 0.7;
}

.close-button,
.clear-selection {
  background: #eef2f7;
  border: 1px solid #c9d2df;
  color: #314156;
  cursor: pointer;
  font: inherit;
  font-weight: 800;
  padding: 0.55rem 0.7rem;
}

.clear-selection {
  grid-column: 2;
  justify-self: start;
  font-size: 0.85rem;
}

.clear-selection:disabled {
  color: #8b97a8;
  cursor: default;
  opacity: 0.65;
}

.success,
.error,
.empty {
  margin: 0;
  padding: 0.75rem;
}

.success {
  background: #eef8f0;
  color: #1d6630;
}

.error {
  background: #fff0f0;
  color: #8b1e1e;
}

.empty {
  background: #f4f6fb;
  color: #526276;
}

table {
  border-collapse: collapse;
  width: 100%;
}

tr {
  border-top: 1px solid #e2e7f0;
}

td {
  padding: 0.7rem 0;
}

.right {
  color: #526276;
  font-size: 0.9rem;
  text-align: right;
}

.clickable-row {
  cursor: pointer;
}

.clickable-row:focus,
.clickable-row:hover {
  background: #f4f6fb;
  outline: none;
}

.modal-backdrop {
  align-items: center;
  background: rgb(3 37 98 / 0.48);
  display: flex;
  inset: 0;
  justify-content: center;
  padding: 1rem;
  position: fixed;
  z-index: 10;
}

.assistant-list {
  display: grid;
  gap: 0.6rem;
  list-style: none;
  margin: 0;
  padding: 0;
}

.assistant-list li {
  border-top: 1px solid #e2e7f0;
  padding: 0.75rem 0 0;
}

.assistant-list strong,
.assistant-list span {
  display: block;
}

.assistant-list span {
  color: #526276;
  font-size: 0.9rem;
  margin-top: 0.15rem;
}

@media (max-width: 760px) {
  label {
    grid-template-columns: 1fr;
  }

  .clear-selection {
    grid-column: 1;
  }
}
</style>
