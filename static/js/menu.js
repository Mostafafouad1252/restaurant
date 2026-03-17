(function () {
  document.querySelectorAll('.add-to-cart').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var id = parseInt(btn.getAttribute('data-meal-id'), 10);
      if (!id) return;
      btn.disabled = true;
      btn.textContent = 'Adding…';
      fetch('/api/cart/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
        body: JSON.stringify({ meal_id: id, quantity: 1 })
      })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data.success) {
            btn.textContent = 'Added ✓';
            if (typeof document.dispatchEvent === 'function') {
              document.dispatchEvent(new CustomEvent('cartUpdated'));
            }
          } else {
            btn.textContent = 'Add to Cart';
          }
        })
        .catch(function () { btn.textContent = 'Add to Cart'; })
        .finally(function () { btn.disabled = false; });
    });
  });
})();
