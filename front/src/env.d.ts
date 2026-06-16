/// <reference types="vite/client" />

import 'vue-router'

declare module '*.vue' {
  import type { DefineComponent } from 'vue'

  const component: DefineComponent<object, object, unknown>
  export default component
}

declare module 'vue-router' {
  interface RouteMeta {
    requiresAuth?: boolean
    guestOnly?: boolean
    requiresDashboardAccess?: boolean
    requiresAdmin?: boolean
  }
}
