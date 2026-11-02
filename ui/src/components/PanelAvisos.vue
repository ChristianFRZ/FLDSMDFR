<script setup lang="ts">
import type { NotificationOut } from '../api/types'
import { useNotificaciones } from '../composables/useNotificaciones'
import { usePlayer } from '../composables/usePlayer'
import TarjetaAviso from './TarjetaAviso.vue'

// Lista de avisos dentro del popover de la campana.
const { items, aceptar, ignorar } = useNotificaciones()
const player = usePlayer()

function escuchar(aviso: NotificationOut): void {
  if (aviso.song) void player.play(aviso.song)
}
</script>

<template>
  <div class="panel-avisos">
    <p class="antetitulo">AVISOS</p>
    <p v-if="items.length === 0" class="texto-secundario">
      No tienes avisos. Sigue artistas desde el catálogo para enterarte de sus lanzamientos.
    </p>
    <ul v-else class="panel-avisos__lista">
      <li v-for="aviso in items" :key="aviso.id">
        <TarjetaAviso
          :aviso="aviso"
          @escuchar="escuchar(aviso)"
          @aceptar="aviso.invite && aceptar(aviso.invite.token)"
          @ignorar="aviso.invite && ignorar(aviso.invite.token)"
        />
      </li>
    </ul>
  </div>
</template>

<style scoped>
.panel-avisos {
  display: grid;
  gap: var(--space-3);
}

.panel-avisos__lista {
  display: grid;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}
</style>
