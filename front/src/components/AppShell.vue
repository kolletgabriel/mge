<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'

import { currentUser, logout } from '@/auth'

const router = useRouter()
const logoutError = ref('')
const logoutLoading = ref(false)

const initials = computed(() => {
  const name = currentUser.value?.name.trim()

  if (!name) {
    return 'MG'
  }

  return name
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('')
})

async function submitLogout(): Promise<void> {
  logoutLoading.value = true
  logoutError.value = ''

  try {
    await logout()
    await router.push({ name: 'auth' })
  } catch (error) {
    logoutError.value = error instanceof Error ? error.message : 'Não foi possível sair.'
  } finally {
    logoutLoading.value = false
  }
}
</script>

<template>
  <div v-if="currentUser" class="shell">
    <aside class="sidebar" aria-label="Usuário">
      <section class="user-card">
        <div class="avatar" aria-hidden="true">{{ initials }}</div>
        <div>
          <strong>{{ currentUser.name }}</strong>
          <span>{{ currentUser.role_title }}</span>
        </div>
      </section>

      <button class="logout" type="button" :disabled="logoutLoading" @click="submitLogout">
        {{ logoutLoading ? 'Saindo...' : 'Sair' }}
      </button>
      <p v-if="logoutError" class="logout-error" role="alert">{{ logoutError }}</p>
    </aside>

    <div class="main-area">
      <nav class="topbar" aria-label="Principal">
        <RouterLink to="/">Home</RouterLink>
        <RouterLink v-if="currentUser.role_id !== 1" to="/dashboards">Dashboards</RouterLink>
        <RouterLink v-if="currentUser.role_id === 0" to="/professores">Professores</RouterLink>
        <RouterLink v-if="currentUser.role_id === 0" to="/disciplinas">Disciplinas</RouterLink>
      </nav>

      <slot />
    </div>
  </div>
</template>

<style scoped>
.shell {
  background: #f4f6fb;
  color: #10213d;
  display: grid;
  grid-template-columns: 18rem minmax(0, 1fr);
  min-height: 100vh;
}

.sidebar {
  background: #032562;
  color: #fff;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  height: 100vh;
  overflow: auto;
  padding: 1.25rem;
  position: sticky;
  top: 0;
}

.user-card {
  align-items: center;
  border: 1px solid rgb(255 255 255 / 0.22);
  display: flex;
  gap: 0.9rem;
  padding: 1rem;
}

.avatar {
  align-items: center;
  aspect-ratio: 1;
  background: #fff;
  color: #032562;
  display: grid;
  flex: 0 0 3.5rem;
  font-weight: 800;
  place-items: center;
}

.user-card strong,
.user-card span {
  display: block;
}

.user-card span {
  color: rgb(255 255 255 / 0.74);
  font-size: 0.9rem;
  margin-top: 0.2rem;
}

.logout {
  background: #fff;
  border: 0;
  color: #032562;
  cursor: pointer;
  font: inherit;
  font-weight: 800;
  margin-top: auto;
  padding: 0.8rem 1rem;
}

.logout:disabled {
  cursor: wait;
  opacity: 0.72;
}

.logout-error {
  background: rgb(255 255 255 / 0.12);
  margin: 0;
  padding: 0.75rem;
}

.main-area {
  display: grid;
  grid-template-rows: auto 1fr;
  min-width: 0;
}

.topbar {
  align-items: center;
  background: #fff;
  border-bottom: 1px solid #d9dfeb;
  display: flex;
  gap: 0.5rem;
  padding: 0.85rem 1.25rem;
  position: sticky;
  top: 0;
  z-index: 1;
}

.topbar a {
  color: #032562;
  font-weight: 800;
  padding: 0.6rem 0.8rem;
  text-decoration: none;
}

.topbar a.router-link-active {
  background: #032562;
  color: #fff;
}

@media (max-width: 760px) {
  .shell {
    grid-template-columns: 1fr;
  }

  .sidebar {
    gap: 0.75rem;
    height: auto;
    position: static;
  }

  .logout {
    margin-top: 0;
  }
}
</style>
