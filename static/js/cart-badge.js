(function () {
  function updateCartBadge() {
    fetch('/api/cart')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById('cartCount');
        if (!el) return;
        var count = data.count || 0;
        el.textContent = count;
        if (count > 0) el.classList.remove('hidden');
        else el.classList.add('hidden');
      })
      .catch(function () {});
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', updateCartBadge);
  } else {
    updateCartBadge();
  }
  document.addEventListener('cartUpdated', updateCartBadge);
})();
