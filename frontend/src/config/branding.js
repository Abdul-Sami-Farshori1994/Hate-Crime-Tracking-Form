/** Official logo source (also saved under frontend/public/logo.png). */
export const APP_LOGO_URL =
  'https://karwanemohabbat.in/wp-content/uploads/2020/05/Logo.png'

/** Logo shown in the UI (bundled file; override with VITE_APP_LOGO_URL). */
export const APP_LOGO_SRC = import.meta.env.VITE_APP_LOGO_URL?.trim() || '/logo.png'

export const APP_LOGO_ALT = 'Karwan e Mohabbat'

export const APP_TITLE = 'Hate Crime Tracking'
