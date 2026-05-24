import { APP_LOGO_ALT, APP_LOGO_SRC } from '../config/branding'

function cn(...parts) {
  return parts.filter(Boolean).join(' ')
}

const sizeClasses = {
  sm: 'h-9 max-h-9',
  md: 'h-14 max-h-14 sm:h-16',
  lg: 'h-20 max-h-20 sm:h-24',
  xl: 'h-28 max-h-28 sm:h-32',
}

/**
 * Application logo. Uses the bundled /logo.png (from Karwan e Mohabbat) with
 * optional VITE_APP_LOGO_URL override; falls back to the official remote URL.
 */
export default function AppLogo({ size = 'md', className = '', centered = true }) {
  const src = APP_LOGO_SRC

  return (
    <img
      src={src}
      alt={APP_LOGO_ALT}
      width={320}
      height={120}
      decoding="async"
      className={cn(
        'w-auto object-contain',
        sizeClasses[size] || sizeClasses.md,
        centered && 'mx-auto',
        className,
      )}
    />
  )
}
