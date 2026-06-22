<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import {
  associateProfessor,
  createProfessor,
  fetchClasses,
  fetchProfessors,
  type AdminClass,
  type AdminProfessor,
} from '@/admin'
import AppShell from '@/components/AppShell.vue'

const professors = ref<AdminProfessor[]>([])
const classes = ref<AdminClass[]>([])
const name = ref('')
const mail = ref('')
const selectedClassIds = ref<number[]>([])
const editingProfessor = ref<AdminProfessor | null>(null)
const professorPopupMode = ref<'current' | 'add'>('current')
const popupClassIds = ref<number[]>([])
const loading = ref(false)
const loadingPopup = ref(false)
const saving = ref(false)
const savingAssociations = ref(false)
const message = ref('')
const error = ref('')

const availablePopupClasses = computed(() => {
  const associatedIds = new Set(editingProfessor.value?.classes.map((class_) => class_.id) ?? [])
  return classes.value.filter((class_) => !associatedIds.has(class_.id))
})

function initials(professor: AdminProfessor): string {
  return professor.name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('') || 'PR'
}

async function loadData(): Promise<void> {
  loading.value = true
  error.value = ''

  try {
    const [professorList, classList] = await Promise.all([
      fetchProfessors(),
      fetchClasses(),
    ])
    professors.value = professorList
    classes.value = classList
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Não foi possível carregar os dados.'
  } finally {
    loading.value = false
  }
}

async function submitProfessor(): Promise<void> {
  saving.value = true
  error.value = ''
  message.value = ''

  try {
    const professor = await createProfessor(name.value, mail.value, selectedClassIds.value.map(Number))
    professors.value = [...professors.value, professor]
    name.value = ''
    mail.value = ''
    selectedClassIds.value = []
    message.value = 'Professor cadastrado.'
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Não foi possível cadastrar o professor.'
  } finally {
    saving.value = false
  }
}

async function openProfessorPopup(professor: AdminProfessor): Promise<void> {
  loadingPopup.value = true
  popupClassIds.value = []
  message.value = ''
  error.value = ''

  try {
    const [professorList, classList] = await Promise.all([
      fetchProfessors(),
      fetchClasses(),
    ])
    professors.value = professorList
    classes.value = classList
    editingProfessor.value = professorList.find((freshProfessor) => freshProfessor.id === professor.id) ?? null
    professorPopupMode.value = 'current'

    if (!editingProfessor.value) {
      error.value = 'Não foi possível encontrar o professor selecionado.'
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Não foi possível carregar as associações.'
  } finally {
    loadingPopup.value = false
  }
}

function closeProfessorPopup(): void {
  editingProfessor.value = null
  professorPopupMode.value = 'current'
  popupClassIds.value = []
}

async function submitProfessorAssociations(): Promise<void> {
  if (!editingProfessor.value) {
    return
  }

  savingAssociations.value = true
  error.value = ''
  message.value = ''

  try {
    const professorId = editingProfessor.value.id
    await Promise.all(
      popupClassIds.value.map((classId) => associateProfessor(Number(classId), professorId)),
    )
    const [professorList, classList] = await Promise.all([
      fetchProfessors(),
      fetchClasses(),
    ])
    professors.value = professorList
    classes.value = classList
    closeProfessorPopup()
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
            <h1>Professores</h1>
          </div>
        </header>

        <form class="entity-form" @submit.prevent="submitProfessor">
          <label>
            Nome
            <input v-model="name" maxlength="100" required type="text">
          </label>
          <label>
            E-mail
            <input v-model="mail" maxlength="320" required type="email">
          </label>
          <label>
            Associar disciplinas:
            <select v-model="selectedClassIds" multiple>
              <option v-for="class_ in classes" :key="class_.id" :value="class_.id">
                {{ class_.title }}
              </option>
            </select>
            <button
              class="clear-selection"
              type="button"
              :disabled="selectedClassIds.length === 0"
              @click="selectedClassIds = []"
            >
              Limpar disciplinas selecionadas
            </button>
          </label>
          <button class="submit-button" type="submit" :disabled="saving">
            {{ saving ? 'Salvando...' : 'Cadastrar professor' }}
          </button>
        </form>

        <p v-if="message" class="success" role="status">{{ message }}</p>
        <p v-if="error" class="error" role="alert">{{ error }}</p>

        <p v-if="loading" class="empty">Carregando professores...</p>
        <p v-else-if="loadingPopup" class="empty">Atualizando associações...</p>
        <p v-else-if="professors.length === 0" class="empty">
          Nenhum professor cadastrado ainda.
        </p>
        <table v-else>
          <thead>
            <tr>
              <th>Professor</th>
              <th class="right">Disciplina</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="professor in professors"
              :key="professor.id"
              class="clickable-row"
              tabindex="0"
              @click="openProfessorPopup(professor)"
              @keyup.enter="openProfessorPopup(professor)"
            >
              <td>
                <div class="person">
                  <div class="avatar" aria-hidden="true">{{ initials(professor) }}</div>
                  <div>
                    <strong>{{ professor.name }}</strong>
                    <span>{{ professor.mail }}</span>
                  </div>
                </div>
              </td>
              <td class="right">
                {{ professor.classes[0]?.title ?? 'Sem disciplina associada' }}
              </td>
            </tr>
          </tbody>
        </table>
      </section>

      <div v-if="editingProfessor" class="modal-backdrop" @click.self="closeProfessorPopup">
        <section class="modal-panel" role="dialog" aria-modal="true" aria-labelledby="professor-modal-title">
          <header>
            <div>
              <p class="eyebrow">Associações</p>
              <h2 id="professor-modal-title">{{ editingProfessor.name }}</h2>
            </div>
            <div class="mode-actions">
              <button
                class="mode-button"
                :class="{ active: professorPopupMode === 'current' }"
                type="button"
                @click="professorPopupMode = 'current'"
              >
                Atuais
              </button>
              <button
                class="mode-button"
                :class="{ active: professorPopupMode === 'add' }"
                type="button"
                @click="professorPopupMode = 'add'"
              >
                Adicionar
              </button>
            </div>
            <button class="close-button" type="button" @click="closeProfessorPopup">Fechar</button>
          </header>

          <div class="modal-body">
            <section v-if="professorPopupMode === 'current'" class="association-summary">
              <h3>Disciplinas associadas</h3>
              <p v-if="editingProfessor.classes.length === 0" class="summary-empty">
                Nenhuma disciplina associada.
              </p>
              <ul v-else class="association-list">
                <li v-for="class_ in editingProfessor.classes" :key="class_.id">
                  <strong>{{ class_.title }}</strong>
                </li>
              </ul>
            </section>

            <form v-else class="entity-form" @submit.prevent="submitProfessorAssociations">
              <label>
                Associar disciplinas:
                <select v-model="popupClassIds" multiple>
                  <option v-for="class_ in availablePopupClasses" :key="class_.id" :value="class_.id">
                    {{ class_.title }}
                  </option>
                </select>
                <button
                  class="clear-selection"
                  type="button"
                  :disabled="popupClassIds.length === 0"
                  @click="popupClassIds = []"
                >
                  Limpar disciplinas selecionadas
                </button>
              </label>
              <button class="submit-button" type="submit" :disabled="savingAssociations">
                {{ savingAssociations ? 'Salvando...' : 'Salvar associações' }}
              </button>
            </form>
          </div>
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
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  max-height: min(36rem, calc(100vh - 3rem));
  overflow: hidden;
  padding: 1.25rem;
  width: min(40rem, calc(100vw - 2rem));
}

.modal-panel > header {
  border-bottom: 1px solid #d9dfeb;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  padding-bottom: 1rem;
}

.modal-body {
  min-height: 0;
  overflow-y: auto;
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
  align-self: start;
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

.mode-actions {
  align-items: center;
  display: flex;
  gap: 0.25rem;
  justify-self: center;
}

.mode-button {
  background: transparent;
  border: 0;
  color: #032562;
  cursor: pointer;
  font: inherit;
  font-size: 0.74rem;
  font-weight: 800;
  padding: 0.32rem 0.5rem;
}

.mode-button.active {
  background: #032562;
  color: #fff;
}

.close-button {
  justify-self: end;
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
  margin-top: 0.45rem;
  width: 100%;
}

tr {
  border-top: 1px solid #e2e7f0;
}

thead tr {
  border-top: 0;
}

th {
  color: #526276;
  font-size: 0.78rem;
  letter-spacing: 0.08em;
  padding: 0 0 0.7rem;
  text-align: left;
  text-transform: uppercase;
}

th.right {
  color: #526276;
  font-size: 0.78rem;
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
  padding: 0.55rem 0;
}

.person {
  align-items: center;
  display: flex;
  gap: 0.7rem;
}

.avatar {
  align-items: center;
  aspect-ratio: 1;
  background: #032562;
  color: #fff;
  display: grid;
  flex: 0 0 2rem;
  font-size: 0.78rem;
  font-weight: 900;
  place-items: center;
}

.person strong,
.person span {
  display: block;
}

.person span,
.right {
  color: #526276;
  font-size: 0.9rem;
}

.right {
  text-align: right;
}

.association-summary {
  display: grid;
  gap: 0.5rem;
}

h3 {
  color: #10213d;
  font-size: 1.05rem;
  font-weight: 900;
  margin: 0;
}

.summary-empty {
  background: #f4f6fb;
  color: #526276;
  margin: 0;
  padding: 0.7rem;
}

.association-list {
  display: grid;
  gap: 0.45rem;
  font-size: 0.9rem;
  list-style: none;
  margin: 0;
  padding: 0;
}

.association-list li {
  border-top: 1px solid #e2e7f0;
  padding-top: 0.6rem;
}

.modal-backdrop {
  align-items: flex-start;
  background: rgb(3 37 98 / 0.48);
  display: flex;
  inset: 0;
  justify-content: center;
  padding: max(1.5rem, calc((100vh - 36rem) / 2)) 1rem 1rem;
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

  .mode-actions {
    justify-self: start;
  }

  .modal-panel > header {
    gap: 0.75rem;
    grid-template-columns: 1fr;
  }

  .close-button {
    justify-self: start;
  }
}
</style>
