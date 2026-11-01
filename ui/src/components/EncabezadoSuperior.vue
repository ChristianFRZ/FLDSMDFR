<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useSession } from '../composables/useSession'
import { iniciales } from '../composables/texto'
import Icono from './icons/Icono.vue'

const router = useRouter()
const { user, isAdmin, logout } = useSession()

const consulta = ref('')
const campo = ref<HTMLInputElement | null>(null)
const menuAbierto = ref(false)
const esMac = typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.platform)

const rol = computed(() => (isAdmin.value ? 'Administrador' : 'Oyente'))
const avatar = computed(() => iniciales(user.value?.name ?? ''))

function buscar(): void {
  const q = consulta.value.trim()
  void router.push({ name: 'catalogo', query: q ? { q } : {} })
}

function alTeclear(evento: KeyboardEvent): void {
  if ((evento.ctrlKey || evento.metaKey) && evento.key.toLowerCase() === 'k') {
    evento.preventDefault()
    campo.value?.focus()
    campo.value?.select()
  }
  if (evento.key === 'Escape') menuAbierto.value = false
}

function cerrarMenuFuera(evento: MouseEvent): void {
  if (!(evento.target as HTMLElement).closest('.encabezado__cuenta')) menuAbierto.value = false
}

onMounted(() => {
  document.addEventListener('keydown', alTeclear)
  document.addEventListener('click', cerrarMenuFuera)
})
onBeforeUnmount(() => {
  document.removeEventListener('keydown', alTeclear)
  document.removeEventListener('click', cerrarMenuFuera)
})
</script>

<template>
  <header class="encabezado">
    <div class="encabezado__historial">
      <button type="button" class="boton-icono" aria-label="Atrás" @click="router.back()">
        <Icono nombre="chevron-left" :tam="19" />
      </button>
      <button type="button" class="boton-icono" aria-label="Adelante" @click="router.forward()">
        <Icono nombre="chevron-right" :tam="19" />
      </button>
    </div>

    <form class="encabezado__busqueda busqueda-pildora" role="search" @submit.prevent="buscar">
      <Icono nombre="search" :tam="18" />
      <label for="busqueda-global" class="visualmente-oculto">Buscar música</label>
      <input
        id="busqueda-global"
        ref="campo"
        v-model="consulta"
        type="search"
        placeholder="¿Qué te apetece escuchar?"
        autocomplete="off"
      />
      <kbd class="encabezado__atajo">{{ esMac ? '⌘K' : 'Ctrl K' }}</kbd>
    </form>

    <div class="encabezado__cuenta">
      <span
        class="encabezado__plus"
        data-prueba="plus"
        role="note"
        aria-disabled="true"
        title="Próximamente"
      >
        Plus
      </span>
      <span class="encabezado__rol">{{ rol }}</span>
      <slot name="campana" />
      <div class="encabezado__perfil">
        <button
          type="button"
          class="encabezado__avatar"
          :aria-label="`Cuenta de ${user?.name ?? ''}`"
          aria-haspopup="menu"
          :aria-expanded="menuAbierto"
          @click="menuAbierto = !menuAbierto"
        >
          {{ avatar }}
        </button>
        <ul v-if="menuAbierto" class="encabezado__menu" role="menu">
          <li role="none">
            <p class="encabezado__nombre">{{ user?.name }}</p>
          </li>
          <li role="none">
            <button type="button" role="menuitem" class="boton-texto" @click="logout">
              <Icono nombre="log-out" :tam="16" />
              Cerrar sesión
            </button>
          </li>
        </ul>
      </div>
    </div>
  </header>
</template>

<style scoped>
.encabezado {
  display: flex;
  align-items: center;
  gap: 22px;
  height: var(--header-height);
  padding: 0 var(--space-6);
  border-bottom: 1px solid var(--rule);
}

.encabezado__historial {
  display: flex;
  gap: var(--space-1);
}

.encabezado__busqueda {
  flex: 0 1 480px;
  min-width: 0;
}

.encabezado__atajo {
  font-family: inherit;
  font-size: 10px;
  color: var(--ink-muted);
}

.encabezado__cuenta {
  display: flex;
  flex: 1;
  align-items: center;
  justify-content: flex-end;
  gap: 22px;
}

.encabezado__rol,
.encabezado__plus {
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
}

.encabezado__plus {
  padding: 3px 8px;
  border: 1px solid var(--surface);
  border-radius: var(--radius-pill);
}

.encabezado__perfil {
  position: relative;
}

.encabezado__avatar {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border: 0;
  border-radius: var(--radius-pill);
  background: var(--surface-active);
  color: var(--ink-on-active);
  font-size: 12px;
  font-weight: 600;
}

.encabezado__menu {
  position: absolute;
  right: 0;
  top: calc(100% + var(--space-2));
  z-index: 20;
  display: grid;
  gap: var(--space-1);
  min-width: 200px;
  margin: 0;
  padding: var(--space-3);
  list-style: none;
  border: 1px solid var(--surface);
  border-radius: var(--radius-l);
  background: var(--bg);
}

.encabezado__nombre {
  padding: 0 var(--space-1) var(--space-2);
  color: var(--ink-muted);
}

@media (max-width: 899px) {
  .encabezado {
    gap: var(--space-3);
    padding: 0 var(--space-4);
    height: 64px;
  }

  .encabezado__historial,
  .encabezado__atajo,
  .encabezado__rol,
  .encabezado__plus {
    display: none;
  }

  .encabezado__busqueda {
    flex: 1;
  }

  .encabezado__cuenta {
    flex: none;
    gap: var(--space-3);
  }
}
</style>
