<script setup lang="ts">
import Biblioteca from '../components/Biblioteca.vue'

// En pantallas estrechas la biblioteca de la barra lateral vive en su propia vista.
</script>

<template>
  <section class="vista-biblioteca" aria-label="Biblioteca">
    <Biblioteca />
  </section>
</template>

<style scoped>
.vista-biblioteca {
  padding: var(--space-4);
}
</style>
