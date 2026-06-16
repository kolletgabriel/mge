<script setup lang="ts">
import { onMounted, ref } from 'vue'

import {
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
const loading = ref(false)
const saving = ref(false)
const message = ref('')
const error = ref('')

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
        <p v-else-if="professors.length === 0" class="empty">
          Nenhum professor cadastrado ainda.
        </p>
        <table v-else>
          <tbody>
            <tr v-for="professor in professors" :key="professor.id">
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

@media (max-width: 760px) {
  label {
    grid-template-columns: 1fr;
  }

  .clear-selection {
    grid-column: 1;
  }
}
</style>
