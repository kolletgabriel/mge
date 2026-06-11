<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import { login, register } from '@/auth'
import PasswordToggle from '@/components/PasswordToggle.vue'

const router = useRouter()

const loginMail = ref('')
const loginPassword = ref('')
const loginError = ref('')
const loginLoading = ref(false)
const showLoginPassword = ref(false)

const registerName = ref('')
const registerMail = ref('')
const registerPassword = ref('')
const registerPasswordConfirmation = ref('')
const registerError = ref('')
const registerLoading = ref(false)
const showRegisterPassword = ref(false)
const showRegisterPasswordConfirmation = ref(false)

type RegistrationErrors = {
  name?: string
  mail?: string
  password?: string
  passwordConfirmation?: string
}

const registerErrors = ref<RegistrationErrors>({})
const emailPattern = /^[^@\s]+@[^@\s]+\.[^@\s]+$/

function validateRegistration(): boolean {
  const errors: RegistrationErrors = {}
  const name = registerName.value.trim()
  const mail = registerMail.value.trim()
  const password = registerPassword.value

  if (name.length === 0) {
    errors.name = 'Informe seu nome.'
  } else if (name.length > 100) {
    errors.name = 'Nome muito longo.'
  }

  if (!emailPattern.test(mail)) {
    errors.mail = 'Endereço de e-mail inválido.'
  } else if (mail.length > 320) {
    errors.mail = 'E-mail muito longo.'
  }

  if (password.length < 8) {
    errors.password = 'Senha muito curta.'
  } else if (password.length > 128) {
    errors.password = 'Senha muito longa.'
  }

  if (registerPasswordConfirmation.value !== password) {
    errors.passwordConfirmation = 'As senhas não conferem.'
  }

  registerErrors.value = errors

  return Object.keys(errors).length === 0
}

async function submitLogin(): Promise<void> {
  loginLoading.value = true
  loginError.value = ''

  try {
    await login({ mail: loginMail.value, password: loginPassword.value })
    await router.push({ name: 'home' })
  } catch (error) {
    loginError.value = error instanceof Error ? error.message : 'Não foi possível entrar.'
  } finally {
    loginLoading.value = false
  }
}

async function submitRegistration(): Promise<void> {
  if (!validateRegistration()) {
    registerError.value = 'Revise os campos destacados.'
    return
  }

  registerLoading.value = true
  registerError.value = ''

  try {
    await register({
      mail: registerMail.value.trim(),
      name: registerName.value.trim(),
      password: registerPassword.value,
    })
    await router.push({ name: 'home' })
  } catch (error) {
    registerError.value = error instanceof Error ? error.message : 'Não foi possível criar a conta.'
  } finally {
    registerLoading.value = false
  }
}
</script>

<template>
  <main class="auth-page">
    <section class="auth-intro" aria-labelledby="auth-title">
      <p class="eyebrow">MGE</p>
      <p class="subtitle">Monitorias e Grupos de Estudo</p>
      <h1 id="auth-title">Bem-vindo.</h1>
    </section>

    <section class="forms" aria-label="Autenticação">
      <form class="panel" novalidate @submit.prevent="submitLogin">
        <h2>Entrar</h2>
        <label>
          E-mail
          <input
            v-model="loginMail"
            autocomplete="email"
            name="login-mail"
            required
            type="email"
          >
        </label>
        <label>
          Senha
          <span class="password-control">
            <input
              v-model="loginPassword"
              autocomplete="current-password"
              name="login-password"
              required
              :type="showLoginPassword ? 'text' : 'password'"
            >
            <PasswordToggle
              :shown="showLoginPassword"
              @toggle="showLoginPassword = !showLoginPassword"
            />
          </span>
        </label>
        <p v-if="loginError" class="message" role="alert">{{ loginError }}</p>
        <button type="submit" :disabled="loginLoading">
          {{ loginLoading ? 'Entrando...' : 'Entrar' }}
        </button>
      </form>

      <form class="panel" novalidate @submit.prevent="submitRegistration">
        <h2>Criar conta</h2>
        <label>
          Nome
          <input
            v-model="registerName"
            autocomplete="name"
            maxlength="100"
            name="register-name"
            required
            type="text"
            :aria-invalid="Boolean(registerErrors.name)"
          >
          <span v-if="registerErrors.name" class="field-error">{{ registerErrors.name }}</span>
        </label>
        <label>
          E-mail
          <input
            v-model="registerMail"
            autocomplete="email"
            maxlength="320"
            name="register-mail"
            required
            type="email"
            :aria-invalid="Boolean(registerErrors.mail)"
          >
          <span v-if="registerErrors.mail" class="field-error">{{ registerErrors.mail }}</span>
        </label>
        <label>
          <span class="label-row">
            Senha
            <small>Mínimo de 8 caracteres</small>
          </span>
          <span class="password-control">
            <input
              v-model="registerPassword"
              autocomplete="new-password"
              maxlength="128"
              minlength="8"
              name="register-password"
              required
              :type="showRegisterPassword ? 'text' : 'password'"
              :aria-invalid="Boolean(registerErrors.password)"
            >
            <PasswordToggle
              :shown="showRegisterPassword"
              @toggle="showRegisterPassword = !showRegisterPassword"
            />
          </span>
          <span v-if="registerErrors.password" class="field-error">{{ registerErrors.password }}</span>
        </label>
        <label>
          Confirmar senha
          <span class="password-control">
            <input
              v-model="registerPasswordConfirmation"
              autocomplete="new-password"
              maxlength="128"
              minlength="8"
              name="register-password-confirmation"
              required
              :type="showRegisterPasswordConfirmation ? 'text' : 'password'"
              :aria-invalid="Boolean(registerErrors.passwordConfirmation)"
            >
            <PasswordToggle
              :shown="showRegisterPasswordConfirmation"
              @toggle="showRegisterPasswordConfirmation = !showRegisterPasswordConfirmation"
            />
          </span>
          <span v-if="registerErrors.passwordConfirmation" class="field-error">
            {{ registerErrors.passwordConfirmation }}
          </span>
        </label>
        <p v-if="registerError" class="message" role="alert">{{ registerError }}</p>
        <button type="submit" :disabled="registerLoading">
          {{ registerLoading ? 'Criando...' : 'Criar conta' }}
        </button>
      </form>
    </section>
  </main>
</template>

<style scoped>
.auth-page {
  align-items: center;
  background: #032562;
  color: #fff;
  display: grid;
  gap: 3rem;
  grid-template-columns: minmax(0, 0.9fr) minmax(22rem, 1.1fr);
  min-height: 100vh;
  padding: 3rem clamp(1rem, 5vw, 5rem);
}

.auth-intro {
  max-width: 32rem;
}

.eyebrow {
  font-size: 0.85rem;
  font-weight: 700;
  letter-spacing: 0.16em;
  margin: 0 0 0.45rem;
}

.subtitle {
  color: rgb(255 255 255 / 0.78);
  font-style: italic;
  margin: 0 0 1.4rem;
}

h1 {
  font-size: clamp(2rem, 4vw, 4rem);
  line-height: 1;
  margin: 0;
}

.forms {
  display: grid;
  gap: 1rem;
}

.panel {
  background: #fff;
  border: 1px solid rgb(3 37 98 / 0.12);
  color: #10213d;
  display: grid;
  gap: 1rem;
  padding: 1.4rem;
}

h2 {
  color: #032562;
  margin: 0;
}

label {
  display: grid;
  font-size: 0.9rem;
  font-weight: 700;
  gap: 0.35rem;
}

input {
  border: 1px solid #b7c0cf;
  font: inherit;
  padding: 0.75rem;
  width: 100%;
}

input:focus {
  outline: 3px solid rgb(3 37 98 / 0.2);
  outline-offset: 1px;
}

input[aria-invalid="true"] {
  border-color: #8b1e1e;
}

.label-row {
  align-items: baseline;
  display: flex;
  gap: 0.75rem;
  justify-content: space-between;
}

.label-row small {
  color: #526276;
  font-weight: 500;
}

.field-error {
  color: #8b1e1e;
  font-size: 0.85rem;
  font-weight: 600;
}

.password-control {
  display: block;
  position: relative;
}

.password-control input {
  padding-right: 2.8rem;
}

.password-control :deep(.password-toggle) {
  position: absolute;
  right: 0.35rem;
  top: 50%;
  transform: translateY(-50%);
}

button {
  background: #032562;
  border: 0;
  color: #fff;
  cursor: pointer;
  font: inherit;
  font-weight: 700;
  padding: 0.8rem 1rem;
}

button:disabled {
  cursor: wait;
  opacity: 0.7;
}

.message {
  background: #fff0f0;
  color: #8b1e1e;
  margin: 0;
  padding: 0.75rem;
}

@media (max-width: 840px) {
  .auth-page {
    align-items: stretch;
    grid-template-columns: 1fr;
    padding-block: 2rem;
  }
}
</style>
