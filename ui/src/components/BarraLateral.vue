<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { useSession } from '../composables/useSession'
import LogoMeloxo from './LogoMeloxo.vue'
import TarjetaCabina from './TarjetaCabina.vue'
import Icono from './icons/Icono.vue'
import type { NombreIcono } from './icons/iconos'

const { isAdmin } = useSession()

const DESTINOS: ReadonlyArray<{ to: string; texto: string; icono: NombreIcono; exacto: boolean }> = [
  { to: '/', texto: 'Página de inicio', icono: 'house', exacto: true },
  { to: '/catalogo', texto: 'Catálogo', icono: 'compass', exacto: false },
  { to: '/streaming', texto: 'Streaming', icono: 'radio', exacto: false },
]
</script>

<template>
  <div class="lateral">
    <RouterLink to="/" class="lateral__marca" aria-label="MELOXO, ir a la página de inicio">
      <LogoMeloxo />
    </RouterLink>

    <nav aria-label="Principal">
      <ul class="lateral__nav">
        <li v-for="d in DESTINOS" :key="d.to">
          <RouterLink
            v-slot="{ href, navigate, isActive, isExactActive }"
            :to="d.to"
            custom
          >
            <a
              :href="href"
              class="lateral__destino"
              :class="{ 'lateral__destino--activo': d.exacto ? isExactActive : isActive }"
              :aria-current="(d.exacto ? isExactActive : isActive) ? 'page' : undefined"
              @click="navigate"
            >
              <Icono :nombre="d.icono" :tam="20" />
              <span class="lateral__texto">{{ d.texto }}</span>
              <span
                v-if="d.exacto ? isExactActive : isActive"
                class="lateral__punto"
                aria-hidden="true"
              />
            </a>
          </RouterLink>
        </li>
      </ul>
    </nav>

    <hr class="lateral__separador" />

    <div class="lateral__biblioteca">
      <slot name="biblioteca" />
    </div>

    <TarjetaCabina v-if="isAdmin" />
  </div>
</template>

<style scoped>
.lateral {
  display: flex;
  flex-direction: column;
  gap: 26px;
  height: 100%;
  padding: 30px var(--space-4) var(--space-5);
  border-right: 1px solid var(--rule);
  overflow-y: auto;
}

.lateral__marca {
  display: flex;
  align-items: center;
  padding: 0 var(--space-3);
  min-height: 31px;
  border: 1px solid var(--rule);
  border-radius: var(--radius-l);
  text-decoration: none;
}

.lateral__nav {
  display: grid;
  gap: 5px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.lateral__destino {
  display: flex;
  align-items: center;
  gap: 13px;
  min-height: 44px;
  padding: 0 14px;
  border-radius: var(--radius-m);
  color: var(--ink);
  font-size: 14px;
  text-decoration: none;
}

.lateral__destino--activo {
  background: var(--surface-active);
  color: var(--ink-on-active);
  font-weight: 600;
}

@media (hover: hover) {
  .lateral__destino:not(.lateral__destino--activo):hover {
    background: color-mix(in srgb, var(--surface) 45%, transparent);
  }
}

.lateral__texto {
  flex: 1;
}

.lateral__punto {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: currentColor;
}

.lateral__separador {
  width: 100%;
  margin: 0;
  border: 0;
  border-top: 1px solid var(--rule);
}

.lateral__biblioteca {
  flex: 1;
  min-height: 0;
}
</style>
