(function () {
  function loadCart() {
    fetch('/api/cart')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var loading = document.getElementById('cartLoading');
        var content = document.getElementById('cartContent');
        var empty = document.getElementById('cartEmpty');
        var list = document.getElementById('cartItems');
        var totalEl = document.getElementById('cartTotal');
        var checkoutBtn = document.getElementById('checkoutBtn');
        if (loading) loading.classList.add('hidden');
        if (!data.items || data.items.length === 0) {
          if (content) content.classList.add('hidden');
          if (empty) empty.classList.remove('hidden');
          return;
        }
        if (empty) empty.classList.add('hidden');
        if (content) content.classList.remove('hidden');
        list.innerHTML = data.items.map(function (item) {
          return (
            '<li class="p-4 flex flex-wrap items-center gap-4">' +
            '  <img src="' + (item.image_url || '/static/images/meals/default.svg') + '" alt="" class="w-16 h-16 object-cover rounded">' +
            '  <div class="flex-1 min-w-0">' +
            '    <p class="font-medium" style="font-size: 1.0625rem;">' + (item.name || '') + '</p>' +
            '    <p class="text-stone-500" style="font-size: 1rem;">$' + (item.price ? item.price.toFixed(2) : '0.00') + ' each</p>' +
            '  </div>' +
            '  <div class="flex items-center gap-2">' +
            '    <button type="button" class="cart-qty-minus px-2 py-1 rounded border border-stone-300 dark:border-stone-600" data-meal-id="' + item.meal_id + '">−</button>' +
            '    <span class="cart-qty w-8 text-center">' + (item.quantity || 0) + '</span>' +
            '    <button type="button" class="cart-qty-plus px-2 py-1 rounded border border-stone-300 dark:border-stone-600" data-meal-id="' + item.meal_id + '">+</button>' +
            '  </div>' +
            '  <p class="font-semibold w-20 text-right" style="font-size: 1rem;">$' + (item.subtotal ? item.subtotal.toFixed(2) : '0.00') + '</p>' +
            '  <button type="button" class="cart-remove text-red-600 dark:text-red-400" style="font-size: 1rem;" data-meal-id="' + item.meal_id + '">Remove</button>' +
            '</li>'
          );
        }).join('');
        if (totalEl) totalEl.textContent = '$' + (data.total != null ? data.total.toFixed(2) : '0.00');
        if (checkoutBtn) checkoutBtn.classList.remove('hidden');
        bindCartButtons();
      })
      .catch(function () {
        var loading = document.getElementById('cartLoading');
        if (loading) { loading.classList.add('hidden'); loading.textContent = 'Failed to load cart.'; }
      });
  }
  function bindCartButtons() {
    document.querySelectorAll('.cart-qty-minus').forEach(function (btn) {
      btn.onclick = function () {
        var id = parseInt(btn.getAttribute('data-meal-id'), 10);
        var qtyEl = btn.closest('li').querySelector('.cart-qty');
        var qty = parseInt(qtyEl.textContent, 10) || 1;
        if (qty <= 1) return;
        fetch('/api/cart/update', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ meal_id: id, quantity: qty - 1 })
        }).then(function () { loadCart(); document.dispatchEvent(new CustomEvent('cartUpdated')); });
      };
    });
    document.querySelectorAll('.cart-qty-plus').forEach(function (btn) {
      btn.onclick = function () {
        var id = parseInt(btn.getAttribute('data-meal-id'), 10);
        var qtyEl = btn.closest('li').querySelector('.cart-qty');
        var qty = (parseInt(qtyEl.textContent, 10) || 0) + 1;
        fetch('/api/cart/update', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ meal_id: id, quantity: qty })
        }).then(function () { loadCart(); document.dispatchEvent(new CustomEvent('cartUpdated')); });
      };
    });
    document.querySelectorAll('.cart-remove').forEach(function (btn) {
      btn.onclick = function () {
        var id = parseInt(btn.getAttribute('data-meal-id'), 10);
        fetch('/api/cart/remove', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ meal_id: id })
        }).then(function () { loadCart(); document.dispatchEvent(new CustomEvent('cartUpdated')); });
      };
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', loadCart);
  else loadCart();
})();
