JS = """
try {
  new ResizeObserver(() => {}).observe(document.body);
} catch (e) {}
window.addEventListener("error", function(e) {
  if (e && e.message && e.message.indexOf('ResizeObserver loop limit exceeded') > -1)
    e.preventDefault();
}, true);
"""
