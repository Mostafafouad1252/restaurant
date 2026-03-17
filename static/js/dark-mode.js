(function () {
  const key = 'darkMode';
  const root = document.documentElement;
  function setDark(isDark) {
    if (isDark) {
      root.classList.add('dark');
      localStorage.setItem(key, '1');
    } else {
      root.classList.remove('dark');
      localStorage.setItem(key, '0');
    }
  }
  const stored = localStorage.getItem(key);
  if (stored === '1' || (!stored && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
    setDark(true);
  } else {
    setDark(false);
  }
  document.getElementById('darkToggle')?.addEventListener('click', function () {
    setDark(!root.classList.contains('dark'));
  });
})();
