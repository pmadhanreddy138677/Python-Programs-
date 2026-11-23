/** Tailwind (v3) build config. Rebuild with:  tailwindcss -c tailwind.config.js -i static/src/tailwind.input.css -o static/css/tailwind.css --minify */
module.exports = {
  darkMode: 'class',
  content: ['./templates/**/*.html', './static/js/**/*.js', './apps/**/*.py'],
  theme: { extend: {} },
  plugins: [],
};
