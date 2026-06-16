<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import {
  associateAssistant,
  associateProfessor,
  createClass,
  fetchClasses,
  fetchProfessors,
  fetchStudents,
  type AdminClass,
  type AdminProfessor,
  type StudentRef,
} from '@/admin'
import AppShell from '@/components/AppShell.vue'

const classes = ref<AdminClass[]>([])
const professors = ref<AdminProfessor[]>([])
const students = ref<StudentRef[]>([])
const title = ref('')
const selectedProfessorIds = ref<number[]>([])
const selectedAssistantIds = ref<number[]>([])
const editingClass = ref<AdminClass | null>(null)
const popupProfessorIds = ref<number[]>([])
const popupAssistantIds = ref<number[]>([])
const loading = ref(false)
const loadingPopup = ref(false)
const saving = ref(false)
const savingAssociations = ref(false)
const message = ref('')
const error = ref('')

const availablePopupProfessors = computed(() => {
  const associatedIds = new Set(editingClass.value?.professors.map((professor) => professor.id) ?? [])
  return professors.value.filter((professor) => !associatedIds.has(professor.id))
})

const availablePopupAssistants = computed(() => {
  const associatedIds = new Set(editingClass.value?.assistants.map((assistant) => assistant.id) ?? [])
  return students.value.filter((student) => !associatedIds.has(student.id))
})

async function loadData(): Promise<void> {
  loading.value = true
  error.value = ''

  try {
    const [classList, professorList, studentList] = await Promise.all([
      fetchClasses(),
      fetchProfessors(),
      fetchStudents(),
    ])
    classes.value = classList
    professors.value = professorList
    students.value = studentList
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Não foi possível carregar os dados.'
  } finally {
    loading.value = false
  }
}

async function submitClass(): Promise<void> {
  saving.value = true
  error.value = ''
  message.value = ''

  try {
    const class_ = await createClass(
      title.value,
      selectedProfessorIds.value.map(Number),
      selectedAssistantIds.value.map(Number),
    )
    classes.value = [...classes.value, class_]
    title.value = ''
    selectedProfessorIds.value = []
    selectedAssistantIds.value = []
    message.value = 'Disciplina cadastrada.'
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Não foi possível cadastrar a disciplina.'
  } finally {
    saving.value = false
  }
}

async function openClassPopup(class_: AdminClass): Promise<void> {
  loadingPopup.value = true
  popupProfessorIds.value = []
  popupAssistantIds.value = []
  message.value = ''
  error.value = ''

  try {
    const [classList, professorList, studentList] = await Promise.all([
      fetchClasses(),
      fetchProfessors(),
      fetchStudents(),
    ])
    classes.value = classList
    professors.value = professorList
    students.value = studentList
    editingClass.value = classList.find((freshClass) => freshClass.id === class_.id) ?? null

    if (!editingClass.value) {
      error.value = 'Não foi possível encontrar a disciplina selecionada.'
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Não foi possível carregar as associações.'
  } finally {
    loadingPopup.value = false
  }
}

function closeClassPopup(): void {
  editingClass.value = null
  popupProfessorIds.value = []
  popupAssistantIds.value = []
}

async function submitClassAssociations(): Promise<void> {
  if (!editingClass.value) {
    return
  }

  savingAssociations.value = true
  error.value = ''
  message.value = ''

  try {
    const classId = editingClass.value.id
    await Promise.all([
      ...popupProfessorIds.value.map((professorId) => associateProfessor(classId, Number(professorId))),
      ...popupAssistantIds.value.map((assistantId) => associateAssistant(classId, Number(assistantId))),
    ])
    classes.value = await fetchClasses()
    closeClassPopup()
    message.value = 'Associações atualizadas.'
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Não foi possível atualizar as associações.'
  } finally {
    savingAssociations.value = false
  }
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
            <h1>Disciplinas</h1>
          </div>
        </header>

        <form class="entity-form" @submit.prevent="submitClass">
          <label>
            Título
            <input v-model="title" maxlength="255" required type="text">
          </label>
          <label>
            Associar professores:
            <select v-model="selectedProfessorIds" multiple>
              <option v-for="professor in professors" :key="professor.id" :value="professor.id">
                {{ professor.name }} - {{ professor.mail }}
              </option>
            </select>
            <button
              class="clear-selection"
              type="button"
              :disabled="selectedProfessorIds.length === 0"
              @click="selectedProfessorIds = []"
            >
              Limpar professores selecionados
            </button>
          </label>
          <label>
            Associar monitores:
            <select v-model="selectedAssistantIds" multiple>
              <option v-for="student in students" :key="student.id" :value="student.id">
                {{ student.name }} - {{ student.mail }}
              </option>
            </select>
            <button
              class="clear-selection"
              type="button"
              :disabled="selectedAssistantIds.length === 0"
              @click="selectedAssistantIds = []"
            >
              Limpar monitores selecionados
            </button>
          </label>
          <button class="submit-button" type="submit" :disabled="saving">
            {{ saving ? 'Salvando...' : 'Cadastrar disciplina' }}
          </button>
        </form>

        <p v-if="message" class="success" role="status">{{ message }}</p>
        <p v-if="error" class="error" role="alert">{{ error }}</p>

        <p v-if="loading" class="empty">Carregando disciplinas...</p>
        <p v-else-if="loadingPopup" class="empty">Atualizando associações...</p>
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
              @click="openClassPopup(class_)"
              @keyup.enter="openClassPopup(class_)"
            >
              <td>
                <strong>{{ class_.title }}</strong>
              </td>
              <td class="right">
                {{ class_.professors[0]?.name ?? 'Sem professor associado' }}
              </td>
            </tr>
          </tbody>
        </table>
      </section>

      <div v-if="editingClass" class="modal-backdrop" @click.self="closeClassPopup">
        <section class="modal-panel" role="dialog" aria-modal="true" aria-labelledby="class-modal-title">
          <header>
            <div>
              <p class="eyebrow">Associações</p>
              <h2 id="class-modal-title">{{ editingClass.title }}</h2>
            </div>
            <button class="close-button" type="button" @click="closeClassPopup">Fechar</button>
          </header>

          <form class="entity-form" @submit.prevent="submitClassAssociations">
            <label>
              Associar professores:
              <select v-model="popupProfessorIds" multiple>
                <option v-for="professor in availablePopupProfessors" :key="professor.id" :value="professor.id">
                  {{ professor.name }} - {{ professor.mail }}
                </option>
              </select>
              <button
                class="clear-selection"
                type="button"
                :disabled="popupProfessorIds.length === 0"
                @click="popupProfessorIds = []"
              >
                Limpar professores selecionados
              </button>
            </label>
            <label>
              Associar monitores:
              <select v-model="popupAssistantIds" multiple>
                <option v-for="student in availablePopupAssistants" :key="student.id" :value="student.id">
                  {{ student.name }} - {{ student.mail }}
                </option>
              </select>
              <button
                class="clear-selection"
                type="button"
                :disabled="popupAssistantIds.length === 0"
                @click="popupAssistantIds = []"
              >
                Limpar monitores selecionados
              </button>
            </label>
            <button class="submit-button" type="submit" :disabled="savingAssociations">
              {{ savingAssociations ? 'Salvando...' : 'Salvar associações' }}
            </button>
          </form>
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

h1 {
  color: #032562;
  margin: 0;
}

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

input,
select {
  border: 1px solid #b7c0cf;
  font: inherit;
  padding: 0.7rem;
}

select {
  min-height: 7rem;
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
  cursor: wait;
  opacity: 0.7;
}

.close-button {
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
  background: #eef2f7;
  border: 1px solid #c9d2df;
  color: #314156;
  cursor: pointer;
  font: inherit;
  font-size: 0.85rem;
  font-weight: 800;
  padding: 0.55rem 0.7rem;
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

.clickable-row {
  cursor: pointer;
}

.clickable-row:focus,
.clickable-row:hover {
  background: #f4f6fb;
  outline: none;
}

td {
  padding: 0.7rem 0;
}

.right {
  color: #526276;
  font-size: 0.9rem;
  text-align: right;
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

@media (max-width: 760px) {
  label {
    grid-template-columns: 1fr;
  }

  .clear-selection {
    grid-column: 1;
  }
}
</style>
