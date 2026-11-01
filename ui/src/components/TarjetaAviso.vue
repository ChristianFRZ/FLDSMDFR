<script setup lang="ts">
import { computed } from 'vue'
import type { NotificationOut } from '../api/types'
import { iniciales, tiempoRelativo } from '../composables/texto'
import Icono from './icons/Icono.vue'

// Tarjeta de aviso: lanzamiento de un artista seguido o invitación a un casete (DESIGN.md §7.6).
const props = defineProps<{ aviso: NotificationOut }>()
const emit = defineEmits<{ escuchar: []; aceptar: []; ignorar: [] }>()

const hace = computed(() => tiempoRelativo(props.aviso.created_at))
</script>

<template>
  <article class="aviso-tarjeta tarjeta" :class="{ 'aviso-tarjeta--nuevo': !aviso.read }">
    <template v-if="aviso.type === 'release' && aviso.song">
      <header class="aviso-tarjeta__cabecera">
        <span class="aviso-tarjeta__marca"><Icono nombre="audio-lines" :tam="14" /></span>
        <span class="antetitulo">NUEVO LANZAMIENTO</span>
        <span class="texto-secundario aviso-tarjeta__hace">{{ hace }}</span>
      </header>
      <p class="aviso-tarjeta__titulo">{{ aviso.song.artist }} · «{{ aviso.song.title }}»</p>
      <p class="texto-secundario">Un artista que sigues publicó una canción nueva.</p>
      <div class="aviso-tarjeta__acciones">
        <button type="button" class="boton-texto" @click="emit('escuchar')">
          Escuchar ahora <Icono nombre="arrow-right" :tam="14" />
        </button>
      </div>
    </template>

    <template v-else-if="aviso.type === 'invite' && aviso.invite">
      <header class="aviso-tarjeta__cabecera">
        <span class="aviso-tarjeta__marca">{{ iniciales(aviso.invite.inviter_name) }}</span>
        <span class="antetitulo">INVITACIÓN A CASETE</span>
        <span class="texto-secundario aviso-tarjeta__hace">{{ hace }}</span>
      </header>
      <p class="aviso-tarjeta__titulo">
        «{{ aviso.invite.playlist_name }}» · de {{ aviso.invite.inviter_name }}
      </p>
      <p class="texto-secundario">Te invitaron a grabar canciones en este casete.</p>
      <div class="aviso-tarjeta__acciones">
        <button type="button" class="boton-principal" @click="emit('aceptar')">Aceptar</button>
        <button type="button" class="boton-texto boton-texto--secundario" @click="emit('ignorar')">
          Ignorar
        </button>
      </div>
    </template>
  </article>
</template>

<style scoped>
.aviso-tarjeta {
  display: grid;
  gap: var(--space-2);
}

.aviso-tarjeta--nuevo {
  border-color: var(--accent);
}

.aviso-tarjeta__cabecera {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.aviso-tarjeta__marca {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--surface-active);
  color: var(--ink-on-active);
  font-size: 10px;
  font-weight: 700;
}

.aviso-tarjeta__hace {
  margin-left: auto;
  font-size: 11px;
}

.aviso-tarjeta__titulo {
  font-weight: 600;
}

.aviso-tarjeta__acciones {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
</style>
