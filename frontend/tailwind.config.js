import colors from 'tailwindcss/colors'

export default {
  content: ['./index.html', './src/**/*.{vue,js,ts}'],
  theme: {
    extend: {
      colors: {
        maple: {
          50: '#FFF8F0', 100: '#FFEAD5', 200: '#FFD4A8',
          300: '#FFB875', 400: '#F5A623', 500: '#E88A1E',
          600: '#C73B1D', 700: '#A32E16', 800: '#7A2210',
          900: '#52160B',
        },
        error: colors.red,
        success: colors.green,
        text: { primary: '#2D2D2D', secondary: '#8C8C8C' },
        border: '#E8DDD4',
      },
      fontFamily: {
        sans: ['"Noto Sans SC"', '"PingFang SC"', '"Microsoft YaHei"', 'sans-serif'],
      },
      fontSize: {
        'aux': ['13px', { lineHeight: '1.5' }],
        'tag': ['12px', { lineHeight: '1.4', fontWeight: '500' }],
      },
      borderRadius: {
        'xl': '12px',
        '2xl': '16px',
      },
      boxShadow: {
        'card': '0 2px 8px rgba(0, 0, 0, 0.06)',
        'float': '0 2px 12px rgba(0, 0, 0, 0.08)',
        'modal': '0 8px 32px rgba(0, 0, 0, 0.12)',
      },
      keyframes: {
        'fade-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        'fade-out': {
          '0%': { opacity: '1' },
          '100%': { opacity: '0' },
        },
        'slide-in-bottom': {
          '0%': { opacity: '0', transform: 'translateY(100%)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'slide-out-bottom': {
          '0%': { opacity: '1', transform: 'translateY(0)' },
          '100%': { opacity: '0', transform: 'translateY(100%)' },
        },
        'dialog-in': {
          '0%': { opacity: '0', transform: 'scale(0.95)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
        'dialog-out': {
          '0%': { opacity: '1', transform: 'scale(1)' },
          '100%': { opacity: '0', transform: 'scale(0.95)' },
        },
        'slide-up': {
          '0%': { opacity: '0', transform: 'translateY(12px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'slide-in-right': {
          '0%': { opacity: '0', transform: 'translateX(100%)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
        'scale-in': {
          '0%': { opacity: '0', transform: 'scale(0.95)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
        'pulse-soft': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.5' },
        },
        'stagger-fade-in': {
          '0%': { opacity: '0', transform: 'translateY(16px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'card-lift': {
          '0%': { transform: 'translateY(0)', boxShadow: '0 2px 8px rgba(0, 0, 0, 0.06)' },
          '100%': { transform: 'translateY(-4px)', boxShadow: '0 8px 24px rgba(0, 0, 0, 0.10)' },
        },
        'like-pop': {
          '0%': { transform: 'scale(1)' },
          '40%': { transform: 'scale(1.3)' },
          '100%': { transform: 'scale(1)' },
        },
        'image-zoom': {
          '0%': { transform: 'scale(1)' },
          '100%': { transform: 'scale(1.05)' },
        },
      },
      animation: {
        'fade-in': 'fade-in 0.3s ease-out',
        'fade-out': 'fade-out 0.2s ease-out forwards',
        'slide-in-bottom': 'slide-in-bottom 0.25s ease-out forwards',
        'slide-out-bottom': 'slide-out-bottom 0.2s ease-out forwards',
        'dialog-in': 'dialog-in 0.2s ease-out forwards',
        'dialog-out': 'dialog-out 0.2s ease-out forwards',
        'slide-up': 'slide-up 0.3s ease-out',
        'slide-in-right': 'slide-in-right 0.3s ease-out',
        'scale-in': 'scale-in 0.2s ease-out',
        'pulse-soft': 'pulse-soft 2s ease-in-out infinite',
        'stagger-fade-in': 'stagger-fade-in 0.4s ease-out both',
        'card-lift': 'card-lift 0.25s ease-out forwards',
        'like-pop': 'like-pop 0.35s ease-out',
        'image-zoom': 'image-zoom 0.3s ease-out forwards',
      },
    },
  },
}
