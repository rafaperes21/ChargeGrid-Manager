import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  // Porta fixa (cliente 5173, proprietario 5174): sem isso o Vite pegava a primeira livre e os
  // portais trocavam de porta entre execucoes do dev.sh - e como o navegador guarda o login por
  // porta, um portal herdava o login do outro. strictPort: falha com erro claro em vez de pular.
  server: { port: 5174, strictPort: true },
})
