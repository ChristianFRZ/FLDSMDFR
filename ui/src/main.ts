import '@fontsource-variable/fraunces/full.css'
import '@fontsource-variable/figtree'
import '@fontsource-variable/caveat'
import './styles/tokens.css'
import './styles/base.css'

import { createApp } from 'vue'
import App from './App.vue'
import { useTheme } from './composables/useTheme'
import { router } from './router'

// Fija data-lado en <html> antes del primer render para evitar un parpadeo de tema.
useTheme()

createApp(App).use(router).mount('#app')
